"""Courtyard context composed during one fresh scaffold build.

Construction is grouped by neighborhood, covered court, ceramic finish and skyline.
There are no source-file mutations, revision prerequisites or intermediate saves.
"""
import math
from pathlib import Path
import sys
import bpy
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/blender'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import second_rite_asset_core as core
import thestra_camera
from first_stratum.common import box, box_geometry
from opening_families import door as door_family, window as window_family
CANDIDATE=ROOT/'projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard'

def _neighborhood():
    scene = bpy.context.scene
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
                          shutters=True, source=True,
                          joinery_material=bpy.data.materials["Court painted casement"],
                          shutter_material=bpy.data.materials["Court shutter panel"])
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
    residential_block("near_cortico_house", -8.3, -5.2, 7.4, 3.0,
                      5.45, 1.55, variants["rose"], -6.7, -3.1, 3.45)
    residential_block("backstreet_west_house", 12.7, -4.8, 11.0, 3.8,
                      7.15, 1.65, variants["warm"], -6.6, -3.5, 4.65)
    residential_block("backstreet_centre_house", 15.2, 7.8, 14.2, 4.1,
                      8.05, 1.85, variants["cream"], 4.8, 8.9, 5.25)
    residential_block("backstreet_east_house", 13.8, 20.8, 12.6, 3.6,
                      6.85, 1.75, variants["rose"], 18.3, 21.4, 4.45)
    for index in range(24):
        y = -1.1 + index*.72
        if any(abs(y-opening) < .86 for opening in (.5, 3.5, 6.8, 11.5)):
            continue
        part(f"passage_azulejo_{index}", (.035, .68, .28),
             (4.325, y, .63), tile if index % 4 in (0, 3) else pale, role="source")
    receiver("passage_azulejo_receiver", 4.34, 9.1, .63, 16.4, .38)
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
    scene["camera_calibration_source"] = "candidate Map 32 traversal.camera -> WorldCameraCalibration"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    bpy.context.view_layer.update()

