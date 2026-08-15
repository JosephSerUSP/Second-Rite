"""Re-author eight high-salience St. Maria relics with the composable 3D vocabulary.

This cohort is intentionally not a family of near-identical forms. It uses the
new parts/lathe stack as an art-direction pressure test: open sweeps, nested
rings, hollow vessels, flattened sculptural forms, composed sub-parts, authored
normals/UVs, and sphere-mapped material sheen all appear in objects that need
to read differently in the 80x80 item viewer.

Run:
    python tools/asset-production/build_relic_showcase.py
    lovec . item-sheet tools/asset-production/relic-showcase-items.txt relic-showcase.png
"""

from __future__ import annotations

from pathlib import Path

import lathe
import parts

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "assets" / "models" / "items"
MTL_NAME = "relic_showcase.mtl"

GOLD = "ritual_gold"
BRONZE = "oxidized_bronze"
IRON = "wrought_iron"
CLOTH = "aged_cloth"
GLASS = "smoked_glass"
CRYSTAL = "crystal"
STONE = "old_limestone"
BONE = "bone"
WAX = "wax"
WOOD = "dark_wood"
WET = "wet_residue"

MATERIALS = sorted({
    GOLD, BRONZE, IRON, CLOTH, GLASS, CRYSTAL,
    STONE, BONE, WAX, WOOD, WET,
})


def forbidden_lamp():
    """A squat forbidden lamp: sealed flame, cage, carrying hoop, chapel seal."""
    base = parts.disc(0.64, 0.18, bevel=0.05, material=BRONZE, segments=14)
    belly = lathe.transform(
        lathe.lathe(
            [(0.00, 0.42), (0.18, 0.60), (0.55, 0.56), (0.80, 0.38), (0.95, 0.26)],
            segments=14, material=BRONZE, name="lamp_body",
        ),
        translate=(0.0, 0.12, 0.0),
    )
    flame = lathe.transform(
        parts.teardrop(0.24, 0.60, material=CRYSTAL, segments=10),
        translate=(0.0, 0.62, 0.0),
    )
    cage = parts.scatter(
        parts.rod(0.035, 0.88, material=IRON, segments=5),
        count=6, radius=0.46, height=0.34, name="cage",
    )
    crown = lathe.transform(
        parts.band(0.37, 0.065, material=GOLD, segments=14),
        translate=(0.0, 1.20, 0.0),
    )
    roof = lathe.transform(
        parts.dome(0.46, 0.34, flatten=0.1, material=BRONZE, segments=14),
        translate=(0.0, 1.05, 0.0),
    )
    handle = lathe.transform(
        parts.band(0.72, 0.055, sweep=0.66, material=IRON, segments=18),
        rotate=(90, 0, 0), translate=(0.0, 0.95, -0.48),
    )
    seal = lathe.transform(
        parts.disc(0.18, 0.07, bevel=0.02, material=GOLD, segments=10),
        rotate=(90, 0, 0), translate=(0.0, 0.62, 0.64),
    )
    return lathe.merge("forbidden_lamp", [base, belly, flame, cage, crown, roof, handle, seal])


def town_portal():
    """A hand-held broken astrolabe whose missing arcs are the open seam."""
    outer = lathe.transform(
        parts.band(0.78, 0.085, sweep=0.82, material=GOLD, segments=22),
        rotate=(90, 0, 0), translate=(0.0, 0.80, 0.0),
    )
    inner = lathe.transform(
        parts.band(0.53, 0.055, sweep=0.72, material=IRON, segments=18),
        rotate=(90, 0, 28), translate=(0.0, 0.80, 0.02),
    )
    inner2 = lathe.transform(
        parts.band(0.42, 0.040, sweep=0.62, material=BRONZE, segments=18),
        rotate=(90, 35, -18), translate=(0.0, 0.80, 0.04),
    )
    core = lathe.transform(
        parts.teardrop(0.30, 0.58, material=GLASS, segments=10),
        scale=(1.0, 0.85, 0.28), translate=(0.0, 0.49, 0.06),
    )
    grip = lathe.transform(parts.rod(0.11, 0.62, material=WOOD, segments=7),
                           translate=(0.0, -0.02, 0.0))
    pommel = lathe.transform(
        parts.disc(0.22, 0.12, bevel=0.03, material=GOLD, segments=10),
        translate=(0.0, -0.03, 0.0),
    )
    studs = parts.scatter(
        parts.dome(0.08, 0.06, flatten=0.3, material=GOLD, segments=6),
        count=4, radius=0.60, height=0.80, name="studs",
    )
    return lathe.merge("town_portal", [outer, inner, inner2, core, grip, pommel, studs])


