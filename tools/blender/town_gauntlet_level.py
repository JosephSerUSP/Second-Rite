"""Level-camera Second Gate town authoring set.

This is intentionally separate from #856's historical builder.  It places the
playable set inside PR #859's very narrow 28 degree level-camera frustum rather
than trying to rescue the old pitched-camera blockout with camera movement.
"""
from __future__ import annotations
import argparse, os, sys, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "hichaukitoden-game"
sys.path.insert(0, str(ROOT / "tools" / "blender"))

def calibration():
    import json
    p = os.environ.get("THESTRA_TOWN_CAMERA_CALIBRATION")
    if not p: raise RuntimeError("THESTRA_TOWN_CAMERA_CALIBRATION is required")
    return json.loads(Path(p).read_text(encoding="utf-8"))

def build(attempt: str, save: Path | None = None, offset_x: float = 0.0, preview_actors: bool = True, anchors_json: Path | None = None, engine: str = 'EEVEE'):
    import bpy
    import thestra_camera
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    # Iteration frames are environment-only and native 426x240.  EEVEE is
    # intentionally the default: it is fast, stable and sufficiently masked
    # by the final low-resolution presentation.  Cycles is reserved for bake.
    scene.render.engine = 'CYCLES' if engine == 'CYCLES' else 'BLENDER_EEVEE'
    if engine == 'CYCLES':
        scene.cycles.samples = 8
        scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 426, 240
    scene.render.resolution_percentage = 100
    # The target is a 426x240 game frame: a restrained filmic transform keeps
    # masonry readable instead of crushing the narrow street into orange/black
    # stage lighting.
    scene.view_settings.look = 'AgX - Medium Low Contrast'
    scene.world = bpy.data.worlds.new('TownWorld')
    scene.world.color = (0.015, 0.02, 0.04)
    root = scene.collection
    cols = {n:bpy.data.collections.new(n) for n in ('TH_SOURCE','TH_RENDER','TH_COLLISION','TH_ANCHORS','TH_PREVIEW_ACTORS','TH_PREVIEW_ONLY','TH_CAMERA_PREVIEW')}
    for c in cols.values(): root.children.link(c)
    cols['TH_RENDER'].hide_render = cols['TH_COLLISION'].hide_render = cols['TH_PREVIEW_ONLY'].hide_render = True
    def link(o, c='TH_SOURCE'):
        cols[c].objects.link(o)
        for cc in list(o.users_collection):
            if cc != cols[c]: cc.objects.unlink(o)
        return o
    # A 24x48 runtime cell is our human-scale authority.  The old preview
    # billboard made the façade set read four times too tall, so compress the
    # authored vertical vocabulary around the walk plane rather than altering
    # the calibrated camera or scaling a sprite after the fact.
    ground_plane, vertical_scale = -1.5, 0.62
    def height_metric(p, height):
        return (p[0], p[1], ground_plane + (p[2] - ground_plane) * vertical_scale), height * vertical_scale
    def box(n, p, s, m, c='TH_SOURCE'):
        p, sz = height_metric(p, s[2]); bpy.ops.mesh.primitive_cube_add(location=p); o=bpy.context.object; o.name=n; o.scale=(s[0]/2,s[1]/2,sz/2); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(m); return link(o,c)
    def cyl(n,p,r,d,m,c='TH_SOURCE'):
        p, depth = height_metric(p,d); bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=r,depth=depth,location=p); o=bpy.context.object;o.name=n;o.data.materials.append(m);return link(o,c)
    def mat(n, color, rough=.75, metal=0):
        m=bpy.data.materials.new(n);m.use_nodes=True; bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
        tex=m.node_tree.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=7;tex.inputs['Detail'].default_value=4
        bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.06
        m.node_tree.links.new(tex.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal']);return m
    stone=mat('Procedural warm limestone',(0.31,.25,.19)); plaster=mat('Procedural aged plaster',(.43,.29,.20)); timber=mat('Procedural dark oak',(.07,.028,.012)); roof=mat('Procedural ceramic roof',(.20,.028,.018)); iron=mat('Procedural oxidized iron',(.035,.045,.052),.42,.72); glow=mat('Warm window emission',(1,.31,.07),.35)
    glow.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value=(1,.08,.01,1); glow.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=3.5
    # Keep the authored procedural noise as a secondary breakup, but make the
    # generated limestone source a real material contributor rather than a
    # provenance-only experiment. Its separate height and roughness maps feed
    # Blender's own bump/roughness path (never a generated normal map).
    generated_root=PROJECT/'assets'/'authoring'/'town'/'material-sources'
    generated_albedo=generated_root/'generated-limestone-albedo.png'
    generated_height=generated_root/'generated-limestone-height.png'
    generated_rough=generated_root/'generated-limestone-roughness.png'
    if generated_albedo.exists() and generated_height.exists() and generated_rough.exists():
        n=stone.node_tree.nodes; l=stone.node_tree.links; bs=n['Principled BSDF']
        coord=n.new('ShaderNodeTexCoord')
        albedo_node=n.new('ShaderNodeTexImage'); albedo_node.name='OpenAI Limestone Albedo'; albedo_node.image=bpy.data.images.load(str(generated_albedo)); albedo_node.extension='REPEAT'; albedo_node.projection='BOX'; albedo_node.projection_blend=.18
        height_node=n.new('ShaderNodeTexImage'); height_node.name='OpenAI Limestone Height'; height_node.image=bpy.data.images.load(str(generated_height)); height_node.image.colorspace_settings.name='Non-Color'; height_node.extension='REPEAT'; height_node.projection='BOX'; height_node.projection_blend=.18
        rough_node=n.new('ShaderNodeTexImage'); rough_node.name='OpenAI Limestone Roughness'; rough_node.image=bpy.data.images.load(str(generated_rough)); rough_node.image.colorspace_settings.name='Non-Color'; rough_node.extension='REPEAT'; rough_node.projection='BOX'; rough_node.projection_blend=.18
        generated_bump=n.new('ShaderNodeBump'); generated_bump.inputs['Strength'].default_value=.13; generated_bump.inputs['Distance'].default_value=.045
        for tex in (albedo_node,height_node,rough_node): l.new(coord.outputs['Generated'],tex.inputs['Vector'])
        l.new(albedo_node.outputs['Color'],bs.inputs['Base Color']); l.new(rough_node.outputs['Color'],bs.inputs['Roughness']); l.new(height_node.outputs['Color'],generated_bump.inputs['Height']); l.new(generated_bump.outputs['Normal'],bs.inputs['Normal'])
    cobble=mat('PolyHaven Cobblestone 01 CC0',(.22,.16,.11)); source=PROJECT/'assets'/'authoring'/'town'/'material-sources'/'polyhaven-cobblestone-01'/'cobblestone_01_diff_1k.jpg'
    if source.exists():
        img=bpy.data.images.load(str(source)); node=cobble.node_tree.nodes.new('ShaderNodeTexImage');node.image=img;node.extension='REPEAT';node.interpolation='Linear';coord=cobble.node_tree.nodes.new('ShaderNodeTexCoord');cobble.node_tree.links.new(coord.outputs['Generated'],node.inputs['Vector']);cobble.node_tree.links.new(node.outputs['Color'],cobble.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    # fixed-eye level scene: y is horizontal screen travel, x is depth.
    floor=box('SRC_cobble_street',(5.7,5.5,-1.58),(5.8,9.0,.18),cobble)
    box('SRC_backing',(10.0,5.5,1.3),(.35,8.4,5.8),stone)
    # distinct facade rhythm in the narrow frustum.
    palette={'01':(plaster,roof),'02':(stone,roof),'03':(plaster,roof),'04':(stone,iron),'05':(plaster,timber),'06':(stone,roof),'07':(plaster,roof),'08':(stone,timber),'09':(plaster,roof)}
    face, top = palette[attempt]
    for i,y in enumerate((3.3,4.8,6.3,7.8)):
        h=(3.1,4.1,3.6,4.5)[(i+int(attempt))%4]
        box(f'SRC_facade_{i}',(8.7,y,-1.5+h/2),(1.25,1.34,h),face)
        box(f'SRC_roof_{i}',(8.35,y,-1.5+h+.22),(1.9,1.55,.42),top)
        # recessed, layered window and sill
        if i != 1 or attempt in ('03','05','07','09'):
            box(f'SRC_window_frame_{i}',(8.03,y,-.15),( .12,.62,.92),timber)
            box(f'SRC_window_glow_{i}',(7.95,y,-.15),(.08,.46,.68),glow)
            box(f'SRC_sill_{i}',(7.87,y,-.63),(.28,.78,.13),stone)
    # unmistakable doorway and architectural depth.
    door_y=5.5 if attempt not in ('02','04','06') else 4.8
    box('SRC_door_recess',(7.98,door_y,-.35),(.22,.88,1.95),timber)
    box('SRC_door_warmth',(7.85,door_y,-.35),(.08,.64,1.65),glow)
    for y in (door_y-.62,door_y+.62): cyl('SRC_door_column',(7.68,y,-.38),.13,2.2,stone)
    # Divergence vocabulary: each early attempt tests a distinct theatrical
    # frontage under the same locked camera, rather than cosmetic recolors.
    if attempt == '03':
        box('SRC_market_awning',(5.9,6.95,.82),(1.5,2.1,.18),roof)
        for y in (6.05,7.85): cyl('SRC_awning_pole',(5.9,y,-.15),.07,2.0,timber)
    elif attempt == '04':
        box('SRC_wharf_rail',(5.15,3.55,-.45),(1.3,.16,1.45),iron)
        for y in (3.0,3.55,4.1): cyl('SRC_wharf_post',(5.15,y,-.45),.09,1.45,iron)
    elif attempt == '05':
        box('SRC_tavern_sign_arm',(6.55,3.75,1.12),(1.4,.10,.10),iron)
        box('SRC_tavern_sign',(6.55,3.25,.73),(.12,.72,.72),roof)
    elif attempt == '06':
        for y in (4.55,6.45): cyl('SRC_gate_pillar',(6.7,y,-.1),.38,3.0,stone)
        box('SRC_gate_lintel',(6.7,5.5,1.25),(.65,2.7,.35),stone)
    elif attempt == '07':
        for y in (3.65,7.35):
            cyl('SRC_planter',(5.4,y,-1.05),.32,.55,stone)
            cyl('SRC_tree',(5.4,y,-.35),.12,1.0,timber)
        box('SRC_tavern_porche',(6.65,5.55,-.92),(1.1,2.45,.38),timber)
        box('SRC_tavern_beam',(6.5,5.55,1.35),(.28,2.75,.22),timber)
        box('SRC_tavern_sign',(6.1,7.0,.78),(.12,.72,.78),roof)
        for y in (4.45,6.65): cyl('SRC_tavern_lantern',(6.25,y,.2),.12,2.2,iron)
    elif attempt == '08':
        box('SRC_balcony',(7.15,6.75,.55),(1.1,1.7,.18),timber)
        for y in (6.05,6.55,7.05,7.45): cyl('SRC_balcony_rail',(6.62,y,.88),.045,.72,iron)
        # Convergence response to blind evaluation: give the facade a named,
        # readable civic function and a deep arch silhouette, not another box.
        box('SRC_apothecary_gable',(8.15,5.45,2.25),(1.7,2.7,.55),roof)
        bpy.ops.mesh.primitive_torus_add(major_radius=.62,minor_radius=.12,major_segments=20,minor_segments=8,location=(7.72,5.48,-.12),rotation=(0,1.5708,0))
        arch=bpy.context.object;arch.name='SRC_apothecary_stone_arch';arch.data.materials.append(stone)
        box('SRC_apothecary_counter',(6.95,5.48,-.95),(.7,1.05,.75),timber)
        for y in (4.55,6.42):
            box('SRC_apothecary_display',(7.62,y,.55),(.25,.48,1.05),glow)
        # Different frame indices give the two stand-ins distinct poses while
        # retaining the owner-provided walker sheet.
    elif attempt == '09':
        box('SRC_hybrid_canopy',(6.35,7.45,.92),(1.3,1.85,.16),roof)
        box('SRC_hybrid_sign',(6.35,3.45,.65),(.16,.65,.65),iron)
        for y in (3.05,7.85): cyl('SRC_hybrid_lantern',(5.25,y,.25),.12,2.5,iron)
        box('SRC_gatehouse_mass',(8.18,5.45,2.42),(1.55,3.35,.55),stone)
        for y in (4.0,6.9): cyl('SRC_gatehouse_tower',(7.45,y,.45),.48,3.9,stone)
        box('SRC_gate_portcullis',(7.6,5.45,.1),(.15,1.65,2.7),iron)
        for y in (4.75,5.2,5.7,6.15): box('SRC_gate_bar',(7.48,y,.1),(.18,.06,2.3),iron)
        # Native-scale evaluation chose Old Gate + Wharf.  Final 09 combines
        # their readable transition silhouette with a lateral water channel
        # and timber bridge, preserving a clear centre walking route.
        water=mat('Final canal water',(.015,.07,.12),.18,.18)
        box('SRC_final_canal',(4.8,3.55,-1.42),(1.4,2.6,.14),water)
        box('SRC_final_bridge',(5.0,3.55,-.95),(1.0,1.05,.24),timber)
        for y in (2.55,4.55): cyl('SRC_final_mooring',(4.9,y,-.5),.1,1.6,iron)
    # Large-format divergence masses.  These deliberately change the usable
    # spatial program within the fixed frustum (not merely its palette).
    if attempt == '01':
        # A gateway is a destination, not a fence.  The previous study put
        # horizontal stone courses directly across its opening, which made it
        # read as a modern barricade at native resolution.  This arrangement
        # deliberately leaves a tall, dark recess framed by a legible arch.
        gate_dark=mat('Old gate shadow',(0.025,.018,.015),.9)
        for y in (3.95,7.05):
            cyl('SRC_old_gate_tower',(7.55,y,.22),.60,4.15,stone)
            box('SRC_old_gate_tower_cap',(7.55,y,1.52),(.95,1.15,.25),roof)
            box('SRC_old_gate_banner',(6.88,y,.48),(.10,.42,1.05),roof)
            cyl('SRC_old_gate_lantern',(5.95,y,-.18),.10,1.65,iron)
        # Interior void and timber doors sit behind the stone rim.
        box('SRC_old_gate_recess',(7.43,5.5,-.24),(.22,1.80,2.60),gate_dark)
        box('SRC_old_gate_door_left',(7.27,5.10,-.62),(.10,.72,1.70),timber)
        box('SRC_old_gate_door_right',(7.27,5.90,-.62),(.10,.72,1.70),timber)
        # Individual voussoirs make a *top* arch.  A complete torus was a
        # tempting shortcut here, but at 1:1 it reads as a sci-fi ring rather
        # than masonry because it incorrectly continues below the threshold.
        for i in range(9):
            theta = math.pi * i / 8.0
            y = 5.5 + math.cos(theta) * .84
            z = .03 + math.sin(theta) * .84
            v = box(f'SRC_old_gate_voussoir_{i}',(7.10,y,z),(.18,.27,.22),stone)
            v.rotation_euler.x = theta - math.pi / 2.0
        for y in (4.66,6.34):
            box('SRC_old_gate_jamb',(7.10,y,-.68),(.18,.27,1.45),stone)
        box('SRC_old_gate_lintel',(7.30,5.5,1.30),(.42,2.25,.42),stone)
        # A small civic crest and lamps give the approach a story cue without
        # occupying the actor lane.
        cyl('SRC_old_gate_crest',(6.98,5.5,.80),.24,.12,roof)
        for y in (4.68,6.32):
            box('SRC_old_gate_keystone',(6.94,y,.55),(.12,.22,.34),stone)
    elif attempt == '02':
        cyl('SRC_plaza_fountain_basin',(5.9,5.5,-1.1),.85,.42,stone)
        cyl('SRC_plaza_fountain_spire',(5.9,5.5,-.45),.18,1.25,iron)
        box('SRC_plaza_low_wall',(7.4,5.5,-.72),(.42,5.7,.65),stone)
    elif attempt == '03':
        box('SRC_market_long_counter',(5.7,5.5,-.85),(1.25,5.9,.8),timber)
        for y in (3.65,5.5,7.35): cyl('SRC_market_canopy_post',(5.1,y,.0),.08,2.7,timber)
    elif attempt == '04':
        water=mat('Wharf water',(.02,.09,.16),.2,.15)
        # Wharf is composed as a canal-side arrival, not a recoloured street:
        # water owns the foreground, a timber quay breaks it into depth bands,
        # and a moored boat creates an unmistakable lateral destination.
        # Keep the canal to one side of the street. A full-width foreground
        # water plane flattened the perspective and swallowed the walkers.
        box('SRC_wharf_water',(4.65,7.25,-1.42),(2.45,2.75,.13),water)
        box('SRC_wharf_quay',(5.85,6.02,-1.03),(.58,.42,.26),timber)
        box('SRC_wharf_bridge',(5.05,6.70,-.77),(1.05,1.10,.25),timber)
        for y in (6.18,6.78,7.52,8.28):
            cyl('SRC_wharf_piling',(5.15,y,-.58),.12,1.75,iron)
        # A small hull lives off the player lane, allowing the water to read
        # as a harbour rather than a mirrored floor.
        box('SRC_wharf_boat_hull',(4.20,7.45,-1.02),(1.05,1.42,.42),timber)
        box('SRC_wharf_boat_gunwale',(4.08,7.45,-.72),(1.18,1.57,.12),roof)
        cyl('SRC_wharf_boat_mast',(4.22,7.45,.05),.07,2.35,timber)
        canvas=mat('Wharf sail',(.63,.54,.39),.92)
        box('SRC_wharf_sail',(4.35,7.75,.55),(.08,1.28,1.15),canvas)
        box('SRC_wharf_crane_post',(6.42,3.35,.05),(.18,.20,3.1),timber)
        box('SRC_wharf_crane_arm',(6.12,3.75,1.15),(.88,.14,.15),timber)
        cyl('SRC_wharf_crane_lantern',(5.70,3.75,.25),.10,1.55,iron)
    elif attempt == '05':
        box('SRC_tavern_front',(6.75,5.5,-.35),(.8,5.4,2.1),timber)
        box('SRC_tavern_door',(6.3,5.5,-.55),(.15,1.2,1.55),glow)
    elif attempt == '06':
        box('SRC_fortress_wall',(7.65,5.5,.1),(1.1,5.8,3.3),stone)
        box('SRC_fortress_portal',(6.98,5.5,-.25),(.22,1.3,1.85),iron)
    # foreground framing, deliberately outside walk lane.
    fg_y=3.0 if attempt in ('01','04','06','07','09') else 8.0
    cyl('SRC_foreground_post',(3.9,fg_y,.0),.23,3.3,timber)
    box('SRC_foreground_awning',(4.0,fg_y+.35,1.52),(1.1,1.25,.14),top)
    # low props / depth cues.
    for y in (4.1,6.9): cyl('SRC_barrel',(5.7,y,-1.02),.23,.92,timber)
    box('SRC_market_counter',(6.4,7.55,-.72),(.75,1.05,.75),timber)
    # source lighting.
    bpy.ops.object.light_add(type='AREA', location=(5.2,4.3,3.8)); key=bpy.context.object;key.data.energy=430;key.data.shape='DISK';key.data.size=5;key.data.color=(1,.62,.34);link(key)
    bpy.ops.object.light_add(type='AREA', location=(6.0,7.8,2.2)); fill=bpy.context.object;fill.data.energy=180;fill.data.size=3;fill.data.color=(.22,.34,.75);fill.rotation_euler=(0,.8,2.4);link(fill)
    # coarse runtime geometry: street, facade silhouette, doorway, foreground occluder.
    for args in [('RND_street',(5.7,5.5,-1.58),(5.8,9,.18)),('RND_facade',(8.9,5.5,.5),(1.3,8.4,4.2)),('RND_door',(7.9,door_y,-.35),(.3,.95,2.0)),('RND_occluder',(3.9,fg_y,0),(.55,.55,3.4))]: box(*args,mat('runtime placeholder',(.5,.5,.5)),c='TH_RENDER')
    box('COL_street',(5.7,5.5,-1.72),(5.4,9,.2),stone,c='TH_COLLISION');box('COL_facade',(8.8,5.5,.3),(1.6,8.4,4.0),stone,c='TH_COLLISION')
    anchor_points = [('spawn_player',(5.35,5.5,-1.5)),('npc_merchant',(5.35,6.7,-1.5)),('npc_guard',(5.35,4.25,-1.5)),('door_tavern',(7.55,door_y,-1.5))]
    for n,p in anchor_points:
        o=bpy.data.objects.new(n,None);o.location=p;cols['TH_ANCHORS'].objects.link(o)
    cal = calibration()
    cal['projectionWindowOffsetX'] = offset_x
    cal['viewportCenterX'] = float(cal['viewportCenterX']) + offset_x
    cam=thestra_camera.create_or_update_camera(cal,scene=scene,make_active=True);link(cam,'TH_CAMERA_PREVIEW')
    if anchors_json:
        from bpy_extras.object_utils import world_to_camera_view
        projected = {}
        for name, point in anchor_points:
            uv = world_to_camera_view(scene, cam, Vector(point))
            projected[name] = {'x': round(uv.x * 426, 3), 'y': round((1.0 - uv.y) * 240, 3)}
        anchors_json.parent.mkdir(parents=True, exist_ok=True)
        anchors_json.write_text(__import__('json').dumps(projected, indent=2) + '\n', encoding='utf-8')
    walker=PROJECT/'assets'/'character'/'walker.png'
    if preview_actors:
        for n,p,f in [('ACTOR_Protagonist',(5.35,5.5,-1.5),0),('ACTOR_NPC_Merchant',(5.35,6.7,-1.5),1),('ACTOR_NPC_Guard',(5.35,4.25,-1.5),2)]:
            o=thestra_camera.create_actor_preview(str(walker),cam,anchor=p,frame_width=24,frame_height=48,frame_index=f,world_height=1.75,name=n)
            # The calibrated camera stores a Thestra-facing orientation, whereas
            # preview planes need Blender's visible (Y horizontal / Z vertical)
            # billboard basis.  Keep the actor-facing correction local to preview
            # presentation; it never affects camera authority or the bake.
            o.rotation_quaternion = Vector((-1, 0, 0)).to_track_quat('Z', 'Y')
            link(o,'TH_PREVIEW_ACTORS')
    if save: bpy.ops.wm.save_as_mainfile(filepath=str(save.resolve()))

def main():
    p=argparse.ArgumentParser();p.add_argument('attempt');p.add_argument('--render');p.add_argument('--blend');p.add_argument('--offset-x',type=float,default=0.0);p.add_argument('--no-actors',action='store_true');p.add_argument('--anchors-json',type=Path);p.add_argument('--engine',choices=('EEVEE','CYCLES'),default='EEVEE');a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    build(a.attempt,Path(a.blend) if a.blend else None,a.offset_x,not a.no_actors,a.anchors_json,a.engine)
    if a.render:
        import bpy; bpy.context.scene.render.filepath=str(Path(a.render).resolve()); bpy.context.scene.render.image_settings.file_format='PNG'; bpy.ops.render.render(write_still=True)
if __name__=='__main__': main()
