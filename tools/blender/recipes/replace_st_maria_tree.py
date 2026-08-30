"""Replace St. Maria's foreground bougainvillea with a generated tree.

This is a surgical edit, not a rebuild.  ``st_maria_praca.py`` regenerates the
whole document and would destroy hand authoring, so this script opens the
existing file, removes exactly the two placeholder objects, adds the generated
specimen to the same collection, and saves.  Everything else is left alone.

Blender must not have the document open: it holds no lock, so a running
session would simply overwrite this edit on its next save.

    blender -b -noaudio --factory-startup -P tools/blender/recipes/replace_st_maria_tree.py

Pass ``-- --dry-run`` to report what would change without writing.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
sys.path.insert(0, str(ROOT / "tools/blender/recipes"))
import tree_material  # noqa: E402
from tree_generator import generate, preset, reduce_lod, validate  # noqa: E402
from tree_mesh import branch_mesh, foliage_mesh  # noqa: E402

DOCUMENT = ROOT / "projects/hichaukitoden-game/assets/authoring/environments/st_maria_praca.blend"
#: The placeholder it replaces: an eight-vertex box trunk and a 42-vertex blob.
REPLACES = ("FG_bougainvillea_trunk", "FG_bougainvillea_crown")
COLLECTION = "21_FOREGROUND"
NAME = "FG_praca_tree"
#: The bougainvillea stood at x=-1.7, y=20.5 and topped out near 6.55 m.
LOCATION = (-1.7, 20.5, 0.0)


def _mesh_object(name, verts, faces, material, uvs=None, smooth=False):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata([list(v) for v in verts], [], [list(f) for f in faces])
    mesh.update()
    if uvs:
        layer = mesh.uv_layers.new(name="UVMap")
        for loop, coord in enumerate(uvs):
            layer.data[loop].uv = coord
    if material is not None:
        mesh.materials.append(material)
    if smooth:
        for polygon in mesh.polygons:
            polygon.use_smooth = True
    return bpy.data.objects.new(name, mesh)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preset", default="round_shade")
    parser.add_argument("--height", type=float, default=6.6)
    parser.add_argument("--crown-radius", type=float, default=2.1)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--document", type=Path, default=DOCUMENT)
    args = parser.parse_args(argv)

    bpy.ops.wm.open_mainfile(filepath=str(args.document.resolve()))

    collection = bpy.data.collections.get(COLLECTION)
    if collection is None:
        raise SystemExit(f"collection {COLLECTION} is missing; is this the right document?")
    missing = [name for name in REPLACES if bpy.data.objects.get(name) is None]
    if missing == list(REPLACES):
        raise SystemExit("the bougainvillea is already gone; nothing to replace")
    if missing:
        raise SystemExit("partially replaced already, refusing to guess: missing " + ", ".join(missing))
    for suffix in ("BRANCHES", "CARDS"):
        if bpy.data.objects.get(f"{NAME}_{suffix}"):
            raise SystemExit(f"{NAME}_{suffix} already exists; remove it first")

    # Reuse the trunk's own wood so the replacement inherits the document's
    # authored material rather than introducing a second one.
    wood = bpy.data.objects[REPLACES[0]].data.materials[0]

    spec = preset(args.preset, seed_offset=args.seed_offset,
                  height=args.height, crown_radius=args.crown_radius)
    skeleton = generate(spec, "authoring")
    validate(skeleton)
    skeleton = reduce_lod(skeleton, "low")
    validate(skeleton, "low")

    verts, faces = branch_mesh(skeleton, sides=6)
    card_verts, card_faces, card_uvs = foliage_mesh(skeleton, lod="low")
    print(f"replacing {', '.join(REPLACES)} with {NAME}_BRANCHES/{NAME}_CARDS")
    print(f"  preset {spec.name} seed {spec.seed} height {spec.height} "
          f"crown radius {spec.crown_radius}")
    print(f"  {len(skeleton.segments)} segments, {len(skeleton.foliage_indices)} cards, "
          f"{len(verts) + len(card_verts)} vertices")
    if args.dry_run:
        print("DRY RUN, nothing written")
        return

    for name in REPLACES:
        obj = bpy.data.objects[name]
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data and data.users == 0:
            bpy.data.meshes.remove(data)

    branches = _mesh_object(NAME + "_BRANCHES", verts, faces, wood, smooth=True)
    cards = _mesh_object(NAME + "_CARDS", card_verts, card_faces,
                         tree_material.foliage_material(), card_uvs)
    for obj in (branches, cards):
        collection.objects.link(obj)
        obj.location = LOCATION
        obj["treePreset"] = spec.name
        obj["treeLOD"] = "low"
        obj["treeSeed"] = spec.seed

    backup = args.document.with_suffix(".blend.bak")
    shutil.copy2(args.document, backup)
    bpy.ops.wm.save_mainfile(filepath=str(args.document.resolve()))
    print(f"SAVED {args.document} (previous version kept at {backup.name})")


main()
