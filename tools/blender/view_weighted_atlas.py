"""Camera-envelope-aware UV density allocation for Blender environment bakes.

This module separates two concerns:

1. pure demand weighting, which can be tested without Blender; and
2. Blender measurement/packing, which samples a bounded authored camera envelope.

The allocator never deletes geometry. Low-importance faces retain a configurable
world-space density floor. Destructive culling, if ever desired, belongs to a
separate explicit optimization.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence


_EPS = 1e-9


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


@dataclass(frozen=True)
class ViewSample:
    """One plausible authored camera state.

    ``cost`` is an authoring-relative movement distance in [0, 1]: 0 is the
    nominal view, 1 is the edge of the intended envelope. It intentionally does
    not prescribe how eye motion, pitch, yaw and projection-window motion are
    converted into one scalar; the caller owns that policy when building the
    envelope.
    """

    name: str
    weight: float = 1.0
    cost: float = 0.0
    projection_window_offset_x: float = 0.0
    projection_window_offset_y: float = 0.0
    eye_offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    yaw_deg: float = 0.0
    pitch_deg: float = 0.0

    def __post_init__(self):
        if self.weight < 0:
            raise ValueError("ViewSample.weight must be >= 0")
        if not 0.0 <= self.cost <= 1.0:
            raise ValueError("ViewSample.cost must be in [0, 1]")


@dataclass(frozen=True)
class FaceObservation:
    """One face measured from one camera sample."""

    sample_name: str
    sample_weight: float
    sample_cost: float
    projected_area_px: float
    facing_cos: float
    in_frame: bool
    occluded: bool

    @property
    def visible_area_px(self) -> float:
        if self.in_frame and not self.occluded and self.facing_cos > 0.0:
            return max(0.0, self.projected_area_px)
        return 0.0


@dataclass(frozen=True)
class AllocationPolicy:
    """Controls the blend between world fairness and view demand."""

    view_bias: float = 0.75
    peak_mix: float = 0.35
    min_density: float = 0.08
    accessibility_reserve: float = 0.35
    movement_falloff: float = 1.75
    occlusion_penalty: float = 0.70
    offscreen_penalty: float = 0.85
    rear_facing_cos: float = -0.95
    near_facing_cos: float = 0.15

    def __post_init__(self):
        for name in ("view_bias", "peak_mix", "min_density", "accessibility_reserve"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"AllocationPolicy.{name} must be in [0, 1]")
        if self.movement_falloff < 0:
            raise ValueError("movement_falloff must be >= 0")
        if not 0.0 <= self.occlusion_penalty <= 1.0:
            raise ValueError("occlusion_penalty must be in [0, 1]")
        if not 0.0 <= self.offscreen_penalty <= 1.0:
            raise ValueError("offscreen_penalty must be in [0, 1]")
        if self.rear_facing_cos >= self.near_facing_cos:
            raise ValueError("rear_facing_cos must be < near_facing_cos")


@dataclass
class FaceDemand:
    index: int
    world_area: float
    expected_screen_px: float
    peak_screen_px: float
    screen_metric_px: float
    visibility_probability: float
    best_facing_cos: float
    accessibility: float
    category: str
    world_density: float = 1.0
    view_density: float = 0.0
    density_multiplier: float = 1.0
    target_weight: float = 0.0


def _normalised_weights(observations: Sequence[FaceObservation]) -> list[float]:
    total = sum(max(0.0, o.sample_weight) for o in observations)
    if total <= _EPS:
        if not observations:
            return []
        return [1.0 / len(observations)] * len(observations)
    return [max(0.0, o.sample_weight) / total for o in observations]


def _orientation_accessibility(best_facing_cos: float, policy: AllocationPolicy) -> float:
    span = policy.near_facing_cos - policy.rear_facing_cos
    return _clamp((best_facing_cos - policy.rear_facing_cos) / max(span, _EPS))


def _movement_discount(cost: float, policy: AllocationPolicy) -> float:
    return math.exp(-policy.movement_falloff * _clamp(cost))


def summarise_face(
    index: int,
    world_area: float,
    observations: Sequence[FaceObservation],
    policy: AllocationPolicy,
    *,
    explicitly_unreachable: bool = False,
) -> FaceDemand:
    """Reduce one face's camera-envelope observations into a demand summary."""

    if world_area <= 0.0:
        raise ValueError("world_area must be > 0")
    if not observations:
        return FaceDemand(
            index=index,
            world_area=world_area,
            expected_screen_px=0.0,
            peak_screen_px=0.0,
            screen_metric_px=0.0,
            visibility_probability=0.0,
            best_facing_cos=-1.0,
            accessibility=0.0 if explicitly_unreachable else policy.min_density,
            category="unreachable" if explicitly_unreachable else "strongly-back-facing",
        )

    weights = _normalised_weights(observations)
    visible = [o.visible_area_px for o in observations]
    expected = sum(w * area for w, area in zip(weights, visible))
    peak = max(visible, default=0.0)
    visibility_probability = sum(w for w, area in zip(weights, visible) if area > 0.0)
    screen_metric = (1.0 - policy.peak_mix) * expected + policy.peak_mix * peak
    best_facing = max(o.facing_cos for o in observations)

    if explicitly_unreachable:
        accessibility = 0.0
        category = "unreachable"
    else:
        visible_costs = [o.sample_cost for o in observations if o.visible_area_px > 0.0]
        if visible_costs:
            best_cost = min(visible_costs)
            accessibility = _movement_discount(best_cost, policy)
            category = "visible-nominal" if best_cost <= _EPS else "visible-in-envelope"
        else:
            orientation = _orientation_accessibility(best_facing, policy)
            close = [
                o for o in observations
                if o.facing_cos >= best_facing - 0.05
            ] or list(observations)
            best_cost = min(o.sample_cost for o in close)
            accessibility = orientation * _movement_discount(best_cost, policy)

            front_in_frame = [o for o in observations if o.facing_cos > 0.0 and o.in_frame]
            front_offscreen = [o for o in observations if o.facing_cos > 0.0 and not o.in_frame]
            if front_in_frame and all(o.occluded for o in front_in_frame):
                accessibility *= policy.occlusion_penalty
                category = "occluded"
            elif front_offscreen:
                accessibility *= policy.offscreen_penalty
                category = "offscreen-reachable"
            elif accessibility >= 0.25:
                category = "near-visible"
            else:
                category = "strongly-back-facing"

    return FaceDemand(
        index=index,
        world_area=world_area,
        expected_screen_px=expected,
        peak_screen_px=peak,
        screen_metric_px=screen_metric,
        visibility_probability=visibility_probability,
        best_facing_cos=best_facing,
        accessibility=_clamp(accessibility),
        category=category,
    )


