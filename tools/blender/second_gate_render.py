"""Second Gate presentation defaults layered over generic Blender profiles."""

from __future__ import annotations

from typing import Any, Dict

import thestra_render


NATIVE_WIDTH = 426
NATIVE_HEIGHT = 240
BASE_PROJECTION_WIDTH = 256
BASE_PROJECTION_HEIGHT = 144

WALKER_SHEET_WIDTH = 144
WALKER_SHEET_HEIGHT = 48
WALKER_FRAME_WIDTH = 24
WALKER_FRAME_HEIGHT = 48

REFERENCE_ACTOR_WORLD_HEIGHT = 1.75
REFERENCE_ACTOR_NATIVE_HEIGHT = 48.0

PIXELS_PER_WORLD_UNIT = REFERENCE_ACTOR_NATIVE_HEIGHT / REFERENCE_ACTOR_WORLD_HEIGHT
WORLD_UNITS_PER_PIXEL = 1.0 / PIXELS_PER_WORLD_UNIT
REFERENCE_ACTOR_WORLD_WIDTH = WALKER_FRAME_WIDTH / PIXELS_PER_WORLD_UNIT


def apply(
    scene: Any,
    profile: str = "cycles-lookdev",
    *,
    allow_expensive: bool = False,
) -> Dict[str, Any]:
    return thestra_render.apply_profile(
        scene,
        profile,
        native_width=NATIVE_WIDTH,
        native_height=NATIVE_HEIGHT,
        allow_expensive=allow_expensive,
    )


def presentation_contract() -> Dict[str, Any]:
    return {
        "native": [NATIVE_WIDTH, NATIVE_HEIGHT],
        "baseProjection": [BASE_PROJECTION_WIDTH, BASE_PROJECTION_HEIGHT],
        "walkerSheet": [WALKER_SHEET_WIDTH, WALKER_SHEET_HEIGHT],
        "walkerFrame": [WALKER_FRAME_WIDTH, WALKER_FRAME_HEIGHT],
        "referenceActorWorldHeight": REFERENCE_ACTOR_WORLD_HEIGHT,
        "referenceActorWorldWidth": REFERENCE_ACTOR_WORLD_WIDTH,
        "referenceActorNativeHeight": REFERENCE_ACTOR_NATIVE_HEIGHT,
        "pixelsPerWorldUnit": PIXELS_PER_WORLD_UNIT,
        "worldUnitsPerPixel": WORLD_UNITS_PER_PIXEL,
        "actorSampling": "nearest",
        "actorAlphaBoundary": "hard",
        "environmentBeautySampling": "antialiased",
        "selectedBeautyDownsampleTarget": [NATIVE_WIDTH, NATIVE_HEIGHT],
    }


def assert_reference_actor_height(
    projected_height_px: float,
    tolerance_px: float = 1.0,
) -> None:
    if abs(float(projected_height_px) - REFERENCE_ACTOR_NATIVE_HEIGHT) > float(tolerance_px):
        raise RuntimeError(
            f"reference actor projects to {projected_height_px:.3f}px; expected "
            f"{REFERENCE_ACTOR_NATIVE_HEIGHT:.1f}±{tolerance_px:.1f}px"
        )
