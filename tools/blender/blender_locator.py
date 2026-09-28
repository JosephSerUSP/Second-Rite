"""The one place a Blender executable is chosen, and its version asserted.

Blender used to be located separately in seven places through four environment
variables and hardcoded ``C:\\Program Files`` lists, several of which fell back
to 4.x builds that cannot open 5.x documents (#1254).  Nothing could assert a
version, and version does matter here: Blender's OBJ exporter has already
behaved differently between two 5.0 builds
(``docs/reports/b-item-blend-source-migration-2026-08-15.md``).

The contract, shared by every Python and Node caller:

* the executable comes from ``$BLENDER_EXECUTABLE`` -- no ``PATH`` search, no
  install-directory guessing, no fallback to another version;
* the pinned version lives in ``tools/blender/blender-pin.json``, which is also
  what ``.github/actions/install-blender`` installs, so CI and local
  development cannot drift apart;
* a Blender that reports any other version is an error naming both versions.

Node callers run this file (``python tools/blender/blender_locator.py``) and
read the path from stdout rather than re-implementing the contract.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ENV_VAR = "BLENDER_EXECUTABLE"
PIN_PATH = Path(__file__).resolve().with_name("blender-pin.json")

_VERSION = re.compile(r"^Blender\s+(\d+\.\d+\.\d+)\b", re.MULTILINE)


class BlenderError(SystemExit):
    """Raised as a SystemExit so command-line tools stop with the message."""


def pinned_version() -> str:
    return json.loads(PIN_PATH.read_text(encoding="utf-8"))["version"]


def reported_version(executable: str) -> str:
    """The ``major.minor.patch`` that ``executable --version`` prints."""
    try:
        result = subprocess.run([executable, "--version"], capture_output=True,
                                text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BlenderError(f"could not run {executable} --version: {error}")
    match = _VERSION.search(result.stdout)
    if match is None:
        raise BlenderError(
            f"{executable} --version did not report a Blender version:\n"
            f"{(result.stdout + result.stderr).strip()[:400]}")
    return match.group(1)


def assert_version(executable: str, version: str | None = None) -> str:
    """Fail loudly unless ``executable`` is exactly the pinned Blender."""
    expected = version or pinned_version()
    found = reported_version(executable)
    if found != expected:
        raise BlenderError(
            f"Blender {found} found at {executable}, but this repository pins "
            f"Blender {expected} ({PIN_PATH.name}); install {expected} and point "
            f"{ENV_VAR} at it")
    return executable


def blender_executable(env=None) -> str:
    """The pinned Blender named by ``$BLENDER_EXECUTABLE``, or a loud failure."""
    value = (os.environ if env is None else env).get(ENV_VAR)
    if not value:
        raise BlenderError(
            f"{ENV_VAR} is not set; point it at Blender {pinned_version()} "
            f"(see {PIN_PATH.name} for the pinned build)")
    if not Path(value).is_file():
        raise BlenderError(f"{ENV_VAR} names a file that does not exist: {value}")
    return assert_version(value)


def main(argv=None) -> int:
    """Print the verified executable path (the contract Node callers consume)."""
    print(blender_executable())
    return 0


if __name__ == "__main__":
    sys.exit(main())
