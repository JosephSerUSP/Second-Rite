"""Shared furnishing grammar for St. Maria interiors.

St. Maria is a **colonial Portuguese** town, and that is a specific vocabulary,
not a generic "old" one:

- limewashed masonry (*caiacao*) rather than grey plaster or bare brick;
- an *azulejo* dado -- blue-and-white tin-glazed tile as a waist-high band on
  the wall, never as a whole wall;
- dark tropical hardwood, heavy and turned rather than slender;
- wrought iron: grilles over windows, bands on chests, lantern frames;
- terracotta for pantiles, floor tile and unglazed pottery;
- panelled doors and shutters, not plank doors.

That vocabulary lives in the PROPORTIONS, MATERIALS and JOINERY, which is where
it is load-bearing -- not in the identifiers. Pieces are named in English; a
Portuguese term is kept only where English needs a phrase to say the same thing
(`azulejo` is not "tile", it is waist-high blue-and-white tin-glaze). A
`cadeira` and a `chair` are the same chair, and the name does not make either
one Portuguese: the hardwood, the turning and the iron banding do. The prose
below still names the Portuguese term wherever it helps identify the object.

Every piece here takes an `Interior` and appends to it, so a map file reads as
a furnishing list. Pieces are deterministic, low-poly and axis-aligned, which
keeps them cheap and keeps the world-space box-projected materials clean.

Each piece builds inside `Interior.piece`, so it lands in the `.blend` as ONE
joined object rather than as its component boxes. The `.blend` is the
hand-editable source document and a furnished shop is otherwise ~100 loose
boxes in a flat outliner.

Placement convention: `at=(x, y)` is the footprint CENTRE on the floor, and
pieces build upward from z=0. Larger x is deeper into the room, away from the
camera; -y is screen right.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Self-sufficient: this module must import cleanly regardless of whether
# `interior` happened to be imported first.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import second_rite_asset_core as asset_core  # noqa: E402


def _leg(room, name, x, y, size, height, mat):
    return room.part(name, (size, size, height), (x, y, height / 2.0), mat)


def _revolved(room, name, at, radii, profile, *, mat, sides=8, rotation=0.0,
              tilt=0.0):
    """A radial solid swept from a (scale, level) profile.

    Jars, sacks, barrels and tubs are all this shape with different numbers,
    and radial pieces are what stop an interior reading as a room of boxes.
    `radii` is (rx, ry) so a sack can be slightly oval without a scale on the
    object, which would fight the world-space box projection.

    `tilt` turns the swept axis away from vertical. At tilt=tau/4 the solid
    stands on its edge, which is the only way this vocabulary can make a WHEEL
    -- and a wheel is the one curve in it that reads in elevation rather than
    in plan.
    """
    import bmesh

    x, y = at
    rx, ry = radii
    bm = bmesh.new()
    rings = []
    for scale, level in profile:
        ring = [bm.verts.new((math.cos(math.tau * i / sides) * rx * scale,
                              math.sin(math.tau * i / sides) * ry * scale,
                              level)) for i in range(sides)]
        rings.append(ring)
    bm.faces.new(reversed(rings[0]))
    for lower, upper in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
    bm.faces.new(rings[-1])
    obj = asset_core.mesh_object_from_bmesh(name, bm)
    # room.lift is the surface this is standing on: the floor unless we are
    # inside an `Interior.surface` block. A radial piece parents directly
    # rather than going through `Interior.part`, so it has to add it itself.
    asset_core.parent_local(obj, room.root, loc=(x, y, room.lift),
                            rot=(tilt, 0.0, rotation))
    asset_core.assign_material(obj, mat)
    asset_core.flat_shade(obj)
    room.parts.append(obj)
    return obj


# ---------------------------------------------------------------------------
# Domestic
# ---------------------------------------------------------------------------

def chest(room, name, at, *, length=1.15, depth=0.55, height=0.58):
    """A banded chest (*arca*). The workhorse of a colonial interior: storage,
    seat, and the thing a lodger actually owns."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_body", (depth, length, height * 0.78),
                  (x, y, height * 0.39), room.wood)
        room.part(f"{name}_lid", (depth + 0.05, length + 0.05, height * 0.22),
                  (x, y, height * 0.89), room.wood)
        for index, offset in enumerate((-length * 0.3, length * 0.3)):
            room.part(f"{name}_band_{index}", (depth + 0.07, 0.06, height),
                      (x, y + offset, height / 2.0), room.iron)
        room.part(f"{name}_lock", (0.04, 0.14, 0.12),
                  (x - depth / 2.0 - 0.02, y, height * 0.72), room.iron)


def bed(room, name, at, *, length=1.95, width=0.95, height=0.5):
    """A bed with turned posts, headboard toward the back wall."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_frame", (width, length, height * 0.34),
                  (x, y, height * 0.5), room.wood)
        room.part(f"{name}_mattress", (width - 0.08, length - 0.1, 0.2),
                  (x, y, height + 0.1), room.cloth)
        room.part(f"{name}_bolster", (width - 0.14, 0.3, 0.16),
                  (x, y - length / 2.0 + 0.22, height + 0.26), room.cloth)
        room.part(f"{name}_headboard", (0.08, width + 0.06, 0.85),
                  (x + width / 2.0, y, 0.62), room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            post = 1.05 if dx > 0 else 0.55
            _leg(room, f"{name}_post_{index}", x + dx * (width - 0.12),
                 y + dy * (length - 0.12), 0.09, post, room.wood)


def cabinet(room, name, at, *, width=1.05, depth=0.5, height=1.85):
    """A panelled cabinet (*armario*). Tall, dark and heavy: the room's
    vertical mass."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_carcass", (depth, width, height),
                  (x, y, height / 2.0), room.wood)
        room.part(f"{name}_cornice", (depth + 0.09, width + 0.09, 0.1),
                  (x, y, height + 0.05), room.wood)
        for index, offset in enumerate((-width * 0.24, width * 0.24)):
            room.part(f"{name}_panel_{index}",
                      (0.03, width * 0.38, height * 0.62),
                      (x - depth / 2.0 - 0.015, y + offset, height * 0.55),
                      room.wood)
        room.part(f"{name}_handle", (0.05, 0.05, 0.16),
                  (x - depth / 2.0 - 0.04, y, height * 0.55), room.iron)


def records_press(room, name, at, *, width=2.1, depth=.82, height=2.8, panel_mat=None):
    """Tall civic records cupboard: framed doors, labelled drawers and stepped cornice."""
    x,y=at;front=x-depth/2
    with room.piece(name):
        room.part(name+'_case',(depth,width,height-.10),(x,y,(height-.10)/2),room.wood)
        room.part(name+'_plinth',(depth+.07,width+.10,.16),(x-.01,y,.08),room.wood)
        room.part(name+'_crown_lower',(depth+.09,width+.13,.11),(x-.01,y,height-.06),room.wood)
        room.part(name+'_crown_upper',(depth+.15,width+.22,.08),(x-.025,y,height+.025),room.wood)
        for side in (-1,1):
            cy=y+side*width*.245;door_width=width*.44
            room.part(name+'_door_panel',(.034,door_width-.10,1.57),
                      (front-.028,cy,1.78),panel_mat or room.wood)
            for edge in (-1,1):
                room.part(name+'_door_stile',(.067,.065,1.76),(front-.035,cy+edge*door_width/2,1.78),room.wood)
                room.part(name+'_door_rail',(.067,door_width,.075),(front-.035,cy,1.78+edge*.845),room.wood)
            room.part(name+'_meeting_rail',(.058,door_width,.055),(front-.037,cy,1.77),room.wood)
            for z in (1.12,2.42):
                room.part(name+'_hinge',(.025,.030,.11),(front-.081,cy+side*door_width*.44,z),room.iron)
            room.part(name+'_keyplate',(.026,.055,.12),(front-.085,cy-side*door_width*.34,1.62),room.bronze)
            room.part(name+'_handle',(.056,.11,.028),(front-.104,cy-side*door_width*.34,1.64),room.bronze)
        for z in (.34,.65):
            room.part(name+'_drawer',(.047,width-.17,.24),(front-.028,y,z),panel_mat or room.wood)
            room.part(name+'_drawer_label',(.006,.22,.072),(front-.057,y,z+.018),room.paper)
            for side in (-1,1):
                room.part(name+'_drawer_pull',(.06,.12,.027),(front-.075,y+side*width*.26,z),room.bronze)


