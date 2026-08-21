"""Finalize the selected image-assisted town source without rebuilding projection."""
import bpy
from mathutils import Vector

def collection(name):
    return bpy.data.collections[name]

def anchor(name, position, kind):
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = bpy.data.objects.new(name, None)
        collection("TH_ANCHORS").objects.link(obj)
    obj.location = Vector(position)
    obj.empty_display_type = "ARROWS"
    obj["anchor_id"] = name
    obj["anchor_kind"] = kind

anchor("spawn_player", (-3.4, -0.72, 0.0), "actor")
anchor("walk_start", (-7.8, 0.4, 0.0), "route")
anchor("walk_end", (7.4, 0.4, 0.0), "route")
anchor("doorway", (3.6, 3.0, 0.0), "doorway")
anchor("npc_market_keeper", (1.2, 0.55, 0.0), "actor")
anchor("npc_reliquary_warden", (5.6, 0.55, 0.0), "actor")
scene = bpy.context.scene
scene["sr_environment_id"] = "second_gate_reliquary_market"
scene["sr_selected_direction"] = "B_stacked_reliquary_market"
scene["sr_generated_detail_promoted_to_geometry"] = "roof_canopies,door_recesses,highwalk_cornice"
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
