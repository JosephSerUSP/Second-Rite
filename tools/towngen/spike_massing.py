"""SPIKE: render a St. Maria street as massing, through the real town camera.

Run under Blender, not python:

    blender --background --factory-startup --python tools/towngen/spike_massing.py -- \
        --out out/towngen/massing --horizon-y 66

Why this exists. The 2D plates are wrong on collision and scale, and an
independently generated 2D facade cannot be composited into a street because it
carries its own implicit camera. In 3D the camera is imposed AFTER the geometry,
so perspective is correct by construction at whatever framing we choose.

This spike answers one question and does not pretend to answer more: what does
the street look like at a given framing, with a Walker-sized reference standing
in it? Nothing here is art. Every surface is flat grey; the point is silhouette,
scale and framing.

Camera traps this obeys, all of them previously paid for:
  * the basis must have determinant +1, or a billboarded actor renders upside
    down. right = forward x up; forward +X and up +Z gives right = -Y.
  * a relative render path resolves against the DRIVE ROOT in Blender, so the
    output path is made absolute.
  * the camera forces the Standard view transform; anything else regrades the
    render and the plate stops matching the runtime.
  * EEVEE's engine enum id has moved between releases.
"""

import argparse
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

# The camera contract, from tools/blender/make_town_camera.py. Not re-derived
# here: if these drift, the render stops describing the game.
FOV_HALF_X = 0.25              # tangent
BASE_W, BASE_H = 256, 144      # base projection frame
WALKER_UNITS = 1.75
WALKER_PX = 48
PX_PER_UNIT = WALKER_PX / WALKER_UNITS      # 27.4286
DISTANCE = 18.666666666666668


