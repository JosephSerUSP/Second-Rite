"""Native source review and floor/profile verification, without saving the source."""
import argparse
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools/blender"))
import atlas_allocation
import render_profiles
import thestra_camera


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--map",type=Path,required=True);parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--camera",type=Path)
    parser.add_argument("--quality",choices=tuple(render_profiles.PROFILES),default="draft")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    scene=bpy.context.scene;map_data=json.loads(args.map.read_text(encoding="utf-8"))
    camera_path=(args.camera or args.map.with_name("camera.json")).resolve()
    atlas_allocation.CAMERA_RECORD=camera_path
    profile=map_data["traversal"]["lane"]["groundProfile"]
    floor=bpy.data.objects["COURT_profile_paving"]
    samples=[point["y"] for point in profile]+[(a["y"]+b["y"])/2 for a,b in zip(profile,profile[1:])]+[.5,11.5]
    # Ray-test the actual paving against each authored planar segment, including thresholds.
    for y in samples:
        left,right=next((a,b) for a,b in zip(profile,profile[1:]) if a["y"]<=y<=b["y"])
        expected=left["z"]+(right["z"]-left["z"])*(y-left["y"])/(right["y"]-left["y"])
        hit,point,normal,index=floor.ray_cast(Vector((0,y,10)),Vector((0,0,-1)))
        if not hit or abs(point.z-expected)>1e-6: raise ValueError(f"Floor mismatch at {y}: {point.z} != {expected}")
    previews=bpy.data.collections["TH_PREVIEW_ACTORS"];previews.hide_render=False
    actor=next(obj for obj in previews.objects if obj.type=="MESH")
    args.out.mkdir(parents=True,exist_ok=True)
    frames=[]
    for width in (256,426):
        inputs=json.loads((args.map.parent/"scene.json").read_text(encoding="utf-8"))
        for y in inputs["reviewPositions"]:
            hit,point,normal,index=floor.ray_cast(Vector((0,y,10)),Vector((0,0,-1)))
            if not hit: raise ValueError(f"No paving at review position {y}")
            z=point.z
            camera=atlas_allocation.lane_camera(scene,y,mirrored=False,record_path=camera_path,width=width)
            actor.location=(0,y,z)
            render_profiles.apply(scene,render_profiles.resolve(args.quality))
            scene.render.resolution_percentage=100;scene.render.image_settings.file_format="PNG"
            scene.view_settings.view_transform="AgX"
            bpy.context.view_layer.update()
            bpy.context.view_layer.update()
            feet_world=actor.matrix_world @ Vector((0,0,0))
            head_world=actor.matrix_world @ Vector((0,1.75,0))
            feet=thestra_camera.project_world_point(scene,camera,feet_world)
            head=thestra_camera.project_world_point(scene,camera,head_world)
            scene.render.filepath=str((args.out/f"{width}-{y:g}.png").resolve())
            bpy.ops.render.render(write_still=True)
            frames.append({"width":width,"y":y,"z":z,"feet":feet,"head":head,"height":abs(feet[1]-head[1])})
    (args.out/"frames.json").write_text(json.dumps({"floorSamples":samples,"frames":frames,
        "sourceBeautyTriangles":scene.get('source_beauty_triangles'),
        "sourceMeshRoles":json.loads(scene.get('source_mesh_roles','{}'))},indent=2),encoding="utf-8")
    print("COURTYARD REVIEW OK")


if __name__=="__main__":main()
