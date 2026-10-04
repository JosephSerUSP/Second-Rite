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
result["alcoveHasHeader"] = any(o.name == "alcove_0_header" for o in c.parts)
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

def two_members(r):
    r.foreground("post", 3.4, span=(-0.86, -0.70), z0=-0.4, z1=3.4)
    r.foreground("beam", 3.4, span=(-1.0, 1.0), z0=2.95, z1=3.4)
    r.foreground("beam2", 3.4, span=(-1.0, 1.0), z0=2.5, z1=2.9)


m = room()
result["foregroundCumulative"] = guarded(lambda: two_members(m))

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

# -- a platform can face along the lane; a piece can turn ------------------
e = room()
e.platform("step", -1.0, 2.0, 1.0, 3.0, 0.2, edge="-y")
riser = next(o for o in e.parts if o.name == "step_riser")
result["platformEdgeMinusY"] = {"riserY": round(riser.location.y, 4),
                                "riserSize": [round(v, 4) for v in riser.dimensions]}
result["platformBadEdge"] = guarded(lambda: room().platform("s", 0, 1, 0, 1, 0.2, edge="+x"))

t = room()
with t.piece("turned", turn=90, about=(1.0, 0.0)):
    t.part("turned_slab", (2.0, 0.2, 0.1), (1.0, 0.0, 0.05), t.wood)
turned = next(o for o in t.parts if o.name == "turned")
import bpy  # noqa: E402
bpy.context.view_layer.update()
xs = [(turned.matrix_world @ v.co) for v in turned.data.vertices]
result["pieceTurn"] = {"spanX": round(max(c.x for c in xs) - min(c.x for c in xs), 4),
                       "spanY": round(max(c.y for c in xs) - min(c.y for c in xs), 4),
                       "centre": [round(sum(c.x for c in xs) / len(xs), 4),
                                  round(sum(c.y for c in xs) / len(xs), 4)]}

roof = room(half_width=8)
roof.pitched_ceiling(rise=1.4, bays=9)
bpy.context.view_layer.update()
slopes = [o for o in roof.parts if o.name.startswith('roof_slope')]
points = [o.matrix_world @ v.co for o in slopes for v in o.data.vertices]
centre = (roof.front_x + roof.back_x) / 2
result['pitchedRoof'] = {
    'ridgeZ': max(p.z for p in points if abs(p.x-centre) < .2),
    'eaveZ': max(p.z for p in points if abs(p.x-centre) > 2),
    'gables': len([o for o in roof.parts if o.name.startswith('roof_gable')]),
}
import furnishings
from mathutils import Vector
altar_room = room()
furnishings.altar(altar_room, 'probe_altar', (0, 0))
altar_room.finish()
bpy.context.view_layer.update()
altar = next(o for o in altar_room.parts if o.name == 'probe_altar')
inv = altar.matrix_world.inverted()
def altar_hit(y):
    hit, location, normal, index = altar.ray_cast(inv @ Vector((-1,y,1.674)), Vector((1,0,0)))
    assert hit
    return (altar.matrix_world @ location).x
result['retableDepth'] = altar_hit(0) - altar_hit(.7)
print("PROBE " + json.dumps(result))
