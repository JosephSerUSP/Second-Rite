"""Real Blender: report bounds after lazy translation, rotation and parent edit."""
import contextlib
import io
import json
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy
import item_kit as kit

root=kit.begin('report_fixture','test','lazy transform bound fixture')
vertices=[(x,y,z) for x in (-1,1) for y in (-.5,.5) for z in (-.25,.25)]
ob=kit.mesh_object('head',vertices,[],root)
bpy.context.view_layer.update()
ob.location=(3,0,5)
ob.rotation_euler.y=math.pi/2
root.location=(1,2,0)
stream=io.StringIO()
with contextlib.redirect_stdout(stream):kit.report(root)
result=json.loads(stream.getvalue().removeprefix('ITEM KIT RESULT ').strip())
assert result['min']==[3.75,1.5,4.0],result
assert result['max']==[4.25,2.5,6.0],result
assert result['meshObjects']==1,result
print('ITEM KIT CURRENT TRANSFORM BOUNDS OK')
