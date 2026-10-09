"""Fail when a source or baked product changes without a fresh reviewed export."""
import hashlib
import json
from pathlib import Path

project = Path(__file__).resolve().parents[1]
for name in ("archive_antechamber", "service_annex"):
    package = project / "assets/environments" / name
    manifest = json.loads((package / "environment.json").read_text())
    provenance = manifest["provenance"]
    source = project / "assets/authoring/environments" / provenance["sourceBlend"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["sourceSha256"], f"Stale bake: {name}"
    for product in ("environment.obj", "environment.mtl", "environment.png", "collision.obj"):
        expected = provenance["productsSha256"][product]
        assert hashlib.sha256((package / product).read_bytes()).hexdigest() == expected, f"Changed baked product: {name}/{product}"
    assert provenance["bake"]["backend"] in ("cycles", "eevee"), f"Unlit fixture: {name}"
print("GAUNTLET LIGHTING PROVENANCE OK")
