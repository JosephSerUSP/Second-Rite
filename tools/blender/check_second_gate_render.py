"""Fast non-Blender self-check for Second Gate render-profile facts."""

from __future__ import annotations

import json
import math
import sys
from types import SimpleNamespace
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import second_gate_render
import thestra_render


def main() -> None:
    profiles = thestra_render.describe_profiles()
    expected = {
        "clay": ("EEVEE", None, 1, False),
        "cycles-draft": ("CYCLES", 4, 1, False),
        "cycles-lookdev": ("CYCLES", 8, 1, False),
        "cycles-candidate": ("CYCLES", 16, 1, False),
        "beauty-selected": ("CYCLES", 16, 2, True),
    }
    assert set(profiles) == set(expected)

    for name, (engine, samples, scale, expensive) in expected.items():
        actual = profiles[name]
        assert actual["engine"] == engine
        assert actual["samples"] == samples
        assert actual["resolutionScale"] == scale
        assert actual["expensive"] is expensive

    fake_scene = SimpleNamespace(
        render=SimpleNamespace(
            resolution_x=0,
            resolution_y=0,
            resolution_percentage=0,
            image_settings=SimpleNamespace(file_format=None, color_mode=None),
            engine=None,
        ),
        cycles=SimpleNamespace(
            samples=0,
            use_denoising=False,
            denoiser=None,
            use_adaptive_sampling=False,
        ),
    )
    applied = thestra_render.apply_profile(
        fake_scene, "cycles-draft", native_width=426, native_height=240
    )
    assert applied["width"] == 426 and applied["height"] == 240
    assert fake_scene.cycles.samples == 4
    try:
        thestra_render.apply_profile(
            fake_scene, "beauty-selected", native_width=426, native_height=240
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expensive profile was applied without explicit opt-in")
    selected = thestra_render.apply_profile(
        fake_scene,
        "beauty-selected",
        native_width=426,
        native_height=240,
        allow_expensive=True,
    )
    assert (selected["width"], selected["height"]) == (852, 480)

    contract = second_gate_render.presentation_contract()
    assert contract["native"] == [426, 240]
    assert contract["baseProjection"] == [256, 144]
    assert contract["walkerFrame"] == [24, 48]
    assert math.isclose(contract["pixelsPerWorldUnit"], 48.0 / 1.75, abs_tol=1e-12)
    assert math.isclose(contract["referenceActorWorldWidth"], 0.875, abs_tol=1e-12)
    assert math.isclose(contract["worldUnitsPerPixel"], 1.75 / 48.0, abs_tol=1e-12)
    assert contract["actorSampling"] == "nearest"
    assert contract["environmentBeautySampling"] == "antialiased"

    second_gate_render.assert_reference_actor_height(48.0)
    try:
        second_gate_render.assert_reference_actor_height(50.0, tolerance_px=1.0)
    except RuntimeError:
        pass
    else:
        raise AssertionError("actor-height negative control did not fail")

    print("SECOND_GATE_RENDER_PROFILES OK")
    print(json.dumps({"profiles": profiles, "presentation": contract}, indent=2))


if __name__ == "__main__":
    main()
