"""Deterministic, low-poly procedural tree skeletons.

The generator is intentionally independent of Blender.  A skeleton can be
tested, serialized, reduced to an LOD, and only then turned into mesh data by a
recipe or the live tree lab.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math


@dataclass(frozen=True)
class TreeSpec:
    name: str
    height: float
    crown_radius: float
    crown_depth: float
    clear_trunk: float
    levels: int
    branch_frequency: int
    phyllotaxis_deg: float
    branch_angle_deg: float
    angle_variation_deg: float
    length_decay: float
    apical_dominance: float
    tropism: float
    attraction_weight: float
    attraction_points: int
    influence_radius: float
    kill_radius: float
    segment_length: float
    taper_power: float
    #: How much of the bole radius is lost between the ground and the crown
    #: top.  The pipe model alone only narrows the trunk where a child
    #: leaves it, which leaves the clear length a constant cylinder.
    #: How many leaders rise from the base.  One is a tree; several splayed
    #: leaders sharing a root are what makes a shrub a shrub.
    stems: int = 1
    #: Outward tilt of the secondary leaders, in degrees.  Ignored at stems=1.
    stem_spread_deg: float = 26.0
    #: Real-world length of one foliage spray, in metres.  A spray is a
    #: property of the foliage, not of the tree: a wider crown must be
    #: filled with MORE sprays, never with bigger leaves.
    spray_length: float = 1.6
    trunk_taper: float = .58
    #: Radius multiplier at the ground contact, for the basal flare.
    root_flare: float = 1.5
    seed: int = 1


@dataclass(frozen=True)
class Segment:
    index: int
    parent: int | None
    start: tuple[float, float, float]
    end: tuple[float, float, float]
    radius: float
    level: int
    foliage: bool = False


@dataclass(frozen=True)
class FoliageCarrier:
    """A branch-attached foliage spray with an authored axial orientation."""
    segment_index: int
    roll_radians: float


@dataclass(frozen=True)
class Skeleton:
    spec: TreeSpec
    segments: tuple[Segment, ...]
    foliage_carriers: tuple[FoliageCarrier, ...]

    @property
    def foliage_indices(self):
        return tuple(carrier.segment_index for carrier in self.foliage_carriers)


PRESETS = {
    "round_shade": dict(height=4.6, crown_radius=2.3, crown_depth=1.6, clear_trunk=.34,
                         levels=3, branch_frequency=4, phyllotaxis_deg=137.5,
                         branch_angle_deg=42, angle_variation_deg=8, length_decay=.64,
                         apical_dominance=.35, tropism=.10, attraction_weight=.42,
                         attraction_points=90, influence_radius=1.45, kill_radius=.42,
                         segment_length=.62, taper_power=2.3),
    "umbrella": dict(height=4.3, crown_radius=2.6, crown_depth=1.35, clear_trunk=.48,
                      levels=3, branch_frequency=5, phyllotaxis_deg=137.5,
                      branch_angle_deg=58, angle_variation_deg=7, length_decay=.67,
                      apical_dominance=.15, tropism=-.08, attraction_weight=.45,
                      attraction_points=100, influence_radius=1.6, kill_radius=.46,
                      segment_length=.60, taper_power=2.3),
    "columnar": dict(height=5.0, crown_radius=1.15, crown_depth=1.0, clear_trunk=.28,
                      levels=3, branch_frequency=3, phyllotaxis_deg=137.5,
                      branch_angle_deg=24, angle_variation_deg=5, length_decay=.70,
                      apical_dominance=.75, tropism=.16, attraction_weight=.28,
                      attraction_points=70, influence_radius=1.1, kill_radius=.35,
                      segment_length=.66, taper_power=2.3),
    "conical": dict(height=4.8, crown_radius=2.0, crown_depth=1.8, clear_trunk=.25,
                     levels=3, branch_frequency=4, phyllotaxis_deg=137.5,
                     branch_angle_deg=34, angle_variation_deg=6, length_decay=.66,
                     apical_dominance=.58, tropism=.12, attraction_weight=.36,
                     attraction_points=85, influence_radius=1.3, kill_radius=.40,
                     segment_length=.62, taper_power=2.3),
    "weeping": dict(height=4.4, crown_radius=2.25, crown_depth=1.7, clear_trunk=.36,
                     levels=3, branch_frequency=4, phyllotaxis_deg=137.5,
                     branch_angle_deg=48, angle_variation_deg=10, length_decay=.63,
                     apical_dominance=.20, tropism=-.42, attraction_weight=.40,
                     attraction_points=95, influence_radius=1.5, kill_radius=.43,
                     segment_length=.60, taper_power=2.3),
    "young": dict(height=2.8, crown_radius=1.3, crown_depth=1.1, clear_trunk=.20,
                  levels=2, branch_frequency=3, phyllotaxis_deg=137.5,
                  branch_angle_deg=35, angle_variation_deg=12, length_decay=.61,
                  apical_dominance=.52, tropism=.10, attraction_weight=.34,
                  attraction_points=38, influence_radius=1.0, kill_radius=.32,
                  segment_length=.52, taper_power=2.3),
}


LOD_BUDGETS = {"authoring": (160, 48), "low": (64, 48)}
#: Spec fields a caller may override.  Exported so the live bridge and the
#: lab cannot drift into two different notions of what is tunable.
TUNABLE_FIELDS = frozenset(
    field for field in TreeSpec.__dataclass_fields__ if field not in ("name", "seed"))
LOW_CARD_SUPPORT_SPACING = .48


def preset(name: str, *, seed_offset: int = 0, **overrides) -> TreeSpec:
    if name not in PRESETS:
        raise ValueError(f"unknown tree preset {name!r}")
    values = dict(PRESETS[name])
    values.update(overrides)
    values["name"] = name
    values["seed"] = int(values.get("seed", 1)) + int(seed_offset)
    return TreeSpec(**values)


def _rng(seed):
    state = [(int(seed) * 1103515245 + 12345) & 0x7fffffff]
    def next_value(lo=0.0, hi=1.0):
        state[0] = (state[0] * 1103515245 + 12345) & 0x7fffffff
        return lo + (hi - lo) * state[0] / 0x7fffffff
    return next_value


def _profile(name, z, height, radius, depth):
    t = max(0.0, min(1.0, z / height))
    if name == "umbrella": width = math.sqrt(max(.04, 1.0 - ((t - .70) / .42) ** 2))
    elif name == "columnar": width = .86 + .10 * math.sin(t * math.pi)
    elif name == "conical": width = max(.08, 1.0 - t)
    elif name == "weeping": width = .78 + .28 * t
    elif name == "young": width = .62 + .38 * t
    else: width = math.sqrt(max(.04, 1.0 - ((t - .55) / .58) ** 2))
    return radius * width, depth * width


def _add(a, b): return tuple(x + y for x, y in zip(a, b))
def _scale(a, s): return tuple(x * s for x in a)
def _length(a): return math.sqrt(sum(x * x for x in a))
def _unit(a):
    n = _length(a)
    return (0.0, 0.0, 1.0) if n < 1e-8 else _scale(a, 1.0 / n)


def _spread_foliage(segments, candidates, limit, spec):
    """Select carriers across limb families and crown volume."""
    candidates = list(dict.fromkeys(candidates))
    by_index = {segment.index: segment for segment in segments}
    if len(candidates) <= limit:
        return candidates
    crown_base = spec.height * spec.clear_trunk
    def position(index):
        p = by_index[index].end
        return (p[0] / max(.1, spec.crown_radius),
                p[1] / max(.1, spec.crown_radius),
                (p[2] - crown_base) / max(.1, spec.height - crown_base))
    def primary_family(index):
        node = by_index[index]
        while node.parent is not None and node.level > 1:
            node = by_index[node.parent]
        return node.index

    # Seed every primary-limb family with several spatially separated
    # carriers.  Pure global farthest-point sampling overvalues crown extrema
    # and leaves the woody inner runs bald.
    families = {}
    for index in candidates:
        families.setdefault(primary_family(index), []).append(index)
    selected = []
    family_quota = max(1, limit // max(1, len(families)))
    for family in sorted(families):
        pool = set(families[family])
        if not pool:
            continue
        # Seed with the family's LOWEST carrier.  Seeding with the most
        # radially distant one let farthest-point sampling -- which
        # already favours extremities -- drop the crown base entirely,
        # lifting first foliage well above the authored clear trunk.
        family_selected = [min(pool, key=lambda i: (position(i)[2], i))]
        pool.remove(family_selected[0])
        while pool and len(family_selected) < family_quota:
            choice = max(pool, key=lambda i: (
                min(_length(_add(position(i), _scale(position(j), -1)))
                    for j in family_selected), -i))
            family_selected.append(choice); pool.remove(choice)
        selected.extend(family_selected)
    # Spend any remaining budget globally on the largest uncovered gaps.
    selected = list(dict.fromkeys(selected[:limit]))
    remaining = set(candidates) - set(selected)
    while remaining and len(selected) < limit:
        choice = max(remaining, key=lambda i: (
            min(_length(_add(position(i), _scale(position(j), -1))) for j in selected),
            -i))
        selected.append(choice); remaining.remove(choice)
    return selected


def _foliage_carriers(segments, indices, spec):
    """Give spatially selected sprays deterministic, multi-view branch frames.

    Roll is distributed around supporting branch axes using the preset's
    phyllotactic divergence.  Crown azimuth offsets neighboring fans so the
    population does not collapse into a few shared planes.
    """
    by_index = {segment.index: segment for segment in segments}
    carriers = []
    for order, index in enumerate(indices):
        end = by_index[index].end
        crown_azimuth = math.degrees(math.atan2(end[1], end[0]))
        roll_deg = (order * spec.phyllotaxis_deg + crown_azimuth * .5) % 180.0
        carriers.append(FoliageCarrier(index, math.radians(roll_deg)))
    return tuple(carriers)


def foliage_card_budget(skeleton, lod="low"):
    """Allocate cards from foliage-bearing woody reach, not per tree.

    The full skeleton is the measuring authority even when the result will be
    reduced.  One carrier represents approximately one branch spray per
    LOW_CARD_SUPPORT_SPACING metres of eligible support.
    """
    if lod == "authoring":
        return LOD_BUDGETS[lod][1]
    support_length = sum(
        _length(_add(segment.end, _scale(segment.start, -1)))
        for segment in skeleton.segments if segment.foliage)
    return max(10, min(LOD_BUDGETS[lod][1], int(round(
        support_length / LOW_CARD_SUPPORT_SPACING))))


def generate(spec: TreeSpec, lod: str = "authoring") -> Skeleton:
    if lod not in LOD_BUDGETS: raise ValueError(f"unknown tree LOD {lod!r}")
    max_segments, max_cards = LOD_BUDGETS[lod]
    rng = _rng(spec.seed)
    points = []
    crown_base = spec.height * spec.clear_trunk
    for _ in range(spec.attraction_points):
        z = crown_base + rng() * (spec.height - crown_base)
        rx, ry = _profile(spec.name, z, spec.height, spec.crown_radius, spec.crown_depth)
        theta = rng(0, math.tau); rr = math.sqrt(rng())
        points.append([math.cos(theta) * rx * rr, math.sin(theta) * ry * rr, z])

    segments = []

    def append(parent, end, level, foliage=False):
        start = (0.0, 0.0, 0.0) if parent is None else segments[parent].end
        end = (end[0], end[1], min(spec.height * 1.04, max(0.0, end[2])))
        idx = len(segments)
        segments.append(Segment(idx, parent, start, end, .025, level, foliage))
        return idx

    # A trunk remains the central leader through the entire crown.  Primary
    # limbs attach to different leader nodes; they never all erupt from the
    # clear-trunk endpoint.
    # Every leader leaves the same root node, so a multi-stemmed specimen is
    # one connected graph sharing a single ground contact rather than several
    # trees standing in the same spot.  At stems=1 this is the original single
    # leader, down to the order of the random draws.
    leaders = []
    for stem in range(max(1, int(spec.stems))):
        lean_x = rng(-.025, .025); lean_y = rng(-.025, .025)
        stem_height = spec.height
        if stem:
            # Splay the secondary leaders around the base by the same
            # divergence the limbs use, so stems do not pair up or overlap.
            azimuth = math.radians(stem * spec.phyllotaxis_deg + rng(-20, 20))
            push = math.tan(math.radians(max(0.0, spec.stem_spread_deg)))
            lean_x += math.cos(azimuth) * push
            lean_y += math.sin(azimuth) * push
            stem_height = spec.height * (.72 + rng(0, .26))
        steps = max(5, int(math.ceil(stem_height / spec.segment_length)))
        parent = None
        nodes = []
        for i in range(steps):
            t = (i + 1) / steps
            end = (lean_x * stem_height * t * t, lean_y * stem_height * t * t,
                   stem_height * t)
            parent = append(parent, end, 0, i == steps - 1)
            nodes.append(parent)
        leaders.append(nodes)

    # Leader node i ENDS at (i + 1) / steps of that leader's height, so
    # indexing nodes by the clear-trunk fraction directly attaches the first
    # limb a whole segment too high, and the crown base inherits that error.
    attachments = []
    for nodes in leaders:
        steps = len(nodes)
        first_crown = max(0, int(round(spec.clear_trunk * steps)) - 1)
        usable = list(range(first_crown, max(first_crown + 1, steps - 1)))
        wanted = max(3, spec.branch_frequency + 1)
        # Limbs are shared out between leaders; a shrub's individual stems each
        # carry fewer than a single trunk would.
        wanted = max(2, wanted // max(1, len(leaders)))
        count = min(len(usable), wanted)
        attachments.extend(
            nodes[usable[round(i * (len(usable) - 1) / max(1, count - 1))]]
            for i in range(count))

    for ordinal, attach in enumerate(attachments):
        if len(segments) >= max_segments: break
        z = segments[attach].end[2]
        envelope, _ = _profile(spec.name, z, spec.height,
                               spec.crown_radius, spec.crown_depth)
        az = math.radians(ordinal * spec.phyllotaxis_deg + rng(-18, 18))
        # Lower limbs on a broad crown reach outward before they climb.
        # Giving every limb the same departure angle is what pushed the
        # first foliage most of a metre above the authored crown base.
        attach_t = (z - crown_base) / max(1e-6, spec.height - crown_base)
        spread_bias = max(0.0, 1.0 - attach_t) * spec.branch_angle_deg * .55
        elevation = math.radians(90.0 - spec.branch_angle_deg - spread_bias
                                 + rng(-spec.angle_variation_deg, spec.angle_variation_deg))
        if spec.name == "weeping": elevation -= math.radians(18)
        direction = _unit((math.cos(az) * math.cos(elevation),
                           math.sin(az) * math.cos(elevation),
                           math.sin(elevation)))
        limb_steps = max(2, min(5, int(envelope / max(.15, spec.segment_length * .62)) + 1))
        limb_parent = attach
        limb_nodes = []
        # The lowest limb always carries foliage from its first segment, so
        # the crown base follows the authored clear trunk instead of
        # wherever the second segment of a steep limb happens to reach.
        first_foliage_step = (0 if (ordinal == 0 or attach_t < .35)
                              else max(1, limb_steps // 3))
        for step in range(limb_steps):
            if len(segments) >= max_segments: break
            start = segments[limb_parent].end
            # Gradual curvature produces a limb, not a new fan at every node.
            up = spec.tropism * .16 if spec.name != "weeping" else -.11
            direction = _unit((direction[0], direction[1], direction[2] + up))
            length = spec.segment_length * rng(.72, 1.02) * (spec.length_decay ** (step * .35))
            end = _add(start, _scale(direction, length))
            rx, _ = _profile(spec.name, end[2], spec.height,
                             spec.crown_radius, spec.crown_depth)
            radial = math.hypot(end[0], end[1])
            if radial > max(rx, .08):
                f = max(rx, .08) / radial; end = (end[0] * f, end[1] * f, end[2])
            limb_parent = append(limb_parent, end, 1, step >= first_foliage_step)
            limb_nodes.append(limb_parent)

        # Secondary shoots emerge along the outer half of each primary limb,
        # alternate sides, and continue outward.  This gives visible forks
        # without recursively exploding every endpoint into a radial star.
        for shoot_no, limb_node in enumerate(limb_nodes[max(1, len(limb_nodes)//2):]):
            if len(segments) >= max_segments or spec.levels < 2: break
            base_dir = _unit(_add(segments[limb_node].end,
                                  _scale(segments[limb_node].start, -1)))
            side = (-1.0 if shoot_no % 2 else 1.0)
            perpendicular = _unit((-base_dir[1] * side, base_dir[0] * side, .35 + rng(-.15, .2)))
            shoot_dir = _unit(tuple(base_dir[k] * .55 + perpendicular[k] * .45 for k in range(3)))
            shoot_parent = limb_node
            for shoot_step in range(2):
                if len(segments) >= max_segments: break
                start = segments[shoot_parent].end
                length = spec.segment_length * spec.length_decay * rng(.45, .68)
                end = _add(start, _scale(shoot_dir, length))
                shoot_parent = append(shoot_parent, end, 2, True)
                shoot_dir = _unit((shoot_dir[0], shoot_dir[1], shoot_dir[2] + spec.tropism * .08))
            # A small terminal fork supplies the fine silhouette that the
            # branch cards sit on.  Both twigs share the shoot endpoint and
            # remain part of the connected graph.
            if spec.levels >= 3:
                fork_origin = shoot_parent
                fork_axis = _unit(_add(segments[fork_origin].end,
                                      _scale(segments[fork_origin].start, -1)))
                fork_side = _unit((-fork_axis[1], fork_axis[0], .22))
                for sign in (-1.0, 1.0):
                    if len(segments) >= max_segments: break
                    fork_dir = _unit(tuple(fork_axis[k] * .72 + fork_side[k] * .34 * sign
                                           for k in range(3)))
                    end = _add(segments[fork_origin].end,
                               _scale(fork_dir, spec.segment_length * rng(.30, .46)))
                    append(fork_origin, end, 3, True)

    # Pipe-model radius propagation, with a small terminal taper.
    for idx in range(len(segments) - 1, -1, -1):
        child_radii = [s.radius for s in segments if s.parent == idx]
        if child_radii:
            radius = sum(r ** spec.taper_power for r in child_radii) ** (1.0 / spec.taper_power)
            segments[idx] = replace(segments[idx], radius=max(radius * 1.04, .025))
    # The pipe model narrows a trunk only where a child leaves it, so the
    # clear length below the crown stays a near-constant cylinder.  Real
    # boles taper continuously; apply that to the leader afterwards so the
    # structural radii the crown depends on are unchanged.
    for idx, segment in enumerate(segments):
        if segment.level != 0:
            continue
        t = max(0.0, min(1.0, segment.end[2] / max(1e-6, spec.height)))
        segments[idx] = replace(segment, radius=max(
            .025, segment.radius * (1.0 - spec.trunk_taper * t)))
    foliage = [s.index for s in segments if s.foliage]
    foliage = _spread_foliage(segments, foliage, max_cards, spec)
    return Skeleton(spec, tuple(segments), _foliage_carriers(segments, foliage, spec))


def reduce_lod(skeleton: Skeleton, lod: str) -> Skeleton:
    if lod == "authoring": return skeleton
    max_segments, _max_cards = LOD_BUDGETS[lod]
    max_cards = foliage_card_budget(skeleton, lod)
    # Rank structural axes before fine shoots.  Parents always have a lower
    # level (and earlier index) than their children, so this remains rooted.
    ranked = sorted(skeleton.segments, key=lambda s: (s.level, s.index))
    keep = {s.index for s in ranked[:max_segments]}
    kept = tuple(s for s in skeleton.segments if s.index in keep)
    foliage = _spread_foliage(kept, (s.index for s in kept if s.foliage),
                              max_cards, skeleton.spec)
    return Skeleton(skeleton.spec, kept, _foliage_carriers(kept, foliage, skeleton.spec))


def validate(skeleton: Skeleton, lod: str = "authoring"):
    max_segments, max_cards = LOD_BUDGETS[lod]
    if not skeleton.segments or skeleton.segments[0].parent is not None: raise ValueError("tree skeleton has no root")
    if len(skeleton.segments) > max_segments or len(skeleton.foliage_indices) > max_cards: raise ValueError("tree budget exceeded")
    ids = {s.index for s in skeleton.segments}
    if len(set(skeleton.foliage_indices)) != len(skeleton.foliage_indices): raise ValueError("duplicate foliage carrier")
    for carrier in skeleton.foliage_carriers:
        if carrier.segment_index not in ids: raise ValueError("foliage carrier segment missing")
        if not math.isfinite(carrier.roll_radians): raise ValueError("non-finite foliage orientation")
    for segment in skeleton.segments:
        if segment.parent is not None and segment.parent not in ids: raise ValueError("tree parent missing")
        if _length(_add(segment.end, _scale(segment.start, -1))) < 1e-5: raise ValueError("zero-length tree segment")
        if not all(math.isfinite(v) for v in (*segment.start, *segment.end, segment.radius)): raise ValueError("non-finite tree geometry")
        if segment.end[2] < -1e-4 or segment.end[2] > skeleton.spec.height * 1.05: raise ValueError("tree escaped height envelope")
    return True