def woven_runner(room, name, at, *, length=4.7, width=1.55, cloth_mat, border_mat, motif_mat):
    """Flat decorative textile with broad borders and restrained lozenge repeats.

    The lozenges repeat every 0.74 m along the length, so a long aisle runner
    carries its motif end to end (the 4.7 m default keeps its five).
    """
    x,y=at
    count=max(1,int((length-0.6)/0.74))
    with room.piece(name):
        room.part(name+'_field',(width,length,.012),(x,y,.008),cloth_mat)
        for side in (-1,1):
            room.part(name+'_long_border',(.13,length-.12,.004),(x+side*(width/2-.09),y,.016),border_mat)
            room.part(name+'_end_border',(width-.12,.13,.004),(x,y+side*(length/2-.09),.016),border_mat)
        for i in range(count):
            offset=(i-(count-1)/2)*.74
            obj=room.part(name+'_lozenge',(.25,.25,.003),(x,y+offset,.017),motif_mat)
            obj.rotation_euler.z=math.pi/4
            obj=room.part(name+'_lozenge_inset',(.12,.12,.003),(x,y+offset,.020),cloth_mat)
            obj.rotation_euler.z=math.pi/4


def ledger(room, name, at, *, length=0.42, width=0.24, open_book=False):
    """A narrow bound account book; place on a desk with room.surface()."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_cover", (width, length, 0.014),
                  (x, y, 0.007), room.leather)
        if open_book:
            for index, offset in enumerate((-length * 0.245, length * 0.245)):
                room.part(f"{name}_page_{index}", (width * 0.93, length * 0.46, 0.032),
                          (x, y + offset, 0.030), room.paper)
            room.part(f"{name}_binding", (width, 0.018, 0.055),
                      (x, y, 0.0275), room.leather)
            # A pale page surface remains the dominant native-size accent.
            room.part(f"{name}_ribbon", (width * 0.82, 0.009, 0.003),
                      (x, y - length * 0.28, 0.048), room.leather)
        else:
            room.part(f"{name}_pages", (width * 0.94, length * 0.94, 0.04),
                      (x, y, 0.034), room.paper)
            room.part(f"{name}_lid", (width, length, 0.015),
                      (x, y, 0.0615), room.leather)
            room.part(f"{name}_spine", (width, 0.023, 0.069),
                      (x, y - length / 2, 0.0345), room.leather)


def bound_volume(room, name, at, *, height=.43, thickness=.095, depth=.34, cover_mat=None):
    """Upright ledger with recessed page block, projecting boards and visible spine."""
    x,y=at
    cover=cover_mat or room.leather
    with room.piece(name):
        room.part(name+'_pages',(depth-.045,thickness-.028,height-.045),
                  (x+.012,y,height/2),room.paper)
        for side in (-1,1):
            room.part(name+'_board',(depth, .014,height),
                      (x,y+side*(thickness/2-.007),height/2),cover)
        room.part(name+'_spine',(.028,thickness,height),(x-depth/2+.014,y,height/2),cover)
        for z in (.10,height-.09):
            room.part(name+'_raised_band',(.038,thickness+.009,.019),(x-depth/2+.009,y,z),cover)
        room.part(name+'_label',(.004,thickness*.65,height*.18),
                  (x-depth/2-.003,y,height*.58),room.paper)


def seal_stamp(room, name, at):
    """A handled brass seal beside its dark ink pad."""
    x, y = at
    with room.piece(name):
        _revolved(room, f"{name}_die", (x,y), (.043,.043),
                  [(1,0),(1,.021),(.55,.03),(.4,.048)], mat=room.bronze, sides=12)
        _revolved(room, f"{name}_grip", (x,y), (.035,.035),
                  [(.38,.045),(.6,.067),(1,.09),(.9,.13),(.6,.15)], mat=room.wood, sides=12)
        room.part(f"{name}_pad_tray", (0.13, 0.17, 0.018), (x, y + 0.19, 0.009), room.wood)
        room.part(f"{name}_pad", (0.105, 0.145, 0.006), (x, y + 0.19, 0.021), room.ink)


def waiting_bench(room, name, at, *, length=1.75):
    """Heavy waiting bench with supported back and a lower stretcher."""
    x,y=at
    with room.piece(name):
        room.part(f'{name}_seat',(.48,length,.085),(x,y,.46),room.wood)
        for i,side in enumerate((-1,1)):
            room.part(f'{name}_leg_{i}',(.35,.12,.43),(x,y+side*(length/2-.13),.215),room.wood)
            room.part(f'{name}_post_{i}',(.085,.085,1.0),(x+.20,y+side*(length/2-.12),.5),room.wood)
        room.part(f'{name}_back',(.06,length,.33),(x+.21,y,.86),room.wood)
        room.part(f'{name}_brace',(.07,length-.25,.08),(x,y,.19),room.wood)


def record_bay(room, name, at, *, width=1.5, height=1.65, columns=3, rows=3):
    """Open document pigeonholes with visible grouped paper bundles."""
    x,y=at
    with room.piece(name):
        room.part(f'{name}_back',(.055,width,height),(x+.20,y,height/2),room.wood)
        for i in range(rows+1):
            room.part(f'{name}_shelf_{i}',(.46,width,.055),(x,y,i*height/rows),room.wood)
        for i in range(columns+1):
            room.part(f'{name}_divider_{i}',(.46,.055,height),(x,y-width/2+i*width/columns,height/2),room.wood)
        for row in range(rows):
            for col in range(columns):
                py=y-width/2+(col+.5)*width/columns
                z=row*height/rows+.075
                amount=3+(row+col)%3
                for j in range(amount):
                    room.part(f'{name}_paper_{row}_{col}_{j}',(.32,width/columns*.7,.045),
                              (x-.035,py,z+j*.048),room.paper)
                room.part(f'{name}_cord_{row}_{col}',(.33,.025,.012),
                          (x-.035,py,z+(amount-.5)*.048),room.leather)


def service_screen(room, name, *, front, rear, left, right, panel_mat=None,
                   height=2.78, transom_top=None, beam_spans=()):
    """L-shaped counter joinery: an open serving transom and wall-connected return."""
    if rear<=front or left<=right:raise ValueError('Screen needs positive depth and width')
    transom_top=height if transom_top is None else transom_top
    if transom_top<=2.43 or height<transom_top:raise ValueError('Screen head must sit above serving transom')
    with room.piece(name):
        for y in (left,right):
            room.part('service_screen_front_post',(.12,.12,height),(front,y,height/2),room.wood)
        room.part('service_screen_return_post',(.12,.12,height),(rear-.04,left,height/2),room.wood)
        for z in (2.43,transom_top):
            room.part('service_transom_rail',(.10,left-right+.12,.08),(front,(left+right)/2,z),room.wood)
            room.part('return_transom_rail',(rear-front+.08,.10,.08),((front+rear)/2,left,z),room.wood)
        for j in range(1,8):
            room.part('service_transom_spindle',(.045,.035,transom_top-2.43),
                      (front,right+j*(left-right)/8,(transom_top+2.43)/2),room.wood)
        if beam_spans:
            # Beam pockets are omitted from the infill, leaving existing timbers intact.
            base=transom_top+.04
            cursor=right-.06
            spans=[]
            for low,high in sorted(beam_spans):
                low=max(low,right-.06);high=min(high,left+.06)
                if high<=low:continue
                if low>cursor:spans.append((cursor,low))
                cursor=max(cursor,high)
            if cursor<left+.06:spans.append((cursor,left+.06))
            for low,high in spans:
                room.part('notched_front_head_infill',(.09,high-low,height-base),
                          (front,(low+high)/2,(height+base)/2),panel_mat or room.wood)
                room.part('notched_front_crown',(.13,high-low,.07),
                          (front,(low+high)/2,height-.035),room.wood)
            room.part('return_head_infill',(rear-front,.09,height-base),
                      ((front+rear)/2,left,(height+base)/2),panel_mat or room.wood)
            room.part('return_crown',(rear-front+.08,.13,.07),
                      ((front+rear)/2,left,height-.035),room.wood)
        room.part('service_return_base',(rear-front,.09,.90),((front+rear)/2,left,.45),panel_mat or room.wood)
        room.part('service_return_dado',(rear-front+.08,.12,.07),((front+rear)/2,left,.97),room.wood)
        for j in range(1,7):
            room.part('return_upright',(.065,.075,1.43),(front+j*(rear-front)/7,left,1.715),room.wood)
        room.part('return_middle_rail',(rear-front,.075,.05),((front+rear)/2,left,1.78),room.wood)


def counter_returns(room, name, at, *, length=3.8, depth=.95, height=.92, panel_mat=None):
    """Low cabinetry returning behind a counter; no freestanding architectural frame."""
    x,y=at
    with room.piece(name):
        for side in (-1,1):
            py=y+side*(length/2+.045)
            room.part(name+'_end_panel',(depth,.075,height-.10),
                      (x+depth/2,py,(height-.10)/2),panel_mat or room.wood)
            room.part(name+'_cap',(depth+.06,.12,.075),
                      (x+depth/2,py,height+.025),room.wood)
            room.part(name+'_plinth',(depth,.10,.10),(x+depth/2,py,.05),room.wood)


def service_counter(room, name, at, *, length=3.8, height=.92):
    """Panelled civic counter with overhanging writing surface and foot rail."""
    x,y=at
    counter(room,name,at,length=length,width=.88,height=height,panels=5)
    with room.piece(f'{name}_writing_station'):
        room.part(f'{name}_writing_pad',(.52,1.15,.014),(x-.05,y,height+.087),room.leather)
        room.part(f'{name}_tray_base',(.45,.50,.04),(x,y+1.35,height+.10),room.wood)
        for side in (-1,1):
            room.part(f'{name}_tray_edge_{side}',(.45,.04,.10),(x,y+1.35+side*.24,height+.15),room.wood)
        room.part(f'{name}_writs',(.33,.36,.065),(x,y+1.35,height+.152),room.paper)


def framed_picture(room, name, at, *, width=1.15, height=.82, artwork):
    """A back-wall frame with recessed canvas and explicitly mapped image UVs."""
    import bpy
    x,y,z=at
    with room.piece(name):
        for side in (-1,1):
            room.part(name+'_stile',(.075,.065,height+.12),(x,y+side*(width/2+.0325),z),room.wood)
            room.part(name+'_rail',(.075,width,.065),(x,y,z+side*(height/2+.0325)),room.wood)
        mesh=bpy.data.meshes.new(name+'_canvas')
        mesh.from_pydata([(x-.018,y-width/2,z-height/2),(x-.018,y+width/2,z-height/2),
                          (x-.018,y+width/2,z+height/2),(x-.018,y-width/2,z+height/2)],[],[(3,2,1,0)])
        layer=mesh.uv_layers.new(name='Artwork')
        uv=[(1,0),(0,0),(0,1),(1,1)]
        for loop in mesh.loops:layer.data[loop.index].uv=uv[loop.vertex_index]
        obj=bpy.data.objects.new(name+'_canvas',mesh);bpy.context.collection.objects.link(obj)
        asset_core.parent_local(obj,room.root,loc=(0,0,room.lift))
        asset_core.assign_material(obj,artwork);room.parts.append(obj)


def potted_plant(room, name, at, *, foliage_mat, pot_mat=None):
    """One clay pot with folded, broad-leaved foliage and separate stem silhouettes."""
    import bmesh
    from mathutils import Vector
    x,y=at
    with room.piece(name):
        jar(room,name+'_pot',at,height=.31,radius=.19,mat=pot_mat or room.terracotta)
        for i in range(7):
            angle=i*2.399963
            start=Vector((x,y,.27));tip=Vector((x+math.cos(angle)*.32,y+math.sin(angle)*.32,.64+.12*(i%3)))
            length=(tip-start).length
            stem=room.part(name+'_stem',(.016,.016,length),tuple((start+tip)/2),foliage_mat)
            stem.rotation_euler=(tip-start).to_track_quat('Z','Y').to_euler()
            reach=Vector((math.cos(angle)*.40,math.sin(angle)*.40,.12-.06*(i%3)))
            cross=Vector((-math.sin(angle),math.cos(angle),0))*.135
            bm=bmesh.new()
            verts=[bm.verts.new(tuple(point)) for point in
                (tip,tip+reach*.25+cross*.75,tip+reach*.65+cross,tip+reach,
                 tip+reach*.65-cross,tip+reach*.25-cross*.75,tip+reach*.5+Vector((0,0,.065)))]
            for j in range(6):bm.faces.new((verts[j],verts[(j+1)%6],verts[6]))
            obj=asset_core.mesh_object_from_bmesh(name+'_leaf',bm)
            asset_core.parent_local(obj,room.root,loc=(0,0,room.lift))
            asset_core.assign_material(obj,foliage_mat);room.parts.append(obj)


def table(room, name, at, *, length=1.25, width=0.7, height=0.76):
    """A table on turned legs."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_top", (width, length, 0.07), (x, y, height),
                  room.wood)
        room.part(f"{name}_rail", (width - 0.14, length - 0.14, 0.09),
                  (x, y, height - 0.11), room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.14),
                 y + dy * (length - 0.14), 0.08, height - 0.04, room.wood)