def allocate_demands(
    world_areas: Sequence[float],
    observations_by_face: Sequence[Sequence[FaceObservation]],
    policy: AllocationPolicy = AllocationPolicy(),
    *,
    explicitly_unreachable: Iterable[int] = (),
) -> list[FaceDemand]:
    """Compute per-face texel-density multipliers.

    The world-space baseline is 1.0 texel density everywhere. View demand is
    measured as screen pixels per world-area and normalised so an average face
    remains near 1.0. Faces with little/no current screen demand receive an
    accessibility reserve, then a hard minimum density floor. Finally the
    result eases between world fairness and view demand through ``view_bias``.
    """

    if len(world_areas) != len(observations_by_face):
        raise ValueError("world_areas and observations_by_face length mismatch")
    unreachable = set(int(i) for i in explicitly_unreachable)
    demands = [
        summarise_face(i, float(area), observations_by_face[i], policy,
                       explicitly_unreachable=i in unreachable)
        for i, area in enumerate(world_areas)
    ]
    if not demands:
        return []

    total_area = sum(d.world_area for d in demands)
    total_screen = sum(d.screen_metric_px for d in demands)
    average_screen_density = total_screen / max(total_area, _EPS)

    for d in demands:
        if average_screen_density > _EPS:
            screen_density = (d.screen_metric_px / d.world_area) / average_screen_density
        else:
            screen_density = 0.0
        reserve = policy.accessibility_reserve * d.accessibility
        d.view_density = max(policy.min_density, screen_density, reserve)
        d.density_multiplier = (
            (1.0 - policy.view_bias) * d.world_density
            + policy.view_bias * d.view_density
        )
        d.target_weight = d.world_area * d.density_multiplier

    return demands


