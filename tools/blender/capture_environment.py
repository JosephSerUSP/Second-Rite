"""Capture one staged environment at real runtime surfaces, including device ratios."""
import argparse
import base64
import json
import math
import subprocess
from pathlib import Path


ERROR_HANDLER = b'''\nlove.errorhandler = function(message)
  io.stderr:write("ENVIRONMENT CAPTURE ERROR\\n" .. debug.traceback(tostring(message), 2) .. "\\n")
  io.stderr:flush()
  return function() return 1 end
end
'''


def validate_visible_environment(surface_name, frames):
    """Reject review payloads whose native viewport is effectively empty.

    The capture frame itself may contain UI/Walker pixels, so the staged Lua
    probe reports a viewport-only visible-pixel count through the production
    compositor. Two percent is deliberately conservative for an environment
    review: it rejects the ~Walker-sized remnant from #1393 while staying far
    below the tens of thousands of pixels occupied by a real room.
    """
    for frame in frames:
        width = frame.get('width')
        height = frame.get('height')
        visible = frame.get('viewportVisiblePixels')
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            raise RuntimeError(f'{surface_name}: runtime omitted valid frame dimensions')
        if not isinstance(visible, int) or visible < 0:
            raise RuntimeError(f'{surface_name}: runtime omitted viewport visibility evidence')
        minimum = max(1024, math.ceil(width * height * 0.02))
        if visible < minimum:
            y = frame.get('y', '?')
            raise RuntimeError(
                f'{surface_name}: environment viewport is effectively empty at y={y} '
                f'({visible} visible pixels; expected at least {minimum})')


def capture(args):
    """Prepare a disposable stage, capture, and restore every borrowed file."""
    root = args.game_root.resolve()
    repository = Path(__file__).resolve().parents[2]
    if not root.is_relative_to(repository / 'out'):
        raise ValueError('Capture hooks may only modify a disposable stage inside repository out/')
    if args.output.exists():
        raise ValueError('Use a new capture output directory to preserve previous evidence')
    main_path = root / 'main.lua'
    config_path = root / 'environment-review.json'
    probe_path = root / 'tests/environment_frames.lua'
    probe_source = repository / 'tools/blender/tests/environment_frames.lua'
    # Preflight all dependencies and the hook before the first stage mutation.
    probe = probe_source.read_bytes()
    original = main_path.read_bytes()
    old_config = config_path.read_bytes() if config_path.exists() else None
    old_probe = probe_path.read_bytes() if probe_path.exists() else None
    had_tests = probe_path.parent.exists()
    marker = b'cli_tools.runTownProofFrames(loader)'
    if original.count(marker) != 1:
        raise ValueError('Native capture boundary changed')
    try:
        probe_path.parent.mkdir(exist_ok=True)
        # An existing probe is a caller-owned stage dependency; retain it.
        if old_probe is None:
            probe_path.write_bytes(probe)
        main_path.write_bytes(ERROR_HANDLER + original.replace(marker, b'require("tests.environment_frames").run(loader)'))
        for name in ('classic', 'four_three', 'wide', 'device'):
            config = dict(mapId=args.map_id, positions=args.positions, unobstructed=args.unobstructed)
            config.update(device=args.device) if name == 'device' else config.update(surface=name)
            config_path.write_text(json.dumps(config), encoding='utf-8')
            try:
                result = subprocess.run([args.lovec, str(root), 'surface=classic', 'town-proof-frames'],
                    cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError(f'{name}: environment capture exceeded 120 seconds') from error
            if result.returncode:
                raise RuntimeError(f'{name}: environment capture exited {result.returncode}\n' +
                    result.stdout[-3000:] + result.stderr[-3000:])
            start, end = 'ENVIRONMENT FRAMES BEGIN', 'ENVIRONMENT FRAMES END'
            if result.stdout.count(start) != 1 or result.stdout.count(end) != 1:
                raise RuntimeError(f'{name}: runtime did not emit one complete environment frame payload\n' + result.stdout[-3000:])
            payload = result.stdout.split(start, 1)[1].split(end, 1)[0]
            frames = json.loads(payload)
            if not isinstance(frames, list) or not frames:
                raise RuntimeError(f'{name}: runtime emitted no environment frames')
            validate_visible_environment(name, frames)
            # Decode the complete surface before creating its evidence folder.
            images = [(frame_name(frame), base64.b64decode(frame.pop('image'), validate=True)) for frame in frames]
            output = args.output / name
            output.mkdir(parents=True)
            for filename, data in images:
                (output / filename).write_bytes(data)
            (output / 'frames.json').write_text(json.dumps(dict(config=config, frames=frames), indent=2)+'\n', encoding='utf-8')
    finally:
        main_path.write_bytes(original)
        if old_config is None:
            config_path.unlink(missing_ok=True)
        else:
            config_path.write_bytes(old_config)
        if old_probe is None:
            probe_path.unlink(missing_ok=True)
        else:
            probe_path.write_bytes(old_probe)
        if not had_tests:
            probe_path.parent.rmdir()
    return args.output


def position(text):
    # A bare number is a lane Y on the current level; LEVEL:Y names a storey.
    level, separator, y = text.rpartition(':')
    return dict(level=level, y=float(y)) if separator else float(text)


def frame_name(frame):
    return f"{frame['level']}_{frame['y']:g}.png" if frame.get('level') else f"{frame['y']:g}.png"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--map-id', type=int, required=True)
    parser.add_argument('--positions', type=position, nargs='+', required=True,
        help='lane Y, or LEVEL:Y on a map with storeys (e.g. gallery:6.0)')
    parser.add_argument('--unobstructed', action='store_true')
    parser.add_argument('--device', type=int, nargs=2, default=[2100, 900], metavar=('WIDTH','HEIGHT'))
    parser.add_argument('--lovec', default=r'C:\Program Files\LOVE\lovec.exe')
    args = parser.parse_args()
    try:
        capture(args)
    except ValueError as error:
        parser.error(str(error))
    print('ENVIRONMENT NATIVE REVIEW OK')


if __name__ == '__main__':
    main()