def chair(room, name, at, *, seat=0.44, width=0.44):
    """A straight-backed chair."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_seat", (width, width, 0.06), (x, y, seat),
                  room.wood)
        room.part(f"{name}_back", (0.06, width, 0.52),
                  (x + width / 2.0 - 0.03, y, seat + 0.28), room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.08),
                 y + dy * (width - 0.08), 0.05, seat, room.wood)


def jar(room, name, at, *, height=0.46, radius=0.19, sides=8, mat=None):
    """An unglazed jar (*pote*). Radial, so it breaks up an interior of
    boxes."""
    profile = ((0.55, 0.0), (1.0, 0.28 * height), (0.86, 0.62 * height),
               (0.48, 0.9 * height), (0.58, height))
    with room.piece(name):
        obj = _revolved(room, name, at, (radius, radius), profile,
                        mat=mat or room.terracotta, sides=sides)
    return obj


def shelf(room, name, *, y, z, length=1.3, depth=0.26):
    """A shelf against the back wall, with its brackets."""
    x = room.back_x - depth / 2.0
    with room.piece(name):
        room.part(f"{name}_board", (depth, length, 0.05), (x, y, z), room.wood)
        for index, offset in enumerate((-length * 0.36, length * 0.36)):
            room.part(f"{name}_bracket_{index}", (depth * 0.7, 0.05, 0.16),
                      (x + 0.03, y + offset, z - 0.1), room.iron)


def lantern(room, name, *, y, z=2.1, energy=13.0):
    """A wrought-iron wall lantern, and the light it actually casts.

    The light is a separate object by necessity -- a lamp cannot be joined
    into a mesh -- so it stays a sibling of the joined lantern body.
    """
    x = room.back_x - 0.16
    with room.piece(name):
        room.part(f"{name}_bracket", (0.22, 0.05, 0.05),
                  (x + 0.08, y, z + 0.18), room.iron)
        room.part(f"{name}_cage", (0.16, 0.16, 0.22), (x, y, z), room.iron)
        room.part(f"{name}_flame", (0.09, 0.09, 0.13), (x, y, z),
                  room.lamplight)
    return room.light(f"{name}_light", "POINT", (x - 0.05, y, z),
                      (0.0, 0.0, -1.0), energy, (1.0, 0.82, 0.55), radius=0.14)


def barrel(room, name, at, *, radius=0.32, height=0.76):
    """A staved storage barrel with iron reinforcement hoops."""
    x, y = at
    profile = ((0.86, 0.0), (1.08, 0.5 * height), (0.86, height))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius), profile, mat=room.wood,
                  sides=10)
        for index, level in enumerate((0.18, 0.50, 0.82)):
            room.part(f"{name}_hoop_{index}", (radius * 2.22, radius * 2.22,
                                               0.04),
                      (x, y, height * level), room.iron)


def sack(room, name, at, *, width=0.46, depth=0.42, height=0.58, rotation=0.0):
    """A burlap sack of flour or grain, gathered and tied at the neck."""
    x, y = at
    profile = ((0.75, 0.0), (1.05, 0.32 * height), (0.98, 0.65 * height),
               (0.65, 0.88 * height), (0.72, height))
    with room.piece(name):
        _revolved(room, name, at, (depth / 2.0, width / 2.0), profile,
                  mat=room.cloth, rotation=rotation)
        room.part(f"{name}_tie", (depth * 0.72, width * 0.72, 0.04),
                  (x, y, height * 0.88), room.straw)


def sack_stack(room, name, at, count=3):
    """A leaning cluster of sacks. One piece, not three."""
    x, y = at
    offsets = ((0.0, 0.0, 0.0), (0.22, 0.35, 0.25), (-0.20, -0.32, -0.35))
    with room.piece(name):
        for index in range(min(count, len(offsets))):
            dx, dy, rot = offsets[index]
            sack(room, f"{name}_{index}", (x + dx, y + dy), rotation=rot)


# ---------------------------------------------------------------------------
# The wall itself
# ---------------------------------------------------------------------------

def azulejo_dado(room, *, height=1.15, y0=None, y1=None, proud=0.02,
                 margin=0.06):
    """The tiled band along the back wall, broken around every opening.

    Waist-high, and only ever a band. A whole wall of azulejo reads as a church
    or a station, not a room somebody lives in.

    Tiling is applied to a WALL, so it stops at each doorway and starts again
    on the far side. Running one band across the openings makes the doors look
    painted on; `room.openings` (recorded by `Interior.back_wall`) is the same
    list the wall itself was built from, so the two can never disagree.
    """
    y0 = -room.half_width if y0 is None else y0
    y1 = room.half_width if y1 is None else y1
    x = room.back_x - proud / 2.0

    # Only openings that actually reach into the band interrupt it; a window
    # sill well above the dado does not.
    blockers = sorted((max(y0, oy0 - margin), min(y1, oy1 + margin))
                      for oy0, oy1, oz0, _oz1 in room.openings
                      if oz0 < height and oy1 > y0 and oy0 < y1)

    cursor, spans = y0, []
    for start, end in blockers:
        if start > cursor:
            spans.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < y1:
        spans.append((cursor, y1))

    with room.piece("azulejo_dado"):
        for index, (a, b) in enumerate(spans):
            if b - a < 0.05:
                continue
            room.part(f"azulejo_dado_{index}", (proud, b - a, height),
                      (x, (a + b) / 2.0, height / 2.0), room.azulejo)
            room.part(f"azulejo_rail_{index}", (proud + 0.04, b - a, 0.06),
                      (x - 0.01, (a + b) / 2.0, height + 0.03), room.wood)


def window_dressing(room, name, y0, y1, z0, z1, *, grille=True, shutters=True):
    """An iron grille over the opening, and shutters folded back beside it."""
    x = room.back_x - 0.04
    cy = (y0 + y1) / 2.0
    with room.piece(name):
        if grille:
            for index in range(3):
                gy = y0 + (y1 - y0) * (index + 1) / 4.0
                room.part(f"{name}_bar_{index}", (0.04, 0.035, z1 - z0),
                          (x, gy, (z0 + z1) / 2.0), room.iron)
            room.part(f"{name}_bar_mid", (0.04, y1 - y0, 0.035),
                      (x, cy, (z0 + z1) / 2.0), room.iron)
        if shutters:
            span = y1 - y0
            for index, side in enumerate((-1.0, 1.0)):
                room.part(f"{name}_shutter_{index}",
                          (0.05, span * 0.34, z1 - z0),
                          (x - 0.1, cy + side * (span * 0.5 + span * 0.17),
                           (z0 + z1) / 2.0), room.wood)


def door_frame(room, name, lo, hi, height, *, wall="back", jamb=0.2, proud=0.06):
    """A cut-stone surround (*cantaria*) for a door.

    `lo`/`hi` span the opening along its wall: Y for the back wall, X for a
    side wall (`wall="-y"` or `"+y"`, the end walls of a long hall). Pair it
    with the same opening used by `back_wall`/`doorway` or
    `side_walls`/`side_doorway`. A colonial door is a dark panelled leaf in a
    limestone frame set into limewash: the frame is what makes an opening
    read as a door and not a hole. Jambs, a lintel with a keystone, a sill.
    """
    if wall not in ("back", "-y", "+y"):
        raise ValueError(f"door_frame {name!r}: wall must be back, -y or +y")
    mid = (lo + hi) / 2.0
    width = hi - lo + jamb * 2.0
    if wall == "back":
        face, depth_axis = room.back_x - proud / 2.0, 0
        inward = -1.0
    else:
        sign = -1.0 if wall == "-y" else 1.0
        face, depth_axis = sign * (room.half_width - proud / 2.0), 1
        inward = -sign

    def place(along, across_offset, size_along, size_across, size_z, z):
        # Build in (along-the-wall, out-of-the-wall) terms, then map to X/Y.
        across = face + across_offset
        if depth_axis == 0:
            return (size_across, size_along, size_z), (across, along, z)
        return (size_along, size_across, size_z), (along, across, z)

    with room.piece(name):
        for index, edge in enumerate((lo - jamb / 2.0, hi + jamb / 2.0)):
            size, at = place(edge, 0.0, jamb, proud, height, height / 2.0)
            room.part(f"{name}_jamb_{index}", size, at, room.stone)
        size, at = place(mid, 0.0, width, proud, jamb * 1.2, height + jamb * 0.6)
        room.part(f"{name}_lintel", size, at, room.stone)
        size, at = place(mid, inward * 0.015, jamb * 0.9, proud + 0.03, jamb * 1.5,
                         height + jamb * 0.75)
        room.part(f"{name}_keystone", size, at, room.stone)
        size, at = place(mid, -inward * 0.13, width, 0.3, 0.04, 0.02)
        room.part(f"{name}_sill", size, at, room.stone)


def stair(room, name, *, y, x_start, steps=7, rise=0.19, run=0.3, width=1.5,
          direction=-1.0):
    """A flight of steps going DOWN, away from the floor plane.

    The way out of a storey. `direction` is the axis the flight travels:
    -1 steps toward the camera, +1 steps away from it. At this camera a flight
    running toward the viewer disappears under the status menu almost at once,
    so a visible stair down normally runs AWAY, through an opening.
    """
    with room.piece(name):
        for index in range(steps):
            top = -rise * index
            x = x_start + direction * run * index
            room.part(f"{name}_tread_{index}", (run, width, rise + 0.02),
                      (x, y, top - (rise + 0.02) / 2.0), room.wood)
    return x_start + direction * run * (steps - 1), -rise * (steps - 1)


# ---------------------------------------------------------------------------
# Shop and bakery
# ---------------------------------------------------------------------------

def counter(room, name, at, *, length=1.8, width=0.68, height=0.88, panels=3,
            top_mat=None, body_mat=None, panel_mat=None):
    """A merchant shop counter (*balcao*): heavy dark timber carcass, recessed
    front panelling, overhanging top slab and a plinth.

    `top_mat` gives the counter a stone slab instead of a timber top. Worth
    reaching for in a shop: a dark carcass with a dark top is one unbroken mass
    across the middle of the frame, and anything standing on it disappears.
    A limestone top is also what a counter that gets scrubbed daily is made of.
    """
    x, y = at
    with room.piece(name):
        room.part(f"{name}_carcass",
                  (width * 0.88, length * 0.94, height),
                  (x, y, height / 2.0), body_mat or room.wood)
        room.part(f"{name}_top", (width, length, 0.08),
                  (x, y, height + 0.04), top_mat or room.wood)
        room.part(f"{name}_plinth", (width * 0.92, length * 0.96, 0.10),
                  (x, y, 0.05), room.wood)
        # Panels face -X, toward the customer and the camera.
        panel_w = (length * 0.8) / panels
        front_x = x - (width * 0.88) / 2.0 - 0.015
        for index in range(panels):
            py = y - (length * 0.8) / 2.0 + panel_w * (index + 0.5)
            room.part(f"{name}_panel_{index}",
                      (0.03, panel_w * 0.82, height * 0.58),
                      (front_x, py, height * 0.52), panel_mat or room.wood)


def bread_oven(room, name, at, *, length=1.5, depth=1.3, height=1.6):
    """A masonry wood-fired bread oven (*forno a lenha*).

    Thick stone base with a firewood niche under it, a clay baking vault over
    that, an open mouth showing the ember bed, and a terracotta flue. The
    embers are emissive and want a `room.light` beside them.
    """
    x, y = at
    base_h = 0.72
    with room.piece(name):
        room.part(f"{name}_base", (depth, length, base_h),
                  (x, y, base_h / 2.0), room.stone)
        room.part(f"{name}_log_niche",
                  (depth * 0.7, length * 0.5, base_h * 0.65),
                  (x - depth * 0.16, y, base_h * 0.35), room.whitewash)
        for index, offset in enumerate((-0.18, 0.0, 0.18)):
            room.part(f"{name}_fuel_log_{index}", (depth * 0.55, 0.12, 0.10),
                      (x - depth * 0.15, y + offset, 0.08), room.wood)

        dome_h = height - base_h
        room.part(f"{name}_dome", (depth * 0.92, length * 0.92, dome_h),
                  (x, y, base_h + dome_h / 2.0), room.terracotta)

        mouth_w = length * 0.44
        mouth_h = dome_h * 0.62
        mouth_x = x - (depth * 0.92) / 2.0 - 0.02
        room.part(f"{name}_mouth_frame",
                  (0.08, mouth_w + 0.16, mouth_h + 0.14),
                  (mouth_x + 0.02, y, base_h + mouth_h / 2.0 + 0.08),
                  room.stone)
        room.part(f"{name}_embers", (0.35, mouth_w * 0.85, 0.12),
                  (mouth_x + 0.22, y, base_h + 0.06), room.embers)

        chimney_h = 1.6
        room.part(f"{name}_chimney", (0.32, 0.32, chimney_h),
                  (x + depth * 0.25, y, height + chimney_h / 2.0),
                  room.terracotta)


def bread_basket(room, name, at, *, radius=0.22, height=0.14, loaves=None):
    """A woven basket of crusty loaves (*broas*)."""
    x, y = at
    profile = ((0.80, 0.0), (1.05, 0.5 * height), (1.18, height))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius), profile, mat=room.straw)
        loaf_mat = loaves or room.bread
        for index, (dx, dy, size, lift) in enumerate((
                (-0.06, -0.05, 0.16, 0.04),
                (0.07, 0.04, 0.15, 0.03),
                (-0.02, 0.08, 0.14, 0.05))):
            room.part(f"{name}_loaf_{index}", (size, size, size * 0.68),
                      (x + dx, y + dy, height + lift), loaf_mat)


def peel(room, name, at, *, length=1.75, angle_deg=14.0):
    """A baker's peel (*pa de forno*), leaning against the wall or the oven."""
    x, y = at
    rad = math.radians(angle_deg)
    with room.piece(name):
        room.part(f"{name}_handle", (0.05, 0.05, length),
                  (x + math.sin(rad) * length * 0.45, y,
                   math.cos(rad) * length * 0.5),
                  room.wood, rotation=(0.0, rad, 0.0))
        room.part(f"{name}_blade", (0.34, 0.28, 0.03), (x, y, 0.16), room.wood)


