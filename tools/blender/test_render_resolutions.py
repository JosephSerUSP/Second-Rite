"""Script to render and compare multiple supersample resolutions (48x48, 72x72, 96x96, 192x192) in Blender."""

from __future__ import annotations

import math
import sys
from pathlib import Path

try:
    import bpy
    import bmesh
except ImportError:
    bpy = None

ROOT = Path(__file__).resolve().parents[2]
AUTHORING_DIR = ROOT / "assets" / "authoring" / "characters"
EXPERIMENT_DIR = ROOT / "experiments" / "tiny-character-pipeline"
RES_STUDY_DIR = EXPERIMENT_DIR / "renders" / "resolution_study"


def render_all_resolution_variants():
    """Renders raw frames at 48x48, 72x72, 96x96, and 192x192 for all 3 characters."""
    RES_STUDY_DIR.mkdir(parents=True, exist_ok=True)
    
    resolutions = [48, 72, 96, 192]
    characters = ["knight_volumetric", "rogue_faceted", "mage_planar"]

    for char_id in characters:
        blend_p = AUTHORING_DIR / f"{char_id}.blend"
        if not blend_p.is_file():
            print(f"Skipping missing: {blend_p}")
            continue

        bpy.ops.wm.open_mainfile(filepath=str(blend_p))
        scene = bpy.context.scene

        # Ensure EEVEE fast render
        if hasattr(scene.render, "engine"):
            scene.render.engine = "BLENDER_EEVEE"
        if hasattr(scene, "eevee"):
            if hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = 16

        scene.render.film_transparent = True
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"

        # Frame 1 of Idle facing South
        act_name = f"{char_id.split('_')[0].capitalize()}_Idle"
        act = bpy.data.actions.get(act_name)
        if act:
            for obj in bpy.data.objects:
                if obj.animation_data:
                    obj.animation_data.action = act
            scene.frame_set(1)

        root = (
            bpy.data.objects.get(f"{char_id.split('_')[0].capitalize()}_Root")
            or bpy.data.objects.get("Knight_Root")
            or bpy.data.objects.get("Rogue_Root")
            or bpy.data.objects.get("Mage_Root")
        )
        if root:
            root.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()

        for res in resolutions:
            scene.render.resolution_x = res
            scene.render.resolution_y = res
            scene.render.resolution_percentage = 100
            out_p = RES_STUDY_DIR / f"{char_id}_raw_{res}x{res}.png"
            scene.render.filepath = str(out_p)
            bpy.ops.render.render(write_still=True)
            print(f"Saved: {out_p}")


if __name__ == "__main__":
    render_all_resolution_variants()
