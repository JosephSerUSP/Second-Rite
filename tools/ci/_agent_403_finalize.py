from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_exact(path, old, new, expected=1):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrences of {old!r}, found {count}")
    p.write_text(text.replace(old, new), encoding="utf-8")
    print(f"updated {path}: {count} occurrence(s)")


replace_exact(
    "presentation/viewport_3d.lua",
    'local small_battlers = require("presentation.small_battlers")',
    'local sprite_sheet = require("presentation.sprite_sheet")',
)
replace_exact(
    "presentation/viewport_3d.lua",
    "small_battlers.resolveFile(rawSprite)",
    "sprite_sheet.resolveFile(rawSprite)",
)
replace_exact(
    "engine/resource_reference.lua",
    "-- Sprite resolution delegates to presentation.small_battlers.resolveFile: that\n-- function is already the runtime authority for sprite keys, case variants and\n-- [key=value] filename tokens, so validation must not reproduce that lookup.\nlocal small_battlers = require(\"presentation.small_battlers\")",
    "-- Sprite resolution delegates to presentation.sprite_sheet.resolveFile: that\n-- function is the runtime authority for sprite keys, case variants and\n-- [key=value] filename tokens, so validation must not reproduce that lookup.\nlocal sprite_sheet = require(\"presentation.sprite_sheet\")",
)
replace_exact(
    "engine/resource_reference.lua",
    "small_battlers.resolveFile(value)",
    "sprite_sheet.resolveFile(value)",
)

stale = []
for p in ROOT.rglob("*.lua"):
    if ".git" in p.parts:
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    if "small_battlers.resolveFile" in text:
        stale.append(str(p.relative_to(ROOT)))

if stale:
    raise SystemExit("stale small_battlers.resolveFile references remain:\n  " + "\n  ".join(stale))

print("OK: no stale small_battlers.resolveFile references remain")
