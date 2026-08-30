"""Proves an add-on package is genuinely re-read from disk on reload.

Blender's own script reload leaves submodules cached, so a reload can report
success while the old code keeps serving. This stages a copy of the package,
edits it on disk, and requires the reloaded module to show the edit.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "tools" / "blender" / "live_bridge"


def main():
    staging = Path(tempfile.mkdtemp(prefix="bridge-reload-"))
    package = staging / "live_bridge"
    shutil.copytree(SOURCE, package, ignore=shutil.ignore_patterns("__pycache__"))
    sys.path.insert(0, str(staging))
    addon_utils.enable("live_bridge", default_set=False, persistent=False)

    import live_bridge.server as server
    assert not hasattr(server, "RELOAD_PROBE"), "staged package already carried the marker"

    # An edit to a submodule is the case Blender's script reload misses.
    with (package / "server.py").open("a", encoding="utf-8") as handle:
        handle.write('\n\nRELOAD_PROBE = "reloaded"\n')

    from live_bridge import addon
    addon.reload_package("live_bridge")

    import live_bridge.server as reloaded
    marker = getattr(reloaded, "RELOAD_PROBE", None)
    assert marker == "reloaded", f"submodule was not re-read from disk: {marker!r}"
    assert sys.modules["live_bridge.server"] is reloaded

    addon_utils.disable("live_bridge", default_set=False)
    shutil.rmtree(staging, ignore_errors=True)
    print("LIVE_BRIDGE_RELOAD_OK")


main()
