"""Continuous structures attached to a house wing.

The first operation is a covered veranda: a slab, a regular set of timber
supports, and a shallow tiled lean-to. It is intentionally emitted as one
semantic record so an author can move or replace the whole gallery in Blender
without turning its posts into a pile of scene-specific objects.
"""

from __future__ import annotations

from .records import GrammarError, MeshBuilder


class _Placed:
    """Build local veranda coordinates in the building frame."""

    def __init__(self, name, origin, inward, along):
        self.builder = MeshBuilder(name)
        self.origin = origin
        self.inward = inward
        self.along = along

    def point(self, point):
        depth, across, z = point
        return (self.origin[0] + depth * self.inward[0] + across * self.along[0],
                self.origin[1] + depth * self.inward[1] + across * self.along[1],
                z)

    def add_box(self, low, high, semantic):
        self.builder.add_box(self.point(low), self.point(high), semantic)

    def add_profile_prism(self, profile, low, high, semantic):
        """Extrude an XZ profile along the veranda's across axis."""
        self.builder.add_face(
            [self.point((depth, low, z)) for depth, z in reversed(profile)],
            semantic)
        self.builder.add_face(
            [self.point((depth, high, z)) for depth, z in profile], semantic)
        for index, (depth0, z0) in enumerate(profile):
            depth1, z1 = profile[(index + 1) % len(profile)]
            self.builder.add_face([
                self.point((depth0, low, z0)), self.point((depth1, low, z1)),
                self.point((depth1, high, z1)), self.point((depth0, high, z0)),
            ], semantic)


def _frame(wing, veranda):
    """Return ``origin, inward, along, host_span`` for one elevation."""
    x0, x1 = wing.x_span()
    y0, y1 = wing.y_span()
    if veranda.elevation == "front":
        return (x0, veranda.lane_offset, 0.0), (1.0, 0.0), (0.0, 1.0), (y0, y1)
    if veranda.elevation == "back":
        return (x1, veranda.lane_offset, 0.0), (-1.0, 0.0), (0.0, -1.0), (y0, y1)
    if veranda.elevation == "left":
        return (veranda.lane_offset, y0, 0.0), (0.0, 1.0), (1.0, 0.0), (x0, x1)
    return (veranda.lane_offset, y1, 0.0), (0.0, -1.0), (-1.0, 0.0), (x0, x1)


def _build_attachment(recipe, veranda):
    wing = recipe.wing(veranda.wing)
    origin, inward, along, host_span = _frame(wing, veranda)
    low, high = host_span
    requested_low = veranda.lane_offset - veranda.width / 2.0
    requested_high = veranda.lane_offset + veranda.width / 2.0
    if requested_low < low or requested_high > high:
        raise GrammarError(
            f"veranda {veranda.id}: spans {requested_low}..{requested_high}, "
            f"past wing {wing.id} host span {low}..{high}")
    if veranda.height <= veranda.slab:
        raise GrammarError(
            f"veranda {veranda.id}: height {veranda.height} must exceed slab "
            f"{veranda.slab}")

    half = veranda.width / 2.0
    placed = _Placed(f"veranda_{veranda.id}", origin, inward, along)
    # The slab projects from the wall. Its top remains level so the structure
    # reads as a walkable continuation of the house floor.
    placed.add_box((-veranda.depth, -half, 0.0),
                   (0.0, half, veranda.slab), veranda.support_semantic)

    if veranda.support_count:
        if veranda.support_count == 1:
            positions = (0.0,)
        else:
            positions = tuple(-half + veranda.width * index /
                              (veranda.support_count - 1)
                              for index in range(veranda.support_count))
        for across in positions:
            half_support = veranda.support_width / 2.0
            placed.add_box(
                (-veranda.depth - half_support, across - half_support,
                 veranda.slab),
                (-veranda.depth + half_support, across + half_support,
                 veranda.height), veranda.support_semantic)

    # A single lean-to profile is shared by all bays. It is a roof operation,
    # not a decorative flat board, and stays editable as an ordinary mesh.
    profile = [
        (0.0, veranda.height + veranda.roof_rise),
        (-veranda.depth, veranda.height),
        (-veranda.depth, veranda.height - veranda.roof_thickness),
        (0.0, veranda.height + veranda.roof_rise - veranda.roof_thickness),
    ]
    placed.add_profile_prism(profile, -half, half, veranda.roof_semantic)
    return placed.builder.record(
        f"attachment:{veranda.id}", origin=origin, parent_role="body",
        metadata={"kind": "veranda", "wing": veranda.wing,
                  "elevation": veranda.elevation,
                  "supportCount": veranda.support_count})


def build_attachments(recipe):
    """Build each attached structure in authored order."""
    return [_build_attachment(recipe, veranda)
            for veranda in recipe.attachments]
