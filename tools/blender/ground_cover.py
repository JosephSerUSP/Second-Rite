"""Ground cover as a Geometry Nodes modifier (the #1257 pilot).

The scatter of grass cards over an authored ground -- painted density, a slope
limit, keep-out objects and card instancing -- is a placement problem, which is
where Geometry Nodes earns its place: repeated placement with bounded variation
over a guide the owner can see.  The modifier's inputs stay editable in an
adopted document, and the modifier realises its instances so an exporter, and
therefore the runtime, receives only ordinary mesh: OBJ plus atlas.

Written against the Blender 5.2 Python API, where a modifier's inputs are RNA
properties (``modifier.properties.inputs.<identifier>.value``) rather than
``modifier["Socket_2"]`` ID properties.

Guide objects stay obvious and editable in the document: the terrain is an
ordinary mesh object whose vertex group carries the painted density, and the
keep-out footprints (the walkable lane) are ordinary objects in a collection.
The host object carries the modifier and nothing else, so the terrain itself is
never touched.

The card itself is still ``tree_mesh.card_corners`` / ``tree_mesh.atlas_uvs``,
the shape trees use, so a blade and a branch spray remain one kind of object.
"""
from __future__ import annotations

import math

import bpy

import tree_material
from tree_mesh import atlas_uvs, card_corners

GROUP_NAME = "SR_GroundCover"
HOST_NAME = "GROUND_COVER"
CARDS_COLLECTION = "GROUND_COVER_CARDS"
KEEP_OUT_COLLECTION = "GROUND_COVER_KEEP_OUT"

#: Tuft atlas built by tools/materials/make_grass_atlas.py: four columns.
ATLAS_COLUMNS = 4
TUFT_ASPECT = .95
#: Poisson minimum spacing as a fraction of the mean spacing 1/sqrt(density).
MIN_SPACING_OF_MEAN = .5

#: name -> (socket type, default, extra attributes).  One table drives both the
#: node group interface and :func:`configure`, so a socket cannot exist in one
#: and be misspelt in the other.
INPUTS = {
    "Terrain": ("NodeSocketObject", None, {}),
    "Keep Out": ("NodeSocketCollection", None, {}),
    "Cards": ("NodeSocketCollection", None, {}),
    "Density Group": ("NodeSocketString", "", {}),
    "Density": ("NodeSocketFloat", 14.0, {"min_value": 0.0, "max_value": 400.0}),
    "Slope Limit": ("NodeSocketFloat", 38.0, {"min_value": 0.0, "max_value": 89.9}),
    "Keep Out Margin": ("NodeSocketFloat", 0.0, {"min_value": 0.0}),
    "Tuft Height": ("NodeSocketFloat", .34, {"min_value": .01}),
    "Height Variation": ("NodeSocketFloat", .34, {"min_value": 0.0, "max_value": 1.0}),
    "Lean": ("NodeSocketFloat", 14.0, {"min_value": 0.0, "max_value": 60.0}),
    "Max Tufts": ("NodeSocketInt", 256, {"min_value": 0}),
    "Seed": ("NodeSocketInt", 1, {}),
}


def _link(tree, source, source_name, target, target_name):
    tree.links.new(source.outputs[source_name], target.inputs[target_name])


def _node(tree, kind, **props):
    node = tree.nodes.new(kind)
    for key, value in props.items():
        setattr(node, key, value)
    return node


