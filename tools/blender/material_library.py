"""Second Gate material library: textures bound to semantic material IDs.

The semantic layer already exists in `tools/asset-language/materials.json` --
18 IDs like `dark_wood` and `rough_limestone`, each with a base colour and
roughness hint. Recipes bind those IDs. This module adds an OPTIONAL texture
set underneath each ID, so a recipe never changes when a texture arrives, is
replaced by a hand-authored one, or is promoted from placeholder to final.

    tools/asset-language/materials.json      semantic id + colour fallback
              |
    projects/<project>/assets/materials/<id>/material.json    texture set
              |
    build_material(id)   ->  Blender Principled material

## On disk

    assets/materials/<semantic_id>/
        material.json
        albedo.png
        height.png        (optional)
        roughness.png     (optional)
        ao.png            (optional)

`material.json`:

    {
      "materialKind": "second_gate_material",
      "version": 1,
      "semanticId": "dark_wood",
      "status": "placeholder",
      "worldSizeMetres": 2.0,
      "maps": {"albedo": "albedo.png", "height": "height.png"},
      "provenance": {
        "origin": "procedural",
        "license": "CC0-1.0",
        "retrieved": "2026-08-26",
        "sha256": {"albedo.png": "..."}
      }
    }

`worldSizeMetres` is the load-bearing field: it says how many metres one tile
spans. Everything is textured in WORLD space at that scale, so the same oak
maps identically onto a door, a beam and a floor regardless of object size --
which is the whole reason a shared library beats per-object materials. See the
"preserve physically coherent world/object-space texture scale" rule in
`docs/design/town-authoring-known-good.md`.

`status` carries maturity, and is the promotion path:

    placeholder -> authored -> promoted

Nothing in the pipeline behaves differently per status; it exists so a review
can tell at a glance which surfaces are still standing in for real art.

`provenance` is mandatory. For anything not generated in-repo it must carry a
source and an SPDX license id, per the known-good doc's rule that every fresh
external material records source, license, retrieval date and hashes.

Validate without Blender:

    python tools/blender/material_library.py check
"""

from __future__ import annotations

import argparse
import os
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROJECT = ROOT / "projects" / "hichaukitoden-game"
MATERIAL_KIND = "second_gate_material"
MATERIAL_VERSION = 1
STATUSES = ("placeholder", "authored", "promoted")
MAP_SLOTS = ("albedo", "height", "roughness", "ao")

# How hard `height` pushes the Bump node.
#
# This was 0.35 while every height map in the library was a procedural
# placeholder, where more strength only made soft noise louder. Sourced photo
# displacement carries real relief, and at 0.35 almost none of it survived to a
# 256px frame -- the single largest reason these surfaces read flat. There is
# no normal-map path on purpose: everything is box-projected from world
# position with no UVs, so there is no tangent basis a normal map could be
# interpreted against, and Bump is the projection-independent way to get the
# same relief. See tools/materials/fetch_cc0_materials.py.
BUMP_STRENGTH = 1.2

# How hard the AO map is pushed into base colour, as an exponent: ao ** gain.
# An exponent rather than a blend because it leaves lit faces at 1.0 untouched
# and deepens only what is already occluded, which is exactly the crevice.
AO_GAIN = 1.7

# Both are overridable from the environment so a comparison strip can be
# rendered without editing the library between shots. Authoring decisions get
# baked back into the constants above; the env vars are for the experiment.
BUMP_STRENGTH = float(os.environ.get("SR_BUMP_STRENGTH", BUMP_STRENGTH))
AO_GAIN = float(os.environ.get("SR_AO_GAIN", AO_GAIN))


def library_root(project: Path | None = None) -> Path:
    return (Path(project) if project else DEFAULT_PROJECT) / "assets" / "materials"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic_ids() -> set[str]:
    registry = json.loads((ROOT / "tools" / "asset-language" / "materials.json")
                          .read_text(encoding="utf-8"))
    return {entry["id"] for entry in registry["materials"]}


def load(semantic_id: str, project: Path | None = None) -> dict | None:
    """Return the texture record for a semantic ID, or None if untextured."""
    directory = library_root(project) / semantic_id
    record_path = directory / "material.json"
    if not record_path.is_file():
        return None
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["_directory"] = str(directory)
    return record


