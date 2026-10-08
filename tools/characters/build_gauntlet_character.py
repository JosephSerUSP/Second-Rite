"""Rebuild the gauntlet actor through the existing external chara-compiler.

Sources are read-only; all Blender intermediates stay under out/. A full rebuild
requires the compiler checkout and the owner's animation source. Portable
checks need only the committed GLB and compile_character.py --check.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from compile_character import compile_glb

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'projects/experiments/continuous-surface-gauntlet'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiler', type=Path, default=Path('V:/Projects/tools/chara-compiler'))
    p.add_argument('--animation-source', type=Path,
                   default=Path('G:/Meu Drive/DOCUMENTS/idea/Sairen no Hiiro/Rio/Rio.blend'))
    p.add_argument('--out', type=Path, default=ROOT / 'out/continuous-character/rebuild')
    args = p.parse_args()
    compiler, source, out = args.compiler.resolve(), args.animation_source.resolve(), args.out.resolve()
    if not (compiler / 'chara/cli.py').is_file() or not source.is_file():
        raise ValueError('compiler checkout and authored animation source must exist')
    revision = subprocess.check_output(['git', '-C', str(compiler), 'rev-parse', 'HEAD'], text=True).strip()
    out.mkdir(parents=True, exist_ok=True)
    spec = PROJECT / 'assets/authoring/characters/surveyor.spec.json'
    built, idle, animated, glb = [out / f for f in ('actor.blend', 'idle.blend', 'animated.blend', 'surveyor.glb')]
    commands = [
        ['build', str(spec), '--lib', str(compiler / 'library/animagrid'), '--out', str(built)],
        ['retarget', str(built), str(source), 'Idle', '--map', 'mixamo', '--out', str(idle)],
        ['retarget', str(idle), str(source), 'Walk', '--map', 'mixamo', '--out', str(animated)],
        ['export', str(animated), '--names', 'semantic', '--out', str(glb)],
    ]
    source_before = sha(source)
    steps = []
    for command in commands:
        result = subprocess.run([sys.executable, '-m', 'chara.cli', *command], cwd=compiler,
                                capture_output=True, text=True)
        print(result.stdout, end=''); print(result.stderr, end='', file=sys.stderr)
        result.check_returncode()
        steps.append({'command': command[0], 'output': result.stdout.strip()})
    if sha(source) != source_before:
        raise ValueError('authored animation source changed during compilation')
    bundle, images = compile_glb(glb)
    runtime = out / 'runtime'
    runtime.mkdir(exist_ok=True)
    (runtime / 'character.json').write_bytes((json.dumps(bundle, separators=(',', ':'), allow_nan=False) + '\n').encode())
    for name, data in images.items():
        (runtime / name).write_bytes(data)
    library = {str(f.relative_to(compiler)).replace('\\', '/'): sha(f)
               for f in sorted((compiler / 'library/animagrid').rglob('*')) if f.is_file()}
    record = {'compiler': {'repository': 'JosephSerUSP/chara-compiler', 'revision': revision},
              'specSha256': sha(spec), 'librarySha256': library,
              'animationSource': {'path': str(source), 'sha256': source_before, 'clips': ['Idle', 'Walk'], 'mapping': 'mixamo'},
              'glbSha256': sha(glb), 'buildReport': json.loads(built.with_suffix('.report.json').read_text()),
              'steps': steps}
    (out / 'build.json').write_bytes((json.dumps(record, indent=2) + '\n').encode())
    print(f'CHARACTER BUILD OK: {glb}\nRuntime bundle: {runtime}')


if __name__ == '__main__':
    main()
