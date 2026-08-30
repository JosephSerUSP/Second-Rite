"""Small standard-library client and CLI for the Thestra Live Bridge."""

from __future__ import annotations

import argparse
import json
import os
import socket
import time
import uuid
from pathlib import Path

try:
    from .protocol import PROTOCOL_VERSION, decode_message, encode_message
except ImportError:
    from protocol import PROTOCOL_VERSION, decode_message, encode_message


class BridgeError(RuntimeError): pass


class BridgeClient:
    def __init__(self, token, host="127.0.0.1", port=8765, timeout=60):
        self.token, self.host, self.port, self.timeout = token, host, int(port), timeout
    def call(self, method, **params):
        # The server rejects replayed IDs across the whole live session.  A
        # monotonic counter is therefore insufficient for short-lived CLI
        # processes, each of which would otherwise begin again at one.
        request_id = f"cli-{uuid.uuid4()}"
        with socket.create_connection((self.host, self.port), self.timeout) as sock:
            sock.sendall(encode_message({"id": request_id, "version": PROTOCOL_VERSION, "method": method,
                                         "params": params, "token": self.token,
                                         "timestamp": time.time()}))
            response = decode_message(sock.makefile("rb").readline(1024 * 1024 + 2))
        if response.get("id") != request_id: raise BridgeError("response id mismatch")
        if not response.get("ok"):
            error = response.get("error", "bridge request failed")
            if isinstance(error, dict): error = f"{error.get('code', 'error')}: {error.get('message', '')}"
            raise BridgeError(error)
        return response.get("result")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=int(os.environ.get("THESTRA_BRIDGE_PORT", 8765)))
    parser.add_argument("--token", default=os.environ.get("THESTRA_BRIDGE_TOKEN"))
    parser.add_argument("--pretty", action="store_true", help="indent JSON for human reading")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status"); sub.add_parser("inspect"); sub.add_parser("capabilities"); sub.add_parser("share-context"); sub.add_parser("latest-share"); sub.add_parser("validate")
    geometry = sub.add_parser("geometry")
    geometry.add_argument("objects", nargs="*", help="objects to measure; defaults to the current selection")
    geometry.add_argument("--grid", type=float, default=1.0)
    geometry.add_argument("--tolerance", type=float, default=1e-4)
    geometry.add_argument("--vertices", action="store_true", help="list vertex positions too")
    geometry.add_argument("--max-vertices", type=int, default=512)
    for command in ("capture-camera", "capture-viewport", "capture-selection"):
        capture = sub.add_parser(command)
        capture.add_argument("--out", required=True, type=Path)
        if command == "capture-camera":
            capture.add_argument("--width", type=int, default=426)
            capture.add_argument("--height", type=int, default=240)
            capture.add_argument("--camera")
            capture.add_argument("--allow-active-camera-fallback", action="store_true")
        else:
            capture.add_argument("--width", type=int)
            capture.add_argument("--height", type=int)
    transform = sub.add_parser("transform")
    transform.add_argument("objects", nargs="+")
    transform.add_argument("--fingerprint", required=True,
                           help="context fingerprint from the inspection/share this edit is based on")
    transform.add_argument("--location", nargs=3, type=float)
    transform.add_argument("--delta", nargs=3, type=float)
    transform.add_argument("--rotation", nargs=3, type=float)
    transform.add_argument("--scale", nargs=3, type=float)
    for prefix in ("location", "delta", "rotation", "scale"):
        for axis in "xyz": transform.add_argument(f"--{prefix}-{axis}", type=float)

    def mutation(name):
        command = sub.add_parser(name)
        command.add_argument("--fingerprint", required=True)
        return command

    planes = mutation("remap-planes")
    planes.add_argument("object")
    planes.add_argument("axis", choices=("x", "y", "z"))
    planes.add_argument("--move", action="append", default=[], metavar="FROM=TO",
                        help="repeatable: --move -0.6=-0.5")
    planes.add_argument("--tolerance", type=float, default=1e-4)
    planes.add_argument("--within", nargs=6, type=float, metavar=("MINX", "MINY", "MINZ", "MAXX", "MAXY", "MAXZ"))
    verts = mutation("set-vertices")
    verts.add_argument("object")
    verts.add_argument("--to", action="append", default=[], metavar="INDEX=X,Y,Z",
                       help="repeatable: --to 12=0,-0.5,2.15")
    verts.add_argument("--delta", action="append", default=[], metavar="INDEX=DX,DY,DZ")
    assign = mutation("assign-material"); assign.add_argument("objects", nargs="+")
    material_group = assign.add_mutually_exclusive_group(required=True)
    material_group.add_argument("--material"); material_group.add_argument("--semantic")
    link_mesh = mutation("link-mesh"); link_mesh.add_argument("source"); link_mesh.add_argument("targets", nargs="+")
    unique = mutation("make-unique"); unique.add_argument("objects", nargs="+")
    collection = mutation("collection"); collection.add_argument("objects", nargs="+")
    collection.add_argument("--collection", required=True); collection.add_argument("--mode", choices=("move", "link"), default="move")
    primitive = mutation("create-primitive"); primitive.add_argument("kind", choices=("cube", "plane", "cylinder"))
    primitive.add_argument("--name", required=True); primitive.add_argument("--collection", required=True)
    primitive.add_argument("--location", nargs=3, type=float, default=(0, 0, 0)); primitive.add_argument("--size", type=float, default=1)
    primitive.add_argument("--vertices", type=int, default=16); primitive.add_argument("--radius", type=float, default=.5); primitive.add_argument("--depth", type=float, default=1)
    modifier = mutation("modifier"); modifier.add_argument("object"); modifier.add_argument("type", choices=("BEVEL", "ARRAY", "SOLIDIFY", "MIRROR"))
    modifier.add_argument("--name"); modifier.add_argument("--remove", action="store_true")
    modifier.add_argument("--setting", action="append", default=[], metavar="KEY=JSON")
    thestra = mutation("thestra"); thestra.add_argument("operation", choices=("validate_collections", "recalculate_normals", "update_camera_calibration", "stage_walker_preview"))
    thestra.add_argument("--objects", nargs="+"); thestra.add_argument("--record", type=Path)
    args = parser.parse_args(argv)
    if not args.token: parser.error("--token or THESTRA_BRIDGE_TOKEN is required")
    client = BridgeClient(args.token, port=args.port)
    if args.command == "status": result = client.call("status")
    elif args.command == "inspect": result = client.call("inspect_context")
    elif args.command == "capabilities": result = client.call("capabilities")
    elif args.command == "share-context": result = client.call("share_context")
    elif args.command == "latest-share": result = client.call("latest_share")
    elif args.command == "validate": result = client.call("validate_thestra_collections")
    elif args.command == "geometry": result = client.call(
        "inspect_geometry", grid=args.grid, tolerance=args.tolerance,
        vertices=args.vertices, maxVertices=args.max_vertices,
        **({"objects": args.objects} if args.objects else {}))
    elif args.command == "capture-camera": result = client.call(
        "capture_game_camera", filename=args.out.name, width=args.width, height=args.height,
        camera=args.camera, allowActiveCameraFallback=args.allow_active_camera_fallback)
    elif args.command == "capture-viewport": result = client.call(
        "capture_viewport", filename=args.out.name, width=args.width, height=args.height)
    elif args.command == "capture-selection": result = client.call(
        "capture_selection", filename=args.out.name, width=args.width, height=args.height)
    elif args.command == "transform":
        params = {"objects": args.objects, "expectedFingerprint": args.fingerprint}
        if args.location is not None: params["location"] = args.location
        if args.delta is not None: params["deltaLocation"] = args.delta
        if args.rotation is not None: params["rotationEuler"] = args.rotation
        if args.scale is not None: params["scale"] = args.scale
        for prefix, wire in (("location", "locationAxes"), ("delta", "deltaAxes"),
                             ("rotation", "rotationAxes"), ("scale", "scaleAxes")):
            axes = {axis: getattr(args, f"{prefix}_{axis}") for axis in "xyz"
                    if getattr(args, f"{prefix}_{axis}") is not None}
            if axes: params[wire] = axes
        result = client.call("transform_objects", **params)
    elif args.command == "remap-planes":
        moves = []
        for item in args.move:
            source, _, target = item.partition("=")
            moves.append({"from": float(source), "to": float(target)})
        result = client.call("remap_vertex_planes", object=args.object, axis=args.axis,
                             moves=moves, tolerance=args.tolerance,
                             expectedFingerprint=args.fingerprint,
                             **({"within": list(args.within)} if args.within else {}))
    elif args.command == "set-vertices":
        edits = []
        for item, key in [(value, "to") for value in args.to] + [(value, "delta") for value in args.delta]:
            index, _, coords = item.partition("=")
            edits.append({"vertex": int(index), key: [float(value) for value in coords.split(",")]})
        result = client.call("set_vertices", object=args.object, vertices=edits,
                             expectedFingerprint=args.fingerprint)
    elif args.command == "assign-material": result = client.call(
        "assign_material", objects=args.objects, material=args.material, semanticId=args.semantic,
        expectedFingerprint=args.fingerprint)
    elif args.command == "link-mesh": result = client.call(
        "link_mesh_datablock", source=args.source, targets=args.targets, expectedFingerprint=args.fingerprint)
    elif args.command == "make-unique": result = client.call(
        "make_mesh_unique", objects=args.objects, expectedFingerprint=args.fingerprint)
    elif args.command == "collection": result = client.call(
        "move_objects_to_collection", objects=args.objects, collection=args.collection, mode=args.mode,
        expectedFingerprint=args.fingerprint)
    elif args.command == "create-primitive":
        params = {"kind": args.kind, "name": args.name, "collection": args.collection,
                  "location": args.location, "expectedFingerprint": args.fingerprint}
        if args.kind in ("cube", "plane"): params["size"] = args.size
        else: params.update(vertices=args.vertices, radius=args.radius, depth=args.depth)
        result = client.call("create_primitive", **params)
    elif args.command == "modifier":
        settings = {}
        for item in args.setting:
            if "=" not in item: parser.error("--setting must be KEY=JSON")
            key, raw = item.split("=", 1)
            try: settings[key] = json.loads(raw)
            except json.JSONDecodeError as exc: parser.error(f"invalid JSON setting {item!r}: {exc}")
        params = {"object": args.object, "type": args.type, "settings": settings,
                  "remove": args.remove, "expectedFingerprint": args.fingerprint}
        if args.name: params["name"] = args.name
        result = client.call("add_update_modifier", **params)
    elif args.command == "thestra":
        params = {"operation": args.operation, "expectedFingerprint": args.fingerprint}
        if args.objects: params["objects"] = args.objects
        if args.record:
            try: params["record"] = json.loads(args.record.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc: parser.error(f"cannot read calibration record: {exc}")
        result = client.call("run_thestra_operation", **params)
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True,
                     separators=None if args.pretty else (",", ":")))


if __name__ == "__main__": main()
