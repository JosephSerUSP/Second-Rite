"""The EEVEE atlas bake: what an exporter runs in place of Cycles' selected-to-active bake.

EEVEE cannot bake, so the atlas is a camera-projection bake (`eevee_projection.py`): the lane cameras
photograph the room from the source meshes, and the joined render mesh says which texel each pixel
belongs to. This module is the exporter-facing wrapper, the same for an interior and an exterior:

  * the BEAUTY frames see the source meshes (they carry the real materials and the real housings around
    the lamps) with the joined mesh hidden, so it neither shows nor casts;
  * the UV frames see the joined mesh alone;
  * the optional lighting shims for EEVEE run first, on the source meshes: companion area lights for
    emissive surfaces (`emissive_lights.py`), shadow release for lamps inside small fixtures
    (`light_fixtures.py`), and a baked light probe volume with `capture_world` so a sealed room's walls
    occlude the world fill (`stage_room_model.add_probe_volume`). An exterior needs none of them;
  * `exposure` is a gain in EV on the beauty before it goes into the atlas. It is explicit and recorded
    per environment, not solved here. Neutral exposure is the workflow baseline; lighting is tuned
    at its source, and Cycles comparisons do not define the intended brightness.

Nothing here changes the source document. Object visibility is put back when the bake is done.

Blender-side: import it from a script run with `blender --python`.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import bpy

import render_profiles
import atlas_allocation
import eevee_projection as projection
import emissive_lights
import light_fixtures
import stage_room_model as stager


@dataclass
class EeveeBake:
    """How to bake one environment with EEVEE."""
    positions: list                       # lane positions the bake cameras stand at
    place_camera: object                  # (scene, lane_y) -> camera
    exposure: float = 0.0                 # EV gain on the beauty before it enters the atlas
    supersample: int = 3
    probe_cells: float = 0.0              # light probe volume cells per metre; 0 = none
    probe_samples: int = 256
    emissive_lights: bool = False
    emissive_exclude: tuple = ()
    fixture_lights: bool = False
    eevee_options: list = field(default_factory=list)       # NAME=VALUE overrides of scene.eevee
    sources: list | None = None           # meshes the beauty frames see; None = every mesh in TH_SOURCE

    def describe(self) -> dict:
        return {"exposureEV": self.exposure, "supersample": self.supersample, "probeCells": self.probe_cells,
                "probeSamples": self.probe_samples, "emissiveLights": self.emissive_lights,
                "fixtureLights": self.fixture_lights, "eeveeOptions": list(self.eevee_options),
                "bakeCameras": [round(float(p), 3) for p in self.positions]}


def add_arguments(parser) -> None:
    """The EEVEE bake's command line, shared by the room and exterior exporters.

    Anything left unset falls back to the environment's record in `environment-sources.json` (its
    `eevee` entry), then to the default. A setting on the command line always wins.
    """
    group = parser.add_argument_group("atlas bake backend")
    group.add_argument("--bake-backend", choices=("cycles", "eevee"), default=render_profiles.DEFAULT_BAKE_BACKEND,
                       help="Cycles selected-to-active is the default; EEVEE projection is an explicit comparison")
    group.add_argument("--render-profile", choices=("draft", "lookdev", "review", "export"), default=render_profiles.DEFAULT_EXPORT_PROFILE)
    group.add_argument("--bake-bindings", type=Path, default=None, help="Authored source/receiver ray preflight JSON")
    group.add_argument("--cycles-device", choices=("AUTO", "CPU", "GPU"), default=render_profiles.DEFAULT_DEVICE)
    group.add_argument("--atlas-denoise", choices=("none", "oidn-fast"), default=None,
                       help="Cycles UV-chart denoising; defaults to the shared profile. none is a raw control")
    group.add_argument("--uv-texel-align", action=argparse.BooleanOptionalAction, default=None,
                       help="Snap valid UV charts to pixel corners; preserve charts that would collapse")
    group.add_argument("--exposure", type=float, default=None, metavar="EV",
                       help="eevee: gain in EV on the beauty before it enters the atlas")
    group.add_argument("--probe-cells", type=float, default=None, metavar="CELLS_PER_M",
                       help="eevee: bake a light probe volume at this density so a sealed room's walls occlude "
                            "the world fill (0 = none)")
    group.add_argument("--probe-samples", type=int, default=None)
    group.add_argument("--emissive-lights", action=argparse.BooleanOptionalAction, default=None,
                       help="eevee: companion area lights on emissive surfaces (emissive_lights.py)")
    group.add_argument("--fixture-lights", action=argparse.BooleanOptionalAction, default=None,
                       help="eevee: let a lamp shine out of a fixture smaller than itself (light_fixtures.py)")
    group.add_argument("--eevee-option", action="append", default=None, metavar="NAME=VALUE",
                       help="eevee: scene.eevee overrides, repeatable")
    group.add_argument("--bake-supersample", type=int, default=None)


def settings_from_args(args, blend_path, positions, place_camera, sources=None) -> EeveeBake | None:
    """The EEVEE bake for this run, or None when the backend is Cycles."""
    if args.bake_backend != "eevee":
        return None
    import environment_sources
    entry = environment_sources.entry_for(Path(blend_path)) or {}
    record = entry.get("eevee", {})

    def pick(flag, key, default):
        value = getattr(args, flag)
        return value if value is not None else record.get(key, default)

    return EeveeBake(
        positions=list(positions), place_camera=place_camera, sources=sources,
        exposure=pick("exposure", "exposureEV", 0.0),
        probe_cells=pick("probe_cells", "probeCells", 0.0),
        probe_samples=pick("probe_samples", "probeSamples", 256),
        emissive_lights=pick("emissive_lights", "emissiveLights", True),
        fixture_lights=pick("fixture_lights", "fixtureLights", True),
        eevee_options=list(pick("eevee_option", "eeveeOptions", [])),
        supersample=pick("bake_supersample", "supersample", 3))


def bake_atlas(settings: EeveeBake, scene, target, source_collection, image, log=print, opacity=None) -> dict:
    """Fill `image` (the exporter's bake target) with the EEVEE projection of the room. Returns a report.

    `target` is the joined render mesh with the UVs the atlas is laid out by; `source_collection`
    holds the meshes that carry the real materials.
    """
    sources = settings.sources
    if sources is None:
        sources = [o for o in source_collection.all_objects if o and o.type == "MESH" and not o.hide_render]
    if not sources:
        raise RuntimeError("the EEVEE bake has no source meshes to photograph")
    lamps = [o for o in source_collection.all_objects if o and o.type == "LIGHT"]
    scene_lights = [o for o in scene.objects if o.type == "LIGHT"]
    if not (lamps or scene_lights):
        raise RuntimeError("nothing lights the scene; an EEVEE bake of it would be black")

    saved = {o: o.hide_render for o in bpy.data.objects if o.type == "MESH"}

    def beauty_pass():
        for obj in saved:
            obj.hide_render = obj not in sources
        target.hide_render = True

    def uv_pass():
        for obj in saved:
            obj.hide_render = obj is not target

    report = {"settings": settings.describe(), "sourceMeshes": len(sources)}
    try:
        scene.render.engine = "BLENDER_EEVEE"
        if settings.eevee_options:
            report["eeveeOptions"] = stager.apply_eevee_options(scene.eevee, settings.eevee_options)
        beauty_pass()
        if settings.fixture_lights:
            report["fixtureLights"] = light_fixtures.release_fixture_lights(scene)
        if settings.emissive_lights:
            report["emissiveLights"] = emissive_lights.add_companion_lights(
                scene, exclude=tuple(settings.emissive_exclude))
        if settings.probe_cells > 0:
            report["probeVolume"] = stager.add_probe_volume(
                scene, settings.probe_cells, settings.probe_samples,
                capture_emission=not settings.emissive_lights)
        projected = projection.project_atlas(
            scene, target.data.uv_layers.active.name, settings.positions, settings.place_camera,
            image.size[0], Path(bpy.app.tempdir), supersample=settings.supersample,
            exposure=settings.exposure, beauty_pass=beauty_pass, uv_pass=uv_pass, log=log, opacity=opacity)
        _, coverage = projection.finish_atlas(projected, atlas_allocation.triangle_mask(target.data, image.size[0]),
                                              image.name, None, image=image)
        report["coverage"] = coverage
        report["cameras"] = projected["cameras"]
    finally:
        for obj, hidden in saved.items():
            obj.hide_render = hidden
        bpy.context.view_layer.material_override = None
    log("[eevee] atlas: " + json.dumps(report["coverage"]))
    return report