def demijohn(room, name, at, *, height=0.52, radius=0.18):
    """A wicker-cased glass demijohn (*garrafao*) for oil or wine."""
    x, y = at
    profile = ((0.65, 0.0), (1.1, 0.35 * height), (0.95, 0.75 * height),
               (0.35, 0.88 * height), (0.38, height))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius), profile, mat=room.straw)
        room.part(f"{name}_cork", (0.09, 0.09, 0.08), (x, y, height + 0.03),
                  room.wood)


def scales(room, name, at, *, height=0.42, width=0.38):
    """A tabletop balance (*balanca*) for weighing dry goods and coin."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_base", (0.16, 0.16, 0.04), (x, y, 0.02), room.iron)
        room.part(f"{name}_pillar", (0.04, 0.04, height), (x, y, height / 2.0),
                  room.iron)
        room.part(f"{name}_beam", (0.03, width, 0.03), (x, y, height - 0.02),
                  room.bronze)
        for index, side in enumerate((-1.0, 1.0)):
            pan_y = y + side * (width / 2.0 - 0.04)
            room.part(f"{name}_string_{index}", (0.015, 0.015, height * 0.45),
                      (x, pan_y, height * 0.65), room.iron)
            room.part(f"{name}_pan_{index}", (0.12, 0.12, 0.02),
                      (x, pan_y, height * 0.42), room.bronze)


def wax_bench(room, name, at, *, length=1.6, width=0.64, height=0.78):
    """The candle bench: a wax tray, a dipping frame, and finished lanterns.

    Alicia is scraping wax from a tray when the player finds her during the
    Vigil, and the lantern she hides behind the counter bears no human name.
    So the bakery is also where St. Maria's lanterns are made -- which is not a
    coincidence but an economy: the oven is already hot, and rendering wax
    wants exactly the heat that is otherwise going up the flue.

    Faces the camera: the tray and the taper row read from -X.
    """
    x, y = at
    with room.piece(name):
        room.part(f"{name}_top", (width, length, 0.07), (x, y, height),
                  room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.14),
                 y + dy * (length - 0.14), 0.08, height - 0.035, room.wood)

        # The tray, with the wax slab still in it and a scraper laid across.
        tray_y = y - length * 0.22
        room.part(f"{name}_tray", (width * 0.72, length * 0.42, 0.06),
                  (x, tray_y, height + 0.06), room.iron)
        room.part(f"{name}_wax_slab", (width * 0.6, length * 0.34, 0.05),
                  (x, tray_y, height + 0.08), room.straw)
        room.part(f"{name}_scraper_blade", (0.16, 0.05, 0.015),
                  (x - 0.06, tray_y + length * 0.2, height + 0.12), room.iron)
        room.part(f"{name}_scraper_grip", (0.05, 0.05, 0.14),
                  (x - 0.06, tray_y + length * 0.28, height + 0.13),
                  room.wood, rotation=(1.2, 0.0, 0.0))

        # The dipping frame: uprights, a crossbar, and the tapers hanging in
        # pairs off it. This is the piece's silhouette and it wants to be
        # legible against the whitewash, so the tapers hang clear of the top.
        frame_y = y + length * 0.24
        bar_z = height + 0.72
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_frame_post_{index}",
                      (0.06, 0.06, bar_z - height),
                      (x, frame_y + side * length * 0.2,
                       height + (bar_z - height) / 2.0), room.wood)
        room.part(f"{name}_frame_bar", (0.05, length * 0.46, 0.05),
                  (x, frame_y, bar_z), room.wood)
        for index in range(5):
            ty = frame_y - length * 0.18 + index * (length * 0.09)
            drop = 0.30 if index % 2 else 0.34
            room.part(f"{name}_taper_{index}", (0.035, 0.035, drop),
                      (x, ty, bar_z - 0.03 - drop / 2.0), room.straw)
            room.part(f"{name}_wick_{index}", (0.012, 0.012, 0.05),
                      (x, ty, bar_z - 0.03), room.charcoal)

        # Two finished lantern frames on the under-shelf, waiting for names.
        room.part(f"{name}_shelf", (width - 0.14, length - 0.14, 0.04),
                  (x, y, 0.24), room.wood)
        for index, offset in enumerate((-length * 0.22, length * 0.14)):
            ly = y + offset
            room.part(f"{name}_lantern_body_{index}", (0.16, 0.16, 0.22),
                      (x, ly, 0.37), room.iron)
            room.part(f"{name}_lantern_top_{index}", (0.20, 0.20, 0.04),
                      (x, ly, 0.50), room.iron)


def cloth_bundle(room, name, at, *, radius=0.17, height=0.24, rotation=0.0):
    """Goods tied into a cloth, ready to be carried (*embrulho*).

    Alicia ties bread, cheese and a bruised pear into a cloth for Laura, and
    the cloth comes back folded into a perfect square. A shop where everything
    is still on a shelf has not sold anything yet; a bundle is a transaction
    that has already happened.
    """
    x, y = at
    profile = ((0.55, 0.0), (1.0, height * 0.34), (0.82, height * 0.72),
               (0.30, height * 0.92))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius * 0.92), profile,
                  mat=room.cloth, sides=8, rotation=rotation)
        room.part(f"{name}_knot", (radius * 0.7, radius * 0.7, height * 0.22),
                  (x, y, height * 0.98), room.cloth,
                  rotation=(0.0, 0.0, rotation + 0.5))
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_corner_{index}",
                      (radius * 0.34, radius * 0.34, height * 0.30),
                      (x + side * radius * 0.30, y + side * radius * 0.22,
                       height * 1.06), room.cloth,
                      rotation=(0.0, side * 0.6, rotation))


def stock_shelf(room, name, at, *, length=1.9, depth=0.42, height=2.05,
                tiers=4):
    """An open stock rack, loaded to the top (*prateleira*).

    "Watching people leave with full bags... it means they might come back."
    A shop reads as a shop because of VOLUME, not because of three
    representative props, and a rack is the cheapest volume in this
    vocabulary. Stock is graded by tier the way a real shop grades it: heavy
    and dull below, small and valuable at eye level, overflow above the reach.
    """
    x, y = at
    with room.piece(name):
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_upright_{index}", (depth, 0.08, height),
                      (x, y + side * (length / 2.0 - 0.04), height / 2.0),
                      room.wood)
        room.part(f"{name}_back", (0.04, length, height),
                  (x + depth / 2.0 - 0.02, y, height / 2.0), room.wood)

        for tier in range(tiers):
            z = 0.30 + tier * (height - 0.42) / max(tiers - 1, 1)
            room.part(f"{name}_board_{tier}", (depth, length, 0.05),
                      (x, y, z), room.wood)
            # Deterministic, and deliberately not uniform: a shelf of evenly
            # spaced identical boxes reads as a texture, not as stock.
            slots = 5 if tier % 2 else 4
            for slot in range(slots):
                sy = y - length * 0.40 + slot * (length * 0.80
                                                 / max(slots - 1, 1))
                phase = (tier * 7 + slot * 3) % 5
                with room.surface(z + 0.025):
                    if tier == 0:
                        if slot % 2 == 0:
                            sack(room, f"{name}_sack_{tier}_{slot}", (x, sy),
                                 width=0.30, depth=0.26, height=0.34,
                                 rotation=0.2 * phase)
                        else:
                            room.part(f"{name}_crate_{tier}_{slot}",
                                      (depth * 0.7, 0.30, 0.26),
                                      (x, sy, 0.13), room.wood)
                    elif tier == tiers - 1:
                        room.part(f"{name}_stack_{tier}_{slot}",
                                  (depth * 0.62, 0.24, 0.16 + 0.03 * phase),
                                  (x, sy, 0.08 + 0.015 * phase), room.cloth)
                    elif phase % 2:
                        jar(room, f"{name}_jar_{tier}_{slot}", (x, sy),
                            height=0.20 + 0.03 * (phase % 3), radius=0.085,
                            mat=room.crock)
                    else:
                        room.part(f"{name}_tin_{tier}_{slot}",
                                  (0.16, 0.15, 0.19), (x, sy, 0.095),
                                  room.bronze)


def water_stand(room, name, at, *, height=0.55, radius=0.28):
    """A water crock on a stand, with a dipper and a cup (*talha de agua*).

    "Please drink water before you descend. People return looking like they
    forgot they have bodies." It is the first thing Alicia says to the player
    and the only free thing in the shop, so it stands where a customer can
    reach it rather than behind the counter.
    """
    x, y = at
    # Squat and wide-shouldered, not tall and ovoid. The first proportions
    # rendered as a large smooth egg on a stick, and every review of that pass
    # asked what it was before it asked anything else about the shop.
    profile = ((0.45, 0.0), (1.0, radius * 0.8), (0.94, radius * 1.5),
               (0.60, radius * 1.9), (0.48, radius * 2.05))
    with room.piece(name):
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * 0.34, y + dy * 0.34,
                 0.07, height, room.wood)
        room.part(f"{name}_top", (0.52, 0.52, 0.06), (x, y, height + 0.03),
                  room.wood)
        with room.surface(height + 0.06):
            # Terracotta, not `crock`. A water talha is unglazed fired clay;
            # bound to the bone-white crock material it rendered as a large
            # pale ovoid on a stand, and two independent reviews called it an
            # unexplained white blob before anyone called it a water jar.
            _revolved(room, f"{name}_crock", (x, y), (radius, radius), profile,
                      mat=room.terracotta, sides=10)
        # The dipper hangs off the rim by its handle, which is what says the
        # water is for drinking rather than for the dough.
        room.part(f"{name}_dipper_bowl", (0.13, 0.13, 0.07),
                  (x - radius * 0.9, y, height + 0.42), room.bronze)
        room.part(f"{name}_dipper_handle", (0.04, 0.04, 0.26),
                  (x - radius * 0.9, y, height + 0.56), room.wood,
                  rotation=(0.0, 0.35, 0.0))
        room.part(f"{name}_cup", (0.10, 0.10, 0.09),
                  (x + 0.06, y + 0.30, height + 0.11), room.crock)


# ---------------------------------------------------------------------------
# Forge
# ---------------------------------------------------------------------------

def forge(room, name, at, *, length=1.8, depth=1.1, height=0.86,
          chimney_h=2.3):
    """A masonry forge hearth (*forja*): stone body, a charcoal bed with
    incandescent coke, an iron hood and a flue.

    The ember bed is emissive but casts nothing on its own -- give it a
    `room.light` so the shadows in the room come from the fire that motivates
    them.
    """
    x, y = at
    with room.piece(name):
        room.part(f"{name}_masonry", (depth, length, height),
                  (x, y, height / 2.0), room.stone)
        room.part(f"{name}_rim_front", (0.14, length + 0.06, 0.10),
                  (x - depth / 2.0 + 0.07, y, height + 0.05), room.stone)
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_rim_side{index}", (depth, 0.14, 0.10),
                      (x, y + side * (length / 2.0 - 0.07), height + 0.05),
                      room.stone)

        room.part(f"{name}_charcoal", (depth * 0.78, length * 0.72, 0.10),
                  (x + 0.05, y, height + 0.02), room.charcoal)

        # The fire has to be seen from a LEVEL lens 18 metres away. A flat
        # ember bed lying on top of the hearth is a horizontal plane viewed
        # edge-on from there: it lights the room and is itself invisible, so
        # the forge read as a warm patch on a wall with no fire in it. The
        # coals are therefore heaped PROUD of the rim, and carry a front face
        # square to the camera. This is also what a working fire looks like --
        # coke is banked into a mound over the tuyere, not raked flat.
        mound_h = 0.30
        room.part(f"{name}_fire_bed", (depth * 0.62, length * 0.58, mound_h),
                  (x + 0.03, y, height + mound_h / 2.0), room.embers)
        room.part(f"{name}_fire_crown", (depth * 0.34, length * 0.32, 0.16),
                  (x + 0.03, y, height + mound_h + 0.05), room.embers)
        # Unburnt coke banked around the hot centre: the dark shoulder that
        # makes the bright core read as a CORE rather than as a glowing box.
        for index, (dx, dy) in enumerate(((-0.30, -0.34), (-0.30, 0.34),
                                          (0.26, -0.30), (0.26, 0.30))):
            room.part(f"{name}_coke_{index}",
                      (depth * 0.22, length * 0.22, 0.17),
                      (x + 0.03 + dx * depth * 0.5, y + dy * length * 0.5,
                       height + 0.09), room.charcoal,
                      rotation=(0.0, 0.0, 0.6 * index))

        # The hood, built as a taper rather than a slab. A single box hanging
        # over the fire reads as a black bar across the frame; a gathering
        # hood catches the firelight on its underside and its throat, which is
        # what puts the fire's own light back into the top of the picture.
        hood_z = height + 1.1
        room.part(f"{name}_hood_skirt", (depth * 0.98, length * 0.98, 0.10),
                  (x + 0.05, y, hood_z - 0.24), room.iron)
        room.part(f"{name}_hood", (depth * 0.85, length * 0.85, 0.44),
                  (x + 0.05, y, hood_z), room.iron)
        room.part(f"{name}_hood_throat", (depth * 0.52, length * 0.52, 0.26),
                  (x + 0.05, y, hood_z + 0.34), room.iron)
        room.part(f"{name}_chimney", (0.42, 0.42, chimney_h),
                  (x + depth * 0.22, y, hood_z + chimney_h / 2.0 + 0.25),
                  room.stone)


def anvil(room, name, at, *, horn_len=0.78, width=0.26, height=0.44,
          stump_h=0.46):
    """An anvil (*bigorna*) on a banded hardwood stump (*cepo*)."""
    x, y = at
    stump_dia = max(width * 1.8, 0.48)
    with room.piece(name):
        room.part(f"{name}_stump", (stump_dia, stump_dia, stump_h),
                  (x, y, stump_h / 2.0), room.wood)
        room.part(f"{name}_stump_band",
                  (stump_dia + 0.04, stump_dia + 0.04, 0.06),
                  (x, y, stump_h * 0.75), room.iron)

        az = stump_h
        room.part(f"{name}_foot", (width * 1.15, horn_len * 0.62, 0.08),
                  (x, y, az + 0.04), room.forge_scale)
        room.part(f"{name}_waist",
                  (width * 0.65, horn_len * 0.42, height * 0.45),
                  (x, y, az + 0.08 + height * 0.225), room.forge_scale)
        room.part(f"{name}_table", (width, horn_len * 0.65, height * 0.42),
                  (x, y + horn_len * 0.08, az + height * 0.78), room.iron)
        room.part(f"{name}_horn",
                  (width * 0.68, horn_len * 0.38, height * 0.32),
                  (x, y - horn_len * 0.38, az + height * 0.78), room.iron)


def quench_tub(room, name, at, *, radius=0.32, height=0.56):
    """A staved slack tub (*tina de tempera*) with iron hoops, standing full."""
    x, y = at
    profile = ((0.90, 0.0), (1.08, 0.5 * height), (1.14, height))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius), profile, mat=room.wood,
                  sides=10)
        for index, level in enumerate((0.25, 0.82)):
            room.part(f"{name}_hoop_{index}", (radius * 2.3, radius * 2.3,
                                               0.04),
                      (x, y, height * level), room.iron)
        room.part(f"{name}_water", (radius * 1.9, radius * 1.9, 0.02),
                  (x, y, height * 0.90), room.iron)


def bellows(room, name, at, *, length=1.1, width=0.52, height=0.38):
    """Leather and hardwood bellows (*fole*), nozzle pointing into the forge."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_board_bot", (length * 0.85, width, 0.05),
                  (x, y, 0.08), room.wood)
        room.part(f"{name}_board_top", (length * 0.85, width, 0.05),
                  (x, y, height), room.wood)
        room.part(f"{name}_leather",
                  (length * 0.78, width * 0.92, height - 0.12),
                  (x, y, height / 2.0 + 0.02), room.cloth)
        room.part(f"{name}_pipe", (length * 0.45, 0.08, 0.08),
                  (x - length * 0.55, y, 0.18), room.iron)
        room.part(f"{name}_handle", (0.55, 0.06, 0.06),
                  (x + length * 0.55, y, height + 0.08), room.wood)


