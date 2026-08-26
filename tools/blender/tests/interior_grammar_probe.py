"""In-Blender probe for the Interior grammar axes.

Runs inside Blender, exercises each axis and each guard, and prints one JSON
line for `test_interior_grammar.py` to assert against. Kept as a separate file
rather than an inline string so the checks are readable and editable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

import interior as kit  # noqa: E402


def room(**kw):
    front_depth = kit.floor_edge_x(kit.FLOOR_EDGE_NATIVE_Y)[1]
    kw.setdefault("half_width", kit.base_half_width_at(front_depth))
    kw.setdefault("depth", 6.4)
    kw.setdefault("ceiling_z", 3.5)
    return kit.Interior("grammar_probe", **kw)


def guarded(fn):
    """Run a builder and report whether the grammar accepted it."""
    try:
        fn()
        return {"accepted": True, "message": ""}
    except SystemExit as exc:
        return {"accepted": False, "message": str(exc)}
    except ValueError as exc:
        return {"accepted": False, "message": str(exc)}


def named_x(r, prefix):
    return sorted({round(o.location.x, 4) for o in r.parts
                   if o.name.startswith(prefix)})


WINDOW = (0.6, 2.0, 1.15, 2.5)
result = {}

# -- projection helpers are each other's inverse ---------------------------
edge_x, _ = kit.floor_edge_x(kit.FLOOR_EDGE_NATIVE_Y)
result["projectionRoundTrip"] = round(
    kit.native_y_at(edge_x, 0.0) - kit.FLOOR_EDGE_NATIVE_Y, 6)

# -- a plain room is unchanged by passing an empty alcove list -------------
a = room()
a.back_wall(openings=[WINDOW])
a.side_walls()
plain = [(o.name, tuple(round(v, 5) for v in o.location)) for o in a.parts]
# Interior.__init__ resets the scene, which FREES the previous room's objects.
# Everything wanted from `a` has to be read before `b` exists.
result["plainBackWallPlanes"] = named_x(a, "back_wall")

b = room()
b.back_wall(openings=[WINDOW], alcoves=[])
b.side_walls(openings={})
empty_args = [(o.name, tuple(round(v, 5) for v in o.location)) for o in b.parts]
result["emptyArgsAreIdentical"] = plain == empty_args

# -- AXIS: alcove steps the wall back -------------------------------------
c = room()
c.back_wall(openings=[WINDOW], alcoves=[(-3.1, -1.3, 1.4)])
result["alcoveBackWallPlanes"] = named_x(c, "back_wall")
result["alcoveParts"] = sorted({o.name.rsplit("_", 1)[0] for o in c.parts
                                if o.name.startswith("alcove_")})
result["alcoveDepth"] = round(max(named_x(c, "back_wall"))
                              - min(named_x(c, "back_wall")), 4)

# -- AXIS: side wall openings pierce the wall ------------------------------
d = room()
d.back_wall(openings=[WINDOW])
d.side_walls()
solid = len([o for o in d.parts if o.name.startswith("side_wall_1")])

e = room()
e.back_wall(openings=[WINDOW])
e.side_walls(openings={1: [(e.back_x - 3.4, e.back_x - 1.4, 1.5, 2.9)]})
pierced = len([o for o in e.parts if o.name.startswith("side_wall_1")])
result["sideWallSolidParts"] = solid
result["sideWallPiercedParts"] = pierced

# -- AXIS: platform, and its floor-limit guard -----------------------------
f = room()
result["platformRaised"] = guarded(
    lambda: f.platform("dais", f.back_x - 2.0, f.back_x, 1.0, 3.0, 0.34))
g = room()
result["platformShallowDip"] = guarded(
    lambda: g.platform("dip", g.front_x + 0.2, g.front_x + 2.0, -1.0, 1.0,
                       -0.2))
h = room()
result["platformDeepPit"] = guarded(
    lambda: h.platform("pit", h.front_x + 0.2, h.front_x + 2.0, -1.0, 1.0,
                       -1.6))

# -- AXIS: foreground occluder, and its proscenium guard -------------------
cases = {
    "foregroundNarrowPost": dict(span=(-0.99, -0.86), z0=-0.4, z1=3.4),
    "foregroundShallowBeam": dict(span=(-1.0, 1.0), z0=2.95, z1=3.4),
    "foregroundMiddleSlab": dict(span=(-0.5, 0.5), z0=-0.4, z1=3.4),
    "foregroundProscenium": dict(span=(-1.0, 1.0), z0=-0.4, z1=3.4),
}
for label, kw in cases.items():
    r = room()
    result[label] = guarded(lambda r=r, kw=kw: r.foreground("fg", 3.4, **kw))

i = room()
i.foreground("post", 3.4, span=(-0.99, -0.86), z0=-0.4, z1=3.4)
result["foregroundIsInFront"] = bool(
    min(o.location.x for o in i.parts if o.name == "post") < i.front_x)

# -- alcoves are validated -------------------------------------------------
j = room()
result["alcoveOverlapRefused"] = guarded(
    lambda: j.back_wall(alcoves=[(-3.0, -1.0, 1.0), (-1.5, 0.5, 1.0)]))
k = room()
result["alcoveStraddlingOpeningRefused"] = guarded(
    lambda: k.back_wall(openings=[(-1.6, -0.8, 1.0, 2.0)],
                        alcoves=[(-3.0, -1.2, 1.0)]))

print("PROBE " + json.dumps(result))
