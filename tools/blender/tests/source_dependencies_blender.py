"""Exercise real Blender relative-image relocation and packed-source recovery."""
import sys
import tempfile
from pathlib import Path
import bpy

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import source_dependencies

with tempfile.TemporaryDirectory(prefix='source-dependencies-') as directory:
    root=Path(directory);original=root/'original';original.mkdir();moved=root/'moved';moved.mkdir()
    image=bpy.data.images.new('Fixture',width=2,height=2)
    image.filepath_raw=str(original/'texture.png');image.file_format='PNG';image.save()
    texture=bpy.data.images.load(str(original/'texture.png'));texture.filepath='//texture.png'
    material=bpy.data.materials.new('Fixture');material.use_nodes=True
    node=material.node_tree.nodes.new('ShaderNodeTexImage');node.image=texture
    material.node_tree.links.new(node.outputs['Color'],material.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    bpy.ops.mesh.primitive_plane_add();bpy.context.object.data.materials.append(material)
    bpy.ops.wm.save_as_mainfile(filepath=str(original/'source.blend'))
    assert not source_dependencies.assert_available()[0]['packed']
    # Opening a byte-for-byte copy from a different directory breaks //texture.png.
    relocated=moved/'broken.blend';relocated.write_bytes((original/'source.blend').read_bytes())
    bpy.ops.wm.open_mainfile(filepath=str(relocated))
    try:source_dependencies.assert_available()
    except ValueError as error:assert 'dependencies missing' in str(error)
    else:raise AssertionError('Relocated missing image silently accepted')
    bpy.ops.wm.open_mainfile(filepath=str(original/'source.blend'))
    bpy.data.images['texture.png'].pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(moved/'packed.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(moved/'packed.blend'))
    records=source_dependencies.assert_available()
    assert len(records)==1 and records[0]['packed']
    print('SOURCE DEPENDENCY REGRESSION OK')
