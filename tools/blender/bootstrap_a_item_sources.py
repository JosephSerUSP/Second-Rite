"""One-shot bootstrap for the Batch-A semantic-sculpture item cohort.

The saved .blend documents become source authority after visual/runtime review.
This script exists only to materialize that first editable state and is deleted
before the migration PR is finalized.

A maps its useful construction directly into Blender:
- axis profiles -> live SCREW revolutions;
- rods / pillars -> semantic profile revolutions;
- rings / open bands -> closed or partial revolved profiles;
- bowls / hollow bells -> explicit hollow generating profiles;
- composition -> named child objects that remain independently editable.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Euler

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import second_rite_asset_core as asset_core

ROOT = SCRIPT_DIR.parents[1]
SOURCE_DIR = ROOT / "assets" / "authoring" / "items"
SOURCE_DIR.mkdir(parents=True, exist_ok=True)

GOLD = "ritual_gold"
BRONZE = "oxidized_bronze"
IRON = "wrought_iron"
CLOTH = "aged_cloth"
GLASS = "smoked_glass"
CRYSTAL = "crystal"
STONE = "old_limestone"
BONE = "bone"
WAX = "wax"
WOOD = "dark_wood"
WET = "wet_residue"
MATERIAL_IDS = {GOLD, BRONZE, IRON, CLOTH, GLASS, CRYSTAL, STONE, BONE, WAX, WOOD, WET}

# Historical recipe coordinates are Y-up. Runtime Blender sources are Z-up.
BASIS = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
BASIS_INV = BASIS.inverted()


def reset():
    asset_core.reset_scene(factory=True)


def materials():
    mats = {mid: asset_core.make_material(mid, semantic_id=mid) for mid in MATERIAL_IDS}
    mats[GOLD]["sr_runtime_passes_json"] = json.dumps([
        {"uvSource": "sphere", "blend": "add", "strength": 1.0,
         "texture": "assets/models/matcaps/gold.png"}
    ])
    mats[CRYSTAL]["sr_runtime_passes_json"] = json.dumps([
        {"uvSource": "sphere", "blend": "add", "strength": 1.0,
         "texture": "assets/models/matcaps/ruby.png"}
    ])
    return mats


def root_for(item_id: str, description: str):
    root = bpy.data.objects.new(f"ITEM_{item_id}", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.20
    bpy.context.scene.collection.objects.link(root)
    root["item_export"] = True
    root["item_export_name"] = item_id
    asset_core.tag_asset_target(
        root,
        asset_id=item_id,
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
        states=["default"], default_state="default", variants=[],
        extra={
            "sr_source_authority": "blend",
            "sr_authoring_grammar": "semantic_sculpture",
            "sr_authoring_description": description,
        },
    )
    return root


def old_matrix(*, translate=(0, 0, 0), rotate=(0, 0, 0), scale=(1, 1, 1)):
    if isinstance(scale, (int, float)):
        scale = (float(scale),) * 3
    sx, sy, sz = scale
    rx, ry, rz = (math.radians(v) for v in rotate)
    # Historical transform order: scale, rotate X then Y then Z, translate.
    s = Matrix.Diagonal((sx, sy, sz, 1.0))
    r = Euler((rx, ry, rz), "XYZ").to_matrix().to_4x4()
    t = Matrix.Translation(translate)
    return BASIS @ (t @ r @ s) @ BASIS_INV


def place(obj, *, parent, translate=(0, 0, 0), rotate=(0, 0, 0), scale=(1, 1, 1)):
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    obj.matrix_local = old_matrix(translate=translate, rotate=rotate, scale=scale)
    return obj


def screw_profile(name, profile, *, parent, material, segments=16, sweep=1.0,
                  closed_profile=False, cap_axis=True, role="revolved_profile"):
    """Create an editable Curve profile with a live Screw modifier around local Z."""
    source = list(profile)
    if not closed_profile and cap_axis:
        if source[0][1] > 1e-7:
            source.insert(0, (source[0][0], 0.0))
        if source[-1][1] > 1e-7:
            source.append((source[-1][0], 0.0))

    curve = bpy.data.curves.new(name + "ProfileData", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.render_resolution_u = 1
    spline = curve.splines.new("POLY")
    spline.points.add(len(source) - 1)
    spline.use_cyclic_u = bool(closed_profile)
    for point, (height, radius) in zip(spline.points, source):
        point.co = (float(radius), 0.0, float(height), 1.0)

    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    asset_core.parent_local(obj, parent)
    asset_core.assign_material(obj, material)
    obj["sr_authoring_role"] = role
    obj["sr_profile_points_json"] = json.dumps([[float(y), float(r)] for y, r in profile])

    screw = obj.modifiers.new("Revolve", "SCREW")
    screw.axis = "Z"
    screw.angle = math.tau * float(sweep)
    screw.steps = int(segments)
    screw.render_steps = int(segments)
    screw.use_merge_vertices = sweep >= 0.999999
    screw.merge_threshold = 0.0001
    screw.use_smooth_shade = True
    screw.use_normal_calculate = True
    screw.use_stretch_u = True
    screw.use_stretch_v = True
    obj["sr_sweep_fraction"] = float(sweep)
    return obj


def disc(name, radius, thickness, *, parent, material, segments=16, bevel=0.0):
    if bevel > 0:
        p = [(-thickness/2, radius-bevel), (-thickness/2+bevel, radius),
             (thickness/2-bevel, radius), (thickness/2, radius-bevel)]
    else:
        p = [(-thickness/2, radius), (thickness/2, radius)]
    return screw_profile(name, p, parent=parent, material=material, segments=segments, role="disc_profile")


def rod(name, radius, length, *, parent, material, segments=6):
    return screw_profile(name, [(0.0, radius), (length, radius)], parent=parent,
                         material=material, segments=segments, role="rod_profile")


def teardrop(name, radius, height, *, parent, material, segments=12):
    p = [(0.0, 0.0), (height*.12, radius*.72), (height*.34, radius),
         (height*.62, radius*.80), (height*.85, radius*.42), (height, 0.0)]
    return screw_profile(name, p, parent=parent, material=material, segments=segments,
                         cap_axis=False, role="teardrop_profile")


def dome(name, radius, height, *, parent, material, segments=12, flatten=0.0):
    p = [(0.0, radius)]
    for step in range(1, 7):
        a = step / 6 * math.pi / 2
        r = radius * math.cos(a) ** (1.0 - flatten)
        p.append((height * math.sin(a), 0.0 if step == 6 else max(r, 0.0)))
    return screw_profile(name, p, parent=parent, material=material, segments=segments,
                         role="dome_profile")


def band(name, centre_radius, tube, *, parent, material, segments=16, sweep=1.0):
    p = []
    for i in range(12):
        a = math.tau * i / 12
        p.append((tube * math.sin(a), centre_radius + tube * math.cos(a)))
    return screw_profile(name, p, parent=parent, material=material, segments=segments,
                         sweep=sweep, closed_profile=True, cap_axis=False, role="band_profile")


def wrap(name, radius, height, *, parent, material, segments=16, sweep=.55):
    return screw_profile(name, [(0.0, radius), (height, radius)], parent=parent,
                         material=material, segments=segments, sweep=sweep, role="wrap_profile")


def bowl(name, radius, height, *, parent, material, segments=16, wall=.12, foot=.35):
    outer = radius
    inner = max(radius-wall, .05)
    p = [(0.0, foot*radius), (0.0, outer*.55), (height*.55, outer), (height, outer),
         (height, inner), (height*.5, inner*.75), (wall*.8, inner*.30),
         (wall*.5, foot*radius*.95)]
    return screw_profile(name, p, parent=parent, material=material, segments=segments,
                         closed_profile=True, cap_axis=False, role="hollow_vessel_profile")


def lathe_body(name, profile, *, parent, material, segments=16, closed=False):
    return screw_profile(name, profile, parent=parent, material=material, segments=segments,
                         closed_profile=closed, cap_axis=not closed, role="authored_lathe_profile")


def linked_copy(source, name, *, parent, translate=(0,0,0), rotate=(0,0,0), scale=(1,1,1)):
    dup = source.copy()
    dup.data = source.data
    dup.name = name
    bpy.context.scene.collection.objects.link(dup)
    # Modifier settings are copied with object.copy; profile data stays linked.
    place(dup, parent=parent, translate=translate, rotate=rotate, scale=scale)
    dup["sr_linked_source"] = source.name
    return dup


def authoring_readme(item_id, text):
    block = bpy.data.texts.new("AUTHORING_README")
    block.write(
        f"Production item source: {item_id}\n\n{text}\n\n"
        "Batch-A semantic sculpture is represented directly in Blender. Objects with a Revolve modifier expose their generating profile as editable Curve points. Named child objects remain independently art-directable.\n"
        "The committed .blend is source authority; runtime OBJ/MTL are compiled read-only through tools/blender/compile_item_blends.py.\n"
    )


def save(item_id):
    path = SOURCE_DIR / f"{item_id}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
    print(f"WROTE A SOURCE {path.relative_to(ROOT)}")


def build_forbidden_lamp():
    reset(); m=materials(); r=root_for("forbidden_lamp", "Sealed lantern assembled from editable revolved volumes, cage rods, hoop, seal and flame")
    base=disc("A_Base", .64,.18,parent=r,material=m[BRONZE],segments=14,bevel=.05)
    belly=lathe_body("A_Belly", [(0,.42),(.18,.60),(.55,.56),(.80,.38),(.95,.26)], parent=r,material=m[BRONZE],segments=14); place(belly,parent=r,translate=(0,.12,0))
    flame=teardrop("A_Flame",.24,.60,parent=r,material=m[CRYSTAL],segments=10); place(flame,parent=r,translate=(0,.62,0))
    cage0=rod("A_Cage_0",.035,.88,parent=r,material=m[IRON],segments=5); place(cage0,parent=r,translate=(.46,.34,0))
    for i in range(1,6):
        a=math.tau*i/6; linked_copy(cage0,f"A_Cage_{i}",parent=r,translate=(.46*math.cos(a),.34,.46*math.sin(a)))
    crown=band("A_Crown",.37,.065,parent=r,material=m[GOLD],segments=14); place(crown,parent=r,translate=(0,1.20,0))
    roof=dome("A_Roof",.46,.34,parent=r,material=m[BRONZE],segments=14,flatten=.1); place(roof,parent=r,translate=(0,1.05,0))
    handle=band("A_Handle",.72,.055,parent=r,material=m[IRON],segments=18,sweep=.66); place(handle,parent=r,rotate=(90,0,0),translate=(0,.95,-.48))
    seal=disc("A_Seal",.18,.07,parent=r,material=m[GOLD],segments=10,bevel=.02); place(seal,parent=r,rotate=(90,0,0),translate=(0,.62,.64))
    authoring_readme("forbidden_lamp","Move profile points on Belly/Roof/Base to change the lamp volume; cage members share one source profile so rod edits propagate.")
    save("forbidden_lamp")


def build_town_portal():
    reset(); m=materials(); r=root_for("town_portal", "Broken nested astrolabe assembled from editable partial revolve bands, core, grip and studs")
    outer=band("A_OuterRing",.78,.085,parent=r,material=m[GOLD],segments=22,sweep=.82); place(outer,parent=r,rotate=(90,0,0),translate=(0,.80,0))
    inner=band("A_InnerRing",.53,.055,parent=r,material=m[IRON],segments=18,sweep=.72); place(inner,parent=r,rotate=(90,0,28),translate=(0,.80,.02))
    inner2=band("A_InnerRing2",.42,.040,parent=r,material=m[BRONZE],segments=18,sweep=.62); place(inner2,parent=r,rotate=(90,35,-18),translate=(0,.80,.04))
    core=teardrop("A_SuspendedCore",.30,.58,parent=r,material=m[GLASS],segments=10); place(core,parent=r,scale=(1,.85,.28),translate=(0,.49,.06))
    grip=rod("A_Grip",.11,.62,parent=r,material=m[WOOD],segments=7); place(grip,parent=r,translate=(0,-.02,0))
    pommel=disc("A_Pommel",.22,.12,parent=r,material=m[GOLD],segments=10,bevel=.03); place(pommel,parent=r,translate=(0,-.03,0))
    stud0=dome("A_Stud_0",.08,.06,parent=r,material=m[GOLD],segments=6,flatten=.3); place(stud0,parent=r,translate=(.60,.80,0))
    for i in range(1,4):
        a=math.tau*i/4; linked_copy(stud0,f"A_Stud_{i}",parent=r,translate=(.60*math.cos(a),.80,.60*math.sin(a)))
    authoring_readme("town_portal","The three broken rings are live partial Screw profiles; their open seams and relative rotations are intended authoring handles.")
    save("town_portal")


def build_crossing_writ():
    reset(); m=materials(); r=root_for("crossing_writ", "Bone writ assembled from slab, rollers, wax/gold seal, wrap and cloth tail")
    sheet=disc("A_WritSheet",.72,.07,parent=r,material=m[BONE],segments=4,bevel=.03); place(sheet,parent=r,rotate=(90,0,45),scale=(.72,1,1.32),translate=(0,.72,0))
    top=rod("A_TopRoll",.075,1.28,parent=r,material=m[WOOD],segments=7); place(top,parent=r,rotate=(0,0,90),translate=(.64,1.38,0))
    bottom=rod("A_BottomRoll",.075,1.28,parent=r,material=m[WOOD],segments=7); place(bottom,parent=r,rotate=(0,0,90),translate=(.64,.06,0))
    seal=disc("A_Seal",.22,.09,parent=r,material=m[GOLD],segments=12,bevel=.03); place(seal,parent=r,rotate=(90,0,0),translate=(.27,.46,.10))
    cord=wrap("A_CordWrap",.31,.11,parent=r,material=m[CLOTH],segments=12,sweep=.46); place(cord,parent=r,rotate=(90,0,0),translate=(.27,.46,.04))
    tail=rod("A_ClothTail",.045,.50,parent=r,material=m[CLOTH],segments=5); place(tail,parent=r,rotate=(0,0,22),scale=(1,.9,.4),translate=(.10,.09,.08))
    authoring_readme("crossing_writ","Rollers, seal and wrap remain separate semantic objects; the sheet is a low-sided revolved slab preserving the original stylized construction.")
    save("crossing_writ")


def build_smoke_bell():
    reset(); m=materials(); r=root_for("smoke_bell", "Genuinely hollow bell driven by one closed wall profile plus clapper, lip, crown and soot band")
    profile=[(0,.68),(.14,.76),(.55,.60),(.95,.40),(1.10,.24),(1.10,.15),(.93,.30),(.52,.49),(.16,.62),(0,.60)]
    lathe_body("A_HollowBell",profile,parent=r,material=m[BRONZE],segments=16,closed=True)
    band("A_IronLip",.68,.07,parent=r,material=m[IRON],segments=16)
    crown=band("A_Crown",.26,.055,parent=r,material=m[IRON],segments=12); place(crown,parent=r,rotate=(90,0,0),translate=(0,1.19,0))
    stem=rod("A_ClapperStem",.045,.82,parent=r,material=m[IRON],segments=5); place(stem,parent=r,translate=(0,.18,0))
    clapper=teardrop("A_Clapper",.15,.26,parent=r,material=m[IRON],segments=7); place(clapper,parent=r,translate=(0,-.05,0))
    soot=band("A_SootBand",.58,.035,parent=r,material=m[WET],segments=14,sweep=.72); place(soot,parent=r,translate=(0,.28,0))
    authoring_readme("smoke_bell","A_HollowBell exposes the full outer→rim→inner wall section as one closed editable profile, so hollow-ness is authored rather than painted.")
    save("smoke_bell")


def build_mourning_ribbon():
    reset(); m=materials(); r=root_for("mourning_ribbon", "Memorial bow built from editable partial revolve loops, flattened tails, knot and medallion")
    left=band("A_Loop_L",.34,.075,parent=r,material=m[CLOTH],segments=16,sweep=.70); place(left,parent=r,rotate=(90,0,35),scale=(1.05,.80,.40),translate=(-.22,.72,0))
    right=band("A_Loop_R",.34,.075,parent=r,material=m[CLOTH],segments=16,sweep=.70); place(right,parent=r,rotate=(90,0,-35),scale=(1.05,.80,.40),translate=(.22,.72,0))
    knot=dome("A_Knot",.21,.16,parent=r,material=m[CLOTH],segments=10,flatten=.55); place(knot,parent=r,scale=(1,.9,.55),translate=(0,.62,.05))
    tl=rod("A_Tail_L",.095,.58,parent=r,material=m[CLOTH],segments=5); place(tl,parent=r,rotate=(0,0,18),scale=(1,1,.32),translate=(-.03,.08,0))
    tr=rod("A_Tail_R",.095,.55,parent=r,material=m[CLOTH],segments=5); place(tr,parent=r,rotate=(0,0,-20),scale=(1,1,.32),translate=(.04,.08,.02))
    med=disc("A_Medallion",.14,.05,parent=r,material=m[GOLD],segments=10,bevel=.02); place(med,parent=r,rotate=(90,0,0),translate=(0,.61,.16))
    authoring_readme("mourning_ribbon","Loops are editable open band profiles rather than baked ribbon polygons; tails/knot/medallion remain separate for direct art direction.")
    save("mourning_ribbon")


def build_first_scale():
    reset(); m=materials(); r=root_for("first_scale", "Layered flattened Red Dragon scale assembled from revolved teardrop profiles, ridge and scars")
    main=teardrop("A_MainScale",.66,1.55,parent=r,material=m[CRYSTAL],segments=11); place(main,parent=r,scale=(1,1,.20))
    inner=teardrop("A_GoldLayer",.48,1.22,parent=r,material=m[GOLD],segments=9); place(inner,parent=r,scale=(1,1,.07),translate=(0,.13,.15))
    inner2=teardrop("A_IronLayer",.32,.90,parent=r,material=m[IRON],segments=7); place(inner2,parent=r,scale=(1,1,.045),translate=(0,.26,.205))
    ridge=rod("A_Ridge",.035,1.18,parent=r,material=m[GOLD],segments=5); place(ridge,parent=r,translate=(0,.18,.24))
    s1=rod("A_Scar_1",.025,.62,parent=r,material=m[IRON],segments=5); place(s1,parent=r,rotate=(0,0,55),translate=(-.22,.55,.23))
    s2=rod("A_Scar_2",.022,.48,parent=r,material=m[IRON],segments=5); place(s2,parent=r,rotate=(0,0,-60),translate=(.23,.78,.23))
    authoring_readme("first_scale","The scale keeps semantic layered teardrop profiles and separate ridge/scars. Flattening is ordinary object scale, so profile and thickness can be art-directed independently.")
    save("first_scale")


def build_bell_salt():
    reset(); m=materials(); r=root_for("bell_salt", "Hollow stone ritual font with editable vessel profile, salt bed, linked mineral shards and broken halo")
    bowl("A_Font",.74,.44,parent=r,material=m[STONE],segments=16,wall=.08,foot=.28)
    bed=disc("A_SaltBed",.61,.05,parent=r,material=m[GLASS],segments=14); place(bed,parent=r,translate=(0,.37,0))
    shard0=teardrop("A_Shard_0",.14,.68,parent=r,material=m[GLASS],segments=6); place(shard0,parent=r,translate=(-.28,.38,-.10),rotate=(0,0,-12),scale=.90)
    transforms=[((.18,.38,.05),(0,0,14),1.15),((.03,.38,-.22),(8,0,2),.78),((.32,.38,-.12),(0,0,22),.70),((-.08,.38,.24),(0,0,-18),.82)]
    for i,(tr,rot,sc) in enumerate(transforms,1): linked_copy(shard0,f"A_Shard_{i}",parent=r,translate=tr,rotate=rot,scale=sc)
    halo=band("A_BrokenHalo",.54,.035,parent=r,material=m[GOLD],segments=16,sweep=.84); place(halo,parent=r,translate=(0,.52,0))
    authoring_readme("bell_salt","A_Font is a closed hollow wall profile. The five salt shards share one linked generating profile but keep independent placement/scale handles.")
    save("bell_salt")


def build_sealed_reliquary():
    reset(); m=materials(); r=root_for("sealed_reliquary", "Miniature chapel/monstrance assembled from profile-driven base, pillars, shrine, arch, seal, chain and cross")
    base=disc("A_Base",.66,.18,parent=r,material=m[GOLD],segments=6,bevel=.05); place(base,parent=r,scale=(1.25,1,.78))
    foot=disc("A_Foot",.48,.16,parent=r,material=m[BRONZE],segments=6,bevel=.04); place(foot,parent=r,scale=(1.15,1,.72),translate=(0,.18,0))
    left=rod("A_Pillar_L",.065,1.05,parent=r,material=m[GOLD],segments=6); place(left,parent=r,translate=(-.48,.28,0))
    right=linked_copy(left,"A_Pillar_R",parent=r,translate=(.48,.28,0))
    shrine=teardrop("A_ShrineCore",.43,.86,parent=r,material=m[GLASS],segments=10); place(shrine,parent=r,scale=(1,.96,.26),translate=(0,.45,.04))
    arch=band("A_Arch",.50,.065,parent=r,material=m[GOLD],segments=18,sweep=.60); place(arch,parent=r,rotate=(90,0,0),translate=(0,1.10,0))
    seal=disc("A_Seal",.20,.07,parent=r,material=m[WAX],segments=10,bevel=.02); place(seal,parent=r,rotate=(90,0,0),translate=(0,.77,.19))
    chain=band("A_Chain",.27,.028,parent=r,material=m[IRON],segments=14,sweep=.80); place(chain,parent=r,rotate=(90,0,0),translate=(0,.73,.17))
    cv=rod("A_Cross_V",.035,.34,parent=r,material=m[GOLD],segments=5); place(cv,parent=r,translate=(0,1.32,0))
    ch=rod("A_Cross_H",.035,.28,parent=r,material=m[GOLD],segments=5); place(ch,parent=r,rotate=(0,0,90),translate=(.14,1.53,0))
    fin=dome("A_Finial",.10,.16,parent=r,material=m[GOLD],segments=8,flatten=.1); place(fin,parent=r,translate=(0,1.66,0))
    authoring_readme("sealed_reliquary","The reliquary is intentionally a semantic assembly: base, foot, linked pillars, shrine profile, arch, seal, chain, cross and finial all remain named/editable.")
    save("sealed_reliquary")


BUILDERS=[build_forbidden_lamp,build_town_portal,build_crossing_writ,build_smoke_bell,build_mourning_ribbon,build_first_scale,build_bell_salt,build_sealed_reliquary]
for builder in BUILDERS:
    builder()
