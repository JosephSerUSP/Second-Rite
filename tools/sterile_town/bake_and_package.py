'''Fix OBJ export in bake_and_package.py
'''
import os
import sys
import json
import bpy
from pathlib import Path
from mathutils import Vector

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "blender"))

def run_bake_pipeline():
    blend_path = REPO_ROOT / "tools" / "sterile_town" / "output" / "lineage_A3_final.blend"
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    scene = bpy.context.scene

    pkg_dir = REPO_ROOT / "tools" / "sterile_town" / "output" / "environment_package"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    src_coll = bpy.data.collections.get("TH_SOURCE")
    rnd_coll = bpy.data.collections.get("TH_RENDER")
    
    src_tris = sum(len(o.data.polygons) for o in src_coll.objects if o.type == 'MESH')
    rnd_tris = sum(len(o.data.polygons) for o in rnd_coll.objects if o.type == 'MESH')

    # Unhide TH_RENDER
    rnd_coll.hide_viewport = False
    rnd_coll.hide_render = False

    # Select all objects in TH_RENDER
    bpy.ops.object.select_all(action='DESELECT')
    rnd_objs = [o for o in rnd_coll.objects if o.type == 'MESH']
    for obj in rnd_objs:
        obj.hide_set(False)
        obj.select_set(True)
    
    bpy.context.view_layer.objects.active = rnd_objs[0]
    
    obj_path = pkg_dir / "environment_render.obj"
    bpy.ops.wm.obj_export(filepath=str(obj_path), export_selected_objects=True)
    print(f"Exported coarse runtime geometry to {obj_path} ({obj_path.stat().st_size} bytes)")

    # Atlas
    atlas_path = pkg_dir / "atlas_beauty.png"
    beauty_render_path = REPO_ROOT / "tools" / "sterile_town" / "output" / "final_winner_A3_center.png"
    import shutil
    shutil.copy(beauty_render_path, atlas_path)
    print(f"Packaged beauty atlas: {atlas_path} ({atlas_path.stat().st_size} bytes)")

    # Manifest
    env_manifest = {
        "contract": "thestra.side-view-environment-package",
        "version": 1,
        "environmentName": "BastionGate_Guildhouse",
        "mesh": "environment_render.obj",
        "atlas": "atlas_beauty.png",
        "geometry": {
            "sourceTriangles": src_tris,
            "runtimeTriangles": rnd_tris,
            "reductionRatio": round(src_tris / max(1, rnd_tris), 2),
            "atlasDimensions": "426x240",
            "runtimeMaterialCount": 1
        },
        "anchors": {
            "spawn_player": {"x": -0.4, "y": 0.0, "z": 0.0},
            "doorway": {"x": 1.0, "y": 1.8, "z": 0.0, "targetScene": "interior_guildhouse"},
            "npc_1": {"x": 1.8, "y": 0.4, "z": 0.0, "dialogueId": "guild_merchant"},
            "npc_2": {"x": 3.8, "y": 1.0, "z": 2.4, "dialogueId": "terrace_guard"},
            "walk_start": {"x": -4.5, "y": 0.0, "z": 0.0},
            "walk_end": {"x": 4.5, "y": 0.0, "z": 0.0}
        },
        "collision": {
            "minX": -4.5,
            "maxX": 4.5,
            "minY": -0.8,
            "maxY": 0.8,
            "groundZ": 0.0
        },
        "cameraBaseline": {
            "pitchDegrees": 0.0,
            "lensMmEquivalent": 43.27,
            "horizontalFovDegrees": 28.07,
            "principalPointY": 110,
            "eye": {"x": 0.0, "y": -18.666667, "z": 2.37}
        }
    }

    manifest_path = pkg_dir / "environment.json"
    manifest_path.write_text(json.dumps(env_manifest, indent=2), encoding='utf-8')
    print(f"Saved environment manifest to {manifest_path}")

if __name__ == "__main__":
    run_bake_pipeline()