def crossing_writ():
    """A narrow gate writ: bone parchment, wooden rolls, stamped seal and cord."""
    sheet = lathe.transform(
        parts.disc(0.72, 0.07, bevel=0.03, material=BONE, segments=4),
        rotate=(90, 0, 45), scale=(0.72, 1.0, 1.32), translate=(0.0, 0.72, 0.0),
    )
    top = lathe.transform(
        parts.rod(0.075, 1.28, material=WOOD, segments=7),
        rotate=(0, 0, 90), translate=(0.64, 1.38, 0.0),
    )
    bottom = lathe.transform(
        parts.rod(0.075, 1.28, material=WOOD, segments=7),
        rotate=(0, 0, 90), translate=(0.64, 0.06, 0.0),
    )
    seal = lathe.transform(
        parts.disc(0.22, 0.09, bevel=0.03, material=GOLD, segments=12),
        rotate=(90, 0, 0), translate=(0.27, 0.46, 0.10),
    )
    cord = lathe.transform(
        parts.wrap(0.31, 0.11, sweep=0.46, material=CLOTH, segments=12),
        rotate=(90, 0, 0), translate=(0.27, 0.46, 0.04),
    )
    tail = lathe.transform(
        parts.rod(0.045, 0.50, material=CLOTH, segments=5),
        rotate=(0, 0, 22), scale=(1.0, 0.9, 0.4), translate=(0.10, 0.09, 0.08),
    )
    return lathe.merge("crossing_writ", [sheet, top, bottom, seal, cord, tail])


def smoke_bell():
    """A genuinely hollow bell with clapper, black lip and a soot-stained band."""
    profile = [
        (0.00, 0.68), (0.14, 0.76), (0.55, 0.60), (0.95, 0.40), (1.10, 0.24),
        (1.10, 0.15), (0.93, 0.30), (0.52, 0.49), (0.16, 0.62), (0.00, 0.60),
    ]
    body = lathe.lathe(profile, segments=16, material=BRONZE,
                       name="bell_body", closed_profile=True)
    lip = parts.band(0.68, 0.07, material=IRON, segments=16)
    crown = lathe.transform(
        parts.band(0.26, 0.055, material=IRON, segments=12),
        rotate=(90, 0, 0), translate=(0.0, 1.19, 0.0),
    )
    stem = lathe.transform(parts.rod(0.045, 0.82, material=IRON, segments=5),
                           translate=(0.0, 0.18, 0.0))
    clapper = lathe.transform(parts.teardrop(0.15, 0.26, material=IRON, segments=7),
                              translate=(0.0, -0.05, 0.0))
    soot = lathe.transform(
        parts.band(0.58, 0.035, sweep=0.72, material=WET, segments=14),
        translate=(0.0, 0.28, 0.0),
    )
    return lathe.merge("smoke_bell", [body, lip, crown, stem, clapper, soot])


def mourning_ribbon():
    """A tied mourning bow with a small gold memorial medallion."""
    left = lathe.transform(
        parts.band(0.34, 0.075, sweep=0.70, material=CLOTH, segments=16),
        rotate=(90, 0, 35), scale=(1.05, 0.80, 0.40), translate=(-0.22, 0.72, 0.0),
    )
    right = lathe.transform(
        parts.band(0.34, 0.075, sweep=0.70, material=CLOTH, segments=16),
        rotate=(90, 0, -35), scale=(1.05, 0.80, 0.40), translate=(0.22, 0.72, 0.0),
    )
    knot = lathe.transform(
        parts.dome(0.21, 0.16, flatten=0.55, material=CLOTH, segments=10),
        scale=(1.0, 0.9, 0.55), translate=(0.0, 0.62, 0.05),
    )
    tail_l = lathe.transform(
        parts.rod(0.095, 0.58, material=CLOTH, segments=5),
        rotate=(0, 0, 18), scale=(1.0, 1.0, 0.32), translate=(-0.03, 0.08, 0.0),
    )
    tail_r = lathe.transform(
        parts.rod(0.095, 0.55, material=CLOTH, segments=5),
        rotate=(0, 0, -20), scale=(1.0, 1.0, 0.32), translate=(0.04, 0.08, 0.02),
    )
    medallion = lathe.transform(
        parts.disc(0.14, 0.05, bevel=0.02, material=GOLD, segments=10),
        rotate=(90, 0, 0), translate=(0.0, 0.61, 0.16),
    )
    return lathe.merge("mourning_ribbon", [left, right, knot, tail_l, tail_r, medallion])


def first_scale():
    """The Red Dragon's first scale: a faceted tear with layered scarred ridges."""
    main = lathe.transform(
        parts.teardrop(0.66, 1.55, material=CRYSTAL, segments=11),
        scale=(1.0, 1.0, 0.20),
    )
    inner = lathe.transform(
        parts.teardrop(0.48, 1.22, material=GOLD, segments=9),
        scale=(1.0, 1.0, 0.07), translate=(0.0, 0.13, 0.15),
    )
    inner2 = lathe.transform(
        parts.teardrop(0.32, 0.90, material=IRON, segments=7),
        scale=(1.0, 1.0, 0.045), translate=(0.0, 0.26, 0.205),
    )
    ridge = lathe.transform(parts.rod(0.035, 1.18, material=GOLD, segments=5),
                            translate=(0.0, 0.18, 0.24))
    scar1 = lathe.transform(parts.rod(0.025, 0.62, material=IRON, segments=5),
                            rotate=(0, 0, 55), translate=(-0.22, 0.55, 0.23))
    scar2 = lathe.transform(parts.rod(0.022, 0.48, material=IRON, segments=5),
                            rotate=(0, 0, -60), translate=(0.23, 0.78, 0.23))
    return lathe.merge("first_scale", [main, inner, inner2, ridge, scar1, scar2])


