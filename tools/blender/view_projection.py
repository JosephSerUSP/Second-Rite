"""Camera-projected reference colour on a saved mesh, with explicit unseen fallback.

Blender import library. It authors projection UV/visibility attributes and shader
recipes; callers own camera/image correspondence, baking and source saves.
Reference photographs contain lighting: this is appearance transfer, not albedo
recovery. Geometry and existing UVs are never replaced.
"""
from __future__ import annotations

import math

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from multiview_reference import atlas_uv


def world_mesh(obj):
    """Use a finalized mesh; refusing modifiers avoids stale loop correspondence."""
    if obj.type != 'MESH' or obj.modifiers:
        raise ValueError('Projection receiver must be a finalized mesh with no modifiers')
    return [obj.matrix_world @ v.co for v in obj.data.vertices]


def visibility_tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons(world_mesh(obj), [tuple(t.vertices) for t in obj.data.loop_triangles],
                               all_triangles=True)


def project_view(obj, scene, camera, *, name, image_size, rectangle, clip, tree=None,
                 update=False, fit_bounds=False):
    """Map the exact camera frame into an image panel, then UV the mesh loops.

    rectangle/clip are top-left pixel xyxy rectangles in the unchanged full image.
    Each view creates a UV layer and corner visibility attribute. Occlusion is
    against the complete receiver, including other connected components.
    The default keeps the camera's pixel framing: use paintovers of its render.
    `fit_bounds=True` explicitly fits geometry bounds to a measured reference
    rectangle. This cannot repair shape or internal correspondence mismatches.
    """
    if camera.type != 'CAMERA' or camera.data.type != 'ORTHO':
        raise ValueError('Explicit orthographic camera required')
    width, height = image_size
    for bounds in (rectangle, clip):
        if (len(bounds) != 4 or not all(math.isfinite(v) for v in bounds)
                or not 0 <= bounds[0] < bounds[2] <= width
                or not 0 <= bounds[1] < bounds[3] <= height):
            raise ValueError('Image rectangle must be finite, positive and inside image')
    if not (clip[0] <= rectangle[0] < rectangle[2] <= clip[2]
            and clip[1] <= rectangle[1] < rectangle[3] <= clip[3]):
        raise ValueError('Correspondence rectangle leaves its view clip')
    layer_name = 'Projection_' + name
    attribute_name = layer_name + '_visible'
    if not update and (layer_name in obj.data.uv_layers or attribute_name in obj.data.attributes):
        raise ValueError('Projection view already exists; edit its saved calibration explicitly')
    bpy.context.view_layer.update()
    points = world_mesh(obj)
    projected = [world_to_camera_view(scene, camera, p) for p in points]
    low = [min(p[i] for p in projected) for i in (0, 1)] if fit_bounds else [0, 0]
    high = [max(p[i] for p in projected) for i in (0, 1)] if fit_bounds else [1, 1]
    spans = [high[i] - low[i] for i in (0, 1)]
    if min(spans) < 1e-9 or any(p.z <= 0 for p in projected):
        raise ValueError('Receiver is behind camera or projects to an empty extent')
    sx = (rectangle[2] - rectangle[0]) / spans[0]
    sy = (rectangle[3] - rectangle[1]) / spans[1]
    panel = {'axes': [0, 1], 'center': [rectangle[0] - low[0]*sx,
                                      rectangle[3] + low[1]*sy], 'scale': [sx, -sy]}
    uvs = [atlas_uv(tuple(p), panel, image_size) for p in projected]
    toward_camera = (camera.matrix_world.to_quaternion() @ Vector((0, 0, 1))).normalized()
    extent = max((a-b).length for a in points for b in [points[0]]) * 4 + 1
    epsilon = 1e-5
    tree = tree or visibility_tree(obj)
    obj.data.calc_loop_triangles()
    centres = {}
    for tri in obj.data.loop_triangles:
        centre = sum((points[i] for i in tri.vertices), Vector()) / 3
        for li in tri.loops:
            centres.setdefault(li, centre)
    visible = []
    for loop in obj.data.loops:
        # A ray aimed exactly at a boundary vertex can miss its triangle due to
        # floating precision. Sample just inside an actual tessellated triangle.
        point = points[loop.vertex_index].lerp(centres[loop.index], .001)
        # An orthographic camera has parallel rays. Starting outside the receiver
        # catches occluding components; testing only a face's normal does not.
        origin = point + toward_camera * extent
        hit, normal, face, distance = tree.ray_cast(origin, -toward_camera, extent + epsilon)
        visible.append(float(hit is not None and (hit-point).length < epsilon))
    previous_active = obj.data.uv_layers.active.name if obj.data.uv_layers.active else None
    layer = obj.data.uv_layers.get(layer_name) or obj.data.uv_layers.new(name=layer_name)
    attr = obj.data.attributes.get(attribute_name) or obj.data.attributes.new(attribute_name, 'FLOAT', 'CORNER')
    if attr.data_type != 'FLOAT' or attr.domain != 'CORNER':
        raise ValueError('Existing visibility attribute has incompatible type/domain')
    for loop in obj.data.loops:
        layer.data[loop.index].uv = uvs[loop.vertex_index]
        attr.data[loop.index].value = visible[loop.index]
    if previous_active:
        obj.data.uv_layers.active = obj.data.uv_layers[previous_active]
    return {'name': name, 'uvLayer': layer_name, 'visibilityAttribute': attribute_name,
            'fitBounds': bool(fit_bounds),
            'towardCamera': list(toward_camera), 'imageSize': list(image_size),
            'rectangle': list(rectangle), 'clip': list(clip), 'affinePanel': panel,
            'cameraMatrixWorld': [list(row) for row in camera.matrix_world],
            'cameraOrthoScale': camera.data.ortho_scale,
            'renderSize': [scene.render.resolution_x, scene.render.resolution_y],
            'pixelAspect': [scene.render.pixel_aspect_x, scene.render.pixel_aspect_y],
            'visibleCorners': int(sum(visible)), 'corners': len(visible), 'vertices': len(points)}