def argv():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="out/towngen/massing")
    p.add_argument("--horizon-y", type=float, default=66.0)
    p.add_argument("--feet-y", type=float, default=128.0)
    p.add_argument("--pitch", type=float, default=0.0,
                   help="degrees down; 0 keeps verticals parallel")
    p.add_argument("--width", type=int, default=BASE_W)
    p.add_argument("--height", type=int, default=240)
    p.add_argument("--eye-z", type=float, default=None,
                   help="override the solved eye height; needed when pitching, "
                        "because a tilted camera puts the horizon somewhere "
                        "other than the principal point")
    p.add_argument("--principal-y", type=float, default=None,
                   help="native y of the principal point; defaults to horizon-y")
    p.add_argument("--mode", choices=("level","translate","shift","shift_fov","shift_dolly","horizon","billboard"), default="level",
                   help="how the rotation is compensated; see camera_modes.py")
    p.add_argument("--barrel", type=float, default=0.0,
                   help="barrel distortion, 0..~0.3. A rectilinear lens keeps "
                        "straight lines straight at ANY field of view; bowing "
                        "verticals needs a non-rectilinear projection.")
    p.add_argument("--tag", default="")
    return p.parse_args(a)


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def grey(name, v):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    # Sockets are linear: a mid grey is not 0.5 sRGB.
    bsdf.inputs["Base Color"].default_value = (v, v, v, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    return m


def box(name, centre, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=centre)
    o = bpy.context.object
    o.name = name
    o.scale = Vector(size) * 0.5 * 2.0 / 2.0 * 1.0
    o.scale = (size[0] / 2.0 * 2.0 / 2.0, size[1] / 2.0, size[2] / 2.0)
    o.scale = (size[0] / 2.0, size[1] / 2.0, size[2] / 2.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    return o


def checker(name, a, b, squares):
    """A checkerboard sized in WALKERS. Perspective is unreadable without it."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexChecker")
    mapn = nt.nodes.new("ShaderNodeMapping")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    tex.inputs["Color1"].default_value = (a, a, a, 1.0)
    tex.inputs["Color2"].default_value = (b, b, b, 1.0)
    tex.inputs["Scale"].default_value = 1.0
    mapn.inputs["Scale"].default_value = (squares, squares, squares)
    nt.links.new(coord.outputs["Object"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    return m


def sprite_sheet():
    """walker.png, loaded as-is.

    It does NOT need keying. Pillow reports mode "RGB" and drops the PNG's tRNS
    chunk, which is where its colour-key transparency lives; Blender reads that
    chunk and hands back alpha 0 on the key pixels. Two rounds of shader keying
    and a hand-rolled pixel loop were written before checking the file's actual
    alpha channel.
    """
    return bpy.data.images.load(
        os.path.join(os.path.abspath(os.curdir), "projects",
                     "hichaukitoden-game", "assets", "character", "walker.png"))


def walker_billboard(name, lane_y, cam):
    """A VIEW-ALIGNED billboard: real geometry, but never keystoned.

    A world-vertical plane would lean and foreshorten with everything else once
    the camera is pitched. This quad is built from the CAMERA's own axes, so its
    plane is perpendicular to the view axis: every point on it shares one depth,
    which is why it projects as a perfect axis-aligned rectangle that can only
    scale.

    Being geometry is the point. It occupies real depth, so the depth buffer
    resolves what is in front of it and what is behind, per pixel, exactly as
    for any other object. Compositing the actor in 2D would throw that away.

    Its world height is exactly WALKER_UNITS: at the solved slant distance that
    is the height which projects to the sprite's native pixels.
    """
    from mathutils import Vector as V
    rot = cam.matrix_world.to_3x3()
    right, up = rot @ V((1.0, 0.0, 0.0)), rot @ V((0.0, 1.0, 0.0))
    w_units = WALKER_UNITS * (24.0 / 48.0)
    ground = V((0.0, lane_y, 0.0))
    bpy.ops.mesh.primitive_plane_add(size=1.0,
                                     location=ground + up * (WALKER_UNITS / 2.0))
    o = bpy.context.object
    o.name = name
    o.matrix_world = (Matrix.Translation(ground + up * (WALKER_UNITS / 2.0))
                      @ rot.to_4x4() @ Matrix.Diagonal(
                          V((w_units, WALKER_UNITS, 1.0, 1.0))))
    m = bpy.data.materials.new(name + "_mat")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = sprite_sheet()
    img.interpolation = "Closest"      # pixel art: never filter texels
    img.extension = "CLIP"
    mapn = nt.nodes.new("ShaderNodeMapping")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapn.inputs["Scale"].default_value = (1.0 / 6.0, 1.0, 1.0)   # cell 0 of six
    nt.links.new(coord.outputs["UV"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], img.inputs["Vector"])
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(img.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 1.0
    m.surface_render_method = "DITHERED"
    m.blend_method = "CLIP"
    o.data.materials.append(m)
    return o


def build_street(horizon_y):
    """A quay: contiguous floor, a built side, and open water beyond.

    The SEA IS GEOMETRY, not a skybox. A pitched camera sees the water surface
    receding toward the horizon, and a backdrop cannot do that - it cannot
    recede, and it cannot put the horizon where the geometry says it is. Sky
    above the horizon is the world shader; everything below it is a plane.
    """
    W = WALKER_UNITS
    stone = checker("stone", 0.13, 0.17, 1.0 / W)      # 1 square = 1 Walker
    face = checker("face", 0.28, 0.33, 1.0 / W)
    trim = grey("trim", 0.20)
    dark = grey("dark", 0.04)

    sea = bpy.data.materials.new("sea")
    sea.use_nodes = True
    sb = sea.node_tree.nodes["Principled BSDF"]
    sb.inputs["Base Color"].default_value = (0.012, 0.021, 0.035, 1.0)
    sb.inputs["Roughness"].default_value = 0.14

    # Contiguous quay floor, running well past the frame in both directions.
    box("quay", (3.0, 0.0, -0.05), (22.0, 200.0, 0.1), stone)
    # The water, far below and far out: a real plane to the horizon.
    # The water starts BEYOND the quay edge, not under the town.
    box("sea", (414.5, 0.0, -2.6), (800.0, 1600.0, 0.2), sea)
    # The quay wall dropping to the water, and a parapet along the open stretch.
    box("quay_wall", (14.0, 0.0, -1.3), (0.6, 200.0, 2.6), trim)
    box("parapet", (14.0, 26.0, 0.34), (0.7, 48.0, 0.68), trim)

    # The built side, along part of the lane only, so the water is visible past
    # the end of it rather than walled off.
    plan = [(-22.0, 6.0, 3.4, 4.0), (-15.4, 6.2, 2.6, 3.4), (-8.8, 5.6, 4.1, 4.4),
            (-2.6, 5.8, 3.0, 3.6), (2.6, 4.6, 3.6, 3.0)]
    for i, (cy, ly, hw, dx) in enumerate(plan):
        h = hw * W
        box("mass_%d" % i, (6.6 + dx / 2.0, cy, h / 2.0), (dx, ly, h), face)
        box("door_%d" % i, (6.6 - 0.07, cy, W / 2.0), (0.22, 0.95, W), dark)
        for s_i in range(1, int(hw)):
            box("storey_%d_%d" % (i, s_i), (6.6 - 0.05, cy, s_i * W),
                (0.16, ly * 0.93, 0.1), trim)
        box("roof_%d" % i, (6.6 + dx / 2.0, cy, h + 0.12),
            (dx + 0.5, ly + 0.4, 0.24), trim)

    # Bollards along the quay edge: small known-size objects near the camera.
    for j in range(-3, 7):
        box("bollard_%d" % j, (12.8, j * 5.0, 0.34), (0.34, 0.34, 0.68), trim)

    # A crate BETWEEN the camera and the middle actor, to prove the billboard is
    # depth-tested rather than pasted on top.
    box("occluder", (-4.0, 0.8, 0.60), (1.2, 1.5, 1.2), trim)

    # Actors are added after the camera exists, in main().
    # NO world-vertical actor geometry. A plane in a pitched scene keystones with everything
    # else; the actor is an axis-aligned sprite and is composited afterwards by
    # tools/towngen/compose_actor.py, exactly as the engine will draw it.


def place_camera(width, height, horizon_y, feet_y, pitch_deg,
                 eye_override=None, principal_y=None, mode="level"):
    """Place the camera per tools/towngen/camera_modes.py.

    level     - pitch 0, horizon carried by the principal point. Verticals stay
                parallel.
    translate - rotated, then MOVED so the Walker is exactly 48px with feet at
                128. Exact, and the camera ends up somewhere new.
    shift     - rotated in place, principal point slid until the feet land.
                Cannot restore scale, so the Walker comes out a little large.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import camera_modes as cm
    theta = math.radians(pitch_deg)
    k_override = None

    if mode == "level" or not pitch_deg:
        eye_z = eye_override if eye_override is not None else (feet_y - horizon_y) / PX_PER_UNIT
        horiz, pp = DISTANCE, (principal_y if principal_y is not None else horizon_y)
    elif mode == "translate":
        pp = principal_y if principal_y is not None else height / 2.0
        horiz, eye_z = cm.solve_translate(theta, pp)
    elif mode == "billboard":
        # The one solve that is correct for a screen-space actor.
        horiz, eye_z, pp = cm.solve_billboard(theta, horizon_y)
    elif mode == "horizon":
        # Pitch gives the lean, the principal point places the horizon, and the
        # translate solve restores the two invariants.
        horiz, eye_z, pp = cm.solve_for_horizon(theta, horizon_y)
    elif mode == "shift":
        horiz, eye_z, pp, _px = cm.solve_shift(theta)
    elif mode == "shift_fov":
        horiz, eye_z, pp, k_override = cm.solve_shift_fov(theta)
    else:
        horiz, eye_z, pp, _t = cm.solve_shift_dolly(theta)

    cam_data = bpy.data.cameras.new("town")
    cam_data.type = "PERSP"
    cam_data.sensor_fit = "HORIZONTAL"
    k = k_override if mode == "shift_fov" else cm.K
    cam_data.angle_x = 2.0 * math.atan((width / 2.0) / k)
    cam_data.shift_y = (pp - height / 2.0) / float(max(width, height))

    cam = bpy.data.objects.new("town_camera", cam_data)
    bpy.context.collection.objects.link(cam)
    right, up, back = Vector((0.0,-1.0,0.0)), Vector((0.0,0.0,1.0)), Vector((-1.0,0.0,0.0))
    basis = Matrix((right, up, back)).transposed().to_4x4()
    assert round(basis.to_3x3().determinant(), 6) == 1.0,         "camera basis determinant must be +1 or billboards flip (issue #935)"
    cam.matrix_world = (Matrix.Translation(Vector((-horiz, 0.0, eye_z))) @ basis
                        @ Matrix.Rotation(math.radians(-pitch_deg), 4, "X"))
    bpy.context.scene.camera = cam
    return eye_z


def light():
    """Nishita sky for the world, one sun keyed to match it."""
    d = bpy.data.lights.new("key", type="SUN")
    d.energy = 1.1
    d.angle = math.radians(1.5)
    o = bpy.data.objects.new("key", d)
    bpy.context.collection.objects.link(o)
    o.rotation_euler = (math.radians(52), 0.0, math.radians(-118))
    world = bpy.data.worlds.new("w")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    # 5.x renamed the Nishita model to MULTIPLE_SCATTERING.
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_elevation = math.radians(24)
    sky.sun_rotation = math.radians(-118)
    sky.altitude = 20.0
    sky.air_density = 1.5
    nt.links.new(sky.outputs["Color"], bg.inputs[0])
    bg.inputs[1].default_value = 0.30
    # Standard does not roll off highlights, so a physical sky clips to white
    # unless exposure is pulled down. The contract forces Standard, which makes
    # exposure the only handle.
    bpy.context.scene.view_settings.exposure = -1.1


def lens_distortion(amount):
    """Bow the verticals.

    The authored interiors bend vertical edges, which no rectilinear camera can
    do however wide the lens gets - widening stretches the corners but never
    curves a line. That look comes from a non-rectilinear projection, almost
    certainly inherited from the AI-generated source images those rooms were
    built from.

    Two ways to reproduce it deliberately:
      * this one - a compositor Lens Distortion pass, which works with EEVEE,
        costs nothing, and is a post-process on the rendered frame;
      * a Cycles panoramic/fisheye camera, which is a true optical projection
        but is Cycles-only (EEVEE has no panoramic camera) and much slower.

    The post-process is the right starting point because the strength is a dial
    rather than a camera rebuild.
    """
    # Blender 5.x moved scene compositing off `scene.node_tree` onto a node
    # GROUP datablock, `scene.compositing_node_group`, and the group takes its
    # image through a group input/output rather than Render Layers/Composite.
    scene = bpy.context.scene
    nt = bpy.data.node_groups.new("lens", "CompositorNodeTree")
    # 5.x dropped CompositorNodeComposite entirely: the group's OUTPUT is the
    # composite. The source is still a Render Layers node inside the group.
    nt.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    gin = nt.nodes.new("CompositorNodeRLayers")
    gout = nt.nodes.new("NodeGroupOutput")
    dist = nt.nodes.new("CompositorNodeLensdist")
    # In 5.x the node's options are INPUTS, not properties: `use_fit` became
    # the "Fit" socket and "Distort" became "Distortion".
    dist.inputs["Distortion"].default_value = amount
    dist.inputs["Dispersion"].default_value = 0.0
    if "Fit" in dist.inputs:
        dist.inputs["Fit"].default_value = True
    nt.links.new(gin.outputs["Image"], dist.inputs["Image"])
    nt.links.new(dist.outputs["Image"], gout.inputs[0])
    scene.compositing_node_group = nt
    scene.use_nodes = True


def render(path, width, height):
    s = bpy.context.scene
    engines = [e.identifier for e in
               bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    s.render.engine = ("BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines
                       else "BLENDER_EEVEE")
    s.render.resolution_x = width
    s.render.resolution_y = height
    s.render.resolution_percentage = 100
    # Default 1.5 blurs every texel. Pixel art wants a box filter.
    s.render.filter_size = 0.01
    s.render.film_transparent = False
    s.render.image_settings.file_format = "PNG"
    # The camera forces Standard: anything else regrades the plate away from
    # what the runtime will show.
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.render.filepath = os.path.abspath(path)   # relative resolves to drive root
    bpy.ops.render.render(write_still=True)


def main():
    a = argv()
    clear()
    build_street(a.horizon_y)
    eye_z = place_camera(a.width, a.height, a.horizon_y, a.feet_y, a.pitch,
                         a.eye_z, a.principal_y, a.mode)
    cam = bpy.context.scene.camera
    for lane in (-6.0, 0.8, 7.0):
        walker_billboard("walker_%.1f" % lane, lane, cam)
    light()
    if a.barrel:
        lens_distortion(a.barrel)
    tag = a.tag or ("h%d_p%s" % (int(a.horizon_y), str(a.pitch).replace(".", "-")))
    out = os.path.join(a.out, "massing_%s.png" % tag)
    os.makedirs(os.path.abspath(a.out), exist_ok=True)
    render(out, a.width, a.height)
    print("MASSING OK  %s  horizon=%s pitch=%s eye_z=%.4f dist=%.4f px/unit=%.4f"
          % (out, a.horizon_y, a.pitch, eye_z, DISTANCE, PX_PER_UNIT))


if __name__ == "__main__":
    main()