def weapon_rack(room, name, at, *, length=1.65, depth=0.45, height=1.75):
    """A display rack of forged blades, with a shield blank leaning on it."""
    x, y = at
    with room.piece(name):
        for index, side in enumerate((-1.0, 1.0)):
            py = y + side * (length / 2.0 - 0.06)
            room.part(f"{name}_post_{index}", (0.09, 0.09, height),
                      (x, py, height / 2.0), room.wood)
            room.part(f"{name}_foot_{index}", (depth, 0.09, 0.08),
                      (x, py, 0.04), room.wood)
        for index, level in enumerate((height * 0.35, height * 0.85)):
            room.part(f"{name}_rail_{index}", (0.06, length, 0.08),
                      (x, y, level), room.wood)

        for index, offset in enumerate((-0.45, -0.15, 0.15)):
            sy = y + offset
            room.part(f"{name}_blade_{index}", (0.03, 0.07, 0.95),
                      (x - 0.04, sy, height * 0.58), room.iron)
            room.part(f"{name}_guard_{index}", (0.05, 0.22, 0.04),
                      (x - 0.04, sy, height * 0.58 + 0.48), room.iron)
            room.part(f"{name}_grip_{index}", (0.03, 0.03, 0.20),
                      (x - 0.04, sy, height * 0.58 + 0.60), room.wood)

        room.part(f"{name}_shield", (0.05, 0.48, 0.65),
                  (x - 0.08, y + length / 2.0 - 0.22, height * 0.42),
                  room.wood, rotation=(0.0, 0.12, 0.0))
        room.part(f"{name}_shield_boss", (0.09, 0.12, 0.12),
                  (x - 0.12, y + length / 2.0 - 0.22, height * 0.42),
                  room.iron)


