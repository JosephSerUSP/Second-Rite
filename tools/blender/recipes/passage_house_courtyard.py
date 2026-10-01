"""A fresh lodging arrival court, built from the candidate Map's walk profile.

Create once; never overwrite an editable source. No HTTP and no user preferences.
"""
from __future__ import annotations
import argparse
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
import render_profiles
from opening_families import door as door_family, window as window_family
from first_stratum.common import box
from vendor_assets import verify

CANDIDATE = ROOT / "projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard"
OUTPUT = ROOT / "projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend"
LIBRARY = ROOT / "tools/blender/vendor-library"


def mesh(name, vertices, faces, collection, material=None, bake=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    if material:
        data.materials.append(material)
    obj["sr_bake_source"] = bake
    return obj


def profile_surface(name, profile, near_x, far_x, collection, material=None, bake=True, depth_step=None):
    # Exact authored endpoints create planar segments; no second ground-height evaluator.
    count=max(1,math.ceil((far_x-near_x)/depth_step)) if depth_step else 1
    xs=[near_x+(far_x-near_x)*i/count for i in range(count+1)]
    vertices = [(x, point["y"], point["z"]) for point in profile for x in xs]
    faces = [(i*(count+1)+j,i*(count+1)+j+1,(i+1)*(count+1)+j+1,(i+1)*(count+1)+j)
             for i in range(len(profile)-1) for j in range(count)]
    return mesh(name, vertices, faces, collection, material, bake)


def detail_receiver(name, x, y, z, width, height, collection, material):
    obj=mesh(name,[(x,y-width/2,z-height/2),(x,y-width/2,z+height/2),
        (x,y+width/2,z+height/2),(x,y+width/2,z-height/2)],[(0,1,2,3)],collection,material)
    obj["sr_bake_role"]="receiver";obj["sr_bake_open_surface"]=True
    obj.hide_render=True
    return obj


def adapted_material(source, name, color, **inputs):
    material = source.copy()
    material.name = name
    material.asset_clear()
    group = next(node for node in material.node_tree.nodes if node.type == "GROUP")
    group.inputs["Base Color"].default_value = (*color, 1)
    for key, value in inputs.items():
        group.inputs[key].default_value = value
    material["upstream_asset"] = source.name
    material["project_adaptation"] = True
    return material


def weathered(material, low, high, scale):
    tree=material.node_tree
    noise=tree.nodes.new("ShaderNodeTexNoise");noise.inputs["Scale"].default_value=scale
    noise.inputs["Detail"].default_value=2
    coordinates=tree.nodes.new("ShaderNodeTexCoord")
    tree.links.new(coordinates.outputs["Object"],noise.inputs["Vector"])
    ramp=tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color=(*low,1);ramp.color_ramp.elements[1].color=(*high,1)
    tree.links.new(noise.outputs["Fac"],ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"],tree.nodes["Principled BSDF"].inputs["Base Color"])


def build(output):
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite editable source: {output}")
    manifest = verify(LIBRARY)
    map_data = json.loads((CANDIDATE / "32.json").read_text(encoding="utf-8"))
    profile = map_data["traversal"]["lane"]["groundProfile"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    source = core.ensure_collection("TH_SOURCE")
    render = core.ensure_collection("TH_RENDER")
    anchors = core.ensure_collection("TH_ANCHORS")
    collision = core.ensure_collection("TH_COLLISION")
    preview = core.ensure_collection("TH_PREVIEW_ACTORS")
    root = bpy.data.objects.new("Passage House arrival court", None)
    source.objects.link(root)
    with bpy.data.libraries.load(str(LIBRARY / "library/selected_materials.blend"), link=False) as (available, loaded):
        loaded.materials = [record["asset"] for record in manifest["assets"]]
    materials = {material.name: material for material in loaded.materials}
    paving = adapted_material(materials["Bricks - Cobblestone"], "Court warm cobbles", (.30,.28,.23),
        **{"Width":.24,"Height":.18,"Grout Width":.012,"Bump":.24,"Roughness":.94})
    terracotta = adapted_material(materials["Clay"], "Court terracotta", (.40,.13,.065), Bump=.25, Roughness=.90)
    linen = adapted_material(materials["Fabric - Linen"], "Court washed linen", (.68,.62,.49),
        **{"Bump":.10,"Translucency":.15,"Subsurface Weight":0.0})
    plaster = core.make_material("Court limewash",color=(.72,.65,.51),roughness=.97)
    pale = core.make_material("Court threshold stone",color=(.43,.39,.31),roughness=.95)
    wood = core.make_material("Court tropical hardwood",color=(.055,.027,.013),roughness=.85)
    iron = core.make_material("Court wrought iron",color=(.025,.028,.028),roughness=.82,metallic=.3)
    water = core.make_material("Court basin water",color=(.06,.13,.14),roughness=.3)
    tile_blue = core.make_material("Court azulejo blue",color=(.04,.13,.25),roughness=.72)
    weathered(plaster,(.42,.35,.24),(.81,.74,.60),2.4)
    weathered(wood,(.035,.012,.006),(.14,.068,.023),3.5)
    def part(name,size,location,material,**kwargs):
        obj = box(name,root,size,location,material,core,**kwargs)
        core.move_to_collection(obj,source)
        obj["sr_bake_source"] = True
        return obj

    extended = [{"y":-5,"z":profile[0]["z"]},*profile,{"y":17,"z":profile[-1]["z"]}]
    floor = profile_surface("COURT_profile_paving",extended,-14,5.5,source,paving,depth_step=1.0)
    floor["sr_bake_open_surface"]=True
    floor["profile_map"] = "32.json"
    profile_surface("COL_profile_walk",profile,-.75,.75,collision,bake=False)
    # Thick walls and unequal volumes frame a court rather than a symmetric diorama.
    structures = [
        ("passage_roof",(6.0,5.7,.18),(1.4,10.7,3.6),terracotta),
        ("passage_front_beam",(.18,5.9,.24),(-1.5,10.7,3.34),wood),
        ("passage_rear_beam",(.18,5.9,.24),(4.0,10.7,3.34),wood),
        ("near_wall_w",(.5,4.8,.75),(-7.0,-.4,.375),plaster),
        ("near_wall_e",(.5,4.4,.85),(-7.0,14.0,.725),plaster),
        ("drain_channel",(.16,14,.04),(.95,6,.01),iron),
        ("wash_plinth",(1.5,2.0,.45),(3.35,5.2,.32),pale),
        ("wash_back",(.15,2.15,1.45),(4.0,5.2,.94),plaster),
        ("basin_water",(.9,1.45,.04),(3.35,5.2,.58),water),
        ("basin_front",(.15,1.8,.30),(2.8,5.2,.64),pale),
        ("bench_seat",(.65,1.7,.12),(3.1,8.2,.82),wood),
    ]
    for name,size,location,material in structures:
        part(name,size,location,material,bevel=.025,
             rotation=(0,-.06,0) if name=="passage_roof" else (0,0,0))
    # The lodging is one enclosed building shell.  Its rear facade is laid in
    # continuous masonry bays around real openings, with the full volume,
    # return walls, rear wall and pitched roof closing every view through them.
    facade_x, facade_front, facade_back = 4.6, -1.5, 21.5
    wall_thickness, wall_height = .5, 4.2
    door_y, door_width, door_height = 11.5, 1.4, 2.45
    windows = ((.5, 1.22, 1.45, 1.76),
               (3.5, 1.22, 1.45, 1.76),
               (6.8, 1.22, 1.45, 1.76))
    openings = [(door_y, door_width, 0.0, door_height, "door")]
    openings.extend((y, width, sill, height, "window")
                    for y, width, height, sill in windows)
    openings.sort(key=lambda item: item[0])

    def wall_segment(name, y0, y1, z0=0.0, z1=wall_height, material=plaster):
        if y1-y0 < .01 or z1-z0 < .01:
            return
        part(name, (wall_thickness, y1-y0, z1-z0),
             (facade_x, (y0+y1)/2, (z0+z1)/2), material)

    cursor = facade_front
    for index, (center, width, sill, height, kind) in enumerate(openings):
        lo, hi = center-width/2, center+width/2
        wall_segment(f"lodging_facade_bay_{index}", cursor, lo)
        if kind == "window":
            wall_segment(f"lodging_window_{index}_spandrel", lo, hi,
                         0.0, sill)
            wall_segment(f"lodging_window_{index}_lintel", lo, hi,
                         sill+height, wall_height)
        else:
            # A substantial stone head spans the door and bears on both piers.
            wall_segment("lodging_door_head", lo, hi, door_height,
                         wall_height, pale)
        cursor = hi
    wall_segment("lodging_facade_end", cursor, facade_back)
    # Continuous side returns tie both facade ends into the rear room mass.
    # The back return stays within the exporter camera envelope; the longer
    # facade beyond it reads as the lodging's covered gallery wing.
    for y, side in ((facade_front+.20, "west"), (17.8, "east")):
        part(f"lodging_{side}_return",(5.0,.55,wall_height),
             (7.0,y,wall_height/2),plaster)
    part("lodging_rear_wall",(.55,facade_back-facade_front,wall_height),
         (9.4,(facade_front+facade_back)/2,wall_height/2),plaster)
    # A clay gable roof runs along the court, with deep eaves and a real ridge.
    roof_verts=[(4.25,facade_front-.45,4.05),(4.25,facade_back+.45,4.05),
        (7.0,facade_front-.45,5.35),(7.0,facade_back+.45,5.35),
        (9.75,facade_front-.45,4.05),(9.75,facade_back+.45,4.05),
        (4.25,facade_front-.45,3.88),(4.25,facade_back+.45,3.88),
        (7.0,facade_front-.45,5.18),(7.0,facade_back+.45,5.18),
        (9.75,facade_front-.45,3.88),(9.75,facade_back+.45,3.88)]
    mesh("lodging_pitched_roof",roof_verts,
         [(0,1,3,2),(2,3,5,4),(4,5,11,10),(10,11,9,8),(8,9,7,6),(6,7,1,0),
          (0,2,8,6),(2,4,10,8),(1,7,9,3),(3,9,11,5)],source,terracotta)
    host=type("OpeningHost",(),{})()
    host.back_x=4.30
    host.wood=core.make_material("Court lodging door timber",
        color=(.19,.075,.027),roughness=.82)
    host.panel=core.make_material("Court door raised panels",
        color=(.31,.15,.055),roughness=.84)
    host.stone=pale;host.terracotta=terracotta
    host.glass=core.make_material("Court smoked glazing",color=(.018,.027,.035),roughness=.32)
    host.window_glow=host.glass;host.iron=iron
    host.y=lambda value:float(value)
    host.part=lambda name,size,location,material:part(name,size,location,material)
    for index,(y,width,height,sill) in enumerate(windows):
        window_family(host,f"lodging_window_{index+1}",y,width=width,
            height=height,sill_z=sill,x=4.30,shutters=True,source=True)
    door_family(host,"lodging_entry_door",door_y,width=door_width,
        height=door_height,x=4.30,panels=4,panel_material=host.panel,
        source=True)
    # The doorway opens into a short, enclosed vestibule, so the closed leaf is
    # framed by a building and the open aperture can never expose the sky.
    part("vestibule_floor",(3.6,1.6,.12),(6.15,door_y,.12),pale)
    part("vestibule_inner_wall",(.35,2.2,wall_height),(7.8,door_y,2.1),wood)
    part("vestibule_west_return",(3.4,.18,wall_height),(6.1,door_y-.82,2.1),plaster)
    part("vestibule_east_return",(3.4,.18,wall_height),(6.1,door_y+.82,2.1),plaster)
    part("wall_weathered_plinth",(.18,17.4,.30),(4.30,7.2,.18),pale)
    part("passage_eave",(.24,6.05,.12),(-1.68,10.7,3.36),terracotta)
    part("threshold_paving_tongue",(4.4,1.65,.035),(2.0,11.5,.30),paving)
    for y in (8.1,13.1):
        part(f"passage_column_{y}",(.24,.24,3.04),(-1.5,y,1.82),wood)
        part(f"column_foot_{y}",(.42,.42,.32),(-1.5,y,.46),pale)
    for y in (7.5,8.9):
        part(f"bench_leg_{y}",(.12,.12,.5),(3.1,y,.56),wood)
    # A small tile band at the wash area, not an azulejo-covered facade.
    for j in range(10):
        part(f"wash_tile_{j}",(.035,.19,.19),(3.88,4.3+j*.2,1.28),tile_blue if j%2 else pale)
    # Roof ribs are silhouette-bearing; their repetitions use a shared primitive.
    for j in range(20):
        part(f"pantile_ridge_{j}",(6.05,.10,.07),(1.4,8.05+j*.28,3.73),terracotta)
    for y in (8.1,13.1):
        part(f"roof_rafter_{y}",(5.5,.14,.18),(1.2,y,3.18),wood)
    part("linen_wash_towel",(.025,.65,.75),(3.78,6.45,1.05),linen)
    # Low-detail pots carry a rounded silhouette and reuse the acquired clay material.
    for y,radius in ((6.65,.28),(7.05,.19)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=radius,location=(2.5,y,.3+radius))
        pot=bpy.context.object;pot.name=f"Court earthenware {y}"
        pot.scale=(1,1,1.25);core.move_to_collection(pot,source);pot.data.materials.append(terracotta);pot["sr_bake_source"]=True
    for y in (.5,3.5,6.8):
        detail_receiver(f"Window receiver {y}",4.34,y,2.50,1.4,1.75,source,plaster)
    detail_receiver("Lodging door receiver",4.34,11.5,1.95,1.95,2.8,source,plaster)
    for event in map_data["events"]:
        name=next(door["anchor"] for door in map_data["traversal"]["doorways"] if door["eventInstanceId"]==event["instanceId"])
        obj=bpy.data.objects.new(name,None);anchors.objects.link(obj);obj.location=event["worldPosition"]
    spawn=bpy.data.objects.new("spawn_player",None);anchors.objects.link(spawn);spawn.location=(0,1,0)
    world=bpy.data.worlds.new("Court open sky");scene.world=world;world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(.63,.71,.83,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=.35
    bpy.ops.object.light_add(type="SUN",location=(-4,1,8))
    sun=bpy.context.object;sun.name="Court afternoon sky";sun.data.energy=2.0;sun.data.angle=.15
    sun.rotation_euler=(math.radians(28),math.radians(-22),math.radians(-35))
    camera=thestra_camera.create_or_update_camera(thestra_camera.load_calibration(str(ROOT/"tools/blender/fixtures/town_sideview_camera.json")),make_active=True)
    camera.location.y=6
    actor=thestra_camera.create_actor_preview(ROOT/"projects/hichaukitoden-game/assets/character/walker.png",camera,
        anchor=(0,6,0.2),world_height=1.75)
    core.move_to_collection(actor,preview);preview.hide_render=True
    render.hide_render=True;collision.hide_render=True;anchors.hide_render=True
    render_profiles.apply(scene,render_profiles.resolve("draft"));scene.view_settings.view_transform="AgX"
    scene.eevee.use_raytracing=True;scene.eevee.use_fast_gi=True
    scene.eevee.fast_gi_method="AMBIENT_OCCLUSION_ONLY";scene.eevee.fast_gi_distance=1.5
    scene.render.image_settings.file_format="PNG";scene.render.resolution_percentage=100
    scene["candidate_map"]=json.dumps(map_data);scene["source_profile_authority"]="candidate/32.json"
    bpy.ops.file.pack_all()
    output.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    print("COURTYARD SOURCE OK",output)


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,default=OUTPUT)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:]);build(args.output.resolve())
