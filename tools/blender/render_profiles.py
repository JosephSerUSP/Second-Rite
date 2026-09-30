"""Shared render quality; camera, lighting, output encoding and source files belong to callers.

No bpy import: profile selection can be validated without starting Blender.
Supersampling is deliberately explicit and must not filter pixel-art actors.
"""
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class Profile:
    name: str
    engine: str
    samples: int
    supersample: int = 1
    denoise: bool = False

    def record(self):
        return asdict(self)


PROFILES = {
    "draft": Profile("draft", "BLENDER_EEVEE", 16),
    "lookdev": Profile("lookdev", "BLENDER_EEVEE", 32),
    "review": Profile("review", "BLENDER_EEVEE", 64),
    "export": Profile("export", "BLENDER_EEVEE", 64),
    "cycles-comparison": Profile("cycles-comparison", "CYCLES", 8, denoise=True),
}
ENGINES = {"eevee": "BLENDER_EEVEE", "cycles": "CYCLES", "workbench": "BLENDER_WORKBENCH"}


def resolve(name="review", *, engine=None, samples=None, supersample=None):
    if name not in PROFILES:
        raise ValueError(f"Unknown render profile: {name}")
    profile = PROFILES[name]
    if engine is not None:
        if engine not in ENGINES:
            raise ValueError(f"Unknown render engine: {engine}")
        profile = replace(profile, engine=ENGINES[engine], denoise=engine == "cycles")
    for key, value in (("samples", samples), ("supersample", supersample)):
        if value is not None:
            if type(value) is not int or value < 1:
                raise ValueError(f"{key} must be a positive integer")
            profile = replace(profile, **{key: value})
    return profile


def apply(scene, profile):
    """Apply quality without changing camera, dimensions, lights or view transform.

    Exposure is neutral by contract. Adapters may subsequently apply an explicit
    authored exposure record; never infer a correction from another renderer.
    """
    scene.render.engine = profile.engine
    scene.render.filter_size = 0.0
    scene.view_settings.exposure = 0.0
    scene.eevee.taa_render_samples = profile.samples
    scene.cycles.filter_width = 0.01
    if profile.engine == "CYCLES":
        scene.cycles.samples = profile.samples
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.use_denoising = profile.denoise
        if profile.denoise:
            scene.cycles.denoiser = "OPENIMAGEDENOISE"
            scene.cycles.denoising_prefilter = "ACCURATE"
            scene.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    return profile.record()