def tool_rail(room, name, *, y, z, length=1.3):
    """A wall batten hung with tongs and hammers."""
    x = room.back_x - 0.06
    with room.piece(name):
        room.part(f"{name}_batten", (0.04, length, 0.10), (x, y, z), room.wood)
        for index, offset in enumerate((-0.42, -0.14, 0.14, 0.42)):
            ty = y + offset
            room.part(f"{name}_peg_{index}", (0.16, 0.02, 0.02),
                      (x - 0.08, ty, z), room.iron)
            if index % 2 == 0:
                room.part(f"{name}_hammer_handle_{index}", (0.03, 0.03, 0.45),
                          (x - 0.12, ty, z - 0.24), room.wood)
                room.part(f"{name}_hammer_head_{index}", (0.08, 0.14, 0.06),
                          (x - 0.12, ty, z - 0.45), room.iron)
            else:
                room.part(f"{name}_tongs_{index}", (0.04, 0.06, 0.55),
                          (x - 0.12, ty, z - 0.28), room.iron)


def ingot_stack(room, name, at, rows=3, cols=2):
    """A stack of cast iron and bronze ingots."""
    x, y = at
    ingot_l, ingot_w, ingot_h = 0.32, 0.14, 0.07
    with room.piece(name):
        for row in range(rows):
            for col in range(cols):
                ix = x + (col - cols / 2.0 + 0.5) * (ingot_w + 0.02)
                iy = y + (row % 2) * 0.04
                mat = room.bronze if (row + col) % 3 == 0 else room.iron
                room.part(f"{name}_ingot_{row}_{col}",
                          (ingot_w, ingot_l, ingot_h),
                          (ix, iy, row * ingot_h + ingot_h / 2.0), mat)


