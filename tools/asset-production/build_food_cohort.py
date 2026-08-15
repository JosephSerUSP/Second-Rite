"""The eight-food cohort: proving the parts vocabulary, not covering a database.

These eight currently share one mesh with eleven other foods -- a brown box with
a gold lid, for sushi and pizza and mochi alike. Each is re-authored here as a
composition of named forms, so the question the cohort answers is whether an
agent with a vocabulary produces recognisably different objects, not whether
this particular set of items is finished.

Run:
    python tools/asset-production/build_food_cohort.py
    lovec . item-sheet tools/asset-production/food-cohort-items.txt food.png
"""

from __future__ import annotations

import math
from pathlib import Path

import lathe
import parts

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "assets" / "models" / "items"
MTL_NAME = "food_cohort.mtl"

# Semantic materials from the canonical registry. The registry has no food
# colours and should not grow them (SPEC 1.25): tone comes from these, and
# actual appetite appeal comes from albedo, which is the texturing pass.
BROTH = "wet_residue"
RICE = "old_limestone"
CRUST = "wax"
SEAWEED = "dark_wood"
FILLING = "bone"
GLAZE = "ritual_gold"

MATERIALS = sorted({BROTH, RICE, CRUST, SEAWEED, FILLING, GLAZE})


def ramen():
    """A bowl with broth, a nest of noodles and chopsticks laid across."""
    vessel = parts.bowl(0.92, 0.96, wall=0.10, material=RICE, name="vessel")
    broth = lathe.transform(
        parts.disc(0.86, 0.04, material=BROTH, segments=20), translate=(0.0, 0.80, 0.0)
    )
    noodles = parts.scatter(
        parts.dome(0.20, 0.10, flatten=0.5, material=RICE, segments=8),
        count=7, radius=0.40, height=0.84, jitter=0.05, name="noodles",
    )
    topping = parts.scatter(
        parts.disc(0.16, 0.05, material=SEAWEED, segments=8),
        count=3, radius=0.48, height=0.90, name="topping",
    )
    sticks = lathe.merge("sticks", [
        lathe.transform(parts.rod(0.035, 1.5, segments=5), rotate=(0, 0, 96), translate=(-0.6, 1.20, 0.10)),
        lathe.transform(parts.rod(0.035, 1.5, segments=5), rotate=(0, 0, 96), translate=(-0.6, 1.20, -0.10)),
    ])
    return lathe.merge("ramen", [vessel, broth, noodles, topping, sticks])


def onigiri():
    """A rice triangle in a nori band: three segments makes the silhouette."""
    body = lathe.lathe(
        [(0.0, 0.0), (0.10, 0.72), (0.55, 0.80), (1.05, 0.0)],
        segments=3, material=RICE, name="body",
    )
    nori = lathe.transform(
        parts.wrap(0.74, 0.44, sweep=0.42, material=SEAWEED, segments=3),
        translate=(0.0, 0.06, 0.0),
    )
    return lathe.merge("onigiri", [body, nori])


def mochi():
    """A soft round bun, dusted: a dome plus a scatter too small to be lumps."""
    body = parts.dome(0.85, 0.62, flatten=0.55, material=RICE, segments=18)
    dust = parts.scatter(
        parts.disc(0.07, 0.02, material=GLAZE, segments=6),
        count=5, radius=0.30, height=0.58, jitter=0.06, name="dust",
    )
    return lathe.merge("mochi", [body, dust])


def pizza():
    """A wide thin disc with a raised rim and scattered toppings."""
    # Deliberately chunkier than a real pizza. The item viewer tilts only 10
    # degrees, so anything much flatter than this is read edge-on and becomes a
    # line -- proportion has to answer to the camera it will be seen through.
    base = parts.disc(0.88, 0.22, bevel=0.06, material=CRUST, segments=22)
    rim = parts.band(0.84, 0.16, material=CRUST, segments=22)
    sauce = lathe.transform(parts.disc(0.74, 0.06, material=BROTH, segments=20),
                            translate=(0.0, 0.13, 0.0))
    toppings = parts.scatter(
        parts.dome(0.15, 0.10, flatten=0.4, material=FILLING, segments=7),
        count=6, radius=0.44, height=0.16, jitter=0.06, name="toppings",
    )
    return lathe.merge("pizza", [base, rim, sauce, toppings])


def sushi():
    """A short cylinder of rice, banded with nori, topped with a slab."""
    rice = parts.cylinder(0.62, 0.52, material=RICE, segments=16)
    nori = parts.wrap(0.65, 0.52, sweep=1.0, material=SEAWEED, segments=16)
    slab = lathe.transform(
        parts.dome(0.58, 0.20, flatten=0.7, material=FILLING, segments=14),
        translate=(0.0, 0.52, 0.0),
    )
    return lathe.merge("sushi", [rice, nori, slab])


def coxinha():
    """A teardrop croquette: the shape is the whole identity."""
    body = parts.teardrop(0.62, 1.35, material=CRUST, segments=14)
    crumb = parts.scatter(
        parts.dome(0.09, 0.05, material=CRUST, segments=5),
        count=6, radius=0.50, height=0.42, jitter=0.05, name="crumb",
    )
    return lathe.merge("coxinha", [body, crumb])


def mooncake():
    """A stamped disc: straight sides, a pressed pattern, a fluted edge."""
    body = parts.disc(0.86, 0.46, bevel=0.08, material=GLAZE, segments=18)
    flutes = parts.scatter(
        parts.cylinder(0.10, 0.46, material=GLAZE, segments=6),
        count=8, radius=0.84, name="flutes",
    )
    stamp = lathe.transform(
        parts.dome(0.34, 0.10, flatten=0.6, material=CRUST, segments=10),
        translate=(0.0, 0.46, 0.0),
    )
    return lathe.merge("mooncake", [body, flutes, stamp])


def tempura():
    """Irregular fried lumps on a skewer: roughness carried by the scatter."""
    skewer = parts.rod(0.05, 1.6, segments=5)
    lumps = lathe.merge("lumps", [
        lathe.transform(
            parts.dome(0.34 + 0.05 * math.sin(i * 2.1), 0.34, flatten=0.3,
                       material=CRUST, segments=7),
            translate=(0.0, 0.28 + i * 0.40, 0.0),
            rotate=(0.0, i * 47.0, 0.0),
        )
        for i in range(3)
    ])
    return lathe.merge("tempura", [skewer, lumps])


COHORT = {
    "ramen": ramen,
    "onigiri": onigiri,
    "mochi": mochi,
    "pizza": pizza,
    "sushi": sushi,
    "coxinha": coxinha,
    "mooncake": mooncake,
    "tempura": tempura,
}


def build() -> None:
    # The glaze reads as a hard sugar shell rather than flat paint once it
    # carries a sheen. Sphere maps are generated by
    # tools/asset-gen/make_matcaps.py and promoted into assets/models/matcaps.
    lathe.write_mtl(OUT / MTL_NAME, MATERIALS, comment="food cohort",
                    sheens={GLAZE: "assets/models/matcaps/gold.png"})
    for stem, recipe in COHORT.items():
        mesh = recipe()
        mesh.name = stem
        lathe.write_obj(mesh, OUT / f"{stem}.obj", mtllib=MTL_NAME,
                        comment="food cohort: composed from tools/asset-production/parts.py")
        print(f"{stem}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces")


if __name__ == "__main__":
    build()