def allocation_report(demands: Sequence[FaceDemand], policy: AllocationPolicy) -> dict:
    categories: dict[str, dict[str, float]] = {}
    for d in demands:
        row = categories.setdefault(d.category, {"faces": 0, "targetWeight": 0.0})
        row["faces"] += 1
        row["targetWeight"] += d.target_weight
    return {
        "viewBias": policy.view_bias,
        "peakMix": policy.peak_mix,
        "minDensity": policy.min_density,
        "accessibilityReserve": policy.accessibility_reserve,
        "faces": len(demands),
        "categories": categories,
        "density": {
            "min": min((d.density_multiplier for d in demands), default=0.0),
            "max": max((d.density_multiplier for d in demands), default=0.0),
            "mean": (
                sum(d.density_multiplier for d in demands) / len(demands)
                if demands else 0.0
            ),
        },
        "expectedScreenPx": sum(d.expected_screen_px for d in demands),
        "peakScreenPx": sum(d.peak_screen_px for d in demands),
    }


# ---------------------------------------------------------------------------
# Blender adapter


def _clip_polygon(poly, width: float, height: float):
    def inside(p, edge):
        if edge == 0:
            return p[0] >= 0.0
        if edge == 1:
            return p[0] <= width
        if edge == 2:
            return p[1] >= 0.0
        return p[1] <= height

    def intersect(p, q, edge):
        if edge in (0, 1):
            x = 0.0 if edge == 0 else width
            t = (x - p[0]) / (q[0] - p[0]) if abs(q[0] - p[0]) > _EPS else 0.0
            return (x, p[1] + t * (q[1] - p[1]))
        y = 0.0 if edge == 2 else height
        t = (y - p[1]) / (q[1] - p[1]) if abs(q[1] - p[1]) > _EPS else 0.0
        return (p[0] + t * (q[0] - p[0]), y)

    out = list(poly)
    for edge in range(4):
        if not out:
            return []
        src, out = out, []
        for i, cur in enumerate(src):
            prev = src[i - 1]
            cur_in, prev_in = inside(cur, edge), inside(prev, edge)
            if cur_in:
                if not prev_in:
                    out.append(intersect(prev, cur, edge))
                out.append(cur)
            elif prev_in:
                out.append(intersect(prev, cur, edge))
    return out


def _polygon_area_2d(poly) -> float:
    if len(poly) < 3:
        return 0.0
    return abs(sum(
        poly[i][0] * poly[(i + 1) % len(poly)][1]
        - poly[(i + 1) % len(poly)][0] * poly[i][1]
        for i in range(len(poly))
    )) * 0.5


def _world_face_area(obj, poly) -> float:
    pts = [obj.matrix_world @ obj.data.vertices[i].co for i in poly.vertices]
    if len(pts) < 3:
        return 0.0
    origin = pts[0]
    area = 0.0
    for i in range(1, len(pts) - 1):
        area += (pts[i] - origin).cross(pts[i + 1] - origin).length * 0.5
    return max(area, _EPS)


def _camera_state(camera):
    return (
        camera.matrix_world.copy(),
        float(camera.data.shift_x),
        float(camera.data.shift_y),
    )


def _apply_view(scene, camera, sample: ViewSample, base_state):
    from mathutils import Matrix, Quaternion, Vector

    base_matrix, base_shift_x, base_shift_y = base_state
    q = base_matrix.to_quaternion()
    translation = base_matrix.translation.copy() + Vector(sample.eye_offset)

    if sample.yaw_deg:
        q = Quaternion((0.0, 0.0, 1.0), math.radians(sample.yaw_deg)) @ q
    if sample.pitch_deg:
        right = q @ Vector((1.0, 0.0, 0.0))
        q = Quaternion(right, math.radians(sample.pitch_deg)) @ q

    camera.matrix_world = Matrix.Translation(translation) @ q.to_matrix().to_4x4()
    width = float(scene.render.resolution_x)
    height = float(scene.render.resolution_y)
    camera.data.shift_x = base_shift_x - sample.projection_window_offset_x / max(width, 1.0)
    camera.data.shift_y = base_shift_y + sample.projection_window_offset_y / max(height, 1.0)
    scene.view_layers[0].update()