def workbench(room, name, at, *, length=1.65, width=0.68, height=0.86):
    """A smith's workbench with a bench vice and a tool shelf under it."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_top", (width, length, 0.09), (x, y, height),
                  room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.16),
                 y + dy * (length - 0.16), 0.10, height - 0.045, room.wood)
        room.part(f"{name}_shelf", (width - 0.16, length - 0.16, 0.04),
                  (x, y, 0.22), room.wood)
        room.part(f"{name}_vice_base", (0.16, 0.16, 0.10),
                  (x - width / 2.0 + 0.08, y - length / 2.0 + 0.12,
                   height + 0.09), room.iron)
        room.part(f"{name}_vice_jaw", (0.08, 0.18, 0.12),
                  (x - width / 2.0 + 0.04, y - length / 2.0 + 0.12,
                   height + 0.18), room.iron)


def scrap_heap(room, name, at, *, spread=0.9, layers=7):
    """Salvage waiting to be decided about: flattened lantern frames, and
    whatever the Labyrinth failed to digest.

    "She is hammering old lantern frames flat for reuse." Laura's stock is not
    bought, it is recovered, and this is the only disorder her room is allowed
    -- everything else she has already made a decision about. Flat plates lying
    at angles read as a heap at this camera where a mound of boxes does not.
    """
    x, y = at
    with room.piece(name):
        for index in range(layers):
            phase = (index * 5) % 7
            dx = (phase - 3) * spread * 0.09
            dy = (((index * 3) % 5) - 2) * spread * 0.16
            plate = 0.34 + 0.05 * (phase % 3)
            room.part(f"{name}_plate_{index}", (plate, plate * 0.72, 0.025),
                      (x + dx, y + dy, 0.02 + index * 0.022),
                      room.forge_scale if index % 3 else room.iron,
                      rotation=(0.0, 0.05 * (phase - 3), 0.42 * index))
        # Two frames not yet flattened, still recognisably lanterns.
        for index, (dx, dy, rot) in enumerate(((-0.28, 0.34, 0.5),
                                               (0.22, -0.38, -0.3))):
            room.part(f"{name}_frame_{index}", (0.17, 0.17, 0.24),
                      (x + dx, y + dy, 0.12), room.iron,
                      rotation=(0.35, 0.0, rot))
        room.part(f"{name}_bar", (0.06, 0.72, 0.04),
                  (x - spread * 0.34, y + 0.1, 0.03), room.iron,
                  rotation=(0.0, 0.0, 0.8))


def grindstone(room, name, at, *, radius=0.34, height=0.74, rotation=0.0):
    """A treadle grindstone in its frame, over a water trough (*mo de afiar*).

    The wheel is the only curve in this vocabulary that reads in ELEVATION
    rather than in plan -- every other radial piece is a jar seen end-on. Next
    to an anvil and a rack of straight bars that is worth a great deal, and it
    is also the fixture that says a smith SHARPENS as well as forges.
    """
    x, y = at
    axle_z = height + radius * 0.35
    with room.piece(name):
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_post_{index}", (0.10, 0.10, axle_z),
                      (x, y + side * (radius + 0.14), axle_z / 2.0), room.wood)
            room.part(f"{name}_foot_{index}", (0.62, 0.12, 0.09),
                      (x, y + side * (radius + 0.14), 0.045), room.wood)
        room.part(f"{name}_rail", (0.09, radius * 2 + 0.4, 0.09),
                  (x, y, axle_z), room.wood)

        # The wheel: a revolved disc stood on edge by the tilt.
        with room.surface(axle_z):
            _revolved(room, f"{name}_wheel", (x, y), (radius, radius),
                      ((0.30, -0.055), (0.95, -0.045), (1.0, 0.0),
                       (0.95, 0.045), (0.30, 0.055)),
                      mat=room.stone, sides=12, rotation=rotation,
                      tilt=math.tau / 4.0)
        room.part(f"{name}_axle", (0.06, radius * 2 + 0.3, 0.06),
                  (x, y, axle_z), room.iron)
        room.part(f"{name}_crank", (0.06, 0.06, 0.22),
                  (x, y + radius + 0.24, axle_z - 0.11), room.iron)
        room.part(f"{name}_crank_grip", (0.05, 0.14, 0.05),
                  (x, y + radius + 0.30, axle_z - 0.22), room.wood)

        # The trough the wheel dips into. A dry grindstone burns the temper
        # out of an edge, so a stone without water is a smith who does not
        # know her trade.
        room.part(f"{name}_trough", (0.42, radius * 1.7, 0.20),
                  (x, y, height - radius * 0.62), room.wood)
        room.part(f"{name}_water", (0.34, radius * 1.5, 0.02),
                  (x, y, height - radius * 0.56), room.iron)


def fine_bench(room, name, at, *, length=1.15, width=0.52, height=0.92):
    """The precious-metal bench: high, small, and slung with a catch skin.

    "The gold is pure... untouched." Laura takes goldwork as well as blade
    work, and the two are not done at the same bench -- fine work is done
    SITTING, high, close to the eye, over a leather skin that catches every
    filing worth sweeping up. Putting that beside the anvil is what stops the
    forge reading as one generic hammering station.
    """
    x, y = at
    with room.piece(name):
        room.part(f"{name}_top", (width, length, 0.07), (x, y, height),
                  room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.12),
                 y + dy * (length - 0.12), 0.07, height - 0.035, room.wood)
        # The catch skin, sagging between the front rail and the bench.
        room.part(f"{name}_skin", (width * 0.86, length * 0.72, 0.03),
                  (x - width * 0.06, y, height - 0.30), room.cloth,
                  rotation=(0.0, 0.16, 0.0))
        room.part(f"{name}_skin_rail", (0.05, length * 0.72, 0.05),
                  (x - width / 2.0 - 0.06, y, height - 0.20), room.wood)

        # A pitch bowl on its ring, the peg the work is braced against, and a
        # row of small tools -- all small, because that is the whole point.
        room.part(f"{name}_peg", (0.20, 0.10, 0.06),
                  (x - width / 2.0 + 0.06, y - length * 0.24, height + 0.06),
                  room.wood)
        room.part(f"{name}_pitch_ring", (0.17, 0.17, 0.04),
                  (x, y + length * 0.16, height + 0.055), room.wood)
        room.part(f"{name}_pitch_bowl", (0.15, 0.15, 0.08),
                  (x, y + length * 0.16, height + 0.11), room.forge_scale)
        for index, offset in enumerate((-0.34, -0.26, -0.18)):
            room.part(f"{name}_tool_{index}", (0.03, 0.03, 0.20),
                      (x + width * 0.22, y + offset, height + 0.11),
                      room.iron, rotation=(0.0, 1.45, 0.0))
        room.part(f"{name}_box", (0.14, 0.20, 0.10),
                  (x + width * 0.18, y + length * 0.32, height + 0.09),
                  room.wood)


# ---------------------------------------------------------------------------
# Chapel
# ---------------------------------------------------------------------------

def altar(room, name, at, *, length=1.9, depth=0.8, height=1.0,
          retable_height=2.7, turn=0.0):
    """A limewashed block altar under a gilt-framed retable (*retabulo*).

    A colonial chapel's altar is masonry, not furniture: a whitewashed block
    with a stone slab (the *mensa*) overhanging it, a linen frontal hanging
    over the face that meets the congregation, and behind it a dark timber
    retable whose only gold is its frame. The centre of the retable is a deep
    recess with nothing in it -- what a place keeps there is the map's
    business, not the furnishing's.

    `at` is the footprint centre of the block; the retable stands behind it.
    The frontal faces -X; `turn=90` faces it -Y, down a hall seen side-on.
    """
    x, y = at
    slab = 0.09
    with room.piece(name, turn=turn, about=at):
        room.part(f"{name}_block", (depth, length, height - slab),
                  (x, y, (height - slab) / 2.0), room.whitewash)
        room.part(f"{name}_mensa", (depth + 0.12, length + 0.14, slab),
                  (x, y, height - slab / 2.0), room.stone)
        # The frontal hangs over the camera-facing (-X) face.
        room.part(f"{name}_frontal", (0.03, length * 0.82, height * 0.62),
                  (x - depth / 2.0 - 0.065, y, height - height * 0.31),
                  room.cloth)
        room.part(f"{name}_cloth", (depth + 0.04, length + 0.02, 0.02),
                  (x, y, height + 0.01), room.cloth)
        # Two bronze candlesticks at the ends of the mensa. The flames are
        # emissive and cast nothing; a map that lights them adds a light.
        for index, dy in enumerate((-length * 0.36, length * 0.36)):
            base = height + 0.02
            room.part(f"{name}_stick_foot_{index}", (0.14, 0.14, 0.04),
                      (x + 0.1, y + dy, base + 0.02), room.bronze)
            room.part(f"{name}_stick_{index}", (0.04, 0.04, 0.34),
                      (x + 0.1, y + dy, base + 0.21), room.bronze)
            room.part(f"{name}_candle_{index}", (0.045, 0.045, 0.2),
                      (x + 0.1, y + dy, base + 0.48), room.wax)
            room.part(f"{name}_flame_{index}", (0.035, 0.035, 0.06),
                      (x + 0.1, y + dy, base + 0.61), room.lamplight)

        rx = x + depth / 2.0 + 0.16
        width = length + 0.5
        room.part(f"{name}_retable", (0.16, width, retable_height),
                  (rx, y, retable_height / 2.0), room.wood)
        # The recess: a dark panel set back into the retable, framed in gilt.
        room.part(f"{name}_recess", (0.05, width * 0.34, retable_height * 0.36),
                  (rx - 0.06, y, retable_height * 0.62), room.charcoal)
        frame = 0.06
        cz = retable_height * 0.62
        hz = retable_height * 0.18 + frame / 2.0
        hy = width * 0.17 + frame / 2.0
        for index, dz in enumerate((-hz, hz)):
            room.part(f"{name}_gilt_h_{index}", (0.06, width * 0.34 + frame * 2,
                                                 frame),
                      (rx - 0.1, y, cz + dz), room.gilt)
        for index, dy in enumerate((-hy, hy)):
            room.part(f"{name}_gilt_v_{index}", (0.06, frame,
                                                 retable_height * 0.36),
                      (rx - 0.1, y + dy, cz), room.gilt)
        # The outer frame: two gilt pilasters and a cornice.
        for index, dy in enumerate((-width / 2.0 + 0.07, width / 2.0 - 0.07)):
            room.part(f"{name}_pilaster_{index}", (0.1, 0.12, retable_height),
                      (rx - 0.06, y + dy, retable_height / 2.0), room.gilt)
        room.part(f"{name}_cornice", (0.24, width + 0.12, 0.12),
                  (rx - 0.04, y, retable_height + 0.06), room.gilt)


def pew(room, name, at, *, length=2.4, depth=0.5, height=0.45, turn=0.0):
    """A heavy hardwood bench (*banco*) facing the altar (+X).

    Seen from the lane camera a pew shows its BACK, so the back rails and the
    end boards are what carry it: a congregation's seats read as a row of
    dark horizontals, not as chairs. The back is two rails with daylight
    between them and under the seat -- a solid back and full-height ends
    rendered as a row of black crates at native size.

    It faces +X; `turn=90` faces it +Y, so in a hall seen side-on the pews
    stand in rows across the lane and show their end boards. Those ends are
    low, with only a slender post carrying the back rail: as a foreground
    row in front of the player, full-height end boards were a wall of unlit
    slabs that hid everyone to the waist.
    """
    x, y = at
    back_x = x - depth / 2.0 + 0.03
    rail_z = height + 0.34
    with room.piece(name, turn=turn, about=at):
        room.part(f"{name}_seat", (depth, length, 0.06),
                  (x, y, height - 0.03), room.wood)
        room.part(f"{name}_apron", (0.04, length - 0.16, 0.08),
                  (back_x, y, height - 0.1), room.wood)
        room.part(f"{name}_back_low", (0.05, length, 0.1),
                  (back_x, y, height + 0.14), room.wood)
        room.part(f"{name}_rail", (0.09, length + 0.04, 0.07),
                  (back_x, y, rail_z), room.wood)
        for index, dy in enumerate((-length / 2.0 + 0.04, length / 2.0 - 0.04)):
            room.part(f"{name}_end_{index}", (depth * 0.8, 0.08, height + 0.08),
                      (x, y + dy, (height + 0.08) / 2.0), room.wood)
            room.part(f"{name}_post_{index}", (0.06, 0.07, rail_z - height),
                      (back_x, y + dy, (height + rail_z) / 2.0), room.wood)


def votive_stand(room, name, at, *, width=0.9, depth=0.34, height=0.95,
                 candles=7, lit=2):
    """An iron votive stand: a tray of candles, most of them burnt out.

    Cold wax is the point -- the stubs, the drips on the tray, the few still
    burning. `lit` candles get a flame; the rest are stubs of decreasing
    height. The flames are emissive and cast nothing, so a map that lights
    candles still places a `room.light` beside the stand.
    """
    x, y = at
    with room.piece(name):
        room.part(f"{name}_tray", (depth, width, 0.04),
                  (x, y, height), room.iron)
        room.part(f"{name}_lip", (depth + 0.03, width + 0.03, 0.03),
                  (x, y, height + 0.035), room.iron)
        for index, (dx, dy) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
            _leg(room, f"{name}_leg_{index}", x + dx * (depth / 2.0 - 0.03),
                 y + dy * (width / 2.0 - 0.03), 0.035, height, room.iron)
        room.part(f"{name}_stretcher", (0.03, width - 0.06, 0.03),
                  (x, y, height * 0.25), room.iron)
        # Spilled wax pooled on the tray.
        room.part(f"{name}_drip", (depth * 0.6, width * 0.7, 0.012),
                  (x, y, height + 0.026), room.wax)
        for index in range(candles):
            cy = y - width / 2.0 + width * (index + 0.5) / candles
            cx = x + (0.06 if index % 2 else -0.06)
            # Candles are drawn at 2-3 native px wide (~0.07 m at the lane
            # camera); thinner ones vanish into the iron below them.
            tall = 0.3 - 0.035 * ((index * 3) % candles)
            tall = max(tall, 0.07)
            room.part(f"{name}_candle_{index}", (0.07, 0.07, tall),
                      (cx, cy, height + 0.02 + tall / 2.0), room.wax)
            if index < lit:
                room.part(f"{name}_flame_{index}", (0.05, 0.05, 0.08),
                          (cx, cy, height + 0.02 + tall + 0.04),
                          room.lamplight)


def font(room, name, at, *, height=0.95, radius=0.27):
    """A holy-water font (*pia*): a stone basin on a short column.

    Radial, and placed by the door, where a visitor meets it first.
    """
    profile = ((0.55, 0.0), (0.55, 0.08), (0.24, 0.12), (0.2, 0.62 * height),
               (0.42, 0.72 * height), (1.0, 0.88 * height), (0.94, height))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius), profile, mat=room.plaster,
                  sides=10)


def mortar_tub(room, name, at, *, radius=0.24, height=0.3):
    """A wooden tub of lime mortar with a trowel across its rim.

    A repair in progress: the sign that somebody is mending the fabric of the
    place rather than it simply being old.
    """
    x, y = at
    profile = ((0.86, 0.0), (1.0, height * 0.85), (1.02, height))
    with room.piece(name):
        _revolved(room, f"{name}_tub", at, (radius, radius), profile,
                  mat=room.wood, sides=10)
        room.part(f"{name}_mortar", (radius * 1.7, radius * 1.7, 0.03),
                  (x, y, height * 0.82), room.whitewash)
        room.part(f"{name}_blade", (0.2, 0.11, 0.012),
                  (x + radius * 0.4, y, height + 0.012), room.iron,
                  rotation=(0.0, 0.0, 0.5))
        room.part(f"{name}_handle", (0.16, 0.035, 0.035),
                  (x - radius * 0.5, y - 0.07, height + 0.03), room.wood,
                  rotation=(0.0, 0.0, 0.5))
