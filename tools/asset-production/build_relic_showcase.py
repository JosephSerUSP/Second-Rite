"""Six relic reauthors that exercise the new item-model production vocabulary.

This is deliberately a showcase rather than a database-coverage batch. Each item
starts from a different silhouette idea and composes the shared lathe/parts
vocabulary instead of falling back to the old box/blob/diamond grammar.

Build:
    python tools/asset-production/build_relic_showcase.py

Review through the real in-game presentation path:
    lovec . item-sheet tools/asset-production/relic-showcase-items.txt relic-showcase.png
"""

from __future__ import annotations

import json
from pathlib import Path

import lathe
import parts

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "assets" / "models" / "items"
MATERIALS_JSON = REPO_ROOT / "tools" / "asset-language" / "materials.json"
GOLD_MATCAP = "assets/models/matcaps/gold.png"
RUBY_MATCAP = "assets/models/matcaps/ruby.png"


def _jewel(
    radius: float = 0.20,
    height: float = 0.28,
    *,
    material: str = "crystal",
    rotate=(90.0, 0.0, 0.0),
    translate=(0.0, 0.0, 0.0),
    scale=(1.0, 1.0, 1.0),
    segments: int = 8,
):
    return lathe.transform(
        parts.teardrop(radius, height, material=material, segments=segments),
        rotate=rotate,
        translate=translate,
        scale=scale,
    )


def black_hinge():
    """Occult gate hardware: paired leaves, ceremonial pin, halo arcs, jewel."""
    pin = lathe.transform(
        parts.rod(0.13, 2.60, material="wrought_iron", segments=10),
        translate=(0.0, -1.30, 0.0),
    )
    collars = lathe.merge(
        "collars",
        [
            lathe.transform(
                parts.band(0.17, 0.055, material="ritual_gold", segments=12),
                translate=(0.0, y, 0.0),
            )
            for y in (-0.90, 0.0, 0.90)
        ],
    )

    leaf = lathe.transform(
        parts.disc(
            0.90, 0.18, bevel=0.08, material="wrought_iron", segments=14
        ),
        rotate=(90.0, 0.0, 0.0),
        scale=(0.72, 1.0, 0.35),
    )
    leaves = [
        lathe.transform(leaf, translate=(-0.62, 0.0, 0.0)),
        lathe.transform(leaf, translate=(0.62, 0.0, 0.0)),
    ]

    arc = lathe.transform(
        parts.band(
            0.65, 0.055, sweep=0.62, material="ritual_gold", segments=16
        ),
        rotate=(90.0, 0.0, 0.0),
    )
    arcs = [
        lathe.transform(
            arc, translate=(-0.62, 0.0, -0.12), rotate=(0.0, 0.0, 18.0)
        ),
        lathe.transform(
            arc, translate=(0.62, 0.0, -0.12), rotate=(0.0, 0.0, 198.0)
        ),
    ]

    rivet = lathe.transform(
        parts.dome(
            0.09, 0.07, flatten=0.30, material="ritual_gold", segments=7
        ),
        rotate=(90.0, 0.0, 0.0),
    )
    rivets = lathe.merge(
        "rivets",
        [
            lathe.transform(rivet, translate=(side * 0.62, y, -0.19))
            for side in (-1.0, 1.0)
            for y in (-0.55, 0.55)
        ],
    )
    centre = _jewel(
        0.16,
        0.22,
        translate=(0.0, 0.0, -0.22),
        scale=(1.0, 1.30, 0.70),
    )
    return lathe.merge(
        "black_hinge", [*leaves, pin, collars, *arcs, rivets, centre]
    )