def _restore_camera(scene, camera, base_state):
    matrix, shift_x, shift_y = base_state
    camera.matrix_world = matrix
    camera.data.shift_x = shift_x
    camera.data.shift_y = shift_y
    scene.view_layers[0].update()


def _face_occluded(scene, depsgraph, camera, obj, poly_index: int, centre) -> bool:
    direction = centre - camera.matrix_world.translation
    distance = direction.length
    if distance <= _EPS:
        return False
    direction.normalize()
    origin = camera.matrix_world.translation + direction * 1e-4
    hit, _loc, _normal, face_index, hit_obj, _matrix = scene.ray_cast(
        depsgraph, origin, direction, distance=max(distance - 2e-4, 0.0)
    )
    if not hit:
        return False
    return not (hit_obj == obj and face_index == poly_index)


def measure_envelope(scene, camera, obj, samples: Sequence[ViewSample]):
    """Measure every mesh polygon across the authored camera envelope."""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view

    if obj.type != "MESH":
        raise TypeError("view-weighted atlas target must be a MESH")
    if not samples:
        raise ValueError("camera envelope must contain at least one ViewSample")

    width = float(scene.render.resolution_x)
    height = float(scene.render.resolution_y)
    mesh = obj.data
    depsgraph = bpy.context.evaluated_depsgraph_get()
    base_state = _camera_state(camera)
    observations = [[] for _ in mesh.polygons]
    world_areas = [_world_face_area(obj, p) for p in mesh.polygons]
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()

    try:
        for sample in samples:
            _apply_view(scene, camera, sample, base_state)
            eye = camera.matrix_world.translation
            for poly in mesh.polygons:
                world = [obj.matrix_world @ mesh.vertices[i].co for i in poly.vertices]
                centre = sum(world, world[0] * 0.0) / len(world)
                normal = (normal_matrix @ poly.normal).normalized()
                to_eye = eye - centre
                facing = normal.dot(to_eye.normalized()) if to_eye.length > _EPS else 1.0

                points = []
                behind = False
                for vertex in world:
                    co = world_to_camera_view(scene, camera, vertex)
                    if co.z <= 0.0:
                        behind = True
                        break
                    points.append((co.x * width, (1.0 - co.y) * height))
                clipped = [] if behind else _clip_polygon(points, width, height)
                area = _polygon_area_2d(clipped) if facing > 0.0 else 0.0
                in_frame = area > 0.25
                occluded = False
                if in_frame:
                    occluded = _face_occluded(scene, depsgraph, camera, obj, poly.index, centre)
                observations[poly.index].append(FaceObservation(
                    sample_name=sample.name,
                    sample_weight=sample.weight,
                    sample_cost=sample.cost,
                    projected_area_px=area,
                    facing_cos=facing,
                    in_frame=in_frame,
                    occluded=occluded,
                ))
    finally:
        _restore_camera(scene, camera, base_state)

    return world_areas, observations


def _face_basis_world(obj, poly):
    from mathutils import Vector

    pts = [obj.matrix_world @ obj.data.vertices[i].co for i in poly.vertices]
    normal = (pts[1] - pts[0]).cross(pts[2] - pts[0]).normalized()
    ref = Vector((0.0, 0.0, 1.0))
    if abs(normal.dot(ref)) > 0.9:
        ref = Vector((1.0, 0.0, 0.0))
    u = (ref - normal * ref.dot(normal)).normalized()
    v = normal.cross(u).normalized()
    origin = pts[0]
    coords = [((p - origin).dot(u), (p - origin).dot(v)) for p in pts]
    us = [p[0] for p in coords]
    vs = [p[1] for p in coords]
    return min(us), min(vs), max(us) - min(us), max(vs) - min(vs), coords


