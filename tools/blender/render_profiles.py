"""Shared render quality; camera, lighting, output encoding and source files belong to callers.

No bpy import: profile selection can be validated without starting Blender.
Supersampling is deliberately explicit and must not filter pixel-art actors.
"""
from dataclasses import asdict, dataclass, replace

DEFAULT_ATLAS_SIZE = 1024
DEFAULT_BAKE_BACKEND = "cycles"
DEFAULT_EXPORT_PROFILE = "export"
DEFAULT_DEVICE = "AUTO"


@dataclass(frozen=True)
class Profile:
    name: str
    engine: str
    samples: int
    supersample: int = 1
    denoise: bool = False
    max_bounces: int = 4
    diffuse_bounces: int = 2
    glossy_bounces: int = 2
    seed: int = 3201

    def record(self):
        return asdict(self)


PROFILES = {
    "draft": Profile("draft", "CYCLES", 16, denoise=True),
    "lookdev": Profile("lookdev", "CYCLES", 32, denoise=True),
    "review": Profile("review", "CYCLES", 128, denoise=True),
    "export": Profile("export", "CYCLES", 128, denoise=True),
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


def apply(scene, profile, *, bake=False, device=None):
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
        scene.cycles.use_adaptive_sampling = False
        scene.cycles.max_bounces = profile.max_bounces
        scene.cycles.diffuse_bounces = profile.diffuse_bounces
        scene.cycles.glossy_bounces = profile.glossy_bounces
        scene.cycles.seed = profile.seed
        scene.cycles.use_denoising = profile.denoise and not bake
        if profile.denoise and not bake:
            scene.cycles.denoiser = "OPENIMAGEDENOISE"
            scene.cycles.denoising_prefilter = "ACCURATE"
            scene.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    record = profile.record()
    record["denoise"] = profile.denoise and not bake
    if profile.engine == "CYCLES" and device is not None:
        record["hardware"] = configure_device(scene, device)
    return record


def configure_device(scene, requested="AUTO"):
    """Select a process-local device; never save Blender preferences."""
    if requested not in {"AUTO", "CPU", "GPU"}:
        raise ValueError("Cycles device must be AUTO, CPU or GPU")
    import bpy
    if requested != "CPU":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
            try:
                prefs.compute_device_type = backend
                prefs.get_devices()
            except (TypeError, ValueError, RuntimeError):
                continue
            devices = [device for device in prefs.devices if device.type == backend]
            if devices:
                for device in prefs.devices:
                    device.use = device.type == backend
                scene.cycles.device = "GPU"
                return {"device": "GPU", "computeBackend": backend,
                        "devices": [device.name for device in devices]}
        if requested == "GPU":
            raise ValueError("GPU requested but no supported Cycles device is available")
    scene.cycles.device = "CPU"
    return {"device": "CPU", "computeBackend": "CPU", "devices": []}
