"""Fail when a source or baked product changes without a fresh reviewed export."""
import hashlib
import json
from pathlib import Path

project = Path(__file__).resolve().parents[1]
system = json.loads((project / "data/system.json").read_text())
assert system["dungeon"]["psxRendering"]["affineTextures"] is False, "Baked rooms require perspective-correct UVs"

def box_footprints(path):
    # Fixtures have distinct horizontal box tops below 1.5m. Read the exported
    # mesh through the runtime OBJ axis convention, not the Blender manifest.
    vertices, tops = [], {}
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            x, z, y = map(float, line.split()[1:4])
            vertices.append((x, -y, z))
        elif line.startswith("f "):
            points = [vertices[int(ref.split("/")[0]) - 1] for ref in line.split()[1:]]
            z = points[0][2]
            if 0.1 < z < 1.5 and max(p[2] for p in points) - min(p[2] for p in points) < 1e-5:
                tops.setdefault(z, set()).update(points)
    return sorted((min(p[0] for p in points), max(p[0] for p in points),
                   min(p[1] for p in points), max(p[1] for p in points)) for points in tops.values())

for name in ("archive_antechamber", "service_annex"):
    package = project / "assets/environments" / name
    manifest = json.loads((package / "environment.json").read_text())
    expected = sorted((min(p[0] for p in shape["points"]), max(p[0] for p in shape["points"]),
                       min(p[1] for p in shape["points"]), max(p[1] for p in shape["points"]))
                      for shape in manifest["walkSurface"]["obstacles"])
    actual = box_footprints(package / "environment.obj")
    assert len(actual) == len(expected) and all(abs(a-b) < 1e-5 for left,right in zip(actual,expected)
                                               for a,b in zip(left,right)), f"Visible boxes disagree with walk blockers: {name}"
    provenance = manifest["provenance"]
    source = project / "assets/authoring/environments" / provenance["sourceBlend"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["sourceSha256"], f"Stale bake: {name}"
    for product in ("environment.obj", "environment.mtl", "environment.png", "collision.obj"):
        expected = provenance["productsSha256"][product]
        assert hashlib.sha256((package / product).read_bytes()).hexdigest() == expected, f"Changed baked product: {name}/{product}"
    assert provenance["bake"]["backend"] in ("cycles", "eevee"), f"Unlit fixture: {name}"
print("GAUNTLET LIGHTING PROVENANCE OK")