def _covered_court():
    scene = bpy.context.scene
    source = bpy.data.collections["TH_SOURCE"]
    root = bpy.data.objects["Passage House arrival court"]
    roof = bpy.data.materials["Court terracotta"]
    plaster = bpy.data.materials["Court limewash"]
    wood = bpy.data.materials["Court tropical hardwood"]
    stone = bpy.data.materials["Court threshold stone"]
    for name in ["lodging_pitched_roof", *[f"pantile_ridge_{i}" for i in range(20)]]:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)
    def mesh(name, verts, faces, material):
        data = bpy.data.meshes.new(name + "_mesh")
        data.from_pydata(verts, [], faces)
        data.materials.append(material)
        data.update()
        obj = bpy.data.objects.new(name, data)
        source.objects.link(obj)
        obj.parent = root
        obj["sr_bake_source"] = True
        return obj
    def roof_section(name, y0, y1, eaves=4.05, ridge=5.35):
        x0, xm, x1 = 4.25, 7.0, 9.75
        t = .17
        verts = [(x0,y0,eaves),(x0,y1,eaves),(xm,y0,ridge),(xm,y1,ridge),
                 (x1,y0,eaves),(x1,y1,eaves),(x0,y0,eaves-t),(x0,y1,eaves-t),
                 (xm,y0,ridge-t),(xm,y1,ridge-t),(x1,y0,eaves-t),(x1,y1,eaves-t)]
        faces = [(0,1,3,2),(2,3,5,4),(4,5,11,10),(10,11,9,8),
                 (8,9,7,6),(6,7,1,0),(0,2,8,6),(2,4,10,8),
                 (1,7,9,3),(3,9,11,5)]
        mesh(name, verts, faces, roof)
        # The cut ends are finished gables, not open roof shells.
        for y, suffix in ((y0, "west"), (y1, "east")):
            mesh(f"{name}_{suffix}_gable", [(x0,y,eaves-.03),(xm,y,ridge-.03),(x1,y,eaves-.03)],
                 [(0,1,2)], plaster)
            mesh(f"{name}_{suffix}_gable_return", [(x0,y+.10,eaves-.03),(xm,y+.10,ridge-.03),(x1,y+.10,eaves-.03)],
                 [(2,1,0)], plaster)
    roof_section("lodging_west_roof", -1.95, 7.65)
    roof_section("lodging_east_roof", 15.0, 21.95)
    x0, x1, y0, y1 = 4.05, 8.0, 9.55, 13.45
    z0, z1, thickness = 4.12, 3.45, .16
    verts = [(x0,y0,z0),(x0,y1,z0),(x1,y0,z1),(x1,y1,z1),
             (x0,y0,z0-thickness),(x0,y1,z0-thickness),
             (x1,y0,z1-thickness),(x1,y1,z1-thickness)]
    faces = [(0,1,3,2),(2,3,7,6),(6,7,5,4),(4,5,1,0),
             (0,2,6,4),(1,5,7,3)]
    mesh("lodging_entry_lean_to", verts, faces, roof)
    for y, tag in ((9.20, "west"), (13.80, "east")):
        obj = bpy.data.meshes.new("lodging_entry_post_"+tag+"_mesh")
        v, f = box_geometry((.20,.20,3.18))
        obj.from_pydata(v, [], f)
        obj.materials.append(wood)
        item = bpy.data.objects.new("lodging_entry_post_"+tag, obj)
        source.objects.link(item)
        item.parent = root
        item.location = (7.88,y,1.62)
        item["sr_bake_source"] = True
    for prefix, ya, yb in (("lodging_west", -1.65, 7.35), ("lodging_east", 15.3, 21.65)):
        count = int((yb-ya)/.34)
        for i in range(count):
            y = ya + i*.34
            bpy.ops.mesh.primitive_cube_add(size=1, location=(7.0,y,5.28))
            obj = bpy.context.object
            obj.name = f"{prefix}_ridge_{i:02d}"
            obj.dimensions = (5.52,.11,.08)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            obj.data.materials.append(roof)
            for collection in list(obj.users_collection): collection.objects.unlink(obj)
            source.objects.link(obj)
            obj.parent = root
            obj["sr_bake_role"] = "source"
            obj["sr_bake_source"] = True
    scene["roof_context"] = "two roofed lodging wings, open lightwell, covered entry lean-to"

