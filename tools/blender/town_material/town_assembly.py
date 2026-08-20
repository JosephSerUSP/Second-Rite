"""Assemble one town attempt into the TH_* collections."""
from __future__ import annotations

import bpy

import materials as M
import proc_materials as P
from town_builder import (ACTION_X, GROUND_Z, STREET_Y, box, col, displace,
                          assign, put, uv_project, facade_panel,
                          displace_panel, uv_scale_panel)

PH = M.PH_DIR
GEN = M.GEN_DIR


def resolve_material(token, scale=1.0, bump=0.4, grime=0.15):
    """'lib:slug' / 'gen:id' / 'proc:name' -> a built material."""
    kind, _, ident = token.partition(":")
    if kind == "lib":
        return M.library_material(ident, scale=scale, bump=bump, grime=grime,
                                  name="LIB_%s_%g" % (ident, scale))
    if kind == "gen":
        return M.generated_material(ident, scale=scale, bump=bump, grime=grime,
                                    name="GEN_%s_%g" % (ident, scale))
    if kind == "proc":
        fn = {"stone_blocks": P.proc_stone_blocks, "plaster": P.proc_plaster,
              "cobblestone": P.proc_cobblestone, "wood": P.proc_wood,
              "roof_tile": P.proc_roof_tile, "metal": P.proc_metal}[ident]
        return fn(scale=scale, bump=bump, name="PROC_%s_%g" % (ident, scale))
    raise ValueError("unknown material token " + token)


def height_for(token):
    """The height map backing a token, for real TH_SOURCE displacement."""
    kind, _, ident = token.partition(":")
    if kind == "lib":
        p = PH / ident / "height.jpg"
    elif kind == "gen":
        p = GEN / (ident + "_height.png")
    else:
        return None
    return p if p.is_file() else None


def _anchor(name, x, y, z, kind):
    a = bpy.data.objects.new(name, None)
    a.empty_display_type = "ARROWS"
    a.location = (x, y, z)
    a["thestra_anchor"] = kind
    bpy.context.scene.collection.objects.link(a)
    return put(a, "TH_ANCHORS")


def _window_material(name, lit=False):
    """Window interior: near-black glass by day, warm emissive by night."""
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if lit:
        sh = nt.nodes.new("ShaderNodeEmission")
        sh.inputs["Color"].default_value = (1.0, 0.62, 0.28, 1.0)
        sh.inputs["Strength"].default_value = 2.2
        nt.links.new(sh.outputs["Emission"], out.inputs["Surface"])
    else:
        mixn = nt.nodes.new("ShaderNodeMixShader")
        sh = nt.nodes.new("ShaderNodeBsdfPrincipled")
        sh.inputs["Base Color"].default_value = (0.075, 0.070, 0.062, 1.0)
        sh.inputs["Roughness"].default_value = 0.30
        sh.inputs["Metallic"].default_value = 0.0
        glow = nt.nodes.new("ShaderNodeEmission")
        glow.inputs["Color"].default_value = (0.55, 0.48, 0.40, 1.0)
        glow.inputs["Strength"].default_value = 0.09
        mixn.inputs["Fac"].default_value = 0.35
        nt.links.new(sh.outputs["BSDF"], mixn.inputs[1])
        nt.links.new(glow.outputs["Emission"], mixn.inputs[2])
        nt.links.new(mixn.outputs[0], out.inputs["Surface"])
    m["th_source_strategy"] = "procedural"
    m["th_source_id"] = "procedural:window"
    return m


