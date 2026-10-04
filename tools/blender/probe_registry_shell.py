import sys,json
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fit_registry_ceiling import bounds
bpy.ops.wm.open_mainfile(filepath=str(Path(sys.argv[-1]).resolve()))
print('SHELL BOUNDS '+json.dumps({o.name:bounds(o) for o in bpy.data.objects if o.type=='MESH' and (o.name=='ceiling' or o.name.startswith(('side_wall','back_wall','ceiling_beam')))}))
