"""Authenticated, loopback-only command bridge for an open Blender session.

Socket threads only parse and enqueue requests. Every bpy read or mutation is
performed by the timer callback on Blender's main thread. Mutations execute as
one registered Blender operator with ``UNDO`` support.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import math
import os
import re
import time
import queue
import socket
import sys
import threading
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .protocol import PROTOCOL_VERSION, ProtocolError, decode_message, encode_message, validate_request

try:
    import bpy
except ImportError:  # Protocol/client unit tests run outside Blender.
    bpy = None



def _repo_tools_blender() -> Path:
    """Locate the repository's ``tools/blender`` directory.

    The bridge runs both from the checkout (``parents[1]`` is already the
    directory) and from a ZIP installed into Blender's addons folder, where it
    is not. Probe the explicit override, then the checkout layout, then walk up
    from the open document, so an installed add-on can still reach the
    repository modules the owner is authoring against. The module's own
    presence is the test; no repository marker file is trusted.
    """
    candidates = []
    override = os.environ.get("THESTRA_REPO")
    if override:
        candidates.append(Path(override) / "tools" / "blender")
    candidates.append(Path(__file__).resolve().parents[1])
    if bpy is not None and bpy.data.filepath:
        # Every ancestor, not the nearest repository marker: a project carries
        # its own AGENTS.md, so a marker search stops inside the project and
        # never reaches the checkout that owns tools/blender.
        for parent in Path(bpy.data.filepath).resolve().parents:
            candidates.append(parent / "tools" / "blender")
    for candidate in candidates:
        if (candidate / "material_library.py").is_file():
            return candidate
    raise ValueError(
        "repository tools/blender not found; set THESTRA_REPO to the Second Rite "
        "checkout so the bridge can reach material_library and thestra_camera")


def _use_repo_modules() -> None:
    root = str(_repo_tools_blender())
    if root not in sys.path:
        sys.path.insert(0, root)


READ_METHODS = {
    "status", "get_active_object", "get_selection", "get_scene_summary",
    "get_object", "get_material_summary", "get_datablock_sharing",
    "get_modifiers", "validate_thestra_collections", "inspect_context", "share_context",
    "capabilities", "latest_share", "capture_viewport", "capture_selection",
    "capture_game_camera",
}
MUTATION_METHODS = {
    "transform_objects", "assign_material", "link_mesh_datablock",
    "create_primitive", "move_objects_to_collection", "add_update_modifier",
    "make_mesh_unique", "run_thestra_operation",
}
REQUIRED_COLLECTIONS = ("TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS", "TH_CAMERA_PREVIEW")
CAMERA_CALIBRATION_CONTRACT = "thestra.world-camera-calibration"

METHOD_PARAMS = {
    "status": set(), "capabilities": set(), "inspect_context": set(),
    "share_context": set(), "latest_share": set(), "get_active_object": set(),
    "get_selection": set(), "get_scene_summary": set(),
    "get_object": {"name"}, "get_material_summary": set(),
    "get_datablock_sharing": set(), "get_modifiers": {"name"},
    "validate_thestra_collections": set(),
    "capture_game_camera": {"filename", "width", "height", "camera", "allowActiveCameraFallback"},
    "capture_viewport": {"filename", "width", "height"},
    "capture_selection": {"filename", "width", "height"},
    "transform_objects": {"objects", "location", "deltaLocation", "rotationEuler", "scale",
                          "locationAxes", "deltaAxes", "rotationAxes", "scaleAxes", "expectedFingerprint"},
    "assign_material": {"objects", "material", "semanticId", "expectedFingerprint"},
    "link_mesh_datablock": {"source", "targets", "expectedFingerprint"},
    "make_mesh_unique": {"objects", "expectedFingerprint"},
    "create_primitive": {"kind", "name", "collection", "location", "size", "vertices", "radius",
                         "depth", "expectedFingerprint"},
    "move_objects_to_collection": {"objects", "collection", "mode", "expectedFingerprint"},
    "add_update_modifier": {"object", "type", "name", "settings", "remove", "expectedFingerprint"},
    "run_thestra_operation": {"operation", "objects", "record", "expectedFingerprint"},
}

MODIFIER_SETTINGS = {
    "BEVEL": {"width": float, "segments": int, "limit_method": str, "angle_limit": float,
               "affect": str, "show_viewport": bool, "show_render": bool},
    "ARRAY": {"count": int, "relative_offset_displace": tuple, "constant_offset_displace": tuple,
               "use_relative_offset": bool, "use_constant_offset": bool,
               "show_viewport": bool, "show_render": bool},
    "SOLIDIFY": {"thickness": float, "offset": float, "use_even_offset": bool,
                  "show_viewport": bool, "show_render": bool},
    "MIRROR": {"use_axis": tuple, "use_clip": bool, "use_mirror_merge": bool,
                "merge_threshold": float, "show_viewport": bool, "show_render": bool},
}
MODIFIER_ENUMS = {
    ("BEVEL", "limit_method"): {"NONE", "ANGLE", "WEIGHT", "VGROUP"},
    ("BEVEL", "affect"): {"EDGES", "VERTICES"},
}


def _validate_method_params(method, params):
    allowed = METHOD_PARAMS.get(method)
    if allowed is None:
        raise ValueError(f"method {method!r} is not allowed")
    unknown = set(params) - allowed
    if unknown:
        raise ValueError(f"unknown parameters for {method}: {', '.join(sorted(unknown))}")
    if method in MUTATION_METHODS:
        fingerprint = params.get("expectedFingerprint")
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ValueError("expectedFingerprint from inspect/share is required for every mutation")


def _require_blender():
    if bpy is None:
        raise RuntimeError("live bridge server must run inside Blender")


def _object(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"unknown object {name!r}")
    return obj


def _vec(value, label, length=3):
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"{label} must contain {length} numbers")
    if not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
        raise ValueError(f"{label} must contain only numbers")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{label} must contain finite numbers")
    return result


def _json_value(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    try:
        return {str(key): _json_value(item) for key, item in value.items()}
    except (AttributeError, TypeError):
        pass
    if hasattr(value, "to_list"):
        return [_json_value(item) for item in value.to_list()]
    try:
        return [_json_value(item) for item in list(value)]
    except (TypeError, ValueError):
        return str(value)


def _duplicate_family(name):
    return re.sub(r"\.\d{3}$", "", name)


def _modifier_record(mod):
    record = {"name": mod.name, "type": mod.type, "showViewport": mod.show_viewport,
              "showRender": mod.show_render}
    for key in MODIFIER_SETTINGS.get(mod.type, {}):
        if hasattr(mod, key):
            record[key] = _json_value(getattr(mod, key))
    return record


def _object_record(obj):
    data = obj.data
    counts = None
    if obj.type == "MESH" and data is not None:
        counts = {"vertices": len(data.vertices), "edges": len(data.edges), "polygons": len(data.polygons)}
    active_material = obj.active_material
    return {
        "name": obj.name, "type": obj.type,
        "duplicateFamily": _duplicate_family(obj.name),
        "location": list(obj.location), "rotationEuler": list(obj.rotation_euler),
        "scale": list(obj.scale), "parent": obj.parent.name if obj.parent else None,
        "collections": sorted(coll.name for coll in obj.users_collection),
        "data": data.name if data else None, "dataType": type(data).__name__ if data else None,
        "dataLibrary": data.library.filepath if data and data.library else None,
        "library": obj.library.filepath if obj.library else None, "readOnly": bool(obj.library or (data and data.library)),
        "visible": not obj.hide_get(), "hideRender": obj.hide_render,
        "dimensions": list(obj.dimensions),
        "counts": counts,
        "activeMaterial": active_material.name if active_material else None,
        "materials": [{"slot": index, "name": slot.material.name,
                       "semanticId": slot.material.get("sr_material_id"),
                       "users": slot.material.users,
                       "nodes": len(slot.material.node_tree.nodes)
                       if slot.material.use_nodes and slot.material.node_tree else 0,
                       "link": slot.link}
                      for index, slot in enumerate(obj.material_slots) if slot.material],
        "instanceCollection": obj.instance_collection.name if obj.instance_collection else None,
        "instanceType": obj.instance_type,
        "modifiers": [_modifier_record(mod) for mod in obj.modifiers],
        "metadata": {key: _json_value(obj[key]) for key in obj.keys() if not str(key).startswith("_")},
    }


def _hierarchy(parent):
    children = []
    for obj in sorted((item for item in bpy.data.objects if item.parent == parent), key=lambda x: x.name):
        record = _object_record(obj); record["children"] = _hierarchy(obj); children.append(record)
    return children


def _collection_tree(collection):
    return {"name": collection.name, "hideViewport": collection.hide_viewport,
            "hideRender": collection.hide_render,
            "objects": sorted(obj.name for obj in collection.objects),
            "children": [_collection_tree(child) for child in sorted(collection.children, key=lambda item: item.name)]}


def _fingerprint():
    active = bpy.context.view_layer.objects.active
    records = []
    data_signatures = {}
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        data_signature = None
        if obj.data:
            key = obj.data.as_pointer()
            if key not in data_signatures:
                if obj.type == "MESH":
                    mesh_payload = {"vertices": [list(vertex.co) for vertex in obj.data.vertices],
                                    "edges": [list(edge.vertices) for edge in obj.data.edges],
                                    "polygons": [list(poly.vertices) for poly in obj.data.polygons]}
                    data_signatures[key] = hashlib.sha256(json.dumps(
                        mesh_payload, separators=(",", ":")).encode()).hexdigest()
                elif obj.type == "CAMERA":
                    data_signatures[key] = {"type": obj.data.type, "lens": obj.data.lens,
                                            "shiftX": obj.data.shift_x, "shiftY": obj.data.shift_y,
                                            "clipStart": obj.data.clip_start, "clipEnd": obj.data.clip_end,
                                            "orthoScale": obj.data.ortho_scale,
                                            "sensorWidth": obj.data.sensor_width}
                else:
                    data_signatures[key] = obj.data.name
            data_signature = data_signatures[key]
        records.append({"name": obj.name, "location": list(obj.location),
                        "rotation": list(obj.rotation_euler), "scale": list(obj.scale),
                        "parent": obj.parent.name if obj.parent else None,
                        "collections": sorted(coll.name for coll in obj.users_collection),
                        "data": obj.data.name if obj.data else None, "dataState": data_signature,
                        "dataLibrary": obj.data.library.filepath if obj.data and obj.data.library else None,
                        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
                        "modifiers": [_modifier_record(mod) for mod in obj.modifiers],
                        "metadata": {name: _json_value(obj[name]) for name in sorted(obj.keys())},
                        "hidden": obj.hide_get(), "hideRender": obj.hide_render})
    materials = [{"name": mat.name, "semanticId": mat.get("sr_material_id"),
                  "users": mat.users,
                  "nodes": [{"name": node.name, "type": node.bl_idname,
                             "inputs": {socket.name: _json_value(socket.default_value)
                                        for socket in node.inputs if hasattr(socket, "default_value")}}
                            for node in sorted(mat.node_tree.nodes, key=lambda item: item.name)]
                  if mat.use_nodes and mat.node_tree else [],
                  "links": sorted((link.from_node.name, link.from_socket.name,
                                   link.to_node.name, link.to_socket.name)
                                  for link in mat.node_tree.links)
                  if mat.use_nodes and mat.node_tree else []}
                 for mat in sorted(bpy.data.materials, key=lambda item: item.name)]
    payload = {"file": bpy.data.filepath or None, "scene": bpy.context.scene.name,
               "frame": bpy.context.scene.frame_current,
               "mutationGeneration": _SERVER.mutation_generation if _SERVER else 0,
               "active": active.name if active else None,
               "selected": sorted(obj.name for obj in bpy.context.selected_objects),
               "objects": records, "materials": materials,
               "render": {"width": bpy.context.scene.render.resolution_x,
                          "height": bpy.context.scene.render.resolution_y,
                          "percentage": bpy.context.scene.render.resolution_percentage,
                          "pixelAspectX": bpy.context.scene.render.pixel_aspect_x,
                          "pixelAspectY": bpy.context.scene.render.pixel_aspect_y}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _material_records():
    return [{"name": mat.name, "duplicateFamily": _duplicate_family(mat.name), "users": mat.users,
             "semanticId": mat.get("sr_material_id"),
             "nodes": len(mat.node_tree.nodes) if mat.use_nodes and mat.node_tree else 0}
            for mat in sorted(bpy.data.materials, key=lambda x: x.name)]


def _camera_record(obj):
    if obj is None:
        return None
    record = _object_record(obj)
    data = obj.data
    record["optics"] = {"type": data.type, "lens": data.lens, "sensorWidth": data.sensor_width,
                        "sensorHeight": data.sensor_height, "shiftX": data.shift_x, "shiftY": data.shift_y,
                        "clipStart": data.clip_start, "clipEnd": data.clip_end,
                        "orthoScale": data.ortho_scale}
    return record


def _is_calibrated_camera(obj):
    preview = bpy.data.collections.get("TH_CAMERA_PREVIEW")
    return bool(obj and obj.type == "CAMERA" and preview and obj.name in preview.all_objects and
                obj.get("thestra_calibration_contract") == CAMERA_CALIBRATION_CONTRACT and
                obj.get("thestra_calibration_version") == 1)


def _context_summary():
    scene = bpy.context.scene
    active = bpy.context.view_layer.objects.active
    collections = []
    for coll in sorted(bpy.data.collections, key=lambda x: x.name):
        parents = sorted(parent.name for parent in bpy.data.collections if coll.name in parent.children)
        collections.append({"name": coll.name, "hideViewport": coll.hide_viewport,
                            "hideRender": coll.hide_render,
                            "objects": sorted(obj.name for obj in coll.objects),
                            "children": sorted(child.name for child in coll.children), "parents": parents})
    groups = {}
    for obj in bpy.data.objects:
        if obj.data: groups.setdefault(obj.data.name, []).append(obj.name)
    sharing = {name: sorted(items) for name, items in sorted(groups.items()) if len(items) > 1}
    duplicate_objects = {}
    for obj in bpy.data.objects:
        duplicate_objects.setdefault(_duplicate_family(obj.name), []).append(obj)
    unlinked_candidates = []
    for family, objects in sorted(duplicate_objects.items()):
        data_names = {obj.data.name if obj.data else None for obj in objects}
        if len(objects) > 1 and len(data_names) > 1:
            unlinked_candidates.append({"family": family, "objects": sorted(obj.name for obj in objects),
                                        "datablocks": sorted(str(name) for name in data_names)})
    duplicate_materials = {}
    for material in bpy.data.materials:
        duplicate_materials.setdefault(_duplicate_family(material.name), []).append(material.name)
    duplicate_materials = {name: sorted(items) for name, items in duplicate_materials.items() if len(items) > 1}
    collection_contract = {}
    warnings = []
    for name in ("TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS",
                 "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW"):
        coll = bpy.data.collections.get(name)
        record = {"present": coll is not None, "visible": bool(coll and not coll.hide_viewport),
                  "hideRender": bool(coll and coll.hide_render),
                  "objects": sorted(obj.name for obj in coll.objects) if coll else []}
        collection_contract[name] = record
        if name in REQUIRED_COLLECTIONS and coll is None:
            warnings.append(f"missing required collection {name}")
    calibrated_collection = bpy.data.collections.get("TH_CAMERA_PREVIEW")
    calibrated_cameras = ([obj.name for obj in calibrated_collection.all_objects if _is_calibrated_camera(obj)]
                          if calibrated_collection else [])
    if calibrated_collection and not calibrated_cameras:
        warnings.append("TH_CAMERA_PREVIEW contains no calibrated camera")
    active_camera = scene.camera
    return {"protocolVersion": PROTOCOL_VERSION,
            "sessionId": _SERVER.session_id if _SERVER else None, "timestamp": time.time(),
            "file": bpy.data.filepath or None,
            "dirty": bpy.data.is_dirty, "scene": scene.name,
            "viewLayer": bpy.context.view_layer.name, "mode": bpy.context.mode,
            "frame": scene.frame_current, "activeObject": _object_record(active) if active else None,
            "selection": [_object_record(obj) for obj in sorted(bpy.context.selected_objects, key=lambda x: x.name)],
            "hierarchy": [{**_object_record(obj), "children": _hierarchy(obj)}
                          for obj in sorted(bpy.data.objects, key=lambda x: x.name) if obj.parent is None],
            "collectionHierarchy": [_collection_tree(collection) for collection in
                                    sorted(scene.collection.children, key=lambda item: item.name)],
            "materials": _material_records(), "duplicateMaterialFamilies": duplicate_materials,
            "datablockSharing": sharing, "unlinkedDuplicateCandidates": unlinked_candidates,
            "collections": collections,
            "camera": _camera_record(active_camera),
            "render": {"width": scene.render.resolution_x, "height": scene.render.resolution_y,
                       "percentage": scene.render.resolution_percentage},
            "cameraCalibrated": _is_calibrated_camera(active_camera),
            "calibratedCameras": sorted(calibrated_cameras),
            "activeAction": (active.animation_data.action.name
                             if active and active.animation_data and active.animation_data.action else None),
            "thestraCollections": collection_contract, "contractWarnings": warnings,
            "mutationGeneration": _SERVER.mutation_generation if _SERVER else 0,
            "fingerprint": _fingerprint()}


def _session_output_root(session_id):
    """Return the repository-owned output root for the open authoring file."""
    if bpy.data.filepath:
        candidates = Path(bpy.data.filepath).resolve().parents
    else:
        working = Path.cwd().resolve()
        candidates = (working, *working.parents)
    for candidate in candidates:
        if (candidate / ".git").exists() and (candidate / "tools" / "blender").is_dir():
            root = candidate / "out" / "blender-live-bridge" / session_id
            root.mkdir(parents=True, exist_ok=True)
            return root
    raise RuntimeError("open .blend is not inside a Thestra repository")


def _safe_capture_path(params, session_id):
    filename = params.get("filename") or params.get("path") or "capture.png"
    if not isinstance(filename, str) or not filename or Path(filename).name != filename:
        raise ValueError("capture filename must be a basename")
    if Path(filename).suffix.lower() != ".png": raise ValueError("capture filename must end in .png")
    return _session_output_root(session_id) / filename


def _capture_manifest(path, kind, session_id, width=None, height=None, metadata=None, warnings=None):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"protocolVersion": PROTOCOL_VERSION, "sessionId": session_id, "kind": kind,
                "path": str(path), "sha256": digest,
                "width": width if width is not None else bpy.context.scene.render.resolution_x,
                "height": height if height is not None else bpy.context.scene.render.resolution_y,
                "timestamp": time.time(),
                "contextFingerprint": _fingerprint(),
                "selectedObjects": sorted(obj.name for obj in bpy.context.selected_objects),
                "cameraOrView": metadata or {}, "warnings": warnings or []}
    path.with_suffix(".json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def _publish_bundle(captures=()):
    context = _context_summary()
    root = _session_output_root(_SERVER.session_id)
    stamp = int(time.time() * 1000)
    context_path = root / f"context-{stamp}.json"
    context_path.write_text(json.dumps(context, indent=2, sort_keys=True), encoding="utf-8")
    bundle_path = root / f"share-{stamp}.json"
    bundle = {"protocolVersion": PROTOCOL_VERSION, "sessionId": _SERVER.session_id,
              "timestamp": time.time(), "contextFingerprint": context["fingerprint"],
              "contextPath": str(context_path), "captures": list(captures),
              "path": str(bundle_path)}
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
    _SERVER.latest_share = bundle
    return bundle


def _resize_capture(path, width, height):
    if width is None and height is None:
        return None
    if width is None or height is None:
        raise ValueError("capture width and height must be supplied together")
    width, height = int(width), int(height)
    if width < 16 or height < 16 or width > 4096 or height > 4096:
        raise ValueError("capture dimensions must be between 16 and 4096")
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        image.scale(width, height)
        image.save_render(str(path))
    finally:
        bpy.data.images.remove(image)
    return width, height


def _view3d_context():
    preferred = bpy.context.window
    windows = ([preferred] if preferred else []) + [window for window in bpy.context.window_manager.windows
                                                      if window != preferred]
    for window in windows:
        if window.screen is None:
            continue
        areas = list(window.screen.areas)
        if bpy.context.area in areas and bpy.context.area.type == "VIEW_3D":
            areas.remove(bpy.context.area)
            areas.insert(0, bpy.context.area)
        for area in areas:
            if area.type != "VIEW_3D":
                continue
            region = next((item for item in area.regions if item.type == "WINDOW"), None)
            if region is not None:
                return window, area, region
    raise RuntimeError("no VIEW_3D window/area/region is available")


def _read(method, params):
    if method == "status":
        return {"bridgeVersion": 1, "protocolVersion": PROTOCOL_VERSION,
                "sessionId": _SERVER.session_id if _SERVER else None,
                "blenderVersion": bpy.app.version_string,
                "file": bpy.data.filepath or None, "dirty": bpy.data.is_dirty}
    if method == "capabilities":
        return {"protocolVersion": PROTOCOL_VERSION, "reads": sorted(READ_METHODS),
                "mutations": sorted(MUTATION_METHODS), "arbitraryPython": False,
                "save": False, "sessionId": _SERVER.session_id if _SERVER else None,
                "classifications": {**{name: "read" for name in sorted(READ_METHODS)},
                                    **{name: "mutation" for name in sorted(MUTATION_METHODS)}}}
    if method == "inspect_context":
        return _context_summary()
    if method == "share_context":
        return _publish_bundle()
    if method == "latest_share":
        return _SERVER.latest_share if _SERVER else None
    if method == "get_active_object":
        obj = bpy.context.view_layer.objects.active
        return _object_record(obj) if obj else None
    if method == "get_selection":
        return [_object_record(obj) for obj in sorted(bpy.context.selected_objects, key=lambda x: x.name)]
    if method == "get_scene_summary":
        scene = bpy.context.scene
        counts = {}
        for obj in scene.objects:
            counts[obj.type] = counts.get(obj.type, 0) + 1
        return {"scene": scene.name, "camera": scene.camera.name if scene.camera else None,
                "objectCounts": counts,
                "collections": sorted(coll.name for coll in bpy.data.collections)}
    if method == "get_object":
        return _object_record(_object(params.get("name")))
    if method == "get_material_summary":
        return _material_records()
    if method == "get_datablock_sharing":
        groups = {}
        for obj in bpy.data.objects:
            if obj.data:
                groups.setdefault(obj.data.name, []).append(obj.name)
        return {name: sorted(names) for name, names in sorted(groups.items()) if len(names) > 1}
    if method == "get_modifiers":
        obj = _object(params.get("name"))
        return [{"name": mod.name, "type": mod.type, "showViewport": mod.show_viewport,
                 "showRender": mod.show_render} for mod in obj.modifiers]
    if method == "validate_thestra_collections":
        missing = [name for name in REQUIRED_COLLECTIONS if bpy.data.collections.get(name) is None]
        return {"ok": not missing, "missing": missing}
    if method == "capture_game_camera":
        output = _safe_capture_path(params, _SERVER.session_id)
        camera_name = params.get("camera")
        if camera_name:
            camera = _object(camera_name)
            if not _is_calibrated_camera(camera):
                raise ValueError(f"camera {camera_name!r} is not a calibrated TH_CAMERA_PREVIEW camera")
        else:
            preview = bpy.data.collections.get("TH_CAMERA_PREVIEW")
            camera = next((obj for obj in sorted(preview.all_objects, key=lambda item: item.name)
                           if _is_calibrated_camera(obj)), None) if preview else None
            if camera is None and params.get("allowActiveCameraFallback"):
                camera = bpy.context.scene.camera
            if camera is None:
                raise ValueError("no calibrated TH_CAMERA_PREVIEW camera; set allowActiveCameraFallback to use scene camera")
        if camera is None or camera.type != "CAMERA":
            raise ValueError("scene has no camera")
        width = int(params.get("width", 426)); height = int(params.get("height", 240))
        if width < 16 or height < 16 or width > 4096 or height > 4096:
            raise ValueError("capture dimensions must be between 16 and 4096")
        scene = bpy.context.scene
        old = (scene.camera, scene.render.filepath, scene.render.resolution_x,
               scene.render.resolution_y, scene.render.resolution_percentage,
               scene.render.image_settings.file_format)
        old_filepath = scene.render.filepath
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            scene.camera = camera; scene.render.filepath = str(output)
            scene.render.resolution_x = width; scene.render.resolution_y = height
            scene.render.resolution_percentage = 100
            scene.render.image_settings.file_format = "PNG"
            bpy.ops.render.render(write_still=True)
        finally:
            (scene.camera, scene.render.filepath, scene.render.resolution_x,
             scene.render.resolution_y, scene.render.resolution_percentage,
             scene.render.image_settings.file_format) = old
        manifest = _capture_manifest(
            output, "game_camera", _SERVER.session_id, width, height,
            metadata={"camera": camera.name, "transform": {"location": list(camera.location),
                      "rotationEuler": list(camera.rotation_euler)},
                      "optics": _camera_record(camera)["optics"],
                      "renderEngine": scene.render.engine},
            warnings=[] if _is_calibrated_camera(camera) else ["used active scene camera fallback"])
        _publish_bundle((manifest,))
        return manifest
    if method in ("capture_viewport", "capture_selection"):
        window, area, region = _view3d_context()
        output = _safe_capture_path(params, _SERVER.session_id)
        selected = list(bpy.context.selected_objects)
        active = bpy.context.view_layer.objects.active
        scene = bpy.context.scene
        old_filepath = scene.render.filepath
        space = area.spaces.active
        region3d = space.region_3d
        view_state = (region3d.view_distance, region3d.view_location.copy(),
                      region3d.view_rotation.copy(), region3d.view_perspective)
        hidden = {obj.name: obj.hide_get() for obj in bpy.data.objects}
        overlay_state = space.overlay.show_overlays
        shading_state = {key: _json_value(getattr(space.shading, key)) for key in
                         ("type", "light", "color_type", "background_type", "background_color")}
        world_color = scene.world.color[:] if scene.world else None
        try:
            if method == "capture_selection":
                if not selected: raise ValueError("capture_selection requires a non-empty selection")
                for obj in bpy.data.objects: obj.hide_set(obj not in selected)
                space.overlay.show_overlays = False
                space.shading.type = "SOLID"
                space.shading.color_type = "MATERIAL"
                space.shading.background_type = "VIEWPORT"
                space.shading.background_color = (0.18, 0.18, 0.18)
            with bpy.context.temp_override(window=window, area=area, region=region):
                if method == "capture_selection": bpy.ops.view3d.view_selected(use_all_regions=False)
                bpy.context.scene.render.filepath = str(output)
                bpy.ops.render.opengl(write_still=True, view_context=True)
            resized = _resize_capture(output, params.get("width"), params.get("height"))
        finally:
            scene.render.filepath = old_filepath
            region3d.view_distance, region3d.view_location, region3d.view_rotation, region3d.view_perspective = view_state
            for obj in bpy.data.objects:
                if obj.name in hidden: obj.hide_set(hidden[obj.name])
            bpy.context.view_layer.objects.active = active
            for obj in bpy.data.objects: obj.select_set(obj in selected)
            space.overlay.show_overlays = overlay_state
            for key, value in shading_state.items():
                setattr(space.shading, key, value)
            if scene.world and world_color is not None:
                scene.world.color = world_color
        capture_width, capture_height = resized or (region.width, region.height)
        manifest = _capture_manifest(
            output, "selection" if method == "capture_selection" else "viewport", _SERVER.session_id,
            capture_width, capture_height,
            metadata={"window": window.screen.name, "areaType": area.type,
                      "viewPerspective": view_state[3], "viewDistance": view_state[0],
                      "viewLocation": list(view_state[1]), "viewRotation": list(view_state[2]),
                      "shading": shading_state, "overlays": overlay_state})
        _publish_bundle((manifest,))
        return manifest
    raise ValueError(f"unknown read method {method!r}")


def _object_names(value, label="objects"):
    if not isinstance(value, list) or not value or any(not isinstance(name, str) or not name for name in value):
        raise ValueError(f"{label} must be a non-empty list of object names")
    if len(set(value)) != len(value):
        raise ValueError(f"{label} must not contain duplicate names")
    return value


def _writable_object(name):
    obj = _object(name)
    if obj.library or (obj.data and obj.data.library):
        raise ValueError(f"object {name!r} is linked/read-only")
    return obj


def _finite_number(value, label, *, minimum=None, maximum=None, integer=False):
    expected = int if integer else (int, float)
    if not isinstance(value, expected) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite {'integer' if integer else 'number'}")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label} must be at most {maximum}")
    return int(value) if integer else float(value)


def _axis_values(value, label):
    if not isinstance(value, dict) or not value or set(value) - {"x", "y", "z"}:
        raise ValueError(f"{label} must be an object containing one or more of x, y, z")
    return {axis: _finite_number(number, f"{label}.{axis}") for axis, number in value.items()}


def _validate_modifier_setting(kind, key, value):
    expected = MODIFIER_SETTINGS[kind].get(key)
    if expected is None:
        raise ValueError(f"unknown {kind} modifier setting {key!r}")
    if expected is bool:
        if not isinstance(value, bool): raise ValueError(f"modifier setting {key} must be boolean")
        return value
    if expected is int:
        maximum = 100 if key == "segments" else None
        return _finite_number(value, f"modifier setting {key}", minimum=1, maximum=maximum, integer=True)
    if expected is float:
        minimum = 0 if key in ("width", "angle_limit", "merge_threshold") else None
        maximum = math.pi if key == "angle_limit" else (1 if key == "offset" else None)
        minimum = -1 if key == "offset" else minimum
        return _finite_number(value, f"modifier setting {key}", minimum=minimum, maximum=maximum)
    if expected is str:
        if not isinstance(value, str) or not value: raise ValueError(f"modifier setting {key} must be a string")
        allowed = MODIFIER_ENUMS.get((kind, key))
        if allowed and value not in allowed:
            raise ValueError(f"modifier setting {key} must be one of {sorted(allowed)}")
        return value
    if expected is tuple:
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise ValueError(f"modifier setting {key} must contain three values")
        if key == "use_axis":
            if any(not isinstance(item, bool) for item in value):
                raise ValueError("modifier setting use_axis must contain booleans")
            return tuple(value)
        return _vec(value, f"modifier setting {key}")
    raise ValueError(f"unsupported modifier setting {key!r}")


def _validate_mutation(method, params):
    if bpy.context.mode != "OBJECT":
        raise ValueError(f"mutations require Object Mode, current mode is {bpy.context.mode}")
    if method == "transform_objects":
        for name in _object_names(params.get("objects")): _writable_object(name)
        for key in ("location", "deltaLocation", "rotationEuler", "scale"):
            if key in params: _vec(params[key], key)
        for key in ("locationAxes", "deltaAxes", "rotationAxes", "scaleAxes"):
            if key in params: _axis_values(params[key], key)
        if not any(key in params for key in ("location", "deltaLocation", "rotationEuler", "scale",
                                               "locationAxes", "deltaAxes", "rotationAxes", "scaleAxes")):
            raise ValueError("at least one transform is required")
    elif method == "assign_material":
        names = _object_names(params.get("objects"))
        for name in names:
            obj = _writable_object(name)
            if obj.type != "MESH": raise ValueError(f"object {name!r} is not a mesh")
            outside_users = sorted(other.name for other in bpy.data.objects
                                   if other.data == obj.data and other.name not in names)
            if outside_users:
                raise ValueError(f"object {name!r} shares mesh {obj.data.name!r} with {outside_users}; "
                                 "include all users or make the target mesh unique first")
        material, semantic = params.get("material"), params.get("semanticId")
        if bool(material) == bool(semantic): raise ValueError("supply exactly one of material or semanticId")
        if material and bpy.data.materials.get(material) is None: raise ValueError(f"unknown material {material!r}")
        if semantic:
            _use_repo_modules()
            from material_library import semantic_ids
            if semantic not in semantic_ids(): raise ValueError(f"unknown semantic material {semantic!r}")
            named = bpy.data.materials.get(f"sr_{semantic}")
            if named and named.get("sr_material_id") != semantic:
                raise ValueError(f"material sr_{semantic!s} already exists with incompatible semantic metadata")
    elif method == "link_mesh_datablock":
        source = _writable_object(params.get("source"))
        if source.type != "MESH": raise ValueError("source must be a mesh object")
        for name in _object_names(params.get("targets"), "targets"):
            if _writable_object(name).type != "MESH": raise ValueError(f"object {name!r} is not a mesh")
    elif method == "make_mesh_unique":
        for name in _object_names(params.get("objects")):
            if _writable_object(name).type != "MESH": raise ValueError(f"object {name!r} is not a mesh")
    elif method == "move_objects_to_collection":
        collection = bpy.data.collections.get(params.get("collection"))
        if collection is None or collection.library: raise ValueError("an existing writable collection is required")
        if params.get("mode", "move") not in ("move", "link"): raise ValueError("collection mode must be move or link")
        for name in _object_names(params.get("objects")): _writable_object(name)
    elif method == "create_primitive":
        if params.get("kind") not in ("cube", "plane", "cylinder"): raise ValueError("kind must be cube, plane, or cylinder")
        if not isinstance(params.get("name"), str) or not params["name"]: raise ValueError("a non-empty primitive name is required")
        if len(params["name"]) > 63: raise ValueError("primitive name must be at most 63 characters")
        if bpy.data.objects.get(params["name"]): raise ValueError(f"object {params['name']!r} already exists")
        collection = bpy.data.collections.get(params.get("collection"))
        if collection is None or collection.library: raise ValueError("an existing writable collection is required")
        _vec(params.get("location", (0, 0, 0)), "location")
        if params["kind"] in ("cube", "plane"): _finite_number(params.get("size", 1), "size", minimum=0.0001)
        else:
            _finite_number(params.get("vertices", 16), "vertices", minimum=3, maximum=256, integer=True)
            _finite_number(params.get("radius", .5), "radius", minimum=0.0001)
            _finite_number(params.get("depth", 1), "depth", minimum=0.0001)
    elif method == "add_update_modifier":
        obj = _writable_object(params.get("object"))
        if obj.type != "MESH": raise ValueError("modifiers require a mesh object")
        kind = str(params.get("type", "")).upper()
        if kind not in MODIFIER_SETTINGS: raise ValueError("modifier type must be BEVEL, ARRAY, SOLIDIFY, or MIRROR")
        name = params.get("name", kind)
        if not isinstance(name, str) or not name: raise ValueError("modifier name must be a non-empty string")
        existing = obj.modifiers.get(name)
        if params.get("remove"):
            if existing is None: raise ValueError(f"unknown modifier {name!r}")
            if existing.type != kind: raise ValueError(f"modifier {name!r} is not {kind}")
        else:
            if existing and existing.type != kind: raise ValueError(f"modifier {name!r} is not {kind}")
            settings = params.get("settings", {})
            if not isinstance(settings, dict): raise ValueError("modifier settings must be an object")
            for key, value in settings.items(): _validate_modifier_setting(kind, key, value)
    elif method == "run_thestra_operation":
        operation = params.get("operation")
        if operation not in ("validate_collections", "recalculate_normals", "update_camera_calibration",
                              "stage_walker_preview"):
            raise ValueError(f"unknown Thestra operation {operation!r}")
        if operation == "recalculate_normals":
            for name in _object_names(params.get("objects")):
                if _writable_object(name).type != "MESH": raise ValueError(f"object {name!r} is not a mesh")
        if operation == "update_camera_calibration" and not isinstance(params.get("record"), dict):
            raise ValueError("record object is required")
        if operation == "update_camera_calibration":
            collection = bpy.data.collections.get("TH_CAMERA_PREVIEW")
            if collection is None or collection.library:
                raise ValueError("TH_CAMERA_PREVIEW must exist and be writable")
            _use_repo_modules()
            import thestra_camera
            thestra_camera.validate_calibration(params["record"])
            thestra_camera._projection_coefficients(params["record"])
            thestra_camera._camera_basis(params["record"])
            eye = params["record"].get("eye")
            if not isinstance(eye, dict) or set(eye) != {"x", "y", "z"}:
                raise ValueError("camera calibration eye must contain exactly x, y, z")
            for axis in "xyz": _finite_number(eye[axis], f"camera calibration eye.{axis}")
        if operation == "stage_walker_preview":
            collection = bpy.data.collections.get("TH_PREVIEW_ACTORS")
            if collection is None or collection.library: raise ValueError("TH_PREVIEW_ACTORS must exist and be writable")


def _touched_names(method, params, result=None):
    if method in ("transform_objects", "assign_material", "make_mesh_unique", "move_objects_to_collection"):
        return list(params.get("objects") or [])
    if method == "link_mesh_datablock": return [params.get("source"), *(params.get("targets") or [])]
    if method == "add_update_modifier": return [params.get("object")]
    if method == "create_primitive": return [params.get("name")]
    if method == "run_thestra_operation":
        names = list(params.get("objects") or [])
        if params.get("operation") == "update_camera_calibration" and bpy.data.objects.get("TH_CAMERA_PREVIEW"):
            names.append("TH_CAMERA_PREVIEW")
        if params.get("operation") == "stage_walker_preview" and bpy.data.objects.get("ACTOR_Walker_Billboard"):
            names.append("ACTOR_Walker_Billboard")
        return names
    return []


class _MutationSnapshot:
    def __init__(self, method, params):
        self.object_names = set(bpy.data.objects.keys())
        self.material_names = set(bpy.data.materials.keys())
        self.mesh_names = set(bpy.data.meshes.keys())
        self.camera_names = set(bpy.data.cameras.keys())
        self.states = {}
        scene = bpy.context.scene
        self.render_state = (scene.render.resolution_x, scene.render.resolution_y,
                             scene.render.resolution_percentage, scene.render.pixel_aspect_x,
                             scene.render.pixel_aspect_y, scene.camera)
        self.data_backups = []
        for name in _touched_names(method, params):
            obj = bpy.data.objects.get(name)
            if obj is None: continue
            self.states[name] = {"location": obj.location.copy(), "rotation": obj.rotation_euler.copy(),
                                 "scale": obj.scale.copy(), "data": obj.data,
                                 "materials": [slot.material for slot in obj.material_slots],
                                 "collections": list(obj.users_collection),
                                 "custom": {key: _json_value(obj[key]) for key in obj.keys()},
                                 "hide": obj.hide_get(), "hideRender": obj.hide_render}
        self.modifier = None
        if method == "add_update_modifier":
            obj = bpy.data.objects[params["object"]]; name = params.get("name", str(params.get("type", "")).upper())
            mod = obj.modifiers.get(name)
            self.modifier = (obj, name, mod.type if mod else None,
                             _modifier_record(mod) if mod else None)
        if method == "run_thestra_operation" and params.get("operation") == "recalculate_normals":
            seen = set()
            for name in params.get("objects", []):
                data = bpy.data.objects[name].data
                if data.as_pointer() in seen: continue
                seen.add(data.as_pointer())
                users = [obj.name for obj in bpy.data.objects if obj.data == data]
                self.data_backups.append(("MESH", data, data.copy(), users))
        if method == "run_thestra_operation" and params.get("operation") == "update_camera_calibration":
            camera = bpy.data.objects.get("TH_CAMERA_PREVIEW")
            if camera and camera.type == "CAMERA":
                fields = {key: _json_value(getattr(camera.data, key)) for key in
                          ("type", "lens", "sensor_fit", "sensor_width", "sensor_height", "clip_start",
                           "clip_end", "shift_x", "shift_y", "ortho_scale")}
                self.data_backups.append(("CAMERA", camera.data, fields, [camera.name]))
        self.before = {name: _object_record(bpy.data.objects[name]) for name in self.states}

    def restore(self):
        for obj in list(bpy.data.objects):
            if obj.name not in self.object_names:
                data = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if data and data.users == 0:
                    collection = getattr(bpy.data, f"{type(data).__name__.lower()}s", None)
                    if collection is not None:
                        try: collection.remove(data)
                        except (RuntimeError, TypeError): pass
        for name, state in self.states.items():
            obj = bpy.data.objects.get(name)
            if obj is None: continue
            obj.location, obj.rotation_euler, obj.scale = state["location"], state["rotation"], state["scale"]
            obj.hide_set(state["hide"]); obj.hide_render = state["hideRender"]
            for key in list(obj.keys()): del obj[key]
            for key, value in state["custom"].items(): obj[key] = value
            if state["data"] is not None: obj.data = state["data"]
            if obj.type == "MESH":
                obj.data.materials.clear()
                for material in state["materials"]: obj.data.materials.append(material)
            for collection in list(obj.users_collection): collection.objects.unlink(obj)
            for collection in state["collections"]:
                if obj.name not in collection.objects: collection.objects.link(obj)
        for kind, original, backup, _users in self.data_backups:
            if kind == "MESH":
                import bmesh
                bm = bmesh.new(); bm.from_mesh(backup); bm.to_mesh(original); bm.free(); original.update()
            else:
                for key, value in backup.items(): setattr(original, key, value)
        if self.modifier:
            obj, name, kind, record = self.modifier
            current = obj.modifiers.get(name)
            if current: obj.modifiers.remove(current)
            if kind:
                restored = obj.modifiers.new(name, kind)
                for key, value in record.items():
                    if key not in ("name", "type") and hasattr(restored, key): setattr(restored, key, value)
        for material in list(bpy.data.materials):
            if material.name not in self.material_names and material.users == 0:
                bpy.data.materials.remove(material)
        for mesh in list(bpy.data.meshes):
            if mesh.name not in self.mesh_names and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for camera in list(bpy.data.cameras):
            if camera.name not in self.camera_names and camera.users == 0:
                bpy.data.cameras.remove(camera)
        scene = bpy.context.scene
        (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage,
         scene.render.pixel_aspect_x, scene.render.pixel_aspect_y, scene.camera) = self.render_state
        bpy.context.view_layer.update()

    def discard(self):
        for kind, _original, backup, _users in self.data_backups:
            if kind == "MESH" and backup.users == 0:
                bpy.data.meshes.remove(backup)


_TEST_FAIL_AFTER_WRITES = None
_test_write_count = 0


def _write_checkpoint():
    global _test_write_count
    _test_write_count += 1
    if _TEST_FAIL_AFTER_WRITES is not None and _test_write_count >= _TEST_FAIL_AFTER_WRITES:
        raise RuntimeError("injected mutation failure")


def _mutate(method, params):
    if method == "transform_objects":
        names = params.get("objects")
        if not isinstance(names, list) or not names:
            raise ValueError("objects must be a non-empty list")
        objects = [_object(name) for name in names]
        location = _vec(params["location"], "location") if "location" in params else None
        delta = _vec(params["deltaLocation"], "deltaLocation") if "deltaLocation" in params else None
        rotation = _vec(params["rotationEuler"], "rotationEuler") if "rotationEuler" in params else None
        scale = _vec(params["scale"], "scale") if "scale" in params else None
        for obj in objects:
            if location is not None: obj.location = location
            if delta is not None: obj.location = tuple(a + b for a, b in zip(obj.location, delta))
            if rotation is not None: obj.rotation_euler = rotation
            if scale is not None: obj.scale = scale
            for key, target, additive in (("locationAxes", obj.location, False),
                                          ("deltaAxes", obj.location, True),
                                          ("rotationAxes", obj.rotation_euler, False),
                                          ("scaleAxes", obj.scale, False)):
                for axis, value in _axis_values(params[key], key).items() if key in params else ():
                    index = "xyz".index(axis)
                    target[index] = target[index] + value if additive else value
            _write_checkpoint()
        return {"objects": names}
    if method == "assign_material":
        material = bpy.data.materials.get(params.get("material"))
        semantic = params.get("semanticId")
        if material is None and semantic:
            material = next((item for item in bpy.data.materials
                             if item.get("sr_material_id") == semantic), None)
        if material is None and semantic:
            _use_repo_modules()
            import second_rite_asset_core as core
            from material_library import build_material
            material = build_material(core, semantic)
        if material is None: raise ValueError(f"unknown material {params.get('material') or semantic!r}")
        names = params.get("objects") or []
        objects = [_object(name) for name in names]
        if not objects: raise ValueError("objects must be a non-empty list")
        for obj in objects:
            if obj.type != "MESH": raise ValueError(f"object {obj.name!r} is not a mesh")
        for obj in objects:
            obj.data.materials.clear(); obj.data.materials.append(material)
            _write_checkpoint()
        return {"objects": names, "material": material.name, "semanticId": material.get("sr_material_id")}
    if method == "link_mesh_datablock":
        source = _object(params.get("source"))
        targets = params.get("targets") or []
        target_objects = [_object(name) for name in targets]
        if source.type != "MESH" or not target_objects: raise ValueError("source mesh and targets are required")
        for target in target_objects:
            if target.type != "MESH": raise ValueError(f"object {target.name!r} is not a mesh")
        for target in target_objects:
            target.data = source.data
            _write_checkpoint()
        return {"source": source.name, "targets": targets, "mesh": source.data.name,
                "implications": "Targets now share geometry and mesh material slots; edits affect every user. Export may still duplicate instances depending on the exporter."}
    if method == "create_primitive":
        kind = params.get("kind", "cube")
        location = _vec(params.get("location", (0, 0, 0)), "location")
        collection_name = params.get("collection")
        coll = bpy.data.collections.get(collection_name)
        if kind == "cube": bpy.ops.mesh.primitive_cube_add(size=float(params.get("size", 1)), location=location)
        elif kind == "plane": bpy.ops.mesh.primitive_plane_add(size=float(params.get("size", 1)), location=location)
        elif kind == "cylinder": bpy.ops.mesh.primitive_cylinder_add(vertices=int(params.get("vertices", 16)), radius=float(params.get("radius", .5)), depth=float(params.get("depth", 1)), location=location)
        obj = bpy.context.object; obj.name = params["name"]
        for old in list(obj.users_collection): old.objects.unlink(obj)
        coll.objects.link(obj)
        _write_checkpoint()
        return _object_record(obj)
    if method == "move_objects_to_collection":
        coll = bpy.data.collections.get(params.get("collection"))
        names = params.get("objects") or []
        objects = [_object(name) for name in names]
        mode = params.get("mode", "move")
        for obj in objects:
            if mode == "move":
                for old in list(obj.users_collection): old.objects.unlink(obj)
            if obj.name not in coll.objects: coll.objects.link(obj)
            _write_checkpoint()
        return {"objects": names, "collection": coll.name, "mode": mode}
    if method == "add_update_modifier":
        obj = _object(params.get("object"))
        kind = str(params.get("type", "")).upper()
        name = params.get("name", kind)
        if params.get("remove"):
            modifier = obj.modifiers.get(name)
            if modifier is None: raise ValueError(f"unknown modifier {name!r}")
            obj.modifiers.remove(modifier)
            _write_checkpoint()
            return {"object": obj.name, "name": name, "removed": True}
        modifier = obj.modifiers.get(name) or obj.modifiers.new(name, kind)
        for key, value in params.get("settings", {}).items():
            setattr(modifier, key, _validate_modifier_setting(kind, key, value))
            _write_checkpoint()
        return {"object": obj.name, "name": modifier.name, "type": modifier.type}
    if method == "make_mesh_unique":
        names = params.get("objects") or []
        objects = [_object(name) for name in names]
        if not objects: raise ValueError("objects must be a non-empty list")
        for obj in objects:
            if obj.type != "MESH": raise ValueError(f"object {obj.name!r} is not a mesh")
        for obj in objects:
            obj.data = obj.data.copy(); _write_checkpoint()
        return {"objects": names, "unique": True,
                "implications": "Each object now owns independent mesh geometry and material slots; later edits no longer propagate and memory/export size may increase."}
    if method == "run_thestra_operation":
        operation = params.get("operation")
        if operation == "validate_collections":
            return _read("validate_thestra_collections", {})
        if operation == "recalculate_normals":
            import bmesh
            names = params.get("objects") or [obj.name for obj in bpy.context.selected_objects]
            objects = [_object(name) for name in names]
            if any(obj.type != "MESH" for obj in objects): raise ValueError("normal recalculation requires mesh objects")
            for obj in objects:
                bm = bmesh.new(); bm.from_mesh(obj.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(obj.data); bm.free(); _write_checkpoint()
            return {"objects": names, "operation": operation}
        if operation == "update_camera_calibration":
            record = params.get("record")
            if not isinstance(record, dict): raise ValueError("record object is required")
            _use_repo_modules()
            import thestra_camera
            camera = thestra_camera.create_or_update_camera(record)
            preview = bpy.data.collections["TH_CAMERA_PREVIEW"]
            if camera.name not in preview.objects: preview.objects.link(camera)
            _write_checkpoint()
            return {"camera": camera.name, "operation": operation}
        if operation == "stage_walker_preview":
            collection = bpy.data.collections["TH_PREVIEW_ACTORS"]
            existing = bpy.data.objects.get("ACTOR_Walker_Billboard")
            if existing:
                return {"object": existing.name, "operation": operation, "created": False}
            bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, 0.0, 0.875),
                                             rotation=(math.radians(90), 0.0, 0.0))
            actor = bpy.context.object; actor.name = "ACTOR_Walker_Billboard"
            actor.scale = (0.4, 1.75, 1.0)
            for old in list(actor.users_collection): old.objects.unlink(actor)
            collection.objects.link(actor); actor["th_preview_actor"] = "walker"
            _write_checkpoint()
            return {"object": actor.name, "operation": operation, "created": True}
        raise ValueError(f"unknown Thestra operation {operation!r}")
    raise ValueError(f"unknown mutation method {method!r}")


_mutation_requests = {}
_SERVER = None


def _refresh_after_undo(*_args):
    """Make restored object bounds observable immediately after Ctrl+Z.

    Blender 5.1 can restore transform RNA from a timer-dispatched operator
    while leaving ``Object.dimensions`` on the pre-undo dependency-graph
    evaluation.  That makes the viewport and every bridge serializer report a
    partially undone transform until some unrelated edit dirties the graph.
    The handler does not perform an undo or alter authored state; it only asks
    Blender to evaluate the state its own undo stack just restored.
    """
    if bpy is None:
        return
    for obj in bpy.context.scene.objects:
        obj.update_tag()
    if bpy.context.view_layer is not None:
        bpy.context.view_layer.update()
    for window in bpy.context.window_manager.windows:
        if window.screen is None:
            continue
        for area in window.screen.areas:
            area.tag_redraw()


def _error_payload(exc):
    text = str(exc)
    if isinstance(exc, PermissionError): code = "auth_failed"
    elif isinstance(exc, BridgeStoppedError): code = "bridge_stopped"
    elif isinstance(exc, MutationBusyError): code = "mutation_busy"
    elif isinstance(exc, ProtocolError): code = "protocol_error"
    elif text.startswith("stale_context:"): code = "stale_context"
    elif isinstance(exc, TimeoutError): code = "timeout"
    elif isinstance(exc, ValueError): code = "invalid_request"
    else: code = "server_error"
    return {"code": code, "message": text}


if bpy is not None:
    class THESTRA_OT_live_bridge_mutation(bpy.types.Operator):
        bl_idname = "thestra.live_bridge_mutation"
        bl_label = "Thestra Live Bridge Mutation"
        bl_options = {"REGISTER", "UNDO"}
        request_key: bpy.props.StringProperty(options={"HIDDEN"})

        def execute(self, _context):
            pending = _mutation_requests.get(self.request_key)
            if pending is None:
                self.report({"ERROR"}, "mutation request state is unavailable")
                return {"CANCELLED"}
            method, params, sink = pending
            snapshot = _MutationSnapshot(method, params)
            global _test_write_count
            _test_write_count = 0
            try:
                value = _mutate(method, params)
                touched = [name for name in _touched_names(method, params, value) if bpy.data.objects.get(name)]
                sink["result"] = value
                sink["before"] = snapshot.before
                sink["after"] = {name: _object_record(bpy.data.objects[name]) for name in touched}
                snapshot.discard()
            except Exception as exc:
                try: snapshot.restore()
                except Exception as rollback_exc:
                    sink["error"] = (f"{type(exc).__name__}: {exc}; rollback failed: "
                                     f"{type(rollback_exc).__name__}: {rollback_exc}")
                else:
                    sink["error"] = f"{type(exc).__name__}: {exc}"
            return {"FINISHED"} if "error" not in sink else {"CANCELLED"}


def _mutation_ui_context():
    """Return a real editor context so Blender records an interactive undo."""
    return _view3d_context()


@dataclass
class _Request:
    request_id: object
    method: str
    params: dict
    done: threading.Event = field(default_factory=threading.Event)
    response: dict | None = None
    is_mutation: bool = False


class BridgeStoppedError(RuntimeError): pass
class MutationBusyError(RuntimeError): pass


class LiveBridgeServer:
    def __init__(self, token: str, port: int = 8765):
        _require_blender()
        if not token or len(token) < 16: raise ValueError("bridge token must be at least 16 characters")
        self.token, self.port = token, int(port)
        self.session_id = hashlib.sha256(f"{time.time_ns()}:{os.getpid()}".encode()).hexdigest()[:16]
        self.latest_share = None
        self.failure = None
        self.mutation_generation = 0
        self._seen_ids = set()
        self._id_lock = threading.Lock()
        self._mutation_lock = threading.Lock(); self._mutation_busy = False
        self._queue = queue.Queue(); self._stop = threading.Event(); self._socket = None; self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._stop.clear()
        self.failure = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", self.port)); self._socket.listen(4); self._socket.settimeout(.25)
        self.port = self._socket.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, name="thestra-live-bridge", daemon=True)
        global _SERVER
        _SERVER = self
        self._thread.start(); bpy.app.timers.register(self._drain, first_interval=.02, persistent=True)

    def stop(self):
        global _SERVER
        if _SERVER is self: _SERVER = None
        self._stop.set()
        if self._socket:
            try: self._socket.close()
            except OSError: pass
        self._socket = None
        while True:
            try: item = self._queue.get_nowait()
            except queue.Empty: break
            item.response = {"id": item.request_id, "ok": False,
                             "error": {"code": "bridge_stopped", "message": "bridge has shut down"}}
            if item.is_mutation:
                with self._mutation_lock: self._mutation_busy = False
            item.done.set()

    def _serve(self):
        while not self._stop.is_set():
            listener = self._socket
            if listener is None: break
            try: connection, _address = listener.accept()
            except socket.timeout: continue
            except OSError as exc:
                if not self._stop.is_set():
                    self.failure = f"server socket failed: {exc}"
                    self.stop()
                break
            threading.Thread(target=self._connection, args=(connection,), daemon=True).start()

    @property
    def running(self):
        return not self._stop.is_set() and self._thread is not None and self._thread.is_alive()

    def _connection(self, connection):
        with connection:
            stream = connection.makefile("rb")
            line = stream.readline(1024 * 1024 + 2)
            request_id = None
            try:
                if self._stop.is_set(): raise BridgeStoppedError("bridge has shut down")
                request_id, method, params, token, _timestamp = validate_request(decode_message(line))
                if not hmac.compare_digest(token, self.token): raise PermissionError("authentication failed")
                _validate_method_params(method, params)
                with self._id_lock:
                    if request_id in self._seen_ids: raise ProtocolError("duplicate request id")
                    self._seen_ids.add(request_id)
                is_mutation = method in MUTATION_METHODS
                if is_mutation:
                    with self._mutation_lock:
                        if self._mutation_busy: raise MutationBusyError("another mutation is already pending")
                        self._mutation_busy = True
                item = _Request(request_id, method, params, is_mutation=is_mutation); self._queue.put(item)
                if not item.done.wait(60): raise TimeoutError("Blender main thread did not answer within 60 seconds")
                response = item.response
            except Exception as exc:
                response = {"id": request_id, "ok": False, "error": _error_payload(exc)}
            try:
                payload = encode_message(response)
            except ProtocolError:
                payload = encode_message({"id": request_id, "ok": False,
                                          "error": {"code": "response_too_large",
                                                    "message": "response exceeds 1 MiB limit"}})
            try: connection.sendall(payload)
            except OSError: pass

    def _drain(self):
        if self._stop.is_set(): return None
        try: item = self._queue.get_nowait()
        except queue.Empty: return .02
        try:
            _validate_method_params(item.method, item.params)
            if item.method in READ_METHODS: result = _read(item.method, item.params)
            elif item.method in MUTATION_METHODS:
                _validate_mutation(item.method, item.params)
                expected = item.params.get("expectedFingerprint")
                if expected != _fingerprint():
                    raise RuntimeError("stale_context: expectedFingerprint does not match live context")
                before = _fingerprint()
                sink = {}
                mutation_key = f"{item.request_id}:{time.time_ns()}"
                _mutation_requests[mutation_key] = (item.method, item.params, sink)
                window, area, region = _mutation_ui_context()
                with bpy.context.temp_override(window=window, area=area, region=region):
                    # Ensure the pre-mutation undo snapshot contains settled
                    # evaluated bounds as well as the authored RNA values.
                    bpy.context.view_layer.update()
                    # Timer-dispatched operators do not reliably establish a
                    # pre-mutation editor undo state on Blender 5.1. Push that
                    # state explicitly while retaining UNDO on the one
                    # registered operator that performs the mutation.
                    pushed = bpy.ops.ed.undo_push(message="Thestra Live Bridge Mutation")
                    if "FINISHED" not in pushed:
                        raise RuntimeError("could not establish Blender undo state")
                    outcome = bpy.ops.thestra.live_bridge_mutation(
                        "EXEC_DEFAULT", request_key=mutation_key)
                    bpy.context.view_layer.update()
                if "error" in sink: raise RuntimeError(sink["error"])
                if "FINISHED" not in outcome: raise RuntimeError("mutation operator was cancelled")
                value = sink["result"]
                self.mutation_generation += 1
                result = {"result": value, "before": sink.get("before", {}), "after": sink.get("after", {}),
                          "beforeFingerprint": before, "afterFingerprint": _fingerprint(),
                          "mutationGeneration": self.mutation_generation}
            else: raise ValueError(f"method {item.method!r} is not allowed")
            item.response = {"id": item.request_id, "ok": True, "result": result}
        except Exception as exc:
            item.response = {"id": item.request_id, "ok": False, "error": _error_payload(exc)}
        finally:
            if "mutation_key" in locals():
                _mutation_requests.pop(mutation_key, None)
            item.done.set()
            if item.is_mutation:
                with self._mutation_lock: self._mutation_busy = False
        return .001 if not self._queue.empty() else .02


def register_operator():
    if bpy is not None:
        bpy.utils.register_class(THESTRA_OT_live_bridge_mutation)
        if _refresh_after_undo not in bpy.app.handlers.undo_post:
            bpy.app.handlers.undo_post.append(_refresh_after_undo)


def unregister_operator():
    if bpy is not None:
        if _refresh_after_undo in bpy.app.handlers.undo_post:
            bpy.app.handlers.undo_post.remove(_refresh_after_undo)
        try: bpy.utils.unregister_class(THESTRA_OT_live_bridge_mutation)
        except RuntimeError: pass
