"""Shared Blender render-profile helpers.

Project-specific presentation dimensions belong in a thin wrapper such as
``second_gate_render.py``. This module only owns render cost/application.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Union


@dataclass(frozen=True)
class RenderProfile:
    name: str
    engine: str
    resolution_scale: int = 1
    samples: Optional[int] = None
    denoise: bool = False
    adaptive_sampling: bool = False
    expensive: bool = False
    description: str = ""


PROFILES: Mapping[str, RenderProfile] = {
    "clay": RenderProfile(
        "clay", "EEVEE", description="Fast native blockout/composition review."
    ),
    "cycles-draft": RenderProfile(
        "cycles-draft", "CYCLES", samples=4, denoise=True,
        adaptive_sampling=True,
        description="Very cheap Cycles lookdev; denoising is part of the look.",
    ),
    "cycles-lookdev": RenderProfile(
        "cycles-lookdev", "CYCLES", samples=8, denoise=True,
        adaptive_sampling=True,
        description="Default textured/material lookdev.",
    ),
    "cycles-candidate": RenderProfile(
        "cycles-candidate", "CYCLES", samples=16, denoise=True,
        adaptive_sampling=True,
        description="Candidate-quality native render after a scene earns it.",
    ),
    "beauty-selected": RenderProfile(
        "beauty-selected", "CYCLES", resolution_scale=2, samples=16,
        denoise=True, adaptive_sampling=True, expensive=True,
        description="Selected-only 2x beauty source for later downsampling.",
    ),
}


def get_profile(profile: Union[str, RenderProfile]) -> RenderProfile:
    if isinstance(profile, RenderProfile):
        return profile
    try:
        return PROFILES[profile]
    except KeyError as exc:
        choices = ", ".join(sorted(PROFILES))
        raise ValueError(
            f"unknown render profile {profile!r}; expected one of: {choices}"
        ) from exc


def _set_eevee_engine(scene: Any) -> str:
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except TypeError as exc:
            raise RuntimeError("this Blender build exposes no Eevee engine") from exc
    return scene.render.engine


def _apply_cycles(scene: Any, profile: RenderProfile) -> None:
    scene.render.engine = "CYCLES"
    scene.cycles.samples = int(profile.samples or 1)

    if hasattr(scene.cycles, "use_denoising"):
        scene.cycles.use_denoising = bool(profile.denoise)
    if profile.denoise and hasattr(scene.cycles, "denoiser"):
        try:
            scene.cycles.denoiser = "OPENIMAGEDENOISE"
        except (TypeError, ValueError):
            pass
    if hasattr(scene.cycles, "use_adaptive_sampling"):
        scene.cycles.use_adaptive_sampling = bool(profile.adaptive_sampling)


def apply_profile(
    scene: Any,
    profile: Union[str, RenderProfile],
    *,
    native_width: int,
    native_height: int,
    allow_expensive: bool = False,
) -> Dict[str, Any]:
    """Apply one named profile and return the resolved render facts."""

    resolved = get_profile(profile)
    if resolved.expensive and not allow_expensive:
        raise RuntimeError(
            f"render profile {resolved.name!r} is selected-only/expensive; "
            "pass allow_expensive=True after the scene has earned it"
        )
    if native_width <= 0 or native_height <= 0:
        raise ValueError("native dimensions must be positive")

    scene.render.resolution_x = int(native_width * resolved.resolution_scale)
    scene.render.resolution_y = int(native_height * resolved.resolution_scale)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    if hasattr(scene.render.image_settings, "color_mode"):
        scene.render.image_settings.color_mode = "RGBA"

    if resolved.engine == "EEVEE":
        engine = _set_eevee_engine(scene)
    elif resolved.engine == "CYCLES":
        _apply_cycles(scene, resolved)
        engine = scene.render.engine
    else:
        raise ValueError(f"unsupported render engine {resolved.engine!r}")

    return {
        "profile": resolved.name,
        "engine": engine,
        "width": scene.render.resolution_x,
        "height": scene.render.resolution_y,
        "resolutionScale": resolved.resolution_scale,
        "samples": resolved.samples,
        "denoise": resolved.denoise,
        "adaptiveSampling": resolved.adaptive_sampling,
        "expensive": resolved.expensive,
    }


def describe_profiles() -> Dict[str, Dict[str, Any]]:
    """Return JSON-friendly profile facts without importing Blender."""

    return {
        name: {
            "engine": profile.engine,
            "resolutionScale": profile.resolution_scale,
            "samples": profile.samples,
            "denoise": profile.denoise,
            "adaptiveSampling": profile.adaptive_sampling,
            "expensive": profile.expensive,
            "description": profile.description,
        }
        for name, profile in PROFILES.items()
    }
