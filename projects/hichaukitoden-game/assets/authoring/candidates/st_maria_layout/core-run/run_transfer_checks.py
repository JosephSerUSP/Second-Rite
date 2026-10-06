import json,base64,subprocess,os,argparse,sys
from pathlib import Path
c=Path(__file__).resolve().parent;r=c.parents[6];g=r/'out/st-maria-playtest/game'
sys.path.insert(0,str(r))
from tools.blender.capture_environment import ERROR_HANDLER
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=c/'runtime/town-B18-transfers');args=parser.parse_args();folder=args.output;folder.mkdir(parents=True,exist_ok=True)
(g/'tests/transfer_frames.lua').write_bytes((c/'transfer_frames.lua').read_bytes());p=g/'main.lua';original=p.read_bytes();marker=b'cli_tools.runTownProofFrames(loader)';assert original.count(marker)==1
try:
 p.write_bytes(ERROR_HANDLER+original.replace(marker,b'local ok,err=pcall(require("tests.transfer_frames").run,loader);if not ok then print("TRANSFER FRAMES FAILED "..tostring(err));love.event.quit(1) end'))
 result=subprocess.run([os.environ.get('LOVEC_PATH','C:/Program Files/LOVE/lovec.exe'),str(g),'town-proof-frames'],cwd=g,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=120);(folder/'capture.log').write_text(result.stdout+result.stderr,encoding='utf8');assert result.returncode==0 and 'TRANSFER FRAMES BEGIN' in result.stdout,result.stdout[-2500:]
 frames=json.loads(result.stdout.split('TRANSFER FRAMES BEGIN')[1].split('TRANSFER FRAMES END')[0])
 for f in frames:(folder/(f['label']+'.png')).write_bytes(base64.b64decode(f.pop('image')))
 labels=[f['label'] for f in frames]
 assert frames and len(labels)==len(set(labels)) and all(f['boundaryChecks']>0 for f in frames)
 (folder/'captures.json').write_text(json.dumps(frames,indent=2)+'\n',encoding='utf8');print('TRANSFER CHECKS OK',len(frames),'zones;',sum(f['boundaryChecks'] for f in frames),'boundary checks')
finally:p.write_bytes(original)
