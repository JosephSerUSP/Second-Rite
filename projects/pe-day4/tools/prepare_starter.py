#!/usr/bin/env python3
"""Verify, stage and probe a playable Hospital starter through canonical tools."""
import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'out/hospital-start/prepared')
    parser.add_argument('--lovec', type=Path, default=Path('C:/Program Files/LOVE/lovec.exe'))
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to(ROOT / 'out'), 'preparation output must stay under repository out/'
    assert args.lovec.is_file(), 'provide the LOVE console executable with --lovec'
    output.mkdir(parents=True, exist_ok=True)
    results = []

    def run(label, command, timeout=120, expected=0):
        log = output / (label + '.log')
        started = time.perf_counter()
        with log.open('w', encoding='utf8') as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        duration = (time.perf_counter() - started) * 1000
        subprocess.run(['node', 'tools/ci/time-step.js', '--record', '--label', 'hospital ' + label,
                        '--ms', str(round(duration)), '--exit', str(result.returncode)], cwd=ROOT, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        results.append({'label': label, 'exitCode': result.returncode, 'milliseconds': round(duration), 'log': log.name})
        assert result.returncode == expected, f'{label} failed; inspect {log}'
        print(label + ' OK', flush=True)
        return log

    tools = PROJECT / 'tools'
    for label, script, extra in [
        ('reference', tools / 'verify_reference.py', []),
        ('reference-negative-controls', tools / 'test_reference.py', []),
        ('generated-data', tools / 'compile_starter.py', ['--check']),
        ('standalone-boundary', tools / 'verify_starter.py', []),
        ('source-authority', ROOT / 'tools/blender/environment_sources.py', ['--check', '--root', str(PROJECT)]),
        ('lit-products', ROOT / 'projects/experiments/continuous-surface-gauntlet/tools/check_lighting.py', ['--project', str(PROJECT)]),
        ('compiled-character', ROOT / 'tools/characters/compile_character.py', [str(PROJECT / 'assets/authoring/characters/surveyor.glb'), '--out', str(PROJECT / 'assets/characters/surveyor'), '--check']),
    ]:
        run(label, [sys.executable, str(script), *extra])
    stage = output / 'play'
    run('stage', ['node', 'tools/ci/stage-project-gates.js', '--project', str(PROJECT), '--output', str(stage)])
    run('validate', [str(args.lovec), str(stage), 'validate'])
    shutil.copyfile(stage / 'main.lua', stage / 'player-main.lua')
    shutil.copyfile(tools / 'starter-proof.lua', stage / 'main.lua')
    try:
        log = run('native-input', [str(args.lovec), str(stage), 'surface=wide'], timeout=90)
        text = log.read_text(encoding='utf8', errors='replace')
        assert 'HOSPITAL STARTER INPUT TRANSFER AND SAVE OK' in text, 'native completion marker missing'
        assert '[formula] error' not in text, 'formula diagnostic in actual player host'
        frames = set()
        for line in text.splitlines():
            if line.startswith('HOSPITAL FRAME '):
                _, _, label, data = line.split(' ', 3)
                assert label in {'entrance', 'basement'}, 'unexpected frame label'
                (output / (label + '.png')).write_bytes(base64.b64decode(data, validate=True))
                frames.add(label)
        assert frames == {'entrance', 'basement'}, 'native captures incomplete'
        # A severed authored transfer must fail actual input, not merely the
        # Python reference graph. Corrupt only the disposable stage and restore.
        map_path = stage / 'data/maps.json'
        original = map_path.read_bytes()
        data = json.loads(original)
        def sever(value):
            if isinstance(value, dict):
                if value.get('cmd') == 'LOAD_MAP' and value.get('mapId') == 4:
                    value['mapId'] = 1
                    return 1
                return sum(sever(child) for child in value.values())
            if isinstance(value, list): return sum(sever(child) for child in value)
            return 0
        assert sever(data) == 1, 'negative control did not locate the basement transfer'
        try:
            map_path.write_text(json.dumps(data), encoding='utf8')
            negative = run('native-severed-transfer', [str(args.lovec), str(stage), 'surface=wide'], timeout=90, expected=1)
            assert 'elevator did not reach basement' in negative.read_text(encoding='utf8', errors='replace'), 'negative control failed for an unrelated reason'
        finally:
            map_path.write_bytes(original)
    finally:
        shutil.copyfile(stage / 'player-main.lua', stage / 'main.lua')
    report = {'mode': 'traversal starter with original proxy art', 'mechanicalCombatAccepted': False,
              'ownerPlayAccepted': False, 'stage': str(stage), 'checks': results}
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(f'HOSPITAL STARTER PREPARED: {stage}\nCombat/resource calibration remains separate.', flush=True)


if __name__ == '__main__':
    main()