def validate(record: dict, *, known_ids: set[str] | None = None) -> list[str]:
    """Return a list of problems; empty means valid."""
    problems: list[str] = []
    directory = Path(record["_directory"])
    known = semantic_ids() if known_ids is None else known_ids

    if record.get("materialKind") != MATERIAL_KIND:
        problems.append(f"materialKind must be {MATERIAL_KIND!r}")
    if record.get("version") != MATERIAL_VERSION:
        problems.append(f"version must be {MATERIAL_VERSION}")
    semantic = record.get("semanticId")
    if semantic not in known:
        problems.append(f"semanticId {semantic!r} is not in materials.json")
    if directory.name != semantic:
        problems.append(f"directory {directory.name!r} disagrees with semanticId {semantic!r}")
    if record.get("status") not in STATUSES:
        problems.append(f"status must be one of {STATUSES}")

    size = record.get("worldSizeMetres")
    if not isinstance(size, (int, float)) or size <= 0:
        problems.append("worldSizeMetres must be a positive number")

    maps = record.get("maps") or {}
    if "albedo" not in maps:
        problems.append("maps.albedo is required")
    for slot, filename in maps.items():
        if slot not in MAP_SLOTS:
            problems.append(f"unknown map slot {slot!r}")
        if not (directory / filename).is_file():
            problems.append(f"missing map file {filename!r}")

    provenance = record.get("provenance") or {}
    if not provenance.get("origin"):
        problems.append("provenance.origin is required")
    if not provenance.get("license"):
        problems.append("provenance.license is required")
    if str(provenance.get("origin", "")).startswith("http") and not provenance.get("retrieved"):
        problems.append("external material requires provenance.retrieved")

    hashes = provenance.get("sha256") or {}
    for slot, filename in maps.items():
        path = directory / filename
        if not path.is_file():
            continue
        if filename not in hashes:
            problems.append(f"provenance.sha256 missing entry for {filename!r}")
        elif hashes[filename] != sha256(path):
            problems.append(f"{filename!r} does not match its recorded sha256")
    return problems


def iter_library(project: Path | None = None):
    root = library_root(project)
    if not root.is_dir():
        return
    for directory in sorted(root.iterdir()):
        if (directory / "material.json").is_file():
            yield load(directory.name, project)


# --------------------------------------------------------------------------
# Blender side
# --------------------------------------------------------------------------

def build_material(asset_core, semantic_id: str, *, project: Path | None = None,
                   blend: float = 0.25):
    """Semantic material, with library textures applied when they exist.

    Falls back to the flat semantic colour when the ID has no texture set, so a
    recipe can bind every surface before any art exists.
    """
    import bpy

    material = asset_core.make_material(f"sr_{semantic_id}", semantic_id=semantic_id)
    record = load(semantic_id, project)
    if record is None:
        return material

    directory = Path(record["_directory"])
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    principled = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if principled is None:
        return material

    # World-space box projection: identical texel scale on every object,
    # independent of object size or UVs.
    coord = nodes.new("ShaderNodeNewGeometry")
    mapping = nodes.new("ShaderNodeMapping")
    scale = 1.0 / float(record["worldSizeMetres"])
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(coord.outputs["Position"], mapping.inputs["Vector"])

    def image_node(filename, non_color):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(directory / filename), check_existing=True)
        node.projection = "BOX"
        node.projection_blend = float(blend)
        node.extension = "REPEAT"
        if non_color:
            node.image.colorspace_settings.name = "Non-Color"
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        return node

    maps = record["maps"]
    albedo = image_node(maps["albedo"], False)
    if "ao" in maps:
        # Contact darkening belongs in the TEXTURE, never in a light: this
        # vocabulary has no key and a scene lit only by what the room contains
        # cannot produce its own crevice shadow. Multiplying it in is what
        # gives mortar joints, plank gaps and weave their depth at 256px.
        occlusion = nodes.new("ShaderNodeMixRGB")
        occlusion.blend_type = "MULTIPLY"
        occlusion.inputs["Fac"].default_value = 1.0
        links.new(albedo.outputs["Color"], occlusion.inputs["Color1"])
        ao_node = image_node(maps["ao"], True)
        if AO_GAIN != 1.0:
            power = nodes.new("ShaderNodeMath")
            power.operation = "POWER"
            power.inputs[1].default_value = AO_GAIN
            links.new(ao_node.outputs["Color"], power.inputs[0])
            links.new(power.outputs["Value"], occlusion.inputs["Color2"])
        else:
            links.new(ao_node.outputs["Color"], occlusion.inputs["Color2"])
        links.new(occlusion.outputs["Color"], principled.inputs["Base Color"])
    else:
        links.new(albedo.outputs["Color"], principled.inputs["Base Color"])
    if "roughness" in maps:
        links.new(image_node(maps["roughness"], True).outputs["Color"],
                  principled.inputs["Roughness"])
    if "height" in maps:
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = BUMP_STRENGTH
        links.new(image_node(maps["height"], True).outputs["Color"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], principled.inputs["Normal"])

    material["sr_material_status"] = record["status"]
    material["sr_material_world_size_m"] = float(record["worldSizeMetres"])
    return material


def main() -> None:
    parser = argparse.ArgumentParser(prog="material_library")
    parser.add_argument("command", choices=("check", "list"))
    parser.add_argument("--project", type=Path, default=None)
    args = parser.parse_args()

    known = semantic_ids()
    records = list(iter_library(args.project))
    if not records:
        print(f"no materials under {library_root(args.project)}")
        return

    failures = 0
    for record in records:
        problems = validate(record, known_ids=known) if args.command == "check" else []
        maps = ",".join(sorted((record.get("maps") or {}).keys()))
        status = record.get("status")
        print(f"{record.get('semanticId'):18s} {status:12s} "
              f"{record.get('worldSizeMetres')}m  [{maps}]"
              + ("" if not problems else "  FAILED"))
        for problem in problems:
            print(f"    - {problem}")
            failures += 1

    untextured = sorted(known - {r.get("semanticId") for r in records})
    if untextured:
        print(f"\nuntextured semantic ids ({len(untextured)}): {', '.join(untextured)}")
    if failures:
        raise SystemExit(f"{failures} problem(s)")


if __name__ == "__main__":
    main()