def chrysalis_sigil():
    """A cold crystal cocoon inside a gold/verdigris ritual armature."""
    cocoon = lathe.transform(
        parts.teardrop(0.48, 1.65, material="crystal", segments=12),
        translate=(0.0, -0.80, 0.0),
        scale=(0.82, 1.0, 0.62),
    )
    halo = lathe.transform(
        parts.band(0.82, 0.055, material="ritual_gold", segments=18),
        rotate=(90.0, 0.0, 0.0),
        translate=(0.0, 0.05, 0.08),
    )
    ribs = [
        lathe.transform(
            parts.band(
                0.58, 0.035, sweep=0.72, material="ritual_gold", segments=16
            ),
            rotate=(90.0, angle, 0.0),
            translate=(0.0, -0.02, -0.05),
        )
        for angle in (-38.0, 0.0, 38.0)
    ]

    wing = lathe.transform(
        parts.band(
            0.44, 0.05, sweep=0.45, material="oxidized_bronze", segments=12
        ),
        rotate=(90.0, 0.0, 0.0),
        scale=(1.25, 0.72, 0.45),
    )
    wings = lathe.merge(
        "wings",
        [
            lathe.transform(
                wing, translate=(-0.55, 0.10, -0.02), rotate=(0.0, 0.0, 35.0)
            ),
            lathe.transform(
                wing, translate=(0.55, 0.10, -0.02), rotate=(0.0, 0.0, 215.0)
            ),
            lathe.transform(
                wing,
                translate=(-0.48, -0.38, -0.02),
                rotate=(0.0, 0.0, -15.0),
                scale=0.80,
            ),
            lathe.transform(
                wing,
                translate=(0.48, -0.38, -0.02),
                rotate=(0.0, 0.0, 165.0),
                scale=0.80,
            ),
        ],
    )
    top_loop = lathe.transform(
        parts.band(0.23, 0.05, material="ritual_gold", segments=14),
        rotate=(90.0, 0.0, 0.0),
        translate=(0.0, 0.95, 0.0),
    )
    gem = lathe.transform(
        parts.dome(0.14, 0.12, flatten=0.30, material="crystal", segments=8),
        rotate=(90.0, 0.0, 0.0),
        translate=(0.0, 0.42, -0.48),
    )
    return lathe.merge(
        "chrysalis_sigil", [cocoon, halo, *ribs, wings, top_loop, gem]
    )


def qilin_bell():
    """A temple bell with horned shoulders and a cold crystal clapper."""
    bell = lathe.lathe(
        [
            (-0.95, 0.00),
            (-0.92, 0.62),
            (-0.78, 0.76),
            (-0.35, 0.62),
            (0.08, 0.45),
            (0.32, 0.32),
            (0.48, 0.24),
        ],
        segments=16,
        material="ritual_gold",
        name="bell",
    )
    rim = lathe.transform(
        parts.band(0.69, 0.07, material="oxidized_bronze", segments=16),
        translate=(0.0, -0.80, 0.0),
    )
    cap = lathe.transform(
        parts.dome(
            0.34, 0.22, flatten=0.30, material="ritual_gold", segments=12
        ),
        translate=(0.0, 0.45, 0.0),
    )
    loop = lathe.transform(
        parts.band(0.32, 0.055, material="wrought_iron", segments=14),
        rotate=(90.0, 0.0, 0.0),
        translate=(0.0, 0.86, 0.0),
    )
    clapper = lathe.transform(
        parts.teardrop(0.16, 0.40, material="crystal", segments=8),
        translate=(0.0, -1.22, 0.0),
    )

    horn = lathe.transform(
        parts.band(
            0.48, 0.05, sweep=0.42, material="wrought_iron", segments=14
        ),
        rotate=(90.0, 0.0, 0.0),
        scale=(1.0, 0.80, 0.60),
    )
    horns = lathe.merge(
        "horns",
        [
            lathe.transform(
                horn, translate=(-0.36, 0.30, 0.0), rotate=(0.0, 0.0, 35.0)
            ),
            lathe.transform(
                horn, translate=(0.36, 0.30, 0.0), rotate=(0.0, 0.0, 215.0)
            ),
        ],
    )
    studs = parts.scatter(
        lathe.transform(
            parts.dome(
                0.055, 0.04, flatten=0.40, material="crystal", segments=6
            ),
            rotate=(90.0, 0.0, 0.0),
        ),
        count=4,
        radius=0.46,
        height=-0.55,
        name="studs",
    )
    return lathe.merge(
        "qilin_bell", [bell, rim, cap, loop, clapper, horns, studs]
    )