def build_group():
    """Create (or rebuild) the ``SR_GroundCover`` node group."""
    old = bpy.data.node_groups.get(GROUP_NAME)
    if old is not None:
        bpy.data.node_groups.remove(old)
    tree = bpy.data.node_groups.new(GROUP_NAME, "GeometryNodeTree")
    interface = tree.interface
    for name, (kind, default, extra) in INPUTS.items():
        socket = interface.new_socket(name, in_out="INPUT", socket_type=kind)
        if default is not None:
            socket.default_value = default
        for key, value in extra.items():
            setattr(socket, key, value)
    interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    group_in = _node(tree, "NodeGroupInput")
    group_out = _node(tree, "NodeGroupOutput")

    # The ground, read from its own object so the host stays empty.
    terrain = _node(tree, "GeometryNodeObjectInfo", transform_space="RELATIVE")
    _link(tree, group_in, "Terrain", terrain, "Object")

    # Slope: a face is rootable when its normal is steep enough to stand on.
    normal = _node(tree, "GeometryNodeInputNormal")
    split = _node(tree, "ShaderNodeSeparateXYZ")
    _link(tree, normal, "Normal", split, "Vector")
    radians = _node(tree, "ShaderNodeMath", operation="RADIANS")
    _link(tree, group_in, "Slope Limit", radians, 0)
    cosine = _node(tree, "ShaderNodeMath", operation="COSINE")
    _link(tree, radians, "Value", cosine, 0)
    flat_enough = _node(tree, "FunctionNodeCompare", data_type="FLOAT",
                        operation="GREATER_EQUAL")
    _link(tree, split, "Z", flat_enough, "A")
    _link(tree, cosine, "Value", flat_enough, "B")

    # Painted density: the named vertex group, read as a float attribute.  An
    # empty group name means "unpainted, use the flat density everywhere".
    painted = _node(tree, "GeometryNodeInputNamedAttribute", data_type="FLOAT")
    _link(tree, group_in, "Density Group", painted, "Name")
    has_group = _node(tree, "FunctionNodeCompare", data_type="STRING",
                      operation="NOT_EQUAL")
    _link(tree, group_in, "Density Group", has_group, "A")
    has_group.inputs["B"].default_value = ""
    factor = _node(tree, "GeometryNodeSwitch", input_type="FLOAT")
    _link(tree, has_group, "Result", factor, "Switch")
    factor.inputs["False"].default_value = 1.0
    _link(tree, painted, "Attribute", factor, "True")

    # Poisson-disk distribution rather than uniform random: the Python scatter
    # used a jittered grid because pure random leaves visible clumps and bald
    # patches at these densities, and a minimum spacing gives the same even
    # coverage while density still varies freely with the painted weight.
    scatter = _node(tree, "GeometryNodeDistributePointsOnFaces",
                    distribute_method="POISSON")
    _link(tree, terrain, "Geometry", scatter, "Mesh")
    _link(tree, flat_enough, "Result", scatter, "Selection")
    _link(tree, group_in, "Density", scatter, "Density Max")
    _link(tree, factor, "Output", scatter, "Density Factor")
    _link(tree, group_in, "Seed", scatter, "Seed")
    mean_spacing = _node(tree, "ShaderNodeMath", operation="INVERSE_SQRT")
    _link(tree, group_in, "Density", mean_spacing, 0)
    min_spacing = _node(tree, "ShaderNodeMath", operation="MULTIPLY")
    _link(tree, mean_spacing, "Value", min_spacing, 0)
    min_spacing.inputs[1].default_value = MIN_SPACING_OF_MEAN
    _link(tree, min_spacing, "Value", scatter, "Distance Min")

    # Keep-out: flatten the footprint objects and the point to z = 0, then a
    # zero-ish distance means "inside the footprint".  This is the same
    # world-XY footprint the Python keep_out_mask used, but a lane may now be
    # any shape rather than a box.
    lane = _node(tree, "GeometryNodeCollectionInfo", transform_space="RELATIVE")
    lane.inputs["Separate Children"].default_value = False
    lane.inputs["Reset Children"].default_value = False
    _link(tree, group_in, "Keep Out", lane, "Collection")
    lane_real = _node(tree, "GeometryNodeRealizeInstances")
    _link(tree, lane, "Instances", lane_real, "Geometry")
    flat_lane = _node(tree, "GeometryNodeSetPosition")
    _link(tree, lane_real, "Geometry", flat_lane, "Geometry")
    position = _node(tree, "GeometryNodeInputPosition")
    lane_xy = _node(tree, "ShaderNodeCombineXYZ")
    lane_split = _node(tree, "ShaderNodeSeparateXYZ")
    _link(tree, position, "Position", lane_split, "Vector")
    _link(tree, lane_split, "X", lane_xy, "X")
    _link(tree, lane_split, "Y", lane_xy, "Y")
    _link(tree, lane_xy, "Vector", flat_lane, "Position")
    proximity = _node(tree, "GeometryNodeProximity", target_element="FACES")
    _link(tree, flat_lane, "Geometry", proximity, "Target")
    _link(tree, lane_xy, "Vector", proximity, "Source Position")
    near_lane = _node(tree, "FunctionNodeCompare", data_type="FLOAT",
                      operation="LESS_EQUAL")
    _link(tree, proximity, "Distance", near_lane, "A")
    _link(tree, group_in, "Keep Out Margin", near_lane, "B")
    # A keep-out with no objects has no faces; the proximity node reports that
    # as "not valid" rather than as a distance, so only a valid hit can cull.
    in_lane = _node(tree, "FunctionNodeBooleanMath", operation="AND")
    _link(tree, near_lane, "Result", in_lane, 0)
    _link(tree, proximity, "Is Valid", in_lane, 1)

    outside_lane = _node(tree, "GeometryNodeDeleteGeometry", domain="POINT")
    _link(tree, scatter, "Points", outside_lane, "Geometry")
    _link(tree, in_lane, "Boolean", outside_lane, "Selection")

    # Budget: the authored ceiling on tufts, replacing the live bridge's
    # per-request vertex cap as the thing that keeps a patch bounded.  Applied
    # after the keep-out so it counts tufts that are actually placed.
    index = _node(tree, "GeometryNodeInputIndex")
    over_budget = _node(tree, "FunctionNodeCompare", data_type="INT",
                        operation="GREATER_EQUAL")
    _link(tree, index, "Index", over_budget, "A")
    _link(tree, group_in, "Max Tufts", over_budget, "B")
    kept = _node(tree, "GeometryNodeDeleteGeometry", domain="POINT")
    _link(tree, outside_lane, "Geometry", kept, "Geometry")
    _link(tree, over_budget, "Result", kept, "Selection")

    # The cards: one child per atlas cell, picked per instance.
    cards = _node(tree, "GeometryNodeCollectionInfo", transform_space="ORIGINAL")
    cards.inputs["Separate Children"].default_value = True
    cards.inputs["Reset Children"].default_value = True
    _link(tree, group_in, "Cards", cards, "Collection")
    pick = _node(tree, "FunctionNodeRandomValue", data_type="INT")
    pick.inputs["Min"].default_value = 0
    pick.inputs["Max"].default_value = ATLAS_COLUMNS - 1
    _link(tree, group_in, "Seed", pick, "Seed")

    lean_radians = _node(tree, "ShaderNodeMath", operation="RADIANS")
    _link(tree, group_in, "Lean", lean_radians, 0)
    lean_draw = _node(tree, "FunctionNodeRandomValue", data_type="FLOAT")
    lean_draw.inputs["Min"].default_value = -1.0
    lean_draw.inputs["Max"].default_value = 1.0
    _node_seed = _node(tree, "ShaderNodeMath", operation="ADD")
    _link(tree, group_in, "Seed", _node_seed, 0)
    _node_seed.inputs[1].default_value = 101.0
    seed_int = _node(tree, "FunctionNodeFloatToInt", rounding_mode="ROUND")
    _link(tree, _node_seed, "Value", seed_int, "Float")
    _link(tree, seed_int, "Integer", lean_draw, "Seed")
    lean_amount = _node(tree, "ShaderNodeMath", operation="MULTIPLY")
    _link(tree, lean_draw, "Value", lean_amount, 0)
    _link(tree, lean_radians, "Value", lean_amount, 1)
    yaw = _node(tree, "FunctionNodeRandomValue", data_type="FLOAT")
    yaw.inputs["Min"].default_value = 0.0
    yaw.inputs["Max"].default_value = math.tau
    yaw_seed = _node(tree, "ShaderNodeMath", operation="ADD")
    _link(tree, group_in, "Seed", yaw_seed, 0)
    yaw_seed.inputs[1].default_value = 202.0
    yaw_int = _node(tree, "FunctionNodeFloatToInt", rounding_mode="ROUND")
    _link(tree, yaw_seed, "Value", yaw_int, "Float")
    _link(tree, yaw_int, "Integer", yaw, "Seed")
    euler = _node(tree, "ShaderNodeCombineXYZ")
    _link(tree, lean_amount, "Value", euler, "X")
    _link(tree, yaw, "Value", euler, "Z")

    # Height scales the unit card uniformly, so width follows height exactly as
    # the Python scatter's ``tuft * aspect`` did.
    spread = _node(tree, "FunctionNodeRandomValue", data_type="FLOAT")
    spread.inputs["Min"].default_value = -1.0
    spread.inputs["Max"].default_value = 1.0
    spread_seed = _node(tree, "ShaderNodeMath", operation="ADD")
    _link(tree, group_in, "Seed", spread_seed, 0)
    spread_seed.inputs[1].default_value = 303.0
    spread_int = _node(tree, "FunctionNodeFloatToInt", rounding_mode="ROUND")
    _link(tree, spread_seed, "Value", spread_int, "Float")
    _link(tree, spread_int, "Integer", spread, "Seed")
    varied = _node(tree, "ShaderNodeMath", operation="MULTIPLY")
    _link(tree, spread, "Value", varied, 0)
    _link(tree, group_in, "Height Variation", varied, 1)
    plus_one = _node(tree, "ShaderNodeMath", operation="ADD")
    _link(tree, varied, "Value", plus_one, 0)
    plus_one.inputs[1].default_value = 1.0
    height = _node(tree, "ShaderNodeMath", operation="MULTIPLY")
    _link(tree, plus_one, "Value", height, 0)
    _link(tree, group_in, "Tuft Height", height, 1)
    scale = _node(tree, "ShaderNodeCombineXYZ")
    for axis in ("X", "Y", "Z"):
        _link(tree, height, "Value", scale, axis)

    instance = _node(tree, "GeometryNodeInstanceOnPoints")
    _link(tree, kept, "Geometry", instance, "Points")
    _link(tree, cards, "Instances", instance, "Instance")
    instance.inputs["Pick Instance"].default_value = True
    _link(tree, pick, "Value", instance, "Instance Index")
    _link(tree, euler, "Vector", instance, "Rotation")
    _link(tree, scale, "Vector", instance, "Scale")

    realise = _node(tree, "GeometryNodeRealizeInstances")
    _link(tree, instance, "Instances", realise, "Geometry")
    _link(tree, realise, "Geometry", group_out, "Geometry")
    return tree