def build_town(scene, spec):
    """Assemble one attempt. Returns a census dict."""
    st = spec["street"]
    pal = spec["palette"]
    y0 = STREET_Y - st["width"] / 2.0
    mats = {}

    def mat(key, scale, bump, grime=0.15):
        token = pal[key]
        cache = (token, scale)
        if cache not in mats:
            mats[cache] = resolve_material(token, scale=scale, bump=bump, grime=grime)
        return mats[cache], token

    gm, gtok = mat("ground", 0.85, 0.55, grime=0.20)
    wall_m, wall_tok = mat("wall", 0.80, 0.45, grime=0.22)
    wall2_m, wall2_tok = mat("wall2", 0.80, 0.45, grime=0.18)
    roof_m, _ = mat("roof", 1.10, 0.55, grime=0.18)
    timber_m, _ = mat("timber", 0.5, 0.45, grime=0.15)
    trim_m, _ = mat("trim", 0.7, 0.4, grime=0.12)
    metal_m, _ = mat("metal", 1.2, 0.35, grime=0.0)
    glass_m = _window_material("WINDOW_%s" % spec["title"][:12],
                               lit=bool(spec["lighting"].get("practicals")))

    # ---- ground: displaced source, flat runtime plane
    gx = (st["backX"] + 12.0) / 2.0 + 2.0
    ground = box("SRC_ground", gx, STREET_Y, GROUND_Z - 0.25,
                 st["backX"] + 14.0, 46.0, 0.5, "TH_SOURCE")
    uv_project(ground, scale=0.85)
    assign(ground, gm)
    # the street reads its relief from the material bump; a displaced ground
    # box tears at its edges for the same reason a displaced facade box does
    rg = box("RND_ground", gx, STREET_Y, GROUND_Z - 0.25,
             st["backX"] + 14.0, 46.0, 0.5, "TH_RENDER")
    uv_project(rg, scale=0.85)

    # ---- facade row along Y with a real rhythm of widths and heights
    y = y0 - 3.0
    idx = 0
    doors = []
    while y < y0 + st["width"] + 3.0:
        w, hgt = spec["rhythm"][idx % len(spec["rhythm"])]
        # deterministic per-bay variation; identical bays were the single most
        # criticised failure ("reads as a copied module")
        vseed = (idx * 2654435761) % 997
        vary = spec.get("varyBays", False)
        depth = 2.6 + 0.5 * ((idx % 3) - 1)
        # stagger the FRONT face: a dead-straight facade line reads as one flat
        # wall of boxes and kills the depth the side view is supposed to show
        front = st["facadeX"] + ((idx * 37) % 5 - 2) * 0.26
        cx = front + depth / 2.0
        cy = y + w / 2.0
        cz = GROUND_Z + hgt / 2.0
        alt = (idx % 2) == 1
        if vary:
            hgt = hgt * (0.82 + 0.36 * ((vseed % 7) / 6.0))
            cz = GROUND_Z + hgt / 2.0
            alt = (vseed % 3) == 0

        if vary and (vseed % 11) == 3 and 0 < idx:
            # a recessed alley: strong dark vertical break plus a lit side wall
            side = box("SRC_alley_%d" % idx, front + 2.2, cy, cz,
                       4.0, 0.18, hgt, "TH_SOURCE")
            uv_project(side, scale=0.80)
            assign(side, wall2_m)
            box("RND_alley_%d" % idx, front + 2.2, cy, cz,
                4.0, 0.18, hgt, "TH_RENDER")
            back = box("SRC_alleyback_%d" % idx, front + 4.4, cy, cz,
                       0.3, w, hgt, "TH_SOURCE")
            uv_project(back, scale=0.80)
            assign(back, wall_m)
            y += w
            idx += 1
            continue

        b = box("SRC_bldg_%d" % idx, cx, cy, cz, depth, w, hgt, "TH_SOURCE")
        uv_project(b, scale=0.80)
        wm = wall2_m if alt else wall_m
        assign(b, wm)
        ht = height_for(wall2_tok if alt else wall_tok)
        if ht:
            pan = facade_panel("SRC_facade_%d" % idx, front - 0.012,
                               cy, cz, w, hgt, "TH_SOURCE")
            uv_scale_panel(pan, 0.80)
            assign(pan, wm)
            displace_panel(pan, ht, strength=0.05)

        rb = box("RND_bldg_%d" % idx, cx, cy, cz, depth, w, hgt, "TH_RENDER")
        uv_project(rb, scale=0.80)
        box("COL_bldg_%d" % idx, cx, cy, cz, depth, w, hgt, "TH_COLLISION")

        # roof overhang stays geometry: it changes what actors pass beneath
        rf = box("SRC_roof_%d" % idx, cx - 0.18, cy, GROUND_Z + hgt + 0.22,
                 depth + 0.55, w + 0.30, 0.44, "TH_SOURCE")
        uv_project(rf, scale=1.10)
        assign(rf, roof_m)
        rrf = box("RND_roof_%d" % idx, cx - 0.18, cy, GROUND_Z + hgt + 0.22,
                  depth + 0.55, w + 0.30, 0.44, "TH_RENDER")
        uv_project(rrf, scale=1.10)

        # deep doorway recess -- silhouette-critical, kept in TH_RENDER
        if idx % 2 == 0:
            dz = GROUND_Z + 1.05
            rec = box("SRC_door_%d" % idx, front - 0.22, cy, dz,
                      0.5, 1.05, 2.10, "TH_SOURCE")
            uv_project(rec, scale=0.7)
            assign(rec, trim_m)
            box("RND_door_%d" % idx, front - 0.22, cy, dz,
                0.5, 1.05, 2.10, "TH_RENDER")
            _anchor("ANCHOR_door_%d" % idx, ACTION_X, cy, GROUND_Z, "door")
            doors.append(cy)

        # ---- windows: recessed openings with a dark interior, lit at night.
        # Shallow trim disappears into the bake, but the recess itself changes
        # what the facade reads as, so the runtime keeps a matching box.
        n_rows = 1 if hgt < 5.0 else 2
        n_cols = max(1, int(w // 1.15))
        if vary:
            n_cols = max(1, min(n_cols, 1 + (vseed % 3)))
        for wr in range(n_rows):
            wz = GROUND_Z + 2.55 + wr * 1.75
            if wz + 0.55 > GROUND_Z + hgt - 0.35:
                continue
            for wc in range(n_cols):
                wy = cy - w / 2.0 + w * (wc + 0.5) / n_cols
                op = box("SRC_win_%d_%d_%d" % (idx, wr, wc), front + 0.24, wy, wz,
                         0.30, 0.58, 0.86, "TH_SOURCE")
                uv_project(op, scale=1.0)
                assign(op, glass_m)
                box("RND_win_%d_%d_%d" % (idx, wr, wc), front + 0.24, wy, wz,
                    0.30, 0.58, 0.86, "TH_RENDER")
                sill = box("SRC_sill_%d_%d_%d" % (idx, wr, wc), front - 0.07, wy,
                           wz - 0.49, 0.18, 0.78, 0.09, "TH_SOURCE")
                uv_project(sill, scale=1.0)
                assign(sill, trim_m)

        if alt and hgt > 4.8:
            tb = box("SRC_timber_%d" % idx, front - 0.30, cy,
                     GROUND_Z + hgt - 1.30, 0.34, w * 0.92, 1.9, "TH_SOURCE")
            uv_project(tb, scale=0.5)
            assign(tb, timber_m)
            box("RND_timber_%d" % idx, front - 0.30, cy,
                GROUND_Z + hgt - 1.30, 0.34, w * 0.92, 1.9, "TH_RENDER")

        y += w
        idx += 1

    # ---- far silhouette so the street does not end in bare sky
    bgm, _ = mat("wall2", 0.60, 0.25, grime=0.30)
    for j, (byy, bh) in enumerate([(y0 - 4.0, 7.5), (y0 + 4.0, 9.0), (y0 + 12.0, 8.0)]):
        bb = box("SRC_far_%d" % j, st["backX"] + 3.0, byy, GROUND_Z + bh / 2.0,
                 4.0, 7.0, bh, "TH_SOURCE")
        uv_project(bb, scale=0.60)
        assign(bb, bgm)
        box("RND_far_%d" % j, st["backX"] + 3.0, byy, GROUND_Z + bh / 2.0,
            4.0, 7.0, bh, "TH_RENDER")

    # ---- foreground occluder
    kind = spec["foreground"]
    fx = st["foreX"]
    if kind == "post":
        for n, oy in enumerate((y0 - 0.4, y0 + st["width"] + 0.4)):
            p = box("SRC_post_%d" % n, fx, oy, GROUND_Z + 2.6, 0.42, 0.42, 5.2, "TH_SOURCE")
            uv_project(p, scale=0.8)
            assign(p, timber_m)
            box("RND_post_%d" % n, fx, oy, GROUND_Z + 2.6, 0.42, 0.42, 5.2, "TH_RENDER")
            box("COL_post_%d" % n, fx, oy, GROUND_Z + 2.6, 0.42, 0.42, 5.2, "TH_COLLISION")
    elif kind == "arch":
        for n, oy in enumerate((y0 - 0.2, y0 + st["width"] + 0.2)):
            p = box("SRC_pier_%d" % n, fx, oy, GROUND_Z + 2.2, 1.0, 1.0, 4.4, "TH_SOURCE")
            uv_project(p, scale=0.6)
            assign(p, wall_m)
            box("RND_pier_%d" % n, fx, oy, GROUND_Z + 2.2, 1.0, 1.0, 4.4, "TH_RENDER")
            box("COL_pier_%d" % n, fx, oy, GROUND_Z + 2.2, 1.0, 1.0, 4.4, "TH_COLLISION")
        span = box("SRC_arch_span", fx, STREET_Y, GROUND_Z + 5.0,
                   1.0, st["width"] + 2.4, 1.2, "TH_SOURCE")
        uv_project(span, scale=0.6)
        assign(span, wall_m)
        box("RND_arch_span", fx, STREET_Y, GROUND_Z + 5.0,
            1.0, st["width"] + 2.4, 1.2, "TH_RENDER")
    elif kind == "awning":
        for n, oy in enumerate((y0 + 1.2, y0 + st["width"] - 1.2)):
            a = box("SRC_awning_%d" % n, st["facadeX"] - 1.15, oy, GROUND_Z + 2.55,
                    2.0, 2.6, 0.16, "TH_SOURCE")
            uv_project(a, scale=0.7)
            assign(a, trim_m)
            box("RND_awning_%d" % n, st["facadeX"] - 1.15, oy, GROUND_Z + 2.55,
                2.0, 2.6, 0.16, "TH_RENDER")
    elif kind == "balcony":
        for n, oy in enumerate((y0 + 2.0, y0 + st["width"] - 2.0)):
            a = box("SRC_balcony_%d" % n, st["facadeX"] - 0.85, oy, GROUND_Z + 3.1,
                    1.5, 2.8, 0.22, "TH_SOURCE")
            uv_project(a, scale=0.7)
            assign(a, timber_m)
            box("RND_balcony_%d" % n, st["facadeX"] - 0.85, oy, GROUND_Z + 3.1,
                1.5, 2.8, 0.22, "TH_RENDER")
            r = box("SRC_rail_%d" % n, st["facadeX"] - 1.50, oy, GROUND_Z + 3.55,
                    0.10, 2.8, 0.68, "TH_SOURCE")
            uv_project(r, scale=1.2)
            assign(r, metal_m)
            box("RND_rail_%d" % n, st["facadeX"] - 1.50, oy, GROUND_Z + 3.55,
                0.10, 2.8, 0.68, "TH_RENDER")
    elif kind == "frame_arch":
        # Near-camera framing arch. The occluders in 01-06 sat at the frame
        # edges and scored 1.75 for foreground framing; this one crosses the
        # picture and the actors genuinely walk behind it.
        #
        # Two things this geometry has to get right:
        #  * a foreground element this close blows out under the key light and
        #    reads as a blank white slab, so it gets a deliberately dark,
        #    heavily grimed material and reads as near-silhouette framing;
        #  * UVs must be scaled UP on a small object, or less than one texture
        #    tile covers it and the surface looks untextured.
        fg_m = resolve_material(pal["wall"], scale=2.4, bump=0.5, grime=0.55)
        for n, oy in enumerate((STREET_Y - 2.7, STREET_Y + 3.0)):
            pi = box("SRC_fgpier_%d" % n, fx, oy, GROUND_Z + 2.4,
                     0.85, 0.85, 4.8, "TH_SOURCE")
            uv_project(pi, scale=2.4)
            assign(pi, fg_m)
            box("RND_fgpier_%d" % n, fx, oy, GROUND_Z + 2.4,
                0.85, 0.85, 4.8, "TH_RENDER")
            box("COL_fgpier_%d" % n, fx, oy, GROUND_Z + 2.4,
                0.85, 0.85, 4.8, "TH_COLLISION")
        # The lintel must sit low enough to actually enter the frame: at this
        # distance the top of frame is only about z = -1.2, so a beam at eye
        # height crosses the picture instead of hanging invisibly above it.
        lint = box("SRC_fglintel", fx, STREET_Y, GROUND_Z + 2.32,
                   0.95, 7.6, 0.62, "TH_SOURCE")
        uv_project(lint, scale=2.4)
        assign(lint, fg_m)
        box("RND_fglintel", fx, STREET_Y, GROUND_Z + 2.32,
            0.95, 7.6, 0.62, "TH_RENDER")
        beam_m = resolve_material(pal["timber"], scale=2.6, bump=0.5, grime=0.5)
        beam = box("SRC_fgbeam", fx + 3.2, STREET_Y, GROUND_Z + 2.72,
                   0.26, 8.0, 0.30, "TH_SOURCE")
        uv_project(beam, scale=2.6)
        assign(beam, beam_m)
        box("RND_fgbeam", fx + 3.2, STREET_Y, GROUND_Z + 2.72,
            0.26, 8.0, 0.30, "TH_RENDER")
    elif kind == "stairs":
        for s in range(5):
            sy = y0 + st["width"] - 1.0 - s * 0.9
            so = box("SRC_step_%d" % s, ACTION_X - 0.4, sy,
                     GROUND_Z + 0.12 + s * 0.24, 3.0, 0.9, 0.24, "TH_SOURCE")
            uv_project(so, scale=0.5)
            assign(so, gm)
            box("RND_step_%d" % s, ACTION_X - 0.4, sy,
                GROUND_Z + 0.12 + s * 0.24, 3.0, 0.9, 0.24, "TH_RENDER")
        p = box("SRC_post_main", fx, y0 + 0.6, GROUND_Z + 3.0, 0.55, 0.55, 6.0, "TH_SOURCE")
        uv_project(p, scale=0.8)
        assign(p, timber_m)
        box("RND_post_main", fx, y0 + 0.6, GROUND_Z + 3.0, 0.55, 0.55, 6.0, "TH_RENDER")
        box("COL_post_main", fx, y0 + 0.6, GROUND_Z + 3.0, 0.55, 0.55, 6.0, "TH_COLLISION")

    _anchor("ANCHOR_spawn", ACTION_X, y0 + 0.8, GROUND_Z, "spawn")
    _anchor("ANCHOR_exit_left", ACTION_X, y0 - 2.5, GROUND_Z, "transition")
    _anchor("ANCHOR_exit_right", ACTION_X, y0 + st["width"] + 2.5, GROUND_Z, "transition")

    for ob in col("TH_RENDER").objects:
        if ob.type == "MESH" and not ob.data.materials:
            ob.data.materials.append(wall_m)

    return {"doors": doors, "materialCount": len(mats),
            "materialTokens": sorted({t for t, _ in mats})}
