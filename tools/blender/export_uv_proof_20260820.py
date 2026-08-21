"""Export a background-safe UV proof for a baked town environment."""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import bpy


def args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--atlas", required=True)
    return parser.parse_args(raw)


def main():
    a = args()
    output = Path(a.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))

    render = bpy.data.collections.get("TH_RENDER")
    if render is None:
        raise RuntimeError("missing TH_RENDER")
    mesh_objects = [obj for obj in render.objects if obj.type == "MESH"]
    if len(mesh_objects) != 1:
        raise RuntimeError(f"expected one joined render mesh, got {len(mesh_objects)}")
    mesh = mesh_objects[0].data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        raise RuntimeError("TH_RENDER has no active UV layer")

    size = 1024
    polygons = []
    for polygon in mesh.polygons:
        points = []
        for loop_index in polygon.loop_indices:
            uv = uv_layer.data[loop_index].uv
            points.append(f"{uv.x * size:.2f},{(1.0 - uv.y) * size:.2f}")
        if len(points) >= 3:
            polygons.append(" ".join(points))

    atlas_name = html.escape(Path(a.atlas).name, quote=True)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">',
        f'  <image href="{atlas_name}" x="0" y="0" width="{size}" height="{size}" preserveAspectRatio="none"/>',
        '  <g fill="none" stroke="#ffda66" stroke-width="1" stroke-opacity="0.78">',
    ]
    lines.extend(f'    <polygon points="{points}"/>' for points in polygons)
    lines.extend([
        '  </g>',
        f'  <rect x="8" y="8" width="300" height="28" fill="#111b"/>',
        f'  <text x="16" y="28" fill="#fff" font-family="sans-serif" font-size="16">C3 baked atlas UV proof · {len(polygons)} faces</text>',
        '</svg>',
    ])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[uv-proof] wrote {output} ({len(polygons)} faces)")


if __name__ == "__main__":
    main()
