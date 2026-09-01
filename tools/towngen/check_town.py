"""Gate: the St. Maria generator must still reproduce the town it owns.

`build_town.py` writes straight into `data/`. Nothing in a generated map says
so, which is how three doors came to be hand-added to Market Row on 27 Aug and
sat there for four days: correct in the shipped data, invisible to the
generator, and destined to be deleted by the next rebuild. The same silence
would have reverted map 20 - now the authored `lauras_smith` 3D room - back to
a flat plate with the wrong camera distance.

This gate regenerates the town into a throwaway copy of the Project and
compares the result against what is committed. A hand-edit to a generated map
now fails here instead of surviving until someone runs the generator.

    python tools/towngen/check_town.py

Exit 0 when the generator and the Project agree, 1 when they drift.

Line endings are normalised before comparing. The generator writes LF; a
Windows checkout holds CRLF, so a byte comparison reports every line of every
file as different and tells you nothing.
"""

import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from build_town import SCREENS, AUTHORED_NOT_GENERATED  # noqa: E402

PROJECT_REL = os.path.join("projects", "hichaukitoden-game")
ENV_REL = os.path.join("assets", "environments", "st_maria_town")

# Written by main() alongside the maps themselves.
EXTRA_FILES = [
    os.path.join("data", "maps", "index.json"),
    os.path.join("data", "engine.json"),
    os.path.join("data", "system.json"),
    os.path.join("data", "commonEvents.json"),
]


def owned_map_files():
    """The maps the generator claims. Anything else is authored by hand."""
    return [os.path.join("data", "maps", "%d.json" % screen["id"])
            for key, screen in SCREENS.items()
            if key not in AUTHORED_NOT_GENERATED]


def read_normalised(path):
    if not os.path.exists(path):
        return None
    with io.open(path, "rb") as handle:
        return handle.read().replace(b"\r\n", b"\n")


def regenerate(into):
    """Run the generator against a copy, so a check never writes to the tree."""
    project = os.path.join(into, PROJECT_REL)
    os.makedirs(os.path.join(project, "assets", "environments"), exist_ok=True)
    shutil.copytree(os.path.join(ROOT, PROJECT_REL, "data"),
                    os.path.join(project, "data"))
    shutil.copytree(os.path.join(ROOT, PROJECT_REL, ENV_REL),
                    os.path.join(project, ENV_REL))
    result = subprocess.run(
        [sys.executable, os.path.join(HERE, "build_town.py")],
        cwd=into, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        sys.stdout.write(result.stdout.decode("utf-8", "replace"))
        raise SystemExit("towngen: the generator itself failed (exit %d)"
                         % result.returncode)


def main():
    drifted = []
    with tempfile.TemporaryDirectory(prefix="towngen-check-") as tmp:
        regenerate(tmp)
        for rel in owned_map_files() + EXTRA_FILES:
            committed = read_normalised(os.path.join(ROOT, PROJECT_REL, rel))
            rebuilt = read_normalised(os.path.join(tmp, PROJECT_REL, rel))
            if committed != rebuilt:
                drifted.append(rel)

    print("towngen: checked %d generated maps + %d data files"
          % (len(owned_map_files()), len(EXTRA_FILES)))
    for key in sorted(AUTHORED_NOT_GENERATED):
        print("towngen: map %d (%s) is authored, not generated - not checked"
              % (SCREENS[key]["id"], key))

    if not drifted:
        print("TOWNGEN CHECK OK")
        return 0

    print("")
    print("towngen: %d file(s) differ from what build_town.py produces:"
          % len(drifted))
    for rel in drifted:
        print("  %s" % rel.replace("\\", "/"))
    print("")
    print("These files are GENERATED. A hand-edit to them is not durable - the")
    print("next `python tools/towngen/build_town.py` will overwrite it.")
    print("")
    print("Fix it in one of two places, not in the map:")
    print("  * a door, an NPC or a plate  -> edit SCREENS in build_town.py,")
    print("    then re-run the generator;")
    print("  * the map is authored now and should stop being generated ->")
    print("    add its key to AUTHORED_NOT_GENERATED and say why.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
