"""Add a spatially continuous neighborhood around the editable court scaffold."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import second_rite_asset_core as core
import thestra_camera
from first_stratum.common import box
from opening_families import door as door_family, window as window_family

SOURCE = ROOT / "projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend"
CANDIDATE = ROOT / "projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard"


def main():
    if bpy.data.filepath and Path(bpy.data.filepath).resolve() != SOURCE.resolve():
        raise RuntimeError("Open the registered Passage House courtyard scaffold before refining it")
    scene = bpy.context.scene
    if scene.get("courtyard_revision") == 3:
        raise RuntimeError("Courtyard revision 3 is already present")
    source = bpy.data.collections["TH_SOURCE"]
    root = bpy.data.objects.get("Passage House arrival court")
    if root is None:
        raise RuntimeError("Courtyard source root is missing")

    mats = {name: bpy.data.materials[name] for name in (
        "Court limewash", "Court threshold stone", "Court terracotta",
        "Court tropical hardwood", "Court smoked glazing", "Court wrought iron",
        "Court azulejo blue", "Court lodging door timber", "Court door raised panels")}
    tile = bpy.data.materials["Court azulejo blue"]
    pale = bpy.data.materials["Court threshold stone"]
    plaster = bpy.data.materials["Court limewash"]
    roof = bpy.data.materials["Court terracotta"]

    def part(name, size, location, material, role="both", bevel=0.0):
        obj = box(name, root, size, location, material, core, bevel=bevel)
        core.move_to_collection(obj, source)
        obj["sr_bake_source"] = True
        if role != "both":
            obj["sr_bake_role"] = role
        return obj

    def receiver(name, x, y, z, width, height):
        obj = bpy.data.meshes.new(name + "_mesh")
        obj.from_pydata([(x, y-width/2, z-height/2), (x, y-width/2, z+height/2),
                         (x, y+width/2, z+height/2), (x, y+width/2, z-height/2)], [], [(0, 1, 2, 3)])
        obj.update()
        item = bpy.data.objects.new(name, obj)
        source.objects.link(item)
        item["sr_bake_role"] = "receiver"
        item["sr_bake_open_surface"] = True
        item["sr_bake_source"] = True
        item.hide_render = True
        return item

    def roof_prism(name, x_front, x_back, y0, y1, eaves, ridge, material):
        xm = (x_front + x_back) * 0.5
        verts = [(x_front, y0, eaves), (x_front, y1, eaves),
                 (xm, y0, ridge), (xm, y1, ridge),
                 (x_back, y0, eaves), (x_back, y1, eaves),
                 (x_front, y0, eaves-.18), (x_front, y1, eaves-.18),
                 (xm, y0, ridge-.18), (xm, y1, ridge-.18),
                 (x_back, y0, eaves-.18), (x_back, y1, eaves-.18)]
        faces = [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 11, 10),
                 (10, 11, 9, 8), (8, 9, 7, 6), (6, 7, 1, 0),
                 (0, 2, 8, 6), (2, 4, 10, 8), (1, 7, 9, 3), (3, 9, 11, 5)]
        data = bpy.data.meshes.new(name + "_mesh")
        data.from_pydata(verts, [], faces)
        data.materials.append(material)
        data.update()
        item = bpy.data.objects.new(name, data)
        source.objects.link(item)
        item.parent = root
        item["sr_bake_source"] = True
        return item

    def finish_variant(name, low, high):
        result = plaster.copy()
        result.name = name
        for node in result.node_tree.nodes:
            if node.type == "VALTORGB":
                node.color_ramp.elements[0].color = (*low, 1)
                node.color_ramp.elements[1].color = (*high, 1)
        return result

    variants = {
        "warm": finish_variant("Cortico ochre limewash", (.42, .22, .09), (.82, .61, .33)),
        "rose": finish_variant("Cortico faded rose limewash", (.31, .14, .12), (.72, .45, .34)),
        "cream": finish_variant("Cortico chalk limewash", (.42, .37, .27), (.88, .82, .67)),
    }

    class Openings:
        back_x = 0.0
        wood = mats["Court lodging door timber"]
        panel = mats["Court door raised panels"]
        stone = pale
        terracotta = roof
        glass = mats["Court smoked glazing"]
        window_glow = glass
        iron = mats["Court wrought iron"]

        @staticmethod
        def y(value):
            return float(value)

    host = Openings()
    host.part = lambda name, size, location, material: part(name, size, location, material, role="source")

    def residential_block(name, front_x, center_y, width, depth, eaves, rise, material,
                          window_y, door_y, upper_sill):
        y0, y1 = center_y-width/2, center_y+width/2
        wall_thickness = .52
        openings = [(door_y-.62, door_y+.62, 0.0, 2.35, "door")]
        lower_windows = [(window_y-.48, window_y+.48, 1.65, 2.9, "window"),
                         (center_y+width*.31-.48, center_y+width*.31+.48, 1.65, 2.9, "window")]
        upper_windows = [(center_y-width*.28-.46, center_y-width*.28+.46, upper_sill, upper_sill+1.25, "window"),
                         (center_y+width*.20-.46, center_y+width*.20+.46, upper_sill, upper_sill+1.25, "window")]
        openings.extend(lower_windows)
        openings.extend(upper_windows)
        y_edges = sorted({y0, y1, *(edge for opening in openings for edge in opening[:2])})
        z_edges = sorted({0.0, eaves, *(edge for opening in openings for edge in opening[2:4])})
        for yi, (a, b) in enumerate(zip(y_edges, y_edges[1:])):
            for zi, (low, high) in enumerate(zip(z_edges, z_edges[1:])):
                cy, cz = (a+b)/2, (low+high)/2
                if any(oa < cy < ob and oz0 < cz < oz1 for oa, ob, oz0, oz1, _ in openings):
                    continue
                if high-low < .02 or b-a < .02:
                    continue
                part(f"{name}_masonry_{yi}_{zi}", (wall_thickness, b-a, high-low),
                     (front_x+wall_thickness/2, cy, cz), material, bevel=.012)
        # Side returns and an enclosed rear face give the openings believable depth.
        part(f"{name}_return_w", (depth, wall_thickness, eaves),
             (front_x+depth/2, y0+wall_thickness/2, eaves/2), material)
        part(f"{name}_return_e", (depth, wall_thickness, eaves),
             (front_x+depth/2, y1-wall_thickness/2, eaves/2), material)
        part(f"{name}_rear_mass", (wall_thickness, width, eaves),
             (front_x+depth-wall_thickness/2, center_y, eaves/2), material)
        part(f"{name}_foundation", (depth+.18, width+.16, .32),
             (front_x+depth/2, center_y, .16), pale)
        roof_prism(f"{name}_pantile_roof", front_x-.32, front_x+depth+.36,
                   y0-.38, y1+.38, eaves+.06, eaves+rise, roof)
        # Shared adjustable opening families; shallow joinery is baked onto cards.
        door_family(host, f"{name}_door", door_y, x=front_x, width=1.24,
                    height=2.35, panels=4, panel_material=host.panel, source=True)
        for index, (cy, sill, top, opening_width) in enumerate(
                [(window_y, 1.65, 2.9, .96),
                 (center_y+width*.31, 1.65, 2.9, .96),
                 (center_y-width*.28, upper_sill, upper_sill+1.25, .92),
                 (center_y+width*.20, upper_sill, upper_sill+1.25, .92)]):
            window_family(host, f"{name}_window_{index+1}", cy, x=front_x,
                          width=opening_width, height=top-sill, sill_z=sill,
                          shutters=True, source=True)
            receiver(f"{name}_window_receiver_{index+1}", front_x-.005,
                     cy, sill+(top-sill)/2, opening_width+1.05, top-sill+.62)
        receiver(f"{name}_door_receiver", front_x-.005, door_y, 1.33, 1.72, 2.75)
        # A restrained cornice and two chimney stacks break the continuous roofline.
        part(f"{name}_eave_beam", (.32, width+.42, .18),
             (front_x-.08, center_y, eaves-.10), mats["Court tropical hardwood"])
        for side, tag in ((-.34, "a"), (.36, "b")):
            chimney_y = center_y+width*side
            part(f"{name}_chimney_{tag}", (.68, .62, 1.18),
                 (front_x+depth*.70, chimney_y, eaves+rise+.50), material)
            part(f"{name}_chimney_cap_{tag}", (.82, .74, .16),
                 (front_x+depth*.70, chimney_y, eaves+rise+1.17), pale)

    # Replace two detached starter blocks with walls that actually bound the court.
    for name in ("near_wall_w", "near_wall_e"):
        obj = bpy.data.objects.get(name)
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)
    for side, y in (("cortico", -1.95), ("lodging", 13.95)):
        part(f"{side}_court_edge", (11.0, .34, .94), (-1.20, y, .47), plaster, bevel=.025)
        part(f"{side}_coping", (11.22, .52, .16), (-1.20, y, 1.02), pale, bevel=.025)
        for x, tag in ((-6.7, "near"), (4.15, "house")):
            part(f"{side}_wall_pier_{tag}", (.52, .58, 1.52),
                 (x, y, .76), pale, bevel=.035)
            part(f"{side}_pier_cap_{tag}", (.68, .72, .16),
                 (x, y, 1.60), roof, bevel=.025)

    # A close, partial dwelling continues the Cortico flank outside the walking line.
    residential_block("near_cortico_house", -8.3, -5.2, 7.4, 3.0,
                      5.45, 1.55, variants["rose"], -6.7, -3.1, 3.45)

    # Attached, irregular two-storey houses rise behind the Passage House roof.
    residential_block("backstreet_west_house", 12.7, -4.8, 11.0, 3.8,
                      7.15, 1.65, variants["warm"], -6.6, -3.5, 4.65)
    residential_block("backstreet_centre_house", 15.2, 7.8, 14.2, 4.1,
                      8.05, 1.85, variants["cream"], 4.8, 8.9, 5.25)
    residential_block("backstreet_east_house", 13.8, 20.8, 12.6, 3.6,
                      6.85, 1.75, variants["rose"], 18.3, 21.4, 4.45)

    # A tiled band runs only across the inhabited Passage House wall below its openings.
    # It is shallow source relief and bakes to one receiver rather than exporting tile blocks.
    for index in range(24):
        y = -1.1 + index*.72
        if any(abs(y-opening) < .86 for opening in (.5, 3.5, 6.8, 11.5)):
            continue
        part(f"passage_azulejo_{index}", (.035, .68, .28),
             (4.325, y, .63), tile if index % 4 in (0, 3) else pale, role="source")
    receiver("passage_azulejo_receiver", 4.34, 9.1, .63, 16.4, .38)

    # Replace the small hard key with the shared exterior light balance: broad sky,
    # weak direction, and no sharp diorama shadows.
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT" and obj.name == "Court afternoon sky":
            bpy.data.objects.remove(obj, do_unlink=True)
    dome_data = bpy.data.lights.new("Court soft sky", type="AREA")
    dome_data.energy = 504.0
    dome_data.shape = "RECTANGLE"
    dome_data.size = 24.0
    dome_data.size_y = 28.0
    dome_data.color = (.55, .68, .86)
    dome = bpy.data.objects.new("Court soft sky", dome_data)
    scene.collection.objects.link(dome)
    dome.location = (0.0, 6.0, 16.0)
    sun_data = bpy.data.lights.new("Court weak sun", type="SUN")
    sun_data.energy = 1.5
    sun_data.angle = math.radians(6.0)
    sun_data.color = (1.0, .95, .86)
    sun = bpy.data.objects.new("Court weak sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(52.0), 0.0, math.radians(-34.0))

    record = thestra_camera.load_calibration(str(CANDIDATE / "camera.json"))
    camera = thestra_camera.create_or_update_camera(record, scene=scene, make_active=True)
    previews = bpy.data.collections["TH_PREVIEW_ACTORS"]
    previews.hide_render = False
    actor = next((item for item in previews.objects if item.type == "MESH"), None)
    if actor is not None:
        bpy.data.objects.remove(actor, do_unlink=True)
    actor = thestra_camera.create_actor_preview(
        ROOT / "projects/hichaukitoden-game/assets/character/walker.png", camera,
        anchor=(0, 6, .2), world_height=1.75)
    for collection in list(actor.users_collection):
        collection.objects.unlink(actor)
    previews.objects.link(actor)
    actor.hide_render = False
    previews.hide_render = True
    scene["courtyard_revision"] = 3
    scene["camera_calibration_source"] = "candidate Map 32 traversal.camera -> WorldCameraCalibration"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    print("PASSAGE COURTYARD SPATIAL REVISION OK", SOURCE)


if __name__ == "__main__":
    main()