def bell_salt():
    """A low stone font overflowing with tall mineral shards and a broken gold halo."""
    cup = parts.bowl(0.74, 0.44, wall=0.08, foot=0.28, material=STONE, segments=16)
    bed = lathe.transform(parts.disc(0.61, 0.05, material=GLASS, segments=14),
                          translate=(0.0, 0.37, 0.0))
    shard = parts.teardrop(0.14, 0.68, material=GLASS, segments=6)
    shards = lathe.merge("shards", [
        lathe.transform(shard, translate=(-0.28, 0.38, -0.10), rotate=(0, 0, -12), scale=0.90),
        lathe.transform(shard, translate=(0.18, 0.38, 0.05), rotate=(0, 0, 14), scale=1.15),
        lathe.transform(shard, translate=(0.03, 0.38, -0.22), rotate=(8, 0, 2), scale=0.78),
        lathe.transform(shard, translate=(0.32, 0.38, -0.12), rotate=(0, 0, 22), scale=0.70),
        lathe.transform(shard, translate=(-0.08, 0.38, 0.24), rotate=(0, 0, -18), scale=0.82),
    ])
    halo = lathe.transform(
        parts.band(0.54, 0.035, sweep=0.84, material=GOLD, segments=16),
        translate=(0.0, 0.52, 0.0),
    )
    return lathe.merge("bell_salt", [cup, bed, shards, halo])


def sealed_reliquary():
    """A miniature chapel reliquary: pillars, arch, sealed core, chain and cross."""
    base = lathe.transform(
        parts.disc(0.66, 0.18, bevel=0.05, material=GOLD, segments=6),
        scale=(1.25, 1.0, 0.78),
    )
    foot = lathe.transform(
        parts.disc(0.48, 0.16, bevel=0.04, material=BRONZE, segments=6),
        scale=(1.15, 1.0, 0.72), translate=(0.0, 0.18, 0.0),
    )
    left = lathe.transform(parts.rod(0.065, 1.05, material=GOLD, segments=6),
                           translate=(-0.48, 0.28, 0.0))
    right = lathe.transform(parts.rod(0.065, 1.05, material=GOLD, segments=6),
                            translate=(0.48, 0.28, 0.0))
    shrine = lathe.transform(
        parts.teardrop(0.43, 0.86, material=GLASS, segments=10),
        scale=(1.0, 0.96, 0.26), translate=(0.0, 0.45, 0.04),
    )
    arch = lathe.transform(
        parts.band(0.50, 0.065, sweep=0.60, material=GOLD, segments=18),
        rotate=(90, 0, 0), translate=(0.0, 1.10, 0.0),
    )
    seal = lathe.transform(
        parts.disc(0.20, 0.07, bevel=0.02, material=WAX, segments=10),
        rotate=(90, 0, 0), translate=(0.0, 0.77, 0.19),
    )
    chain = lathe.transform(
        parts.band(0.27, 0.028, sweep=0.80, material=IRON, segments=14),
        rotate=(90, 0, 0), translate=(0.0, 0.73, 0.17),
    )
    cross_v = lathe.transform(parts.rod(0.035, 0.34, material=GOLD, segments=5),
                              translate=(0.0, 1.32, 0.0))
    cross_h = lathe.transform(
        parts.rod(0.035, 0.28, material=GOLD, segments=5),
        rotate=(0, 0, 90), translate=(0.14, 1.53, 0.0),
    )
    finial = lathe.transform(
        parts.dome(0.10, 0.16, flatten=0.1, material=GOLD, segments=8),
        translate=(0.0, 1.66, 0.0),
    )
    return lathe.merge(
        "sealed_reliquary",
        [base, foot, left, right, shrine, arch, seal, chain, cross_v, cross_h, finial],
    )


COHORT = {
    "forbidden_lamp": forbidden_lamp,
    "town_portal": town_portal,
    "crossing_writ": crossing_writ,
    "smoke_bell": smoke_bell,
    "mourning_ribbon": mourning_ribbon,
    "first_scale": first_scale,
    "bell_salt": bell_salt,
    "sealed_reliquary": sealed_reliquary,
}


def build() -> None:
    lathe.write_mtl(
        OUT / MTL_NAME,
        MATERIALS,
        comment="St. Maria relic showcase cohort",
        sheens={
            GOLD: "assets/models/matcaps/gold.png",
            CRYSTAL: "assets/models/matcaps/ruby.png",
        },
    )
    for stem, recipe in COHORT.items():
        mesh = recipe()
        mesh.name = stem
        lathe.write_obj(
            mesh,
            OUT / f"{stem}.obj",
            mtllib=MTL_NAME,
            comment="St. Maria relic showcase: composed from parts.py + lathe.py",
        )
        print(f"{stem}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces")


if __name__ == "__main__":
    build()
