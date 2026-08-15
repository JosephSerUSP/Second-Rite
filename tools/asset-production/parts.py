"""A vocabulary of authored forms, composed into objects.

The batch that produced the current library gave an agent one act of invention
per asset and no shared forms, and 124 models collapsed into about four shapes:
a box with a lid, a blob, a bottle, a diamond. Sushi, pizza, mochi and a
thief's glove all came out the same brown box.

The fix is not more effort per asset. It is a vocabulary. An author who has
`bowl`, `dome`, `wrap` and `scatter` describes a bowl of noodles as a bowl with
a scatter of lumps and a wrap of nori, and gets something that reads as food.
An author with only `lathe` describes it as a box, because that is the only
thing one profile can honestly be.

Every part returns a `LatheMesh` and composes through `lathe.merge`, so parts
are values: place them, scale them, merge them, and the corpus checks apply to
the result exactly as they would to a hand-built mesh.

Coordinates follow the lathe: +Y is up, parts sit on or around the origin.
"""

from __future__ import annotations

import math

from lathe import LatheMesh, lathe, merge, transform

TAU = math.tau


def _circle(centre_radius: float, tube: float, points: int = 12):
    return [
        (tube * math.sin(i / points * TAU), centre_radius + tube * math.cos(i / points * TAU))
        for i in range(points)
    ]


def disc(radius: float, thickness: float, *, bevel: float = 0.0,
         material: str = "old_limestone", segments: int = 20, name: str = "disc") -> LatheMesh:
    """A flat round slab: a coin, a mooncake, a pizza base, a pressed cake."""
    if bevel <= 0.0:
        profile = [(-thickness / 2, radius), (thickness / 2, radius)]
    else:
        profile = [
            (-thickness / 2, radius - bevel),
            (-thickness / 2 + bevel, radius),
            (thickness / 2 - bevel, radius),
            (thickness / 2, radius - bevel),
        ]
    return lathe(profile, segments=segments, material=material, name=name)


def dome(radius: float, height: float, *, flatten: float = 0.0,
         material: str = "old_limestone", segments: int = 16, name: str = "dome") -> LatheMesh:
    """A rounded mound: mochi, a rice ball, a dumpling, a stone.

    `flatten` keeps a plateau at the top instead of closing to a point, which
    is the difference between a bun and a cone.
    """
    steps = 6
    profile = [(0.0, radius)]
    for step in range(1, steps + 1):
        angle = step / steps * (math.pi / 2)
        y = height * math.sin(angle)
        r = radius * math.cos(angle) ** (1.0 - flatten)
        # cos(pi/2) is ~6e-17 rather than 0, and raising it to a fractional
        # power lifts it to ~1e-5 -- above the lathe's axis epsilon. The apex
        # would then grow a cap of sliver triangles instead of closing on the
        # axis. Snap it shut.
        profile.append((y, 0.0 if step == steps else max(r, 0.0)))
    return lathe(profile, segments=segments, material=material, name=name)


def bowl(radius: float, height: float, *, wall: float = 0.12, foot: float = 0.35,
         material: str = "old_limestone", segments: int = 20, name: str = "bowl") -> LatheMesh:
    """An open vessel with a foot: ramen, stew, congee, a mortar.

    Modelled as a closed profile so the bowl has a real inside and a real rim
    rather than being a solid with a painted hollow. The interior is what makes
    a bowl read as a bowl at a glance.
    """
    outer = radius
    inner = max(radius - wall, 0.05)
    profile = [
        (0.0, foot * radius),
        (0.0, outer * 0.55),
        (height * 0.55, outer),
        (height, outer),
        (height, inner),
        (height * 0.5, inner * 0.75),
        (wall * 0.8, inner * 0.30),
        (wall * 0.5, foot * radius * 0.95),
    ]
    return lathe(profile, segments=segments, material=material,
                 name=name, closed_profile=True)


def cylinder(radius: float, height: float, *, material: str = "old_limestone",
             segments: int = 16, name: str = "cylinder") -> LatheMesh:
    """A plain round column: a sushi roll, a jar body, a candle, a tin."""
    return lathe([(0.0, radius), (height, radius)], segments=segments,
                 material=material, name=name)


def teardrop(radius: float, height: float, *, material: str = "old_limestone",
             segments: int = 14, name: str = "teardrop") -> LatheMesh:
    """A body that swells low and tapers to a point: a coxinha, a bud, a flame."""
    profile = [
        (0.0, 0.0),
        (height * 0.12, radius * 0.72),
        (height * 0.34, radius),
        (height * 0.62, radius * 0.80),
        (height * 0.85, radius * 0.42),
        (height, 0.0),
    ]
    return lathe(profile, segments=segments, material=material, name=name)


def rod(radius: float, length: float, *, material: str = "dark_wood",
        segments: int = 6, name: str = "rod") -> LatheMesh:
    """A thin shaft: chopsticks, a skewer, a stem, a handle."""
    return lathe([(0.0, radius), (length, radius)], segments=segments,
                 material=material, name=name)


def band(centre_radius: float, tube: float, *, sweep: float = 1.0,
         material: str = "aged_cloth", segments: int = 20, name: str = "band") -> LatheMesh:
    """A ring of material around an axis: a rim, a hoop, a tied cord."""
    return lathe(_circle(centre_radius, tube), segments=segments, material=material,
                 name=name, closed_profile=True, sweep=sweep)


def wrap(radius: float, height: float, *, sweep: float = 0.55, thickness: float = 0.04,
         material: str = "aged_cloth", segments: int = 16, name: str = "wrap") -> LatheMesh:
    """A partial sleeve around a body: a nori band, a label, a bandage, a belt.

    A partial sweep is what makes this a wrap and not a ring -- it has two open
    ends, so it reads as something applied to the object rather than part of it.
    """
    return lathe([(0.0, radius), (height, radius)], segments=segments,
                 material=material, name=name, sweep=sweep)


def scatter(part: LatheMesh, count: int, radius: float, *, height: float = 0.0,
            jitter: float = 0.0, scale: float = 1.0, name: str = "scatter") -> LatheMesh:
    """Place copies of a part evenly around the axis.

    Toppings, studs, petals, rivets, gems in a cluster. Deterministic: `jitter`
    is a fixed per-index offset, not a random one, so two runs of the same
    recipe produce byte-identical output.
    """
    if count < 1:
        raise ValueError(f"scatter needs at least one copy, got {count}")
    placed = []
    for index in range(count):
        angle = index / count * TAU
        wobble = jitter * math.sin(index * 2.399963)  # golden-angle, deterministic
        r = radius + wobble
        placed.append(
            transform(
                part,
                translate=(r * math.cos(angle), height + wobble * 0.5, r * math.sin(angle)),
                scale=scale * (1.0 + wobble * 0.5),
                name=f"{name}_{index}",
            )
        )
    return merge(name, placed)


def stack(parts_with_heights: list[tuple[LatheMesh, float]], name: str = "stack") -> LatheMesh:
    """Place parts at given heights up the axis: layered cakes, tiered lids."""
    return merge(name, [transform(part, translate=(0.0, y, 0.0)) for part, y in parts_with_heights])
