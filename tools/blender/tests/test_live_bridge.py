import json
import os
import socket
import subprocess
import sys
import threading
import unittest
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

from live_bridge.client import BridgeClient, BridgeError
from live_bridge.protocol import MAX_MESSAGE_BYTES, ProtocolError, decode_message, encode_message, validate_request


class ProtocolTests(unittest.TestCase):
    def test_round_trip_and_request_validation(self):
        request = {"id": 7, "method": "status", "params": {}, "token": "secret", "timestamp": time.time()}
        self.assertEqual(decode_message(encode_message(request)), request)
        validated = validate_request(request)
        self.assertEqual(validated[:4], (7, "status", {}, "secret"))

    def test_rejects_non_object_and_missing_authentication(self):
        with self.assertRaises(ProtocolError):
            decode_message(b"[]")
        with self.assertRaisesRegex(ProtocolError, "token"):
            validate_request({"id": 1, "method": "status", "timestamp": time.time()})

    def test_rejects_version_unknown_fields_stale_time_and_nonfinite_ids(self):
        base = {"id": "request", "version": 1, "method": "status", "params": {},
                "token": "secret", "timestamp": time.time()}
        for changed, message in (({"version": 2}, "version"), ({"surprise": True}, "unknown"),
                                 ({"timestamp": time.time() - 301}, "timestamp"),
                                 ({"id": float("inf")}, "finite")):
            with self.subTest(changed=changed), self.assertRaisesRegex(ProtocolError, message):
                validate_request({**base, **changed})

    def test_message_limit_applies_to_encoding_and_decoding(self):
        with self.assertRaisesRegex(ProtocolError, "1 MiB"):
            encode_message({"payload": "x" * MAX_MESSAGE_BYTES})
        with self.assertRaisesRegex(ProtocolError, "1 MiB"):
            decode_message(b"{" + b" " * MAX_MESSAGE_BYTES + b"}")


class ClientTests(unittest.TestCase):
    def run_server(self, response):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0)); listener.listen(1)
        port = listener.getsockname()[1]
        def serve():
            with listener:
                connection, _ = listener.accept()
                with connection:
                    request = decode_message(connection.makefile("rb").readline())
                    value = response(request)
                    connection.sendall(encode_message(value))
        thread = threading.Thread(target=serve); thread.start()
        return port, thread

    def test_client_sends_token_and_returns_result(self):
        def response(request):
            self.assertEqual(request["token"], "session-secret")
            return {"id": request["id"], "ok": True, "result": {"ready": True}}
        port, thread = self.run_server(response)
        self.assertEqual(BridgeClient("session-secret", port=port).call("status"), {"ready": True})
        thread.join(2); self.assertFalse(thread.is_alive())

    def test_client_surfaces_remote_error(self):
        port, thread = self.run_server(lambda request: {
            "id": request["id"], "ok": False, "error": "PermissionError: authentication failed"})
        with self.assertRaisesRegex(BridgeError, "authentication failed"):
            BridgeClient("wrong-token", port=port).call("status")
        thread.join(2)

    def test_client_timeout_is_bounded(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0)); listener.listen(1)
        port = listener.getsockname()[1]

        def serve_without_reply():
            with listener:
                connection, _ = listener.accept()
                with connection:
                    connection.recv(4096)
                    time.sleep(.25)

        thread = threading.Thread(target=serve_without_reply); thread.start()
        with self.assertRaises((TimeoutError, socket.timeout)):
            BridgeClient("session-secret", port=port, timeout=.05).call("status")
        thread.join(1); self.assertFalse(thread.is_alive())


