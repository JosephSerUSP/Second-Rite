"""Render runtime proof frames and source-vs-runtime comparisons for the winning environment."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLENDER_SEARCH = [
    os.environ.get("BLENDER"),
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    "blender",
]


def blender_executable():
    for candidate in BLENDER_SEARCH:
        if candidate and (candidate == "blender" or Path(candidate).is_file()):
            return candidate
    raise SystemExit("Blender not found; set BLENDER or install Blender")


def render_runtime_in_blender(blend_path: Path, package_dir: Path, out_dir: Path):
    import bpy
    import second_gate_render

    blend_path = Path(blend_path).resolve()
    package_dir = Path(package_dir).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    second_gate_render.apply(scene, "cycles-candidate")

    # Hide source collection, show render collection
    col_source = bpy.data.collections.get("TH_SOURCE")
    if col_source:
        col_source.hide_render = True

    col_render = bpy.data.collections.get("TH_RENDER")
    if col_render:
        col_render.hide_render = False

    # Assign baked atlas material to TH_RENDER
    atlas_png = package_dir / "environment.png"
    if atlas_png.exists():
        bake_img = bpy.data.images.load(str(atlas_png), check_existing=True)
        mat = bpy.data.materials.get("EnvironmentBakedAtlas") or bpy.data.materials.new("EnvironmentBakedAtlas")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bake_img
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.85
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

        for obj in col_render.objects:
            if obj.type == 'MESH':
                obj.data.materials.clear()
                obj.data.materials.append(mat)

    cam = scene.camera
    target_w = float(scene.render.resolution_x)
    base_shift_x = float(cam.data.shift_x) if hasattr(cam.data, "shift_x") else 0.0

    col_actors = bpy.data.collections.get("TH_PREVIEW_ACTORS")

    # Render without actors
    if col_actors:
        col_actors.hide_render = True

    for label, offset_px in [("m96", -96.0), ("zero", 0.0), ("p96", 96.0)]:
        cam.data.shift_x = base_shift_x - (offset_px / target_w)
        out_path = out_dir / f"runtime_mesh_{label}.png"
        scene.render.filepath = str(out_path)
        bpy.ops.render.render(write_still=True)
        print(f"[runtime] Saved {out_path}")

    # Render with actors
    if col_actors:
        col_actors.hide_render = False

    for label, offset_px in [("m96", -96.0), ("zero", 0.0), ("p96", 96.0)]:
        cam.data.shift_x = base_shift_x - (offset_px / target_w)
        out_path = out_dir / f"runtime_actors_{label}.png"
        scene.render.filepath = str(out_path)
        bpy.ops.render.render(write_still=True)
        print(f"[runtime] Saved {out_path}")

    cam.data.shift_x = base_shift_x
    print("[runtime] All runtime frames rendered.")


def create_strips_and_comparisons(out_dir: Path, source_dir: Path):
    from PIL import Image

    # Mesh strip
    mesh_files = [out_dir / f"runtime_mesh_{l}.png" for l in ("m96", "zero", "p96")]
    if all(f.exists() for f in mesh_files):
        imgs = [Image.open(f) for f in mesh_files]
        w, h = imgs[0].size
        strip = Image.new("RGBA", (w * len(imgs), h))
        for i, img in enumerate(imgs):
            strip.paste(img, (i * w, 0))
        strip.save(out_dir / "runtime_mesh_strip.png")
        print(f"[strip] Saved {out_dir / 'runtime_mesh_strip.png'}")

    # Actors strip
    actor_files = [out_dir / f"runtime_actors_{l}.png" for l in ("m96", "zero", "p96")]
    if all(f.exists() for f in actor_files):
        imgs = [Image.open(f) for f in actor_files]
        w, h = imgs[0].size
        strip = Image.new("RGBA", (w * len(imgs), h))
        for i, img in enumerate(imgs):
            strip.paste(img, (i * w, 0))
        strip.save(out_dir / "runtime_actors_strip.png")
        print(f"[strip] Saved {out_dir / 'runtime_actors_strip.png'}")

    # Source vs Runtime comparison (center frame)
    src_zero = source_dir / "source_zero.png"
    rt_zero = out_dir / "runtime_actors_zero.png"
    if src_zero.exists() and rt_zero.exists():
        img_src = Image.open(src_zero)
        img_rt = Image.open(rt_zero)
        w, h = img_src.size
        comp = Image.new("RGBA", (w * 2, h))
        comp.paste(img_src, (0, 0))
        comp.paste(img_rt, (w, 0))
        comp.save(out_dir / "source_vs_runtime_center.png")
        print(f"[comp] Saved source-vs-runtime comparison to {out_dir / 'source_vs_runtime_center.png'}")


def main():
    blend_path = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "second_gate_cinder_quay" / "second_gate_cinder_quay.blend"
    package_dir = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "second_gate_cinder_quay" / "package"
    out_dir = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "second_gate_cinder_quay" / "renders" / "runtime"
    source_dir = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "second_gate_cinder_quay" / "renders" / "source"

    blender = blender_executable()
    script_path = Path(__file__).resolve()
    temp_runner = tempfile.NamedTemporaryFile(prefix="th_runtime_proof_", suffix=".py", delete=False, mode="w", encoding="utf-8")
    temp_runner.write(
        f"import sys\n"
        f"sys.path.insert(0, {repr(str(script_path.parent))})\n"
        f"from render_runtime_proof import render_runtime_in_blender\n"
        f"from pathlib import Path\n"
        f"render_runtime_in_blender(Path({repr(str(blend_path))}), Path({repr(str(package_dir))}), Path({repr(str(out_dir))}))\n"
    )
    temp_runner.close()

    try:
        cmd = [blender, "--background", "--factory-startup", str(blend_path), "--python", temp_runner.name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.stdout:
            print(res.stdout)
        if res.stderr:
            print(res.stderr, file=sys.stderr)
        if res.returncode != 0:
            raise SystemExit(f"Runtime render failed with code {res.returncode}")
    finally:
        Path(temp_runner.name).unlink(missing_ok=True)

    create_strips_and_comparisons(out_dir, source_dir)


if __name__ == "__main__":
    main()
