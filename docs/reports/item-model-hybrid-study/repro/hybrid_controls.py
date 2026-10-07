"""Disposable exact-OBJ controls: replace atlas/UV gain with allocation mean RGB."""
from pathlib import Path
import json,shutil,re
src=Path('out/work/hybrid-products');dest=Path('out/work/hybrid-plain-products');dest.mkdir(exist_ok=True)
colours=json.loads(Path('out/work/hybrid/plain-colours.json').read_text())
for path in src.glob('*.obj'):
 shutil.copy2(path,dest/path.name);stem=path.stem;direction=stem.split('_')[1]
 mtl=path.with_suffix('.mtl').read_text();parts=re.split(r'(?=^newmtl )',mtl,flags=re.M);output=[]
 for part in parts:
  lines=part.splitlines()
  if not any(l.startswith('map_Kd ') for l in lines):output.append(part);continue
  name=lines[0].split(maxsplit=1)[1];role=name.removeprefix(stem+'_');colour=colours[direction+'_'+role]
  kept=[l for l in lines if not l.startswith(('map_Kd ','Kd ','pass uv '))]
  kept.insert(1,'Kd '+' '.join(format(c,'.6f') for c in colour));output.append('\n'.join(kept)+'\n')
 (dest/path.with_suffix('.mtl').name).write_text(''.join(output).rstrip()+'\n',encoding='utf-8',newline='\n')
 assert (dest/path.name).read_bytes()==path.read_bytes()
print('EXACT OBJ MATERIAL CONTROLS OK: sphere passes retained; original sources and generated pixels untouched')