def projection_material(name, image, views, fallback, *, fallback_uv='OriginalUV', power=6,
                        mask_image=None):
    """Blend visible front-facing view samples in linear light; return recipe/control.

    `fallback` is a bitmap sampled with an existing UV layer. The returned switch
    chooses appearance (0) or green observed/red fallback evidence (1), which can
    be baked independently. View weights are normal alignment ** power, with
    alpha, panel clip and saved occlusion masks. No sample repairs unseen areas.
    Opaque paintovers may supply the exact render's RGBA support as `mask_image`;
    its full-canvas framing/aspect must match the paintover.
    """
    if not views or not math.isfinite(power) or power < 1:
        raise ValueError('At least one view and finite power >= 1 required')
    if mask_image and abs(mask_image.size[0]/mask_image.size[1] - image.size[0]/image.size[1]) > 1e-6:
        raise ValueError('Support mask and paintover must share full-canvas aspect/framing')
    mat = bpy.data.materials.new(name); mat.use_nodes = True; mat.use_fake_user = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links; nodes.clear()
    def number(op, a, b):
        n = nodes.new('ShaderNodeMath'); n.operation = op
        for i, value in enumerate((a, b)):
            if isinstance(value, (int, float)): n.inputs[i].default_value = value
            else: links.new(value, n.inputs[i])
        return n.outputs[0]
    def vector(op, a, b):
        n = nodes.new('ShaderNodeVectorMath'); n.operation = op
        for i, value in enumerate((a, b)):
            if isinstance(value, tuple): n.inputs[i].default_value = value
            else: links.new(value, n.inputs[i])
        return n.outputs['Vector']
    def scale(colour, amount):
        n = nodes.new('ShaderNodeVectorMath'); n.operation = 'SCALE'
        links.new(colour, n.inputs[0]); links.new(amount, n.inputs['Scale'])
        return n.outputs['Vector']
    geometry = nodes.new('ShaderNodeNewGeometry')
    colours, weights = [], []
    for view in views:
        uv = nodes.new('ShaderNodeUVMap'); uv.uv_map = view['uvLayer']
        tex = nodes.new('ShaderNodeTexImage'); tex.image = image; tex.interpolation = 'Linear'
        links.new(uv.outputs['UV'], tex.inputs['Vector'])
        attr = nodes.new('ShaderNodeAttribute'); attr.attribute_name = view['visibilityAttribute']
        dot = nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
        links.new(geometry.outputs['Normal'], dot.inputs[0]); dot.inputs[1].default_value = view['towardCamera']
        facing = number('POWER', number('MAXIMUM', dot.outputs['Value'], 0), power)
        w = number('MULTIPLY', number('MULTIPLY', facing, attr.outputs['Fac']), tex.outputs['Alpha'])
        if mask_image:
            support = nodes.new('ShaderNodeTexImage'); support.image = mask_image; support.interpolation = 'Linear'
            links.new(uv.outputs['UV'], support.inputs['Vector'])
            w = number('MULTIPLY', w, support.outputs['Alpha'])
        sep = nodes.new('ShaderNodeSeparateXYZ'); links.new(uv.outputs['UV'], sep.inputs[0])
        width, height = view['imageSize']; x0, y0, x1, y1 = view['clip']
        for axis, op, bound in [('X','GREATER_THAN',x0/width), ('X','LESS_THAN',x1/width),
                                ('Y','GREATER_THAN',1-y1/height), ('Y','LESS_THAN',1-y0/height)]:
            w = number('MULTIPLY', w, number(op, sep.outputs[axis], bound))
        weights.append(w); colours.append(scale(tex.outputs['Color'], w))
    total_weight = weights[0]; total_colour = colours[0]
    for weight, colour in zip(weights[1:], colours[1:]):
        total_weight = number('ADD', total_weight, weight)
        total_colour = vector('ADD', total_colour, colour)
    observed = number('GREATER_THAN', total_weight, .001)
    colour = scale(total_colour, number('DIVIDE', 1, number('MAXIMUM', total_weight, 1e-6)))
    uv = nodes.new('ShaderNodeUVMap'); uv.uv_map = fallback_uv
    tex = nodes.new('ShaderNodeTexImage'); tex.image = fallback; tex.interpolation = 'Linear'
    links.new(uv.outputs[0], tex.inputs[0])
    mix = nodes.new('ShaderNodeMixRGB'); links.new(observed, mix.inputs[0])
    links.new(tex.outputs['Color'], mix.inputs[1]); links.new(colour, mix.inputs[2])
    coverage = nodes.new('ShaderNodeMixRGB'); links.new(observed, coverage.inputs[0])
    coverage.inputs[1].default_value = (1,0,0,1); coverage.inputs[2].default_value = (0,1,0,1)
    control = nodes.new('ShaderNodeMixRGB'); control.name = 'Appearance_or_coverage'
    control.inputs[0].default_value = 0
    links.new(mix.outputs[0], control.inputs[1]); links.new(coverage.outputs[0], control.inputs[2])
    emit = nodes.new('ShaderNodeEmission'); links.new(control.outputs[0], emit.inputs['Color'])
    output = nodes.new('ShaderNodeOutputMaterial'); links.new(emit.outputs[0], output.inputs['Surface'])
    return mat, control