def vial_of_second_breath():
    """A smoked vial surrounded by a fan of dry bone 'breath' feathers."""
    body = lathe.lathe(
        [
            (-1.05, 0.18),
            (-0.95, 0.34),
            (-0.65, 0.46),
            (0.25, 0.44),
            (0.48, 0.27),
            (0.62, 0.18),
            (0.82, 0.18),
        ],
        segments=16,
        materials=[
            "ritual_gold",
            "smoked_glass",
            "smoked_glass",
            "smoked_glass",
            "ritual_gold",
            "ritual_gold",
        ],
        name="vial",
    )
    base = lathe.transform(
        parts.band(0.33, 0.055, material="ritual_gold", segments=14),
        translate=(0.0, -0.87, 0.0),
    )
    neck = lathe.transform(
        parts.band(0.22, 0.05, material="ritual_gold", segments=12),
        translate=(0.0, 0.66, 0.0),
    )
    stopper = lathe.transform(
        parts.teardrop(0.20, 0.38, material="crystal", segments=9),
        translate=(0.0, 0.78, 0.0),
    )

    wings = []
    for side in (-1.0, 1.0):
        for radius, y, angle in (
            (0.62, 0.16, 20.0),
            (0.52, -0.05, 2.0),
            (0.42, -0.28, -16.0),
        ):
            arc = lathe.transform(
                parts.band(
                    radius, 0.04, sweep=0.32, material="bone", segments=14
                ),
                rotate=(90.0, 0.0, 0.0),
                scale=(1.0, 0.72, 0.50),
            )
            wings.append(
                lathe.transform(
                    arc,
                    translate=(side * 0.44, y, -0.02),
                    rotate=(
                        0.0,
                        0.0,
                        angle if side < 0.0 else 180.0 - angle,
                    ),
                )
            )

    halo = lathe.transform(
        parts.band(
            0.44, 0.035, sweep=0.84, material="oxidized_bronze", segments=16
        ),
        rotate=(90.0, 0.0, 0.0),
        translate=(0.0, 0.22, 0.05),
    )
    bead = lathe.transform(
        parts.dome(0.10, 0.08, flatten=0.20, material="crystal", segments=7),
        rotate=(90.0, 0.0, 0.0),
        translate=(0.0, -0.30, -0.47),
    )
    return lathe.merge(
        "vial_of_second_breath",
        [body, base, neck, stopper, *wings, halo, bead],
    )


def meteorite_plate():
    """A compact meteor cuirass plate: iron mass, crater, crystal heart, spikes."""
    main = lathe.transform(
        parts.disc(
            0.92, 0.24, bevel=0.08, material="wrought_iron", segments=16
        ),
        rotate=(90.0, 0.0, 0.0),
        scale=(0.92, 1.18, 0.46),
    )
    lobe = lathe.transform(
        parts.disc(
            0.58, 0.20, bevel=0.06, material="oxidized_bronze", segments=14
        ),
        rotate=(90.0, 0.0, 0.0),
        scale=(0.72, 0.82, 0.40),
    )
    left = lathe.transform(
        lobe, translate=(-0.62, -0.05, 0.04), rotate=(0.0, 0.0, 18.0)
    )
    right = lathe.transform(
        lobe, translate=(0.62, -0.05, 0.04), rotate=(0.0, 0.0, -18.0)
    )
    rim = lathe.transform(
        parts.band(0.76, 0.055, material="ritual_gold", segments=18),
        rotate=(90.0, 0.0, 0.0),
        scale=(0.92, 1.18, 0.48),
        translate=(0.0, 0.0, -0.04),
    )
    crater = lathe.transform(
        parts.band(0.30, 0.06, material="rough_limestone", segments=14),
        rotate=(90.0, 0.0, 0.0),
        scale=(1.05, 0.90, 0.50),
        translate=(0.0, 0.03, -0.16),
    )
    core = lathe.transform(
        parts.teardrop(0.18, 0.30, material="crystal", segments=8),
        rotate=(90.0, 0.0, 0.0),
        translate=(0.0, 0.03, -0.28),
        scale=(1.0, 0.80, 0.55),
    )
    crest = lathe.transform(
        parts.band(
            0.38, 0.05, sweep=0.55, material="ritual_gold", segments=14
        ),
        rotate=(90.0, 0.0, 0.0),
        translate=(0.0, 0.82, -0.03),
        scale=(1.20, 0.70, 0.40),
    )

    spikes = []
    for x, y, angle in (
        (-0.72, 0.48, 55.0),
        (0.72, 0.48, -55.0),
        (-0.68, -0.55, 125.0),
        (0.68, -0.55, -125.0),
        (0.0, 0.93, 0.0),
        (0.0, -0.93, 180.0),
    ):
        spike = lathe.transform(
            parts.teardrop(0.095, 0.34, material="bone", segments=7),
            scale=(0.75, 1.0, 0.55),
        )
        spikes.append(
            lathe.transform(
                spike, rotate=(0.0, 0.0, angle), translate=(x, y, 0.02)
            )
        )
    return lathe.merge(
        "meteorite_plate",
        [left, right, main, rim, crater, core, crest, *spikes],
    )


