"""Bind semantic material IDs to sourced CC0 photo-PBR sets.

The library shipped procedural placeholders so every surface could be bound
before any art existed. They did their job and they are the reason St. Maria's
interiors read FLAT: a placeholder carries family and nothing else, so a wall,
a floor and a counter all return the same soft noise at three colours.

This fetches real material sets from **ambientCG**, which publishes its
Materials under **CC0-1.0**, and records where every byte came from. It is a
maintainer action by design -- `docs/design/st-maria-interior-authoring.md`
says external textures need a real source, an SPDX licence and a retrieval
date, and that is a decision this tool writes down rather than assumes.

    python tools/materials/fetch_cc0_materials.py            # fetch all
    python tools/materials/fetch_cc0_materials.py whitewash  # one id
    python tools/materials/fetch_cc0_materials.py --check    # verify hashes

## Which maps, and the one that is deliberately missing

Each set arrives as Color, Roughness, Displacement, AmbientOcclusion and two
normal maps. Everything here is taken EXCEPT the normal maps, and that is not
an oversight:

`material_library.build_material` box-projects every texture from **world
position**, with no UVs anywhere in the vocabulary. A tangent-space normal map
has no tangent basis to be interpreted against in that setup -- Blender would
happily wire it up, and it would be bumpy in a way that has no defensible
relationship to the surface. The projection-independent equivalent is the
**Displacement map through a Bump node**, which derives its gradient from the
sampled height itself, so it is correct under box projection at any scale.
That is what `height.png` is here, and why raising its Bump strength -- not
adding a normal slot -- is what actually bought the relief.

`AmbientOcclusion` is multiplied into base colour rather than fed to a
shading input, which is this project's standing rule: contact darkening is
baked into the texture, never spent as direct light.

## The semantic ID owns the colour; the sourced set owns the structure

A photo set brings its own lighting conditions with it, and binding one raw
throws the town's palette away. Plaster004 averages a mid grey (155, 154, 150)
because it was shot on an overcast day -- while `whitewash` is declared in
`materials.json` as warm off-white (232, 228, 218). Bound raw, it turned every
limewashed wall in St. Maria into grey concrete, which is the FIRST thing the
colonial Portuguese vocabulary says not to do.

So each map is mean-matched to what the semantic ID already declares: albedo is
scaled per channel until its mean is `baseColorSrgb`, and roughness until its
mean is `roughnessHint`. The photograph keeps every bit of its variation,
relief and joint detail -- only its average is moved onto the authored colour.
The material stays recognisably the sourced scan, and the town stays the colour
it was designed to be. Where a pick was already right the correction is nearly
nothing: terracotta and dark wood move by a few units.

## Tile size is a SCREEN decision, not a metric one

`worldSizeMetres` was first set to the surface's real-world size, which is the
physically honest number and the wrong one. At 27.4 screen pixels per metre, a
2.6 m tile spans 71 pixels: every mortar joint in it lands under one pixel and
is filtered away before it reaches the frame. Sizes here are chosen so the
features that carry the material -- a course, a brick, a stone -- land at
roughly **three to six screen pixels**, which is the smallest detail this game
can actually show.

## What relief can and cannot do here

Three things were tried against a rendered comparison before any of this was
settled, and two of them did nothing:

- **Bump strength** 0.85 -> 4.0: no visible change. This vocabulary is
  deliberately keyless ("no sun, no key"), so the lighting is close to uniform,
  and a perturbed normal under uniform light barely changes what a surface
  reflects. Bump is nearly free here and nearly useless.
- **Halving the tile size** on an already-smooth material: no visible change.
- **Choosing a material that HAS structure**: the whole difference. Plaster004
  is smooth plaster -- almost no albedo variance and a nearly flat displacement
  -- so there were no crevices to deepen. PaintedPlaster016 is limewash over
  masonry, and the coursing survives to the frame.

So crevice depth in this renderer comes from the ALBEDO and its baked
occlusion, at a tile size that keeps features above a pixel. It does not come
from turning bump up.

## Size

Sets are downloaded at 1K and stored at 512, matching the library that already
exists. The game renders at 256x240 and materials are box-projected at two to
three metres per tile, so 512 is already finer than anything reaches the
screen -- and it keeps eight full sets to a few megabytes of repository.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
import zipfile
from pathlib import Path

import requests
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import material_library  # noqa: E402

SIZE = 512
LICENSE = "CC0-1.0"
API = "https://ambientcg.com/api/v2/full_json"

# semantic id -> ambientCG asset, tile size in metres, and WHY this one.
#
# Every pick here was made by looking at the previews side by side, not by
# matching a name: the polished Metal055A is a far worse wrought iron than the
# impure, pitted Metal052C, and Planks023A is grey driftwood rather than the
# dark tropical hardwood this town is built from.
RECIPES = {
    "whitewash": {
        # Bigger tile and lower contrast than feature size alone would want.
        # A wall here is 8.3m across, so at 1.6m the box projection repeated
        # five times over it and an adversarial review called it "generic
        # chevron wallpaper" -- correctly. Repetition on the largest surface in
        # the frame costs more than the courses gain, so the tile is sized to
        # cross the wall about three times instead.
        "albedoContrast": 0.38,
        "asset": "PaintedPlaster016", "worldSizeMetres": 2.8,
        "notes": "Caiacao over masonry. Limewash laid on a rubble-and-brick "
                 "wall, so the coursing reads THROUGH the paint -- which is "
                 "what a re-limed colonial wall actually is, and the only "
                 "kind of wall in this vocabulary that has crevices at all.",
    },
    "old_limestone": {
        "albedoContrast": 0.55,
        "asset": "PaintedPlaster014", "worldSizeMetres": 2.0,
        "notes": "The same limewash, older and dirtier, for surfaces that "
                 "have not been redone.",
    },
    "dark_wood": {
        "asset": "Wood051", "worldSizeMetres": 1.0,
        "notes": "Dark tropical hardwood: heavy, close-grained, the timber "
                 "the joinery vocabulary is built on.",
    },
    "terracotta": {
        "albedoContrast": 0.75,
        "asset": "Bricks094", "worldSizeMetres": 1.4,
        "notes": "Unglazed fired clay with joints -- floor tile, oven body "
                 "and flue all read from the same fabric.",
    },
    "rough_limestone": {
        "albedoContrast": 0.8,
        "asset": "Bricks102", "worldSizeMetres": 1.5,
        "notes": "Coursed rubble masonry for hearths and oven bases: the "
                 "structural stone, not the finished wall.",
    },
    "wrought_iron": {
        "asset": "Metal052C", "worldSizeMetres": 1.2,
        "notes": "Impure, pitted, barely reflective. Wrought iron is not "
                 "polished steel and the shiny sets read as chrome.",
    },
    "forge_scale": {
        "asset": "Metal063", "worldSizeMetres": 1.0,
        "notes": "Dark firescale on worked stock -- the surface an anvil and "
                 "a half-finished blade actually carry.",
    },
    "aged_cloth": {
        "asset": "Fabric066", "worldSizeMetres": 1.4,
        "notes": "Coarse undyed linen weave: sacking, aprons, the cloth a "
                 "bundle is tied in.",
    },
}

# ambientCG map name -> our slot. NormalGL/NormalDX are deliberately absent;
# see the module docstring.
WANTED = {
    "Color": ("albedo", False),
    "Roughness": ("roughness", True),
    "Displacement": ("height", True),
    "AmbientOcclusion": ("ao", True),
}


def download_zip(asset: str) -> bytes:
    response = requests.get(API, params={"type": "Material", "limit": 1,
                                         "id": asset,
                                         "include": "downloadData"},
                            timeout=120)
    response.raise_for_status()
    found = response.json().get("foundAssets") or []
    if not found:
        raise SystemExit(f"ambientCG has no asset {asset!r}")
    link = None
    for folder in (found[0].get("downloadFolders") or {}).values():
        for category in folder.get("downloadFiletypeCategories", {}).values():
            for entry in category.get("downloads", []):
                if entry.get("attribute") == "1K-PNG":
                    link = entry["fullDownloadPath"]
    if not link:
        raise SystemExit(f"{asset}: no 1K-PNG download offered")
    blob = requests.get(link, timeout=600)
    blob.raise_for_status()
    return blob.content


def semantic_record(semantic_id: str) -> dict:
    path = ROOT / "tools" / "asset-language" / "materials.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for entry in payload["materials"]:
        if entry["id"] == semantic_id:
            return entry
    raise SystemExit(f"{semantic_id!r} is not in materials.json")


def flatten_contrast(image: Image.Image, keep: float) -> Image.Image:
    """Pull every pixel toward the image's own mean by `keep`.

    Structure and blotchiness arrive from a photo together and are not the same
    thing. PaintedPlaster016 is the right WALL -- limewash over masonry, so the
    coursing reads through the paint -- but at full strength its brown patches
    read as camouflage across the biggest surface in the frame and fight every
    prop in front of it.

    So the albedo's contrast is pulled down while `height`, `ao` and
    `roughness` keep theirs. The relief and the baked crevice shading survive
    untouched; only the paint stops shouting. keep=1.0 changes nothing.
    """
    if keep >= 0.999:
        return image
    bands = []
    for band in image.split():
        stats = band.resize((64, 64), Image.LANCZOS)
        mean = sum(stats.getdata()) / (64 * 64)
        bands.append(band.point(
            lambda v, m=mean: max(0, min(255, int(m + (v - m) * keep + 0.5)))))
    return Image.merge(image.mode, bands)


def mean_match(image: Image.Image, target) -> Image.Image:
    """Scale each channel so the image's MEAN lands on `target`.

    Deliberately a scale rather than a blend toward a flat colour: a blend
    washes out exactly the variation the set was sourced for, while a scale
    moves the average and leaves every relative difference intact.
    """
    bands = image.split()
    scaled = []
    for band, want in zip(bands, target):
        stats = band.resize((64, 64), Image.LANCZOS)
        mean = sum(stats.getdata()) / (64 * 64)
        factor = (float(want) / mean) if mean > 1e-6 else 1.0
        scaled.append(band.point(
            lambda v, f=factor: max(0, min(255, int(v * f + 0.5)))))
    return Image.merge(image.mode, scaled)


def build(semantic_id: str, spec: dict, directory: Path) -> dict:
    semantic = semantic_record(semantic_id)
    archive = zipfile.ZipFile(io.BytesIO(download_zip(spec["asset"])))
    names = {Path(n).stem.rsplit("_", 1)[-1]: n for n in archive.namelist()
             if n.lower().endswith(".png")}

    directory.mkdir(parents=True, exist_ok=True)
    maps, written = {}, []
    for source, (slot, grey) in WANTED.items():
        if source not in names:
            continue
        image = Image.open(io.BytesIO(archive.read(names[source])))
        image = image.convert("L" if grey else "RGB")
        image = image.resize((SIZE, SIZE), Image.LANCZOS)
        if slot == "albedo":
            image = flatten_contrast(image, spec.get("albedoContrast", 1.0))
            image = mean_match(image, semantic["baseColorSrgb"])
        elif slot == "roughness":
            image = mean_match(
                image, (round(float(semantic["roughnessHint"]) * 255),))
        filename = f"{slot}.png"
        image.save(directory / filename, optimize=True)
        maps[slot] = filename
        written.append(filename)
    if "albedo" not in maps:
        raise SystemExit(f"{semantic_id}: {spec['asset']} shipped no Color map")

    derived = None
    if "ao" not in maps and "height" in maps:
        # Most ambientCG scan sets ship no AmbientOcclusion, because for a
        # height-field scan it is derivable rather than measured. Derive it:
        # a cavity map is the height minus its own blur, so anything sitting
        # BELOW its local neighbourhood -- a mortar joint, a plank gap, the
        # trough of a weave -- comes out dark and everything else stays white.
        # Recorded as derived, because it is not a map the source shipped.
        height = Image.open(directory / maps["height"]).convert("L")
        local = height.filter(ImageFilter.GaussianBlur(SIZE / 64.0))
        cavity = Image.new("L", height.size)
        cavity.putdata([max(0, min(255, 255 - int((b - h) * 2.4)))
                        for h, b in zip(height.getdata(), local.getdata())])
        cavity.save(directory / "ao.png", optimize=True)
        maps["ao"] = "ao.png"
        written.append("ao.png")
        derived = ("ao.png derived from Displacement as a cavity map "
                   "(height minus its own blur); the source set ships none")

    record = {
        "materialKind": material_library.MATERIAL_KIND,
        "version": material_library.MATERIAL_VERSION,
        "semanticId": semantic_id,
        # Sourced, checked against the render, and bound on purpose -- not a
        # stand-in for art that has yet to be made.
        "status": "authored",
        "worldSizeMetres": spec["worldSizeMetres"],
        "maps": maps,
        "notes": spec["notes"],
        "provenance": {
            "origin": f"https://ambientcg.com/view?id={spec['asset']}",
            "sourceAsset": spec["asset"],
            "sourceCollection": "ambientCG",
            "generator": "tools/materials/fetch_cc0_materials.py",
            "processing": (
                f"1K-PNG set, resized to {SIZE} (Lanczos); "
                "Color/Roughness/Displacement/AmbientOcclusion only, normal "
                "maps deliberately not used"
                + ". albedo contrast flattened toward its own mean where "
                  "the source's patching would fight the props, then "
                  "mean-matched to baseColorSrgb and roughness to "
                  "roughnessHint from materials.json, so the semantic ID owns "
                  "the colour and the sourced set owns the structure"
                + (". " + derived if derived else "")),
            "license": LICENSE,
            "retrieved": dt.date.today().isoformat(),
            "sha256": {name: material_library.sha256(directory / name)
                       for name in written},
        },
    }
    (directory / "material.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(prog="fetch_cc0_materials")
    parser.add_argument("ids", nargs="*", help="semantic ids (default: all)")
    parser.add_argument("--check", action="store_true",
                        help="validate the tracked files without downloading")
    parser.add_argument("--project", type=Path, default=None)
    args = parser.parse_args()

    root = material_library.library_root(args.project)
    chosen = args.ids or sorted(RECIPES)
    unknown = [i for i in chosen if i not in RECIPES]
    if unknown:
        raise SystemExit(f"not sourced here: {', '.join(unknown)}")

    failures = 0
    for semantic_id in chosen:
        directory = root / semantic_id
        if args.check:
            existing = material_library.load(semantic_id, args.project)
            if existing is None:
                print(f"{semantic_id}: MISSING")
                failures += 1
                continue
            problems = material_library.validate(existing)
            print(f"{semantic_id}: {'ok' if not problems else 'FAILED'}")
            for problem in problems:
                print(f"    - {problem}")
            failures += len(problems)
        else:
            record = build(semantic_id, RECIPES[semantic_id], directory)
            print(f"{semantic_id}: {record['provenance']['sourceAsset']} -> "
                  f"{directory} ({', '.join(sorted(record['maps']))})")
    if failures:
        raise SystemExit(f"{failures} problem(s)")


if __name__ == "__main__":
    main()
