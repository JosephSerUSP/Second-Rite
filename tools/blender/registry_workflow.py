"""Run a repeatable Registry experiment from an editable source into native review.

Each run requires a new output directory. Sources and shipping content are preserved.
Blender errors fail the run even when Blender would otherwise return zero.
"""
import argparse
import hashlib
import html
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_locator import blender_executable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--exit-y', type=float, required=True)
    parser.add_argument('--npc-y', type=float, required=True)
    parser.add_argument('--npc-x', type=float, default=0)
    parser.add_argument('--atlas-size', type=int, default=1024)
    parser.add_argument('--device', type=int, nargs=2, default=[2100,900])
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_file() or not output.is_relative_to(ROOT/'out') or output.exists():
        parser.error('Use an existing source and a new output directory inside out/')
    if any(not 0.35 <= y <= 7.4167 for y in (args.exit_y,args.npc_y)):
        parser.error('Registry anchors must fall within the interior lane')
    if args.atlas_size not in (256,512,1024,2048):
        parser.error('Choose atlas size 256, 512, 1024 or 2048')
    blender = blender_executable()
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    output.mkdir(parents=True)
    logs = output/'logs'; logs.mkdir()
    timings = []
    def step(name, command):
        print(f'[{name}] starting', flush=True)
        start = time.perf_counter()
        result = subprocess.run([str(c) for c in command], cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', errors='replace')
        duration = time.perf_counter()-start
        (logs/f'{name}.log').write_text(result.stdout+'\n'+result.stderr, encoding='utf-8')
        timings.append(dict(step=name,seconds=round(duration,3),exitCode=result.returncode))
        (output/'timings.json').write_text(json.dumps(timings,indent=2)+'\n',encoding='utf-8')
        print(f'[{name}] {duration:.2f}s; exit {result.returncode}', flush=True)
        if result.returncode:
            raise RuntimeError(f'{name} failed; see {logs/name}.log\n{result.stdout[-2000:]}{result.stderr[-500:]}')
    def blend(name, script, *arguments):
        step(name, [blender,'--background','--factory-startup','--disable-autoexec',
            '--python-exit-code','1','--python',ROOT/'tools/blender/offline_blender.py',
            '--',ROOT/'tools/blender'/script,'--',*arguments])
    package = output/'package'
    blend('export','export_room_environment.py','--blend',source,'--output',package,
          '--exit-y',args.exit_y,'--npc',f'registrar={args.npc_y}',
          '--npc-x',args.npc_x,
          '--ceiling','3.65','--atlas-size',args.atlas_size)
    stage = output/'stage'
    step('stage',['node',ROOT/'tools/blender/stage_registry_candidate.js',
                  '--output',stage,'--package',package])
    game = stage/'game'
    positions = sorted(set([0.35,args.npc_y,3.8833,args.exit_y,7.4167]))
    for mode in ('ui','world'):
        arguments = [sys.executable,ROOT/'tools/blender/capture_environment.py',
            '--game-root',game,'--output',output/'review'/mode,'--map-id','28',
            '--positions',*positions,'--device',*args.device]
        if mode=='world': arguments.append('--unobstructed')
        step('capture-'+mode, arguments)
    for surface in ('classic','four_three','wide','device'):
        blend('source-'+surface,'review_room_source.py','--source',source,
              '--frames',output/'review/world'/surface/'frames.json',
              '--output',output/'review/source'/surface,'--positions','3.8833')
    blend('source-clay','review_room_source.py','--source',source,
          '--frames',output/'review/world/wide/frames.json',
          '--output',output/'review/clay','--positions','3.8833','--clay')
    step('validate',['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    ROOT/'tools/golden/check-validate.ps1','-GameRoot',game])
    assert before==hashlib.sha256(source.read_bytes()).hexdigest(), 'Source changed during export/review'
    manifest=json.loads((package/'environment.json').read_text(encoding='utf-8'))
    evidence=dict(source=str(source),sourceSHA256=before,atlasSize=args.atlas_size,
        nominalDevice=args.device,positions=positions,timings=timings,
        stats=manifest['stats'],bake=manifest['provenance']['bake'],
        limitations=['Desktop device-aspect simulation; no physical-phone evidence',
                     'Staged replacement of map 28; shipping maps and topology unchanged',
                     'Source beauty excludes actors; native review includes retained Celina sprite',
                     'Visual and traversal acceptance remain owner review'])
    (output/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    cards=[]
    for surface in ('classic','four_three','wide','device'):
        cards.append(f'<h2>{surface}</h2><div class="row">'+''.join(
            f'<figure><img src="review/{kind}/{surface}/3.8833.png"><figcaption>{label}</figcaption></figure>'
            for kind,label in [('source','Source beauty, runtime camera'),('world','Native world'),('ui','Native with UI')])+'</div>')
        cards.append('<div class="row">'+''.join(
            f'<figure><img src="review/ui/{surface}/{y:g}.png"><figcaption>lane {y:g}</figcaption></figure>'
            for y in positions)+'</div>')
    page='<!doctype html><meta charset="utf-8"><title>Registry workflow review</title><style>body{background:#161719;color:#e9e1d5;font:16px system-ui;margin:24px} .row{display:flex;gap:16px;flex-wrap:wrap}figure{margin:8px 0}img{image-rendering:pixelated;max-width:100%;border:1px solid #555;width:auto;height:480px}figcaption{margin:8px 0}pre{white-space:pre-wrap}</style><h1>Passage Office / Registry</h1><p>Staged experiment. Device preview uses the runtime device-surface path at the supplied nominal aspect. Source views omit actors. No physical-phone or owner acceptance claimed.</p>'+''.join(cards)+'<h2>Source clay</h2><img src="review/clay/3.8833.png"><h2>Evidence</h2><pre>'+html.escape(json.dumps(evidence,indent=2))+'</pre>'
    (output/'review.html').write_text(page,encoding='utf-8')
    print(f'REGISTRY WORKFLOW OK: {output / "review.html"}', flush=True)


if __name__=='__main__':
    main()