def build_cards(collection=None, *, columns: int = ATLAS_COLUMNS, aspect: float = TUFT_ASPECT):
    """One crossed-card source object per atlas cell, unit height, base at z = 0."""
    if collection is None:
        collection = bpy.data.collections.get(CARDS_COLLECTION)
        if collection is None:
            collection = bpy.data.collections.new(CARDS_COLLECTION)
    material = tree_material.grass_material()
    for cell in range(columns):
        name = "CARD_%d" % cell
        if bpy.data.objects.get(name) is not None:
            continue
        verts, faces, uvs = [], [], []
        for axis in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)):
            start = len(verts)
            verts.extend(card_corners((0.0, 0.0, .5), axis, (0.0, 0.0, 1.0), aspect, 1.0))
            faces.append((start, start + 1, start + 2, start + 3))
            uvs.extend(atlas_uvs(columns, cell))
        mesh = bpy.data.meshes.new(name + "_mesh")
        mesh.from_pydata([list(v) for v in verts], [], [list(f) for f in faces])
        mesh.update()
        layer = mesh.uv_layers.new(name="UVMap")
        for loop, coord in enumerate(uvs):
            layer.data[loop].uv = coord
        mesh.materials.append(material)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
    return collection


def configure(host, **values):
    """Set inputs on ``host``'s modifier by their interface names."""
    modifier = host.modifiers[GROUP_NAME]
    interface = modifier.node_group.interface
    identifiers = {item.name: item.identifier for item in interface.items_tree
                   if getattr(item, "in_out", None) == "INPUT"}
    for name, value in values.items():
        if name not in identifiers:
            raise KeyError("ground cover has no input %r" % name)
        getattr(modifier.properties.inputs, identifiers[name]).value = value
    # Setting a modifier input does not by itself dirty the object for the
    # depsgraph; without this an evaluation right after configure() is stale.
    host.update_tag()


