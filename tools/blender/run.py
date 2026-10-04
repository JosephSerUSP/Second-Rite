"""Run one Blender-side script in the pinned Blender, failing loudly.

    python tools/blender/run.py SCRIPT.py [--blend FILE.blend] [-- SCRIPT ARGS...]

Use this instead of typing a ``blender --background ...`` command. It exists
because the hand-typed command has a trap: **Blender exits 0 when the script
raises**, unless ``--python-exit-code`` is passed. A traceback scrolls past, the
shell reports success, and the failed run reads as a pass. This launcher:

* finds Blender only through ``blender_locator`` (``$BLENDER_EXECUTABLE``,
  version-asserted against ``blender-pin.json``);
* always runs ``--background --factory-startup --python-exit-code 1``;
* opens ``--blend FILE`` first when the script edits or reads a document;
* passes everything after ``--`` to the script unchanged;
* exits with Blender's exit code, and names the failure on stderr.

``--dry-run`` prints the command as JSON without needing Blender.

Scripts that do not ``import bpy`` are host tools: run them with ``python``
directly. ``SCRIPTS.md`` says which is which in its "Run with" column.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import blender_locator  # noqa: E402

# The flags every headless run gets. ``--python-exit-code 1`` is the point.
BASE_FLAGS = ("--background", "--factory-startup", "-noaudio", "--python-exit-code", "1")


def resolve(path: str, label: str) -> Path:
    """``path`` as given, else relative to the installation root or this folder."""
    for candidate in (Path(path), ROOT / path, HERE / path):
        if candidate.is_file():
            return candidate.resolve()
    raise SystemExit(f"run.py: {label} not found: {path} "
                     f"(tried it as given, from {ROOT} and from {HERE})")


def command(executable: str, script: Path, script_args=(), blend: Path | None = None) -> list[str]:
    """The full Blender argument list for one fail-loud headless run."""
    head = [executable, *BASE_FLAGS]
    if blend is not None:
        head.append(str(blend))
    return [*head, "--python", str(script), "--", *script_args]


def split_arguments(argv):
    """Everything before the first ``--`` is ours; everything after is the script's."""
    if "--" in argv:
        at = argv.index("--")
        return argv[:at], argv[at + 1:]
    return argv, []


def main(argv=None) -> int:
    ours, script_args = split_arguments(list(sys.argv[1:] if argv is None else argv))
    parser = argparse.ArgumentParser(
        prog="python tools/blender/run.py",
        description="Run a Blender-side script in the pinned Blender; a Python error "
                    "becomes a non-zero exit. Arguments after -- go to the script.")
    parser.add_argument("script", help="the bpy script, e.g. tools/blender/recipes/alicias_padaria.py")
    parser.add_argument("--blend", help="a .blend to open before the script runs")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the command as JSON and exit; needs no Blender")
    args = parser.parse_args(ours)

    script = resolve(args.script, "script")
    blend = resolve(args.blend, "--blend document") if args.blend else None
    executable = "blender" if args.dry_run else blender_locator.blender_executable()
    full = command(executable, script, script_args, blend)
    if args.dry_run:
        print(json.dumps(full))
        return 0

    code = subprocess.run(full, cwd=ROOT).returncode
    if code != 0:
        print(f"run.py: FAILED -- Blender exited {code} running {script.name}; "
              f"the Python traceback is above.", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
