"""Capture the staged courtyard through the native compositor; never recapture goldens."""
import argparse
import base64
import json
import subprocess
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--game-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--lovec',default=r'C:\Program Files\LOVE\lovec.exe')
    args=parser.parse_args()
    for surface in ('classic','wide'):
        result=subprocess.run([args.lovec,str(args.game_root.resolve()),f'surface={surface}','town-proof-frames'],
            cwd=args.game_root,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        if result.returncode:raise RuntimeError(result.stdout[-3000:]+result.stderr[-1000:])
        payload=result.stdout.split('COURTYARD FRAMES BEGIN',1)[1].split('COURTYARD FRAMES END',1)[0]
        frames=json.loads(payload)
        output=args.output/surface;output.mkdir(parents=True,exist_ok=True)
        for frame in frames:
            (output/f"{frame['y']:g}.png").write_bytes(base64.b64decode(frame.pop('image')))
        (output/'frames.json').write_text(json.dumps(frames,indent=2)+'\n',encoding='utf-8')
    print('COURTYARD NATIVE REVIEW OK')

if __name__=='__main__':main()