def philosophers_stone():
    """A cold alchemical stone held in three impossible-looking orbit rings."""
    stone = lathe.transform(
        parts.teardrop(0.42, 1.05, material="crystal", segments=10),
        translate=(0.0, -0.52, 0.0),
        scale=(0.85, 1.0, 0.72),
    )
    rings = [
        lathe.transform(
            parts.band(0.62, 0.045, material="ritual_gold", segments=18),
            rotate=(90.0, 0.0, 0.0),
        ),
        lathe.transform(
            parts.band(0.62, 0.045, material="ritual_gold", segments=18),
            rotate=(35.0, 0.0, 20.0),
        ),
        lathe.transform(
            parts.band(0.62, 0.045, material="oxidized_bronze", segments=18),
            rotate=(-35.0, 0.0, -20.0),
        ),
    ]
    crown = lathe.transform(
        parts.band(
            0.28, 0.05, sweep=0.82, material="wrought_iron", segments=14
        ),
        rotate=(90.0, 0.0, 0.0),
        translate=(0.0, 0.72, 0.0),
    )
    pedestal = lathe.transform(
        parts.cylinder(0.22, 0.28, material="wrought_iron", segments=10),
        translate=(0.0, -0.83, 0.0),
    )
    base = lathe.transform(
        parts.disc(
            0.42, 0.12, bevel=0.04, material="ritual_gold", segments=12
        ),
        translate=(0.0, -0.87, 0.0),
    )
    satellites = parts.scatter(
        lathe.transform(
            parts.dome(
                0.08, 0.06, flatten=0.25, material="crystal", segments=6
            ),
            rotate=(90.0, 0.0, 0.0),
        ),
        count=3,
        radius=0.72,
        height=0.05,
        name="satellites",
    )
    return lathe.merge(
        "philosophers_stone",
        [stone, *rings, crown, pedestal, base, satellites],
    )


RECIPES = {
    "black_hinge": black_hinge,
    "chrysalis_sigil": chrysalis_sigil,
    "qilin_bell": qilin_bell,
    "vial_of_second_breath": vial_of_second_breath,
    "meteorite_plate": meteorite_plate,
    "philosophers_stone": philosophers_stone,
}

PASSES = {
    "black_hinge": {
        "ritual_gold": [f"refl -type sphere {GOLD_MATCAP}"],
        "crystal": [f"pass sphere add 0.65 {RUBY_MATCAP}"],
    },
    "chrysalis_sigil": {
        "ritual_gold": [f"refl -type sphere {GOLD_MATCAP}"],
        "crystal": [
            f"pass sphere screen 0.55 {GOLD_MATCAP}",
            f"pass sphere add 0.30 {RUBY_MATCAP}",
        ],
    },
    "qilin_bell": {
        "ritual_gold": [f"refl -type sphere {GOLD_MATCAP}"],
        "crystal": [f"pass sphere screen 0.35 {GOLD_MATCAP}"],
    },
    "vial_of_second_breath": {
        "ritual_gold": [f"refl -type sphere {GOLD_MATCAP}"],
        "smoked_glass": [f"pass sphere add 0.12 {GOLD_MATCAP}"],
        "crystal": [f"pass sphere screen 0.55 {GOLD_MATCAP}"],
    },
    "meteorite_plate": {
        "ritual_gold": [f"refl -type sphere {GOLD_MATCAP}"],
        "crystal": [f"pass sphere add 0.55 {RUBY_MATCAP}"],
    },
    "philosophers_stone": {
        "ritual_gold": [f"refl -type sphere {GOLD_MATCAP}"],
        "crystal": [
            f"pass sphere add 0.85 {RUBY_MATCAP}",
            f"pass sphere screen 0.35 {GOLD_MATCAP}",
        ],
    },
}


def write_mtl(path: Path, material_ids: set[str], passes: dict[str, list[str]]) -> None:
    data = json.loads(MATERIALS_JSON.read_text(encoding="utf-8"))
    registry = {entry["id"]: entry for entry in data["materials"]}
    unknown = sorted(material_ids - registry.keys())
    if unknown:
        raise lathe.LatheError(f"materials not in canonical registry: {unknown}")

    lines = [
        "# relic showcase: semantic materials plus authored retro overlay passes",
        "# generated by tools/asset-production/build_relic_showcase.py",
    ]
    for material_id in sorted(material_ids):
        r, g, b = registry[material_id]["legacyMtl"]["kd"]
        lines += [f"newmtl {material_id}", f"Kd {r:.3f} {g:.3f} {b:.3f}"]
        lines += passes.get(material_id, [])
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> None:
    for stem, recipe in RECIPES.items():
        mesh = recipe()
        mesh.name = stem
        used = {material for material, _ in mesh.faces}
        write_mtl(OUT / f"{stem}.mtl", used, PASSES.get(stem, {}))
        lathe.write_obj(
            mesh,
            OUT / f"{stem}.obj",
            mtllib=f"{stem}.mtl",
            comment=(
                "relic showcase: composed from the shared "
                "tools/asset-production parts vocabulary"
            ),
        )
        low, high = mesh.bounds()
        print(
            f"{stem}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces, "
            f"bounds={low}..{high}"
        )


if __name__ == "__main__":
    build()
