"""World-scale procedural finishes for authored environment studies.

These bind existing semantic materials and bake through the normal room exporter.
Palette inputs are sRGB; shader inputs are linear. No external texture dependencies.
"""
import bpy

def linear(rgb):
    return tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb)

def finish(name, base, *, colours, scale=3, grain=(1,1,1), relief=.008,
           roughness=.8, wear=None):
    mat=base.copy();mat.name=name
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    nodes.clear()
    out=nodes.new('ShaderNodeOutputMaterial');bsdf=nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    geometry=nodes.new('ShaderNodeNewGeometry')
    mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY'
    mapping.inputs[1].default_value=grain
    links.new(geometry.outputs['Position'],mapping.inputs[0])
    noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=scale
    noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.72
    links.new(mapping.outputs['Vector'],noise.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB')
    for element,c in zip(ramp.color_ramp.elements,colours):element.color=(*linear(c),1)
    ramp.color_ramp.elements[0].position=.22;ramp.color_ramp.elements[1].position=.78
    links.new(noise.outputs['Fac'],ramp.inputs[0])
    colour=ramp.outputs['Color']
    if wear:
        spots=nodes.new('ShaderNodeTexNoise');spots.inputs['Scale'].default_value=7
        spots.inputs['Detail'].default_value=2
        links.new(geometry.outputs['Position'],spots.inputs['Vector'])
        threshold=nodes.new('ShaderNodeValToRGB')
        threshold.color_ramp.elements[0].position=.68
        threshold.color_ramp.elements[1].position=.77
        links.new(spots.outputs['Fac'],threshold.inputs[0])
        mix=nodes.new('ShaderNodeMixRGB');mix.inputs[2].default_value=(*linear(wear),1)
        links.new(threshold.outputs['Color'],mix.inputs[0]);links.new(colour,mix.inputs[1])
        colour=mix.outputs['Color']
    links.new(colour,bsdf.inputs['Base Color'])
    micro=nodes.new('ShaderNodeTexNoise');micro.inputs['Scale'].default_value=95
    links.new(mapping.outputs['Vector'],micro.inputs['Vector'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.32
    bump.inputs['Distance'].default_value=relief
    links.new(micro.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value=roughness
    mat.diffuse_color=(*linear(colours[1]),1)
    mat['sr_finish_description']='World-space mottled pigment and micro-relief; authored finish variant'
    return mat
