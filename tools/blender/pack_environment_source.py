"""Save a new self-contained source revision from a working source document."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
import environment_sources
import source_dependencies


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if args.output.exists(): parser.error('Refusing to overwrite an existing source')
    environment_sources.refuse_superseded(args.source)
    environment_sources.refuse_superseded(args.output)
    before=hashlib.sha256(args.source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    records=source_dependencies.assert_available()
    if bpy.data.libraries: raise ValueError('Make linked libraries local before requesting a self-contained source')
    for image in bpy.data.images:
        if image.source=='FILE' and image.filepath:
            image.pack()
    source_dependencies.assert_available()
    if any(not r['packed'] for r in source_dependencies.assert_available()):
        raise ValueError('Source still has unpacked image dependencies')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    assert before==hashlib.sha256(args.source.read_bytes()).hexdigest()
    (args.output.with_suffix('.dependencies.json')).write_text(json.dumps(dict(
        originalSource=str(args.source),originalSHA256=before,dependencies=records,
        outputSHA256=hashlib.sha256(args.output.read_bytes()).hexdigest(),packed=True),indent=2)+'\n',encoding='utf-8')
    print('PACKED ENVIRONMENT SOURCE OK')


if __name__=='__main__':main()
