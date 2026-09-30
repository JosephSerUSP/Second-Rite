"""Blender side of build_asset_library.py: mark SR_GroundCover as an asset, or describe it.

    blender --background --factory-startup --python tools/blender/asset_library_source.py -- build OUT.blend
    blender --background --factory-startup --python tools/blender/asset_library_source.py -- describe [FILE.blend]

`build` creates the node group with `ground_cover.build_group()`, marks it as an asset
with the metadata in `build_asset_library.py`, and saves a `.blend` holding nothing else.
`describe` prints one `ASSET_LIBRARY_DESCRIPTION {json}` line: the group's interface,
its node and link counts, and its asset metadata, from FILE if given and from a fresh
build otherwise. The test compares the two.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import build_asset_library as spec  # noqa: E402
import ground_cover  # noqa: E402


def describe(group) -> dict:
    sockets = []
    for item in group.interface.items_tree:
        if item.item_type != "SOCKET":
            continue
        default = getattr(item, "default_value", None)
        if hasattr(default, "name"):  # an object or collection default is a datablock
            default = default.name
        sockets.append({"name": item.name, "in_out": item.in_out, "type": item.socket_type,
                        "default": default if isinstance(default, (int, float, str, type(None))) else None,
                        "min": getattr(item, "min_value", None), "max": getattr(item, "max_value", None)})
    asset = group.asset_data
    return {
        "declaredInputs": sorted(ground_cover.INPUTS),
        "sockets": sockets,
        "nodes": dict(sorted(collections.Counter(n.bl_idname for n in group.nodes).items())),
        "links": len(group.links),
        "asset": None if asset is None else {
            "author": asset.author, "copyright": asset.copyright, "license": asset.license,
            "description": asset.description, "tags": sorted(t.name for t in asset.tags),
            "catalog_id": asset.catalog_id},
    }


def build(output: Path) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    group = ground_cover.build_group()
    (_, description, tags) = spec.ASSETS[ground_cover.GROUP_NAME]
    group.asset_mark()
    asset = group.asset_data
    asset.author = spec.AUTHOR
    asset.copyright = spec.COPYRIGHT
    asset.license = spec.LICENSE
    asset.description = description
    for tag in tags:
        asset.tags.new(tag)
    asset.catalog_id = spec.CATALOG_ID
    users = [i.name for i in bpy.data.user_map(subset=[group])[group]]
    if users:
        raise SystemExit(f"{group.name} is not self-contained; it is used by {users}")
    others = [g.name for g in bpy.data.node_groups if g is not group]
    if others or bpy.data.objects or bpy.data.materials or bpy.data.images:
        raise SystemExit("the library file must hold the asset and nothing else")
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0  # no .blend1 backup beside the library file
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()), compress=False)
    print(f"ASSET LIBRARY BUILT {output}")


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: -- build OUT.blend | describe [FILE.blend]")
    if argv[0] == "build":
        build(Path(argv[1]))
    elif argv[0] == "describe":
        if len(argv) > 1:
            bpy.ops.wm.open_mainfile(filepath=str(Path(argv[1]).resolve()))
            group = bpy.data.node_groups[ground_cover.GROUP_NAME]
        else:
            group = ground_cover.build_group()
            group.asset_mark()
        print("ASSET_LIBRARY_DESCRIPTION " + json.dumps(describe(group)))
    else:
        raise SystemExit(f"unknown command {argv[0]!r}")


if __name__ == "__main__":
    main()
