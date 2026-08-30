"""Windowed Blender integration probe for the live bridge."""

import json
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

from live_bridge.client import BridgeClient, BridgeError
from live_bridge.protocol import decode_message, encode_message
from live_bridge.server import LiveBridgeServer, register_operator, unregister_operator
import live_bridge.server as bridge_server
from live_bridge import addon


def run_request(server, callback):
    outcome = {}

    def request():
        try: outcome["value"] = callback(BridgeClient(server.token, port=server.port, timeout=10))
        except Exception as exc: outcome["error"] = exc

    thread = threading.Thread(target=request)
    thread.start(); deadline = time.monotonic() + 20
    while thread.is_alive() and time.monotonic() < deadline:
        server._drain(); time.sleep(.005)
    thread.join(.5)
    assert not thread.is_alive(), "client thread timed out"
    return outcome


def require_success(outcome):
    assert "error" not in outcome, repr(outcome.get("error"))
    return outcome["value"]


def make_scene():
    bpy.context.preferences.edit.use_global_undo = True
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    cube = bpy.context.object; cube.name = "BridgeCube"
    bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
    other = bpy.context.object; other.name = "OtherCube"
    cube.select_set(True); other.select_set(False); bpy.context.view_layer.objects.active = cube
    preview = bpy.data.collections.new("TH_CAMERA_PREVIEW"); bpy.context.scene.collection.children.link(preview)
    camera_data = bpy.data.cameras.new("BridgeCameraData")
    camera = bpy.data.objects.new("BridgeCamera", camera_data); preview.objects.link(camera)
    camera["thestra_calibration_contract"] = "thestra.world-camera-calibration"
    camera["thestra_calibration_version"] = 1
    camera.location = (5, -8, 5)
    camera.rotation_euler = (Vector((1.5, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera
    target_collection = bpy.data.collections.new("BridgeTarget")
    bpy.context.scene.collection.children.link(target_collection)
    material = bpy.data.materials.new("BridgeMaterial")
    return cube, other, camera, target_collection, material


def image_size(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    try: return tuple(int(value) for value in image.size)
    finally: bpy.data.images.remove(image)


def raw_call(server, request_id):
    request = {"id": request_id, "version": 1, "method": "status", "params": {},
               "token": server.token, "timestamp": time.time()}
    with socket.create_connection(("127.0.0.1", server.port), 10) as connection:
        connection.sendall(encode_message(request))
        return decode_message(connection.makefile("rb").readline(1024 * 1024 + 2))


def main():
    cube, other, _camera, target_collection, material = make_scene()
    fixture = ROOT / "out" / "blender-live-bridge" / "integration-source.blend"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(fixture))
    token = "integration-session-token"
    register_operator(); server = LiveBridgeServer(token, port=0); server.start()
    original_selection = [obj.name for obj in bpy.context.selected_objects]
    original_active = bpy.context.view_layer.objects.active.name

    def baseline(client):
        status = client.call("status")
        capabilities = client.call("capabilities")
        context = client.call("inspect_context")
        share = client.call("share_context")
        viewport = client.call("capture_viewport", filename="integration-viewport.png", width=320, height=180)
        selection = client.call("capture_selection", filename="integration-selection.png", width=320, height=180)
        camera_capture = client.call("capture_game_camera", filename="integration-camera.png", width=256, height=144)
        mutation = client.call("transform_objects", objects=[cube.name], location=[1.0, 2.0, 3.0],
                               expectedFingerprint=context["fingerprint"])
        try:
            client.call("transform_objects", objects=[cube.name], location=[4.0, 5.0, 6.0],
                        expectedFingerprint=context["fingerprint"])
        except BridgeError as exc: stale = str(exc)
        else: raise AssertionError("stale fingerprint was accepted")
        return {"status": status, "capabilities": capabilities, "share": share,
                "viewport": viewport, "selection": selection, "camera": camera_capture,
                "mutation": mutation, "stale": stale}

    result = require_success(run_request(server, baseline))
    assert result["capabilities"]["protocolVersion"] == 1
    assert result["capabilities"]["classifications"]["transform_objects"] == "mutation"
    assert Path(result["share"]["path"]).is_file()
    assert Path(server.latest_share["path"]).is_file()
    assert image_size(result["viewport"]["path"]) == (320, 180)
    assert image_size(result["selection"]["path"]) == (320, 180)
    assert image_size(result["camera"]["path"]) == (256, 144)
    assert result["viewport"]["sha256"] != result["selection"]["sha256"]
    assert [obj.name for obj in bpy.context.selected_objects] == original_selection
    assert bpy.context.view_layer.objects.active.name == original_active
    assert tuple(cube.location) == (1.0, 2.0, 3.0)
    assert "stale_context" in result["stale"]
    assert result["mutation"]["before"][cube.name]["location"] == [0.0, 0.0, 0.0]

    traversal = run_request(server, lambda client: client.call(
        "capture_viewport", filename="../escape.png"))
    assert isinstance(traversal.get("error"), BridgeError) and "basename" in str(traversal["error"])
    unauthenticated = run_request(server, lambda _client: BridgeClient(
        "wrong-integration-token", port=server.port, timeout=10).call("status"))
    assert isinstance(unauthenticated.get("error"), BridgeError) and "auth_failed" in str(unauthenticated["error"])
    duplicate = require_success(run_request(
        server, lambda _client: (raw_call(server, "duplicate-id"), raw_call(server, "duplicate-id"))))
    assert duplicate[0]["ok"] is True
    assert duplicate[1]["error"]["code"] == "protocol_error"

    stable_contexts = require_success(run_request(
        server, lambda client: (client.call("inspect_context"), client.call("inspect_context"))))
    assert stable_contexts[0]["fingerprint"] == stable_contexts[1]["fingerprint"]
    external_context = stable_contexts[1]
    original_vertex_x = other.data.vertices[0].co.x
    other.data.vertices[0].co.x += .125
    other.data.update()
    target_changed = run_request(server, lambda client: client.call(
        "transform_objects", objects=[cube.name], deltaLocation=[.25, 0, 0],
        expectedFingerprint=external_context["fingerprint"]))
    assert isinstance(target_changed.get("error"), BridgeError)
    assert "stale_context" in str(target_changed["error"])
    other.data.vertices[0].co.x = original_vertex_x
    other.data.update()

    rollback_context = require_success(run_request(server, lambda client: client.call("inspect_context")))
    before_a, before_b = tuple(cube.location), tuple(other.location)
    bridge_server._TEST_FAIL_AFTER_WRITES = 1
    failed = run_request(server, lambda client: client.call(
        "transform_objects", objects=[cube.name, other.name], deltaLocation=[1.0, 0.0, 0.0],
        expectedFingerprint=rollback_context["fingerprint"]))
    bridge_server._TEST_FAIL_AFTER_WRITES = None
    assert isinstance(failed.get("error"), BridgeError), failed
    assert "injected mutation failure" in str(failed["error"])
    assert tuple(cube.location) == before_a and tuple(other.location) == before_b
    after_rollback = require_success(run_request(server, lambda client: client.call("inspect_context")))
    assert after_rollback["mutationGeneration"] == rollback_context["mutationGeneration"]

    def expect_atomic_rollback(method, params, state):
        before = state()
        context = require_success(run_request(server, lambda client: client.call("inspect_context")))
        bridge_server._TEST_FAIL_AFTER_WRITES = 1
        failed_request = run_request(server, lambda client: client.call(
            method, expectedFingerprint=context["fingerprint"], **params))
        bridge_server._TEST_FAIL_AFTER_WRITES = None
        assert isinstance(failed_request.get("error"), BridgeError), failed_request
        assert "injected mutation failure" in str(failed_request["error"])
        assert state() == before, (method, before, state())
        after = require_success(run_request(server, lambda client: client.call("inspect_context")))
        assert after["mutationGeneration"] == context["mutationGeneration"]

    expect_atomic_rollback(
        "assign_material", {"objects": [cube.name, other.name], "material": material.name},
        lambda: tuple(tuple(slot.material.name if slot.material else None for slot in obj.material_slots)
                      for obj in (cube, other)))
    expect_atomic_rollback(
        "link_mesh_datablock", {"source": cube.name, "targets": [other.name]},
        lambda: (cube.data.name, other.data.name))
    expect_atomic_rollback(
        "make_mesh_unique", {"objects": [cube.name]}, lambda: cube.data.name)
    expect_atomic_rollback(
        "move_objects_to_collection",
        {"objects": [cube.name, other.name], "collection": target_collection.name, "mode": "move"},
        lambda: tuple(tuple(sorted(collection.name for collection in obj.users_collection))
                      for obj in (cube, other)))
    expect_atomic_rollback(
        "add_update_modifier",
        {"object": cube.name, "type": "BEVEL", "name": "BridgeBevel",
         "settings": {"width": .1, "segments": 2}},
        lambda: tuple((modifier.name, modifier.type) for modifier in cube.modifiers))

    # Assign by semantic ID, not by an existing material name. This is the path
    # the owner actually uses to texture a blockout, and it reaches the
    # repository's material library rather than bpy.data alone.
    semantic_context = require_success(run_request(server, lambda client: client.call("inspect_context")))
    semantic = require_success(run_request(server, lambda client: client.call(
        "assign_material", objects=[cube.name], semanticId="whitewash",
        expectedFingerprint=semantic_context["fingerprint"])))
    assert semantic["result"]["semanticId"] == "whitewash", semantic
    built = bpy.data.materials[semantic["result"]["material"]]
    assert built.get("sr_material_id") == "whitewash", dict(built.items())
    assert cube.data.materials[0] is built, "semantic material was not assigned to the target"
    # A flat colour fallback would still satisfy the assignment, so require the
    # library's texture set to be wired in.
    assert any(node.type == "TEX_IMAGE" for node in built.node_tree.nodes), "semantic material lost its texture set"

    invalid_context = require_success(run_request(server, lambda client: client.call("inspect_context")))
    malformed = run_request(server, lambda client: client.call(
        "transform_objects", objects=[cube.name], location=[float("nan"), 0, 0],
        expectedFingerprint=invalid_context["fingerprint"]))
    assert isinstance(malformed.get("error"), BridgeError)

    busy_context = require_success(run_request(server, lambda client: client.call("inspect_context")))
    concurrent = {}
    def first_mutation():
        try: concurrent["first"] = BridgeClient(token, port=server.port, timeout=10).call(
            "transform_objects", objects=[cube.name], deltaLocation=[.25, 0, 0],
            expectedFingerprint=busy_context["fingerprint"])
        except Exception as exc: concurrent["firstError"] = exc
    first_thread = threading.Thread(target=first_mutation); first_thread.start()
    deadline = time.monotonic() + 3
    while not server._mutation_busy and time.monotonic() < deadline: time.sleep(.005)
    assert server._mutation_busy
    second = {}
    def second_mutation():
        try: BridgeClient(token, port=server.port, timeout=10).call(
            "transform_objects", objects=[other.name], deltaLocation=[.25, 0, 0],
            expectedFingerprint=busy_context["fingerprint"])
        except Exception as exc: second["error"] = exc
    second_thread = threading.Thread(target=second_mutation); second_thread.start(); second_thread.join(3)
    assert isinstance(second.get("error"), BridgeError) and "mutation_busy" in str(second["error"])
    deadline = time.monotonic() + 10
    while first_thread.is_alive() and time.monotonic() < deadline: server._drain(); time.sleep(.005)
    first_thread.join(.5); assert "firstError" not in concurrent

    operator = bpy.types.THESTRA_OT_live_bridge_mutation
    assert "UNDO" in operator.bl_options
    stopped = {}
    def queued_read():
        try: BridgeClient(token, port=server.port, timeout=10).call("status")
        except Exception as exc: stopped["error"] = exc
    queued_thread = threading.Thread(target=queued_read); queued_thread.start()
    deadline = time.monotonic() + 3
    while server._queue.empty() and time.monotonic() < deadline: time.sleep(.005)
    assert not server._queue.empty()
    server.stop(); queued_thread.join(3)
    assert isinstance(stopped.get("error"), BridgeError) and "bridge_stopped" in str(stopped["error"])
    unregister_operator()
    addon.register(); addon.unregister()
    print("LIVE_BRIDGE_OK " + json.dumps({
        "addonRegisters": True, "authenticated": True, "captures": True,
        "pathTraversalRejected": True,
        "duplicateIdRejected": True,
        "stableFingerprint": True, "targetStateStaleRejected": True,
        "mainThreadDispatch": True, "rollback": True, "rollbackFamilies": 6, "saveCalls": 0,
        "shutdownTerminal": True, "staleRejected": True, "stateRestored": True,
        "undoOperator": True, "mutationBusyRejected": True,
        "bridgeVersion": result["status"]["bridgeVersion"],
    }, sort_keys=True))
    sys.stdout.flush()
    def quit_later(): bpy.ops.wm.quit_blender(); return None
    bpy.app.timers.register(quit_later, first_interval=0.1)


if __name__ == "__main__":
    try: main()
    except Exception:
        traceback.print_exc(); sys.stdout.flush(); bpy.ops.wm.quit_blender()
