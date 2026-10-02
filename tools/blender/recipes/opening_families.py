"""Shared, adjustable exterior door and window families.

Families keep silhouette and opening geometry while letting the receiver carry
fine joinery through the bake.  ``host.part`` is the one Blender emission seam;
the candidate courtyard and the measured Exterior vocabulary use this same
family builder.
"""


def door(host, name, lane_y, *, width=1.15, height=2.25, x=None,
         lintel=True, panels=0, frame=0.18, panel_material=None,
         source=False, retain_shape=False, base_z=0.0, receiver_collection=None):
    if min(width,height,frame) <= 0 or panels < 0:
        raise ValueError('Door dimensions must be positive and panel count nonnegative')
    base_x = host.back_x if x is None else float(x)
    cy = host.y(lane_y)
    objs = []

    def part(suffix, size, location, material):
        obj = host.part(f"{name}_{suffix}", size, (location[0],location[1],location[2]+base_z), material)
        if source:
            structural = retain_shape and suffix.startswith(("jamb", "threshold", "lintel"))
            obj["sr_bake_role"] = "both" if structural and receiver_collection is None else "source"
            if structural and receiver_collection is not None:
                box_receiver(obj, receiver_collection)
        objs.append(obj)
        return obj

    part("leaf", (0.12, width, height),
         (base_x - 0.015, cy, height / 2), host.wood)
    for side, tag in ((-1, "l"), (1, "r")):
        part(f"jamb_{tag}", (0.16, frame, height + 0.18),
             (base_x - 0.12, cy + side * (width / 2 + frame / 2),
              (height + 0.18) / 2), host.stone)
    part("threshold", (0.52, width + 0.42, 0.16),
         (base_x - 0.22, cy, 0.08), host.stone)
    if lintel:
        part("lintel", (0.26, width + 0.5, 0.24),
             (base_x - 0.16, cy, height + 0.12), host.stone)
        part("drip", (0.34, width + 0.68, 0.10),
             (base_x - 0.21, cy, height + 0.29), host.terracotta)
    # Panel count changes detail density without changing the reusable leaf.
    count = int(panels)
    for index in range(count):
        columns = 2 if count >= 4 and count % 2 == 0 else 1
        rows = count // columns
        z = height * (0.16 + 0.70 * ((index // columns) + 0.5) / rows)
        panel_h = height * 0.58 / rows
        panel_w = width * (0.36 if columns == 2 else 0.70)
        panel_y = cy + ((index % columns) - (columns-1)/2) * width * 0.46
        panel = part(f"panel_{index + 1}", (0.035, panel_w, panel_h),
                     (base_x - 0.09, panel_y, z), panel_material or host.wood)
        panel["sr_bake_detail"] = True
    part("escutcheon", (.025,.045,.12), (base_x-.10,cy+width*.33,height*.44),host.iron)
    part("handle", (.045,.13,.025), (base_x-.12,cy+width*.30,height*.44),host.iron)
    return objs


def window(host, name, lane_y, *, width=0.95, height=1.25, sill_z=1.15,
           x=None, shutters=True, grille=False, lit=False, frame=0.075,
           source=False, recess=0.0, retain_shape=False, shutter_panels=2,
           joinery_material=None, shutter_material=None):
    """Slender casement with pane divisions and panelled, hinged shutters.

    Retained jambs, sill and shutter leaves carry silhouette/parallax; fine rails,
    panels and hardware bake onto those surfaces. Recess is measured into the wall.
    """
    if min(width, height, frame) <= 0 or recess < 0 or shutter_panels < 1:
        raise ValueError('Opening dimensions must be positive and recess nonnegative')
    base_x = host.back_x if x is None else float(x)
    cy = host.y(lane_y)
    pane_material = host.window_glow if lit else host.glass
    joinery = joinery_material or host.wood
    panel_finish = shutter_material or getattr(host, "panel", joinery)
    objs = []

    def part(suffix, size, location, material, silhouette=False):
        obj = host.part(f"{name}_{suffix}", size, location, material)
        if source:
            obj["sr_bake_role"] = "both" if silhouette and retain_shape else "source"
        objs.append(obj)
        return obj

    face_x=base_x+recess
    part("pane", (0.08, width, height),
         (face_x - 0.015, cy, sill_z + height / 2), pane_material)
    for side, tag in ((-1, "l"), (1, "r")):
        part(f"jamb_{tag}", (recess+.16, frame, height+.12),
             (base_x+recess/2-.06,cy+side*(width/2+frame/2),sill_z+height/2),
             host.stone,True)
    part("head",(recess+.18,width+frame*2,.12),
         (base_x+recess/2-.06,cy,sill_z+height+.06),host.stone,True)
    part("sill",(.32+recess,width+frame*3,.10),
         (base_x+recess/2-.12,cy,sill_z-.05),host.stone,True)
    # A true narrow timber frame inside the masonry reveal.
    for side,tag in ((-1,'l'),(1,'r')):
        part(f"stile_{tag}",(.045,.055,height),
             (face_x-.075,cy+side*(width/2-.028),sill_z+height/2),joinery)
    for fraction,tag in ((0,'bottom'),(.58,'meeting'),(1,'top')):
        part(f"rail_{tag}",(.045,width,.055),
             (face_x-.075,cy,sill_z+.028+fraction*(height-.056)),joinery)
    part("mullion",(.055,.055,height),
         (face_x-.08,cy,sill_z+height/2),joinery)
    if shutters:
        leaf_w=width*.48
        for side,tag in ((-1,'l'),(1,'r')):
            leaf_y=cy+side*(width/2+leaf_w/2+.085)
            leaf_x=base_x-.115
            part(f"shutter_{tag}",(.075,leaf_w,height),
                 (leaf_x,leaf_y,sill_z+height/2),joinery,True)
            # Two inset panels, framed by slender rails: no solid featureless slab.
            for j in range(shutter_panels):
                panel_h=(height-.15)/shutter_panels-.055
                centre_z=sill_z+.075+(j+.5)*(height-.15)/shutter_panels
                part(f"shutter_{tag}_panel_{j}",(.014,leaf_w-.11,panel_h),
                     (leaf_x-.042,leaf_y,centre_z),panel_finish)
                for border in (-1,1):
                    part(f"shutter_{tag}_rail_{j}_{border}",(.025,leaf_w-.035,.035),
                         (leaf_x-.058,leaf_y,centre_z+border*(panel_h/2+.018)),joinery)
            for fraction in (.18,.82):
                part(f"hinge_{tag}_{fraction}",(.025,.025,.11),
                     (leaf_x-.060,cy+side*(width/2+.065),sill_z+height*fraction),host.iron)
    if grille:
        # Actual spaced iron bars, never an opaque plate filling the aperture.
        for j in range(1,5):
            part(f"grille_{j}",(.025,.025,height),
                 (base_x-.16,cy-width/2+j*width/5,sill_z+height/2),host.iron)
    return objs


def box_receiver(source, collection):
    """Keep a structural box while its bevels remain in the detailed source."""
    import bpy
    import mesh_export_geometry
    bpy.context.view_layer.update()
    # Bounding corners are object-local: copying the original transform also
    # preserves posed and parented frames without duplicating placement math.
    mesh = bpy.data.meshes.new(source.name + " receiver mesh")
    mesh.from_pydata([tuple(point) for point in source.bound_box], [],
        [(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(0,3,7,4),(1,5,6,2)])
    mesh.update(); mesh_export_geometry.prepare(mesh)
    for material in source.data.materials: mesh.materials.append(material)
    proxy = source.copy(); proxy.data = mesh; proxy.modifiers.clear()
    proxy.name = source.name + " target"; proxy["sr_bake_role"] = "receiver"
    proxy["sr_bake_source"] = True; proxy["sr_bake_preserve"] = True; proxy.hide_render = True
    collection.objects.link(proxy)
    return proxy
