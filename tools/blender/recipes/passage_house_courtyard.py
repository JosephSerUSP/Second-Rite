"""Build a fresh Passage House scaffold from connected architectural assemblies."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.shared.project_paths import project_root
PROJECT = project_root()
sys.path.insert(0,str(ROOT/'tools/blender'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
OUTPUT=PROJECT / 'assets/authoring/environments/passage_house_courtyard.blend'

def build(output, *, map_data=None, profile_authority='data/maps/32.json'):
    from courtyard_scene import build as build_scene
    return build_scene(output, map_data=map_data, profile_authority=profile_authority)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--map-source',type=Path,help='Explicit scaffold Map JSON; required when its former shipping map is retired')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    options={}
    if args.map_source:
        options=dict(map_data=json.loads(args.map_source.read_text(encoding='utf-8')),profile_authority=str(args.map_source))
    build(args.output.resolve(),**options)
