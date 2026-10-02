"""Capture one staged environment at real runtime surfaces, including device ratios."""
import argparse
import base64
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--map-id', type=int, required=True)
    parser.add_argument('--positions', type=float, nargs='+', required=True)
    parser.add_argument('--unobstructed', action='store_true')
    parser.add_argument('--device', type=int, nargs=2, default=[2100, 900], metavar=('WIDTH','HEIGHT'))
    parser.add_argument('--lovec', default=r'C:\Program Files\LOVE\lovec.exe')
    args = parser.parse_args()
    root = args.game_root.resolve()
    repository = Path(__file__).resolve().parents[2]
    if not root.is_relative_to(repository / 'out'):
        parser.error('Capture hooks may only modify a disposable stage inside repository out/')
    if args.output.exists():
        parser.error('Use a new capture output directory to preserve previous evidence')
    main_path = root / 'main.lua'
    config_path = root / 'environment-review.json'
    original = main_path.read_bytes()
    old_config = config_path.read_bytes() if config_path.exists() else None
    marker = b'cli_tools.runTownProofFrames(loader)'
    if original.count(marker) != 1:
        raise ValueError('Native capture boundary changed')
    try:
        main_path.write_bytes(original.replace(marker, b'require("tests.environment_frames").run(loader)'))
        for name in ('classic', 'four_three', 'wide', 'device'):
            config = dict(mapId=args.map_id, positions=args.positions, unobstructed=args.unobstructed)
            config.update(device=args.device) if name == 'device' else config.update(surface=name)
            config_path.write_text(json.dumps(config), encoding='utf-8')
            result = subprocess.run([args.lovec, str(root), 'surface=classic', 'town-proof-frames'],
                                    cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
            if result.returncode:
                raise RuntimeError(result.stdout[-3000:] + result.stderr[-1000:])
            payload = result.stdout.split('ENVIRONMENT FRAMES BEGIN', 1)[1].split('ENVIRONMENT FRAMES END', 1)[0]
            frames = json.loads(payload)
            output = args.output / name
            output.mkdir(parents=True, exist_ok=True)
            for frame in frames:
                (output / f"{frame['y']:g}.png").write_bytes(base64.b64decode(frame.pop('image')))
            (output / 'frames.json').write_text(json.dumps(dict(config=config, frames=frames), indent=2)+'\n', encoding='utf-8')
    finally:
        main_path.write_bytes(original)
        if old_config is None:
            config_path.unlink(missing_ok=True)
        else:
            config_path.write_bytes(old_config)
    print('ENVIRONMENT NATIVE REVIEW OK')


if __name__ == '__main__':
    main()
