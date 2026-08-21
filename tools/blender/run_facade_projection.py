"""Host wrapper for the Blender facade-projection authoring spike."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLENDER_SEARCH = (
    os.environ.get("BLENDER"),
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    "blender",
)


def blender_executable() -> str:
    for candidate in BLENDER_SEARCH:
        if candidate and (candidate == "blender" or Path(candidate).is_file()):
            return candidate
    raise SystemExit("Blender not found; set BLENDER or install Blender")


def _runner_source(expression: str) -> str:
    tool_dir = str(Path(__file__).resolve().parent)
    return (
        "import sys\n"
        f"sys.path.insert(0, {tool_dir!r})\n"
        "from pathlib import Path\n"
        "import bpy\n"
        "from facade_projection import (GeneratedFacadeInput, ProjectionSpec, "
        "export_control_packet, project_generated_facade, read_control_packet)\n"
        f"{expression}\n"
    )


def _run(blend: Path, expression: str) -> None:
    blend = blend.resolve()
    if not blend.is_file():
        raise FileNotFoundError(f"source blend not found: {blend}")
    blender = blender_executable()
    runner = tempfile.NamedTemporaryFile(
        prefix="th_facade_projection_",
        suffix=".py",
        delete=False,
        mode="w",
        encoding="utf-8",
    )
    runner.write(_runner_source(expression))
    runner.close()
    try:
        result = subprocess.run(
            [blender, "--background", "--factory-startup", str(blend), "--python", runner.name],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        if result.returncode != 0:
            raise SystemExit(f"Blender facade projection failed with code {result.returncode}")
    finally:
        Path(runner.name).unlink(missing_ok=True)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--blend", required=True, type=Path, help="calibrated source .blend")
    parser.add_argument("--output", required=True, type=Path, help="derived output directory")
    parser.add_argument("--camera", default="", help="camera object name; defaults to scene camera")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    control = subparsers.add_parser("control", help="export calibrated control renders")
    _common(control)
    control.add_argument("--profile", default="clay", help="named render profile")

    project = subparsers.add_parser("project", help="project and bake an external facade image")
    _common(project)
    project.add_argument("--image", required=True, type=Path, help="external generated facade image")
    project.add_argument("--height", type=Path, help="optional external/estimated height image")
    project.add_argument("--control-packet", type=Path, required=True)
    project.add_argument("--target", action="append", required=True, dest="targets")
    project.add_argument(
        "--face-indices",
        help="optional comma-separated polygon indices applied to every target",
    )
    project.add_argument(
        "--allow-outside-camera",
        action="store_true",
        help="allow selected faces to extend beyond the control frame",
    )
    project.add_argument("--height-scale", type=float, default=0.08)
    project.add_argument("--provider", default="external")
    project.add_argument("--model", default="unrecorded")
    project.add_argument("--prompt", default="")
    project.add_argument("--negative-prompt", default="")
    project.add_argument("--seed", type=int)

    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    camera = args.camera
    if args.command == "control":
        expression = (
            f"scene = bpy.context.scene\n"
            f"camera = bpy.data.objects.get({camera!r}) if {bool(camera)!r} else scene.camera\n"
            f"packet = export_control_packet(scene, camera, Path({str(output)!r}), "
            f"profile={args.profile!r})\n"
            "print(packet)"
        )
    else:
        image = args.image.resolve()
        height = args.height.resolve() if args.height else None
        control_packet = args.control_packet.resolve()
        targets = tuple(args.targets)
        face_indices = (
            tuple(int(value) for value in args.face_indices.split(",") if value.strip())
            if args.face_indices
            else None
        )
        face_record = (
            {target: face_indices for target in targets} if face_indices is not None else {}
        )
        expression = (
            f"scene = bpy.context.scene\n"
            f"camera = bpy.data.objects.get({camera!r}) if {bool(camera)!r} else scene.camera\n"
            f"generated = GeneratedFacadeInput(image=Path({str(image)!r}), "
            f"provider={args.provider!r}, model={args.model!r}, prompt={args.prompt!r}, "
            f"negative_prompt={args.negative_prompt!r}, seed={args.seed!r}, "
            f"height_image=Path({str(height)!r}) if {height is not None!r} else None)\n"
            f"spec = ProjectionSpec(target_objects={targets!r}, face_indices={face_record!r}, "
            f"height_scale={args.height_scale!r}, allow_outside_camera={args.allow_outside_camera!r})\n"
            f"manifest = project_generated_facade(scene, camera, generated, spec, "
            f"Path({str(output)!r}), control_packet=read_control_packet(Path({str(control_packet)!r})), "
            f"source_blend_name=Path({str(args.blend.resolve())!r}).name)\n"
            f"bpy.ops.wm.save_as_mainfile(filepath=str(Path({str(output)!r}) / 'projection_inspection.blend'))\n"
            "print(manifest)"
        )
    _run(args.blend, expression)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