def pack_per_face(obj, demands: Sequence[FaceDemand], *, atlas_size=1024, margin_px=4,
                  uv_name="TH_VIEW_ATLAS") -> dict:
    """Proof-mode per-face packing using demand weights.

    This intentionally favours controllability over seam efficiency. A later
    chart-aware implementation can consume the same demand multipliers without
    changing the camera-envelope measurement or weighting policy.
    """

    mesh = obj.data
    if len(demands) != len(mesh.polygons):
        raise ValueError("demand count must match mesh polygon count")
    uv = mesh.uv_layers.get(uv_name) or mesh.uv_layers.new(name=uv_name)
    mesh.uv_layers.active = uv

    total_weight = sum(max(d.target_weight, _EPS) for d in demands)
    usable = max(1.0, float(atlas_size - 2 * margin_px))
    target_pixels = usable * usable * 0.72
    rects = []
    for poly, demand in zip(mesh.polygons, demands):
        u0, v0, du, dv, coords = _face_basis_world(obj, poly)
        aspect = _clamp(du / max(dv, _EPS), 0.05, 20.0)
        pixel_area = target_pixels * max(demand.target_weight, _EPS) / max(total_weight, _EPS)
        h = max(1.0, math.sqrt(pixel_area / aspect))
        w = max(1.0, aspect * h)
        rects.append((poly.index, w, h, (u0, v0, du, dv, coords)))

    scale = 1.0
    placed = None
    for _ in range(64):
        x = y = float(margin_px)
        shelf_h = 0.0
        trial = []
        ok = True
        for index, raw_w, raw_h, basis in sorted(rects, key=lambda r: -r[2] * scale):
            w, h = max(1.0, raw_w * scale), max(1.0, raw_h * scale)
            if x + w + margin_px > atlas_size:
                x = float(margin_px)
                y += shelf_h + margin_px
                shelf_h = 0.0
            if y + h + margin_px > atlas_size:
                ok = False
                break
            trial.append((index, x, y, w, h, basis))
            x += w + margin_px
            shelf_h = max(shelf_h, h)
        if ok:
            placed = trial
            break
        scale *= 0.90
    if placed is None:
        raise RuntimeError("view-weighted atlas packing failed")

    packed_pixels = 0.0
    for index, px, py, pw, ph, basis in placed:
        poly = mesh.polygons[index]
        u0, v0, du, dv, coords = basis
        for local_i, loop_index in enumerate(poly.loop_indices):
            cu, cv = coords[local_i]
            su = (cu - u0) / max(du, _EPS)
            sv = (cv - v0) / max(dv, _EPS)
            uv.data[loop_index].uv = (
                (px + su * pw) / atlas_size,
                1.0 - (py + sv * ph) / atlas_size,
            )
        packed_pixels += pw * ph
    mesh.update()
    return {
        "mode": "view-weighted-per-face",
        "uvLayer": uv_name,
        "atlasSize": atlas_size,
        "faces": len(placed),
        "globalScale": scale,
        "packedPixels": int(packed_pixels),
        "packedFraction": packed_pixels / float(atlas_size * atlas_size),
        "marginPx": margin_px,
    }


def allocate_blender(scene, camera, obj, samples: Sequence[ViewSample],
                     policy: AllocationPolicy = AllocationPolicy(), *,
                     atlas_size=1024, margin_px=4,
                     explicitly_unreachable: Iterable[int] = ()) -> dict:
    world_areas, observations = measure_envelope(scene, camera, obj, samples)
    demands = allocate_demands(
        world_areas, observations, policy,
        explicitly_unreachable=explicitly_unreachable,
    )
    pack = pack_per_face(obj, demands, atlas_size=atlas_size, margin_px=margin_px)
    report = allocation_report(demands, policy)
    report.update({
        "cameraEnvelope": [
            {
                "name": s.name,
                "weight": s.weight,
                "cost": s.cost,
                "projectionWindowOffset": [
                    s.projection_window_offset_x,
                    s.projection_window_offset_y,
                ],
                "eyeOffset": list(s.eye_offset),
                "yawDeg": s.yaw_deg,
                "pitchDeg": s.pitch_deg,
            }
            for s in samples
        ],
        "packing": pack,
    })
    return report