def _ceramic_finish():
    scene = bpy.context.scene
    source = bpy.data.collections["TH_SOURCE"]
    root = bpy.data.objects["Passage House arrival court"]
    roof = bpy.data.materials["Court terracotta"]
    plaster = bpy.data.materials["Court limewash"]
    pale = bpy.data.materials["Court threshold stone"]
    blue = bpy.data.materials["Court azulejo blue"]
    prefixes = ("lodging_west_roof", "lodging_east_roof",
                "lodging_west_ridge_", "lodging_east_ridge_",
                "passage_azulejo_")
    for obj in list(bpy.data.objects):
        if obj.name == "passage_azulejo_receiver" or obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)
    def mesh(name, verts, faces, material):
        data=bpy.data.meshes.new(name+"_mesh")
        data.from_pydata(verts,[],faces)
        data.materials.append(material)
        data.update()
        obj=bpy.data.objects.new(name,data)
        source.objects.link(obj)
        obj.parent=root
        obj["sr_bake_source"]=True
        return obj
    def roof_section(name,y0,y1):
        x0,xm,x1=4.25,7.0,9.75
        eave,ridge,thick=4.05,5.35,.17
        verts=[(x0,y0,eave),(x0,y1,eave),(xm,y0,ridge),(xm,y1,ridge),
               (x1,y0,eave),(x1,y1,eave),(x0,y0,eave-thick),(x0,y1,eave-thick),
               (xm,y0,ridge-thick),(xm,y1,ridge-thick),(x1,y0,eave-thick),(x1,y1,eave-thick)]
        faces=[(0,1,3,2),(2,3,5,4),(4,5,11,10),(10,11,9,8),(8,9,7,6),
               (6,7,1,0),(0,2,8,6),(2,4,10,8),(1,7,9,3),(3,9,11,5)]
        mesh(name,verts,faces,roof)
        for y,tag,reverse in ((y0,"court",False),(y1,"lodging",True)):
            tri=[(x0,y,eave-.03),(xm,y,ridge-.03),(x1,y,eave-.03)]
            mesh(f"{name}_{tag}_gable",tri,[(2,1,0) if reverse else (0,1,2)],plaster)
    roof_section("lodging_west_roof",-1.95,6.55)
    roof_section("lodging_east_roof",16.25,21.95)
    runs=[(-1.45,-.11),(1.11,2.89),(4.11,6.19),(7.41,10.8),(12.2,21.5)]
    for index,(lo,hi) in enumerate(runs):
        length=hi-lo
        centre=(lo+hi)/2
        obj=bpy.data.meshes.new(f"Passage azulejo dados {index}_mesh")
        verts,faces=box_geometry((.045,length,.42))
        obj.from_pydata(verts,[],faces)
        obj.materials.append(pale)
        obj.update()
        panel=bpy.data.objects.new(f"Passage azulejo dados {index}",obj)
        source.objects.link(panel);panel.parent=root;panel.location=(4.31,centre,.94)
        panel["sr_bake_role"]="source";panel["sr_bake_source"]=True
        # Two restrained blue ceramic bands define the glazed dado.
        for edge,z in (("lower",.78),("upper",1.10)):
            verts,faces=box_geometry((.055,length,.055))
            data=bpy.data.meshes.new(f"Passage azulejo {index} {edge}_mesh")
            data.from_pydata(verts,[],faces);data.materials.append(blue);data.update()
            stripe=bpy.data.objects.new(f"Passage azulejo {index} {edge}",data)
            source.objects.link(stripe);stripe.parent=root;stripe.location=(4.285,centre,z)
            stripe["sr_bake_role"]="source";stripe["sr_bake_source"]=True
        receiver_mesh=bpy.data.meshes.new(f"Passage azulejo receiver {index}_mesh")
        receiver_mesh.from_pydata([(0,-length/2,.26),(0,-length/2,-.26),
                                   (0,length/2,-.26),(0,length/2,.26)],[],[(0,1,2,3)])
        receiver_mesh.update()
        receiver=bpy.data.objects.new(f"Passage azulejo receiver {index}",receiver_mesh)
        source.objects.link(receiver);receiver.parent=root;receiver.location=(4.34,centre,.94)
        receiver["sr_bake_role"]="receiver";receiver["sr_bake_open_surface"]=True
        receiver["sr_bake_source"]=True;receiver.hide_render=True
    scene["roof_context"]="split lodging roof with open lightwell, background houses visible above courtyard wall"