class SourceContractTests(unittest.TestCase):
    def test_server_has_no_arbitrary_execution_or_save_operation(self):
        source = (ROOT / "tools" / "blender" / "live_bridge" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn('"execute_bpy"', source)
        self.assertNotIn("save_mainfile", source)
        self.assertIn('bl_options = {"REGISTER", "UNDO"}', source)
        self.assertIn('bind(("127.0.0.1", self.port))', source)
        for forbidden in ("os.system", "subprocess.", "eval(", "exec(", "save_as_mainfile",
                          "save_mainfile", "shell=True"):
            self.assertNotIn(forbidden, source)
        self.assertIn("expectedFingerprint from inspect/share is required", source)

    def test_repo_modules_are_not_resolved_relative_to_the_installed_addon(self):
        # An installed ZIP does not sit at tools/blender/live_bridge, so a bare
        # parents[1] lookup reaches Blender's addons directory instead of the
        # repository and semantic materials fail with ImportError.
        source = (ROOT / "tools" / "blender" / "live_bridge" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("sys.path.insert(0, str(Path(__file__).resolve().parents[1]))", source)
        for module in ("material_library", "thestra_camera", "second_rite_asset_core"):
            self.assertIn(module, source)
        self.assertEqual(source.count("_use_repo_modules()"), 5)

    def test_repo_tools_blender_prefers_override_then_checkout(self):
        from live_bridge import server
        self.assertEqual(server._repo_tools_blender(), ROOT / "tools" / "blender")
        with tempfile.TemporaryDirectory() as directory:
            previous = os.environ.get("THESTRA_REPO")
            os.environ["THESTRA_REPO"] = directory
            try:
                # A THESTRA_REPO without the module must fall through to the
                # working checkout rather than raise or poison sys.path.
                self.assertEqual(server._repo_tools_blender(), ROOT / "tools" / "blender")
                (Path(directory) / "tools" / "blender").mkdir(parents=True)
                (Path(directory) / "tools" / "blender" / "material_library.py").write_text("", encoding="utf-8")
                self.assertEqual(server._repo_tools_blender(), Path(directory) / "tools" / "blender")
            finally:
                if previous is None:
                    del os.environ["THESTRA_REPO"]
                else:
                    os.environ["THESTRA_REPO"] = previous

    def test_repo_lookup_walks_past_a_nested_project_to_the_checkout(self):
        from live_bridge import server

        class FakeData:
            filepath = ""

        class FakeBpy:
            data = FakeData()

        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "checkout"
            (checkout / "tools" / "blender").mkdir(parents=True)
            (checkout / "tools" / "blender" / "material_library.py").write_text("", encoding="utf-8")
            # A project inside the checkout carries its own AGENTS.md; stopping
            # there leaves the bridge unable to import repository modules.
            document = checkout / "projects" / "game" / "assets" / "scene.blend"
            document.parent.mkdir(parents=True)
            (checkout / "projects" / "game" / "AGENTS.md").write_text("", encoding="utf-8")
            (checkout / "AGENTS.md").write_text("", encoding="utf-8")
            document.write_text("", encoding="utf-8")
            FakeData.filepath = str(document)
            # Stand the module where an installed add-on actually lives, so the
            # checkout-relative candidate cannot mask the ancestor walk.
            installed = Path(directory) / "addons" / "thestra_live_bridge"
            installed.mkdir(parents=True)
            previous_bpy, previous_env = server.bpy, os.environ.pop("THESTRA_REPO", None)
            previous_file = server.__file__
            server.bpy, server.__file__ = FakeBpy(), str(installed / "server.py")
            try:
                self.assertEqual(server._repo_tools_blender(), checkout / "tools" / "blender")
            finally:
                server.bpy, server.__file__ = previous_bpy, previous_file
                if previous_env is not None:
                    os.environ["THESTRA_REPO"] = previous_env

    def test_optional_names_never_reach_rna_lookup_directly(self):
        # bpy_prop_collection.get(None) raises an opaque SystemError, so an
        # omitted --material or --collection must be filtered before RNA.
        source = (ROOT / "tools" / "blender" / "live_bridge" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn(".get(params.get(", source)
        self.assertEqual(source.count("_named(bpy.data."), 4)

    def test_named_lookup_returns_none_for_a_missing_name(self):
        from live_bridge import server

        class Collection:
            def get(self, key):
                raise AssertionError(f"RNA lookup must not receive {key!r}")

        for absent in (None, "", 0, [], {}):
            self.assertIsNone(server._named(Collection(), absent))
        self.assertEqual(server._named({"Wall_A": "material"}, "Wall_A"), "material")

    def test_deterministic_package_contains_only_addon_files(self):
        from live_bridge.package import build
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "one.zip"; second = Path(directory) / "two.zip"
            a = build(first); b = build(second)
            self.assertEqual(a["sha256"], b["sha256"])
            with zipfile.ZipFile(first) as archive:
                names = set(archive.namelist())
                metadata = json.loads(archive.read("thestra_live_bridge/package.json"))
            self.assertEqual(names, {
                "thestra_live_bridge/__init__.py", "thestra_live_bridge/addon.py",
                "thestra_live_bridge/client.py", "thestra_live_bridge/package.json",
                "thestra_live_bridge/protocol.py", "thestra_live_bridge/README.md",
                "thestra_live_bridge/server.py",
            })
            self.assertFalse(any("data/" in name or ".blend" in name or "token" in name for name in names))
            self.assertEqual(metadata["protocolVersion"], 1)
            self.assertEqual(metadata["clientVersion"], 1)


class BlenderIntegrationTests(unittest.TestCase):
    def test_authenticated_windowed_dispatch_registers_undo_operator(self):
        import build_synthetic_environment
        blender = build_synthetic_environment.blender_executable()
        probe = ROOT / "tools" / "blender" / "tests" / "live_bridge_blender.py"
        result = subprocess.run(
            [str(blender), "--factory-startup", "--python", str(probe)],
            cwd=ROOT, text=True, capture_output=True, timeout=45)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        marker = next((line for line in output.splitlines()
                       if line.startswith("LIVE_BRIDGE_OK ")), None)
        self.assertIsNotNone(marker, output)
        report = json.loads(marker.removeprefix("LIVE_BRIDGE_OK "))
        self.assertEqual(report, {"addonRegisters": True, "authenticated": True, "bridgeVersion": 1,
                                  "captures": True, "mainThreadDispatch": True, "rollback": True,
                                  "rollbackFamilies": 6, "mutationBusyRejected": True, "saveCalls": 0,
                                  "pathTraversalRejected": True,
                                  "duplicateIdRejected": True,
                                  "stableFingerprint": True, "targetStateStaleRejected": True,
                                  "shutdownTerminal": True, "staleRejected": True,
                                  "stateRestored": True, "undoOperator": True,
                                  "geometryOffGridDetected": True,
                                  "planeRemap": True, "vertexEdits": True,
                                  "sharedMeshRejected": True,
                                  "vertexRollback": True})


if __name__ == "__main__":
    unittest.main()
