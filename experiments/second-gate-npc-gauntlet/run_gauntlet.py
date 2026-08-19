"""Host-side reproducible build, contact sheets, and sprite-contract validation."""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parent; G=ROOT/'gauntlet'; BLENDER=Path(r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe')
def sheet(paths,out,cols=8,scale=2,title=''):
 imgs=[Image.open(p).convert('RGBA') for p in paths]; w,h=192*scale,192*scale; rows=(len(imgs)+cols-1)//cols
 dst=Image.new('RGBA',(cols*w,rows*h+28),(30,28,38,255));d=ImageDraw.Draw(dst);d.text((8,5),title,fill=(240,235,220,255))
 for n,img in enumerate(imgs):dst.alpha_composite(img.resize((w,h),Image.Resampling.NEAREST),(n%cols*w,28+n//cols*h))
 dst.save(out)
def build():
 subprocess.run([str(BLENDER),'--background','--factory-startup','--python',str(ROOT/'build_blender.py')],check=True)
 for k in ('celina','agnes','gambler'):
  f=G/k/'final'; idle=sorted(f.glob('idle_*.png'));walk=sorted(f.glob('walk_*.png'));ges=sorted(f.glob('gesture_*.png'))
  sheet(idle,G/k/'idle_sheet.png',8,2,k+' idle');sheet(walk,G/k/'walk_sheet.png',8,1,k+' eight-direction walk');sheet(ges,G/k/'gesture_sheet.png',10,2,k+' signature gesture')
  sheet([f/'idle_00.png'],G/k/'native.png',1,1,k+' native scale')
 ensemble=[G/k/'final'/'idle_00.png' for k in ('celina','agnes','gambler')];sheet(ensemble,G/'lineup_native.png',3,1,'Celina / Agnes / Gambler');sheet(ensemble,G/'lineup_2x.png',3,2,'Celina / Agnes / Gambler - 2x nearest')
 # silhouettes retain exact alpha and expose silhouette distinction.
 sil=[]
 for p in ensemble:
  im=Image.open(p).convert('RGBA'); a=im.getchannel('A'); x=Image.new('RGBA',im.size,(0,0,0,0));x.putalpha(a);q=G/(p.parent.parent.name+'_silhouette.png');x.save(q);sil.append(q)
 sheet(sil,G/'lineup_silhouette.png',3,2,'silhouette comparison')
 validate()
def validate():
 errors=[];report={}
 for k in ('celina','agnes','gambler'):
  fs=sorted((G/k/'final').glob('*.png')); report[k]={'frames':len(fs),'anchor':[96,176]}
  if len(fs)!=100:errors.append(k+' needs 100 frames')
  for p in fs:
   im=Image.open(p).convert('RGBA')
   if im.size!=(192,192) or im.getchannel('A').getbbox() is None:errors.append(str(p)+' invalid RGBA')
   box=im.getchannel('A').getbbox()
   if box and box[3]>177:errors.append(str(p)+' anchor/ground exceeds y=176')
   if box and box[3]-box[1]>128 and not p.name.startswith('gesture_'):errors.append(str(p)+' standing height exceeds 128px')
 (G/'technical_validation.json').write_text(json.dumps({'pass':not errors,'report':report,'errors':errors},indent=2));
 if errors: raise SystemExit('\n'.join(errors))
if __name__=='__main__':
 if len(sys.argv)<2 or sys.argv[1]!='build':raise SystemExit('usage: run_gauntlet.py build')
 build()
