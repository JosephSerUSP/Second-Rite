"""Bake PE Day 1 room .blends with Second Gate's environment pipeline and
install the packages the chapter scenes draw.

    python projects/pe-day1/tools/chapter/bake_rooms.py foyer stage ...

Each room's source is assets/authoring/environments/pe_<room>.blend (made once
by author_rooms.py, then the authority). The package lands in
assets/models/rooms/<room>/ and rooms.json gains "environment" for that room.
Re-run build_chapter.py afterwards to regenerate the scenes.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
ROOT = PROJECT.parents[1]
TABLE = HERE / "rooms.json"


def main(rooms):
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in table["rooms"]}
    for room_id in rooms:
        blend = PROJECT / "assets" / "authoring" / "environments" / ("pe_%s.blend" % room_id)
        staging = ROOT / "out" / "pe-rooms" / room_id
        subprocess.run([sys.executable, str(ROOT / "tools" / "blender" / "town_environment_pipeline.py"),
                        str(blend), "-o", str(staging)], check=True)
        dest = PROJECT / "assets" / "models" / "rooms" / room_id
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("environment.obj", "environment.mtl", "environment.png", "environment.json"):
            shutil.copyfile(staging / name, dest / name)
        by_id[room_id]["environment"] = "assets/models/rooms/%s/environment.obj" % room_id
        print("INSTALLED", room_id)
    TABLE.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main(sys.argv[1:])