def add(terrain, *, keep_out=None, cards=None, density_group="", parent_collection=None,
        **values):
    """Attach ground cover to ``terrain`` through a host object, and return it."""
    if terrain is None or terrain.type != "MESH":
        raise ValueError("terrain must be a mesh object")
    tree = bpy.data.node_groups.get(GROUP_NAME) or build_group()
    cards = cards or build_cards()
    if keep_out is None:
        keep_out = bpy.data.collections.get(KEEP_OUT_COLLECTION) or \
            bpy.data.collections.new(KEEP_OUT_COLLECTION)
    mesh = bpy.data.meshes.new(HOST_NAME + "_mesh")
    host = bpy.data.objects.new(HOST_NAME, mesh)
    for collection in (parent_collection or bpy.context.scene.collection,):
        collection.objects.link(host)
    modifier = host.modifiers.new(GROUP_NAME, "NODES")
    modifier.node_group = tree
    host.matrix_world = terrain.matrix_world.copy()
    configure(host, **{"Terrain": terrain, "Keep Out": keep_out, "Cards": cards,
                       "Density Group": density_group}, **values)
    return host


def evaluated_mesh(host):
    """The realised geometry as the depsgraph produces it (what an exporter sees)."""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return host.evaluated_get(depsgraph).to_mesh()
