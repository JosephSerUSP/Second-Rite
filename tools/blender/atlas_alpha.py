"""Preserve authored cutout coverage independently of atlas beauty and camera visibility."""
from __future__ import annotations
import bpy
import numpy as np
SOURCE_UV = "sr_source_uv"
ATLAS_UV = "sr_atlas_uv"

def preserve_uv(mesh):
    if mesh.uv_layers.active:
        original = mesh.uv_layers.active
        saved = mesh.uv_layers.get(SOURCE_UV) or mesh.uv_layers.new(name=SOURCE_UV)
        for a, b in zip(saved.data, original.data):
            a.uv = b.uv
        atlas = mesh.uv_layers.get(ATLAS_UV) or mesh.uv_layers.new(name=ATLAS_UV)
        mesh.uv_layers.active = atlas

def bake_opacity(scene, target, size):
    """Bake Principled alpha to emission, with original UVs and atlas receiver UVs.

    This is a material evaluation, not a lighting bake. Opaque geometry stays opaque,
    including unseen texels; a cutout's alpha is never inferred from a camera background.
    Materials and source documents are restored; the returned image is temporary.
    """
    materials = list(target.data.materials)
    alpha_inputs = []
    for material in materials:
        if material and material.use_nodes:
            if any(n.type == "BSDF_TRANSPARENT" for n in material.node_tree.nodes):
                raise RuntimeError(f"atlas opacity requires Principled alpha: {material.name}")
            shaders = [n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"]
            alpha_inputs.extend(n.inputs["Alpha"] for n in shaders)
    if not any(a.is_linked or a.default_value < 1 for a in alpha_inputs):
        return None
    atlas_uv = target.data.uv_layers.active.name
    image = bpy.data.images.new("SR_ATLAS_OPACITY", size, size, alpha=True, float_buffer=True)
    image.generated_color = (1, 1, 1, 1)
    copies = []
    old_engine = scene.render.engine
    old_selected = scene.render.bake.use_selected_to_active
    old_clear = scene.render.bake.use_clear
    old_active = bpy.context.view_layer.objects.active
    selected = list(bpy.context.selected_objects)
    try:
        for material in materials:
            clone = material.copy() if material else bpy.data.materials.new("SR_OPAQUE")
            clone.use_nodes = True
            nodes, links = clone.node_tree.nodes, clone.node_tree.links
            output = next(n for n in nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
            shader = output.inputs["Surface"].links[0].from_node if output.inputs["Surface"].links else None
            if shader and any(n.type == "BSDF_TRANSPARENT" for n in nodes):
                raise RuntimeError(f"atlas opacity requires a Principled surface: {material.name}")
            emission = nodes.new("ShaderNodeEmission")
            alpha = shader.inputs.get("Alpha") if shader and shader.type == "BSDF_PRINCIPLED" else None
            if alpha and alpha.is_linked:
                origin = alpha.links[0]
                if origin.from_node.type == "NEW_GEOMETRY" or (origin.from_node.type == "TEX_COORD" and origin.from_socket.name != "UV"):
                    raise RuntimeError("atlas opacity requires UV-based alpha")
                pending = [alpha.links[0].from_node]; seen = set()
                while pending:
                    node = pending.pop()
                    if node.name in seen: continue
                    seen.add(node.name)
                    for socket in node.inputs:
                        if socket.is_linked:
                            for link in socket.links:
                                if link.from_node.type == "TEX_COORD" and link.from_socket.name != "UV":
                                    raise RuntimeError("atlas opacity requires UV coordinates, not " + link.from_socket.name)
                                if link.from_node.type == "NEW_GEOMETRY":
                                    raise RuntimeError("atlas opacity cannot flatten geometry-dependent alpha")
                                pending.append(link.from_node)
                        elif socket.name == "Vector" and node.type.startswith("TEX_") and node.type != "TEX_IMAGE":
                            raise RuntimeError("atlas opacity requires explicit UVs for procedural alpha")
                links.new(alpha.links[0].from_socket, emission.inputs["Color"])
            else:
                value = alpha.default_value if alpha else 1.0
                emission.inputs["Color"].default_value = (value, value, value, 1)
            links.new(emission.outputs[0], output.inputs["Surface"])
            source_uv = nodes.new("ShaderNodeUVMap"); source_uv.uv_map = SOURCE_UV
            for node in list(nodes):
                if node.type == "TEX_IMAGE" and not node.inputs["Vector"].is_linked:
                    if not target.data.uv_layers.get(SOURCE_UV):
                        raise RuntimeError("alpha texture has no preserved source UV")
                    links.new(source_uv.outputs[0], node.inputs["Vector"])
            receiver = nodes.new("ShaderNodeTexImage"); receiver.image = image
            nodes.active = receiver
            copies.append(clone)
        # Rasterise the material in receiver-UV space with EEVEE. Source UV
        # attributes stay on the flattened mesh; atlas positions only place texels.
        # This keeps the EEVEE workflow independent of the Cycles baker.
        mesh = bpy.data.meshes.new("SR_OPACITY_UV_MESH")
        vertices, faces, loop_indices = [], [], []
        uv = target.data.uv_layers[atlas_uv].data
        for polygon in target.data.polygons:
            start = len(vertices)
            for loop in polygon.loop_indices:
                vertices.append((*uv[loop].uv, 0.0))
                loop_indices.append(loop)
            faces.append(tuple(range(start, len(vertices))))
        mesh.from_pydata(vertices, [], faces)
        for layer in target.data.uv_layers:
            dest = mesh.uv_layers.new(name=layer.name)
            for index, source_index in enumerate(loop_indices):
                dest.data[index].uv = layer.data[source_index].uv
        for material in copies: mesh.materials.append(material)
        for a, b in zip(mesh.polygons, target.data.polygons): a.material_index = b.material_index
        mask_object = bpy.data.objects.new("SR_OPACITY_UV", mesh)
        scene.collection.objects.link(mask_object)
        camera_data = bpy.data.cameras.new("SR_OPACITY_CAMERA")
        camera = bpy.data.objects.new("SR_OPACITY_CAMERA", camera_data)
        scene.collection.objects.link(camera)
        camera.location = (0.5, 0.5, 1)
        camera_data.type = "ORTHO"; camera_data.ortho_scale = 1
        hidden = [(o, o.hide_render) for o in scene.objects if o not in (mask_object, camera)]
        old_camera = scene.camera
        saved = {key: getattr(scene.render, key) for key in
                 ("resolution_x", "resolution_y", "resolution_percentage", "film_transparent", "filter_size", "filepath")}
        view = {key: getattr(scene.view_settings, key) for key in ("view_transform", "look", "exposure", "gamma")}
        image_settings = {key: getattr(scene.render.image_settings, key) for key in
                          ("file_format", "color_depth", "color_mode")}
        old_override = bpy.context.view_layer.material_override
        try:
            for obj, _ in hidden: obj.hide_render = True
            scene.camera = camera
            scene.render.engine = "BLENDER_EEVEE"
            bpy.context.view_layer.material_override = None
            import eevee_projection
            from pathlib import Path
            path = Path(bpy.app.tempdir) / "atlas_opacity.exr"
            eevee_projection.set_raw_float_output(scene, path, 1)
            scene.render.resolution_x = size; scene.render.resolution_y = size
            scene.render.filter_size = 0.0
            pixels = eevee_projection.render_exr(scene, path)
            # Pixels outside geometry are opaque, not holes in unseen content.
            pixels[pixels[..., 3] < 0.5] = (1, 1, 1, 1)
            image.pixels.foreach_set(pixels.reshape(-1))
        finally:
            for obj, visible in hidden: obj.hide_render = visible
            scene.camera = old_camera
            bpy.context.view_layer.material_override = old_override
            for key, value in saved.items(): setattr(scene.render, key, value)
            for key, value in view.items(): setattr(scene.view_settings, key, value)
            for key, value in image_settings.items(): setattr(scene.render.image_settings, key, value)
            bpy.data.objects.remove(mask_object, do_unlink=True)
            bpy.data.objects.remove(camera, do_unlink=True)
            bpy.data.meshes.remove(mesh)
            bpy.data.cameras.remove(camera_data)
        return image
    finally:
        for material in copies: bpy.data.materials.remove(material)
        scene.render.engine = old_engine
        scene.render.bake.use_selected_to_active = old_selected
        scene.render.bake.use_clear = old_clear
        bpy.ops.object.select_all(action="DESELECT")
        for obj in selected: obj.select_set(True)
        bpy.context.view_layer.objects.active = old_active

def apply(image, opacity):
    if opacity is None: return
    rgba = np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(rgba)
    mask = np.empty(len(opacity.pixels),dtype=np.float32);opacity.pixels.foreach_get(mask)
    rgba.reshape(-1,4)[:,3] = np.clip(mask.reshape(-1,4)[:,0],0,1)
    image.pixels.foreach_set(rgba)
