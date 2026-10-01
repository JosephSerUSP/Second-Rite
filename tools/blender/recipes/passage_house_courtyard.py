"""Build a fresh Passage House scaffold from connected architectural assemblies."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/blender'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
OUTPUT=ROOT/'projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend'

def build(output):
    from courtyard_scene import build as build_scene
    return build_scene(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);build(args.output.resolve())