def _backstreet():
    scene = bpy.context.scene
    source = bpy.data.collections["TH_SOURCE"]
    plaster = bpy.data.materials["Cortico chalk limewash"]
    trim = bpy.data.materials["Court threshold stone"]
    wood = bpy.data.materials["Court tropical hardwood"]
    root = bpy.data.objects["Passage House arrival court"]
    def box(name, size, location, material):
        mesh = bpy.data.meshes.new(name + "_mesh")
        verts, faces = box_geometry(size)
        mesh.from_pydata(verts, [], faces)
        mesh.materials.append(material)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        source.objects.link(obj)
        obj.parent = root
        obj.location = location
        obj["sr_bake_source"] = True
        return obj
    front_x, centre_y, width = 12.15, 7.8, 10.8
    bottom, top = 9.55, 12.5
    window_centres = (4.2, 7.8, 11.4)
    spans = [centre_y-width/2, *[c-.62 for c in window_centres],
             *[c+.62 for c in window_centres], centre_y+width/2]
    ordered = sorted(set(spans))
    for i, (lo, hi) in enumerate(zip(ordered, ordered[1:])):
        mid = (lo+hi)/2
        if any(abs(mid-c) < .62 for c in window_centres):
            box(f"skyline_upper_masonry_{i}", (.58, hi-lo, top-bottom),
                (front_x+.29, mid, (bottom+top)/2), plaster)
    for i, cy in enumerate(window_centres):
        box(f"skyline_upper_lintel_{i}", (.74, 1.45, .18),
            (front_x-.04, cy, top-.12), trim)
        box(f"skyline_upper_sill_{i}", (.82, 1.52, .16),
            (front_x-.08, cy, bottom+.28), trim)
        box(f"skyline_upper_louver_{i}", (.10, .94, 1.62),
            (front_x-.015, cy, bottom+1.47), wood)
    box("skyline_upper_floor_band", (.74, width+.32, .24),
        (front_x-.05, centre_y, bottom+.02), trim)
    box("skyline_upper_eave", (.94, width+.70, .22),
        (front_x-.14, centre_y, top+.05), wood)
    box("skyline_upper_roof_cap", (4.1, width+.16, .20),
        (front_x+1.62, centre_y, top+.34), bpy.data.materials["Court terracotta"])
    box("skyline_upper_ridge", (.32, width+.36, .28),
        (front_x+1.62, centre_y, top+.53), bpy.data.materials["Court terracotta"])
    scene["roof_context"] = "split lodging roof and raised backstreet skyline visible through the lightwell"

def _lightwell():
    scene=bpy.context.scene
    source=bpy.data.collections["TH_SOURCE"]
    root=bpy.data.objects["Passage House arrival court"]
    roof=bpy.data.materials["Court terracotta"]
    plaster=bpy.data.materials["Court limewash"]
    for name in ("lodging_west_roof", "lodging_west_roof_court_gable", "lodging_west_roof_lodging_gable"):
        obj=bpy.data.objects.get(name)
        if obj: bpy.data.objects.remove(obj,do_unlink=True)
    x0,xm,x1=4.25,7.0,9.75
    y0,y1=-1.95,1.9
    eave,ridge,thick=4.05,5.35,.17
    verts=[(x0,y0,eave),(x0,y1,eave),(xm,y0,ridge),(xm,y1,ridge),
           (x1,y0,eave),(x1,y1,eave),(x0,y0,eave-thick),(x0,y1,eave-thick),
           (xm,y0,ridge-thick),(xm,y1,ridge-thick),(x1,y0,eave-thick),(x1,y1,eave-thick)]
    faces=[(0,1,3,2),(2,3,5,4),(4,5,11,10),(10,11,9,8),(8,9,7,6),
           (6,7,1,0),(0,2,8,6),(2,4,10,8),(1,7,9,3),(3,9,11,5)]
    mesh=bpy.data.meshes.new("lodging_west_roof_open_sky_mesh")
    mesh.from_pydata(verts,[],faces);mesh.materials.append(roof);mesh.update()
    obj=bpy.data.objects.new("lodging_west_roof",mesh);source.objects.link(obj);obj.parent=root;obj["sr_bake_source"]=True
    for y, tag, face in ((y0,"court",(0,1,2)),(y1,"lodging",(2,1,0))):
        data=bpy.data.meshes.new(f"lodging_west_open_{tag}_gable_mesh")
        data.from_pydata([(x0,y,eave-.03),(xm,y,ridge-.03),(x1,y,eave-.03)],[ ],[face]);data.materials.append(plaster);data.update()
        panel=bpy.data.objects.new(f"lodging_west_roof_{tag}_gable",data);source.objects.link(panel);panel.parent=root;panel["sr_bake_source"]=True
    scene["roof_context"]="open central sky court and raised backstreet skyline; entry lean-to shelters the lodging door"

def compose():
    """Called only by the fresh recipe, before its single source save."""
    _neighborhood()
    _covered_court()
    _ceramic_finish()
    _backstreet()
    _lightwell()
    bpy.context.scene['courtyard_revision']=8
