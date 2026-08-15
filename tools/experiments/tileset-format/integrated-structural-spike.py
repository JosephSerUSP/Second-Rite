#!/usr/bin/env python3
"""CI-only structural-profile spike for #558.

This script intentionally edits the checked-out worktree, never committed
production files. It exists so the experiment can exercise the real
Map -> tileset resolver -> viewport_3d -> preview-map path without replacing
viewport_3d.lua through the GitHub contents API.
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VIEWPORT = ROOT / "presentation" / "viewport_3d.lua"
MAP = ROOT / "data" / "maps" / "13.json"
MARKER = "-- #558 STRUCTURAL PROFILE INTEGRATION SPIKE"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_renderer() -> None:
    text = VIEWPORT.read_text(encoding="utf-8")
    if MARKER in text:
        print("renderer already carries #558 spike")
        return

    text = replace_once(
        text,
        "    local function addFace(mapX, mapY, kind, p1, p2, nx, ny)\n"
        "        local visible, reason = geometryVisibility.wallSideDecision(\n",
        "    local function addFace(mapX, mapY, kind, p1, p2, nx, ny, options)\n"
        "        options = options or {}\n"
        "        local visible, reason = geometryVisibility.wallSideDecision(\n",
        "addFace options",
    )

    text = replace_once(
        text,
        "        local side = (kind == \"north\" or kind == \"south\") and 1 or 0\n"
        "        local hasLeft = (side == 0 and floorCell(grid, mapX, mapY - 1))\n"
        "            or (side == 1 and floorCell(grid, mapX - 1, mapY))\n"
        "        local hasRight = (side == 0 and floorCell(grid, mapX, mapY + 1))\n"
        "            or (side == 1 and floorCell(grid, mapX + 1, mapY))\n",
        "        local side = options.side ~= nil and options.side\n"
        "            or ((kind == \"north\" or kind == \"south\") and 1 or 0)\n"
        "        local hasLeft = not options.disableEdges and ((side == 0 and floorCell(grid, mapX, mapY - 1))\n"
        "            or (side == 1 and floorCell(grid, mapX - 1, mapY)))\n"
        "        local hasRight = not options.disableEdges and ((side == 0 and floorCell(grid, mapX, mapY + 1))\n"
        "            or (side == 1 and floorCell(grid, mapX + 1, mapY)))\n",
        "edge options",
    )

    text = replace_once(
        text,
        "        uv[2], uv[4] = uv[4], uv[2]\n"
        "        local normalX, normalY = 0, 0\n"
        "        if kind == \"north\" then normalY = -1 elseif kind == \"south\" then normalY = 1\n"
        "        elseif kind == \"west\" then normalX = -1 else normalX = 1 end\n",
        "        uv[2], uv[4] = uv[4], uv[2]\n"
        "        if options.uStart ~= nil or options.uEnd ~= nil then\n"
        "            local sourceU0, sourceU1 = uv[1], uv[3]\n"
        "            local startT = options.uStart or 0\n"
        "            local endT = options.uEnd or 1\n"
        "            uv[1] = sourceU0 + (sourceU1 - sourceU0) * startT\n"
        "            uv[3] = sourceU0 + (sourceU1 - sourceU0) * endT\n"
        "        end\n"
        "        local normalX, normalY = options.normalX or 0, options.normalY or 0\n"
        "        if options.normalX == nil and options.normalY == nil then\n"
        "            if kind == \"north\" then normalY = -1 elseif kind == \"south\" then normalY = 1\n"
        "            elseif kind == \"west\" then normalX = -1 else normalX = 1 end\n"
        "        end\n",
        "profile UV and normals",
    )

    old_loop = """    for _, cell in ipairs(structure.wallCells) do
        local x, y = cell.x, cell.y
        addFace(x, y, \"north\", { x = x, y = y }, { x = x + 1, y = y }, x, y - 1)
        addFace(x, y, \"south\", { x = x + 1, y = y + 1 }, { x = x, y = y + 1 }, x, y + 1)
        addFace(x, y, \"west\", { x = x, y = y + 1 }, { x = x, y = y }, x - 1, y)
        addFace(x, y, \"east\", { x = x + 1, y = y }, { x = x + 1, y = y + 1 }, x + 1, y)
    end
"""

    new_loop = f"""    {MARKER}
    -- Presentation-only shaping. The logical grid and collision stay untouched;
    -- only two simultaneously exposed wall sides may surrender the outer corner
    -- to a chamfer/low-segment arc. Square/default takes the exact old path.
    local structuralProfile = atlas and atlas.manifest and atlas.manifest.structuralProfile
    local structuralCorner = structuralProfile and structuralProfile.corner or \"square\"
    local structuralRadius = math.max(0, math.min(0.45,
        tonumber(structuralProfile and structuralProfile.radius) or 0.12))
    local structuralSegments = math.max(2, math.min(8,
        math.floor(tonumber(structuralProfile and structuralProfile.segments) or 3)))
    local structuralShaped = structuralRadius > 0
        and (structuralCorner == \"chamfer\" or structuralCorner == \"round\")

    local function exposedAt(nx, ny)
        local visible = geometryVisibility.wallSideDecision(profile.name, grid, nx, ny)
        return visible == true
    end

    local function addCornerArc(mapX, mapY, kind, neighborX, neighborY,
            centerX, centerY, angle0, angle1)
        local count = structuralCorner == \"chamfer\" and 1 or structuralSegments
        for index = 0, count - 1 do
            local t0, t1 = index / count, (index + 1) / count
            local a0 = angle0 + (angle1 - angle0) * t0
            local a1 = angle0 + (angle1 - angle0) * t1
            local p1 = {{
                x = centerX + math.cos(a0) * structuralRadius,
                y = centerY + math.sin(a0) * structuralRadius,
            }}
            local p2 = {{
                x = centerX + math.cos(a1) * structuralRadius,
                y = centerY + math.sin(a1) * structuralRadius,
            }}
            local dx, dy = p2.x - p1.x, p2.y - p1.y
            local length = math.sqrt(dx * dx + dy * dy)
            addFace(mapX, mapY, kind, p1, p2, neighborX, neighborY, {{
                normalX = dy / length,
                normalY = -dx / length,
                disableEdges = true,
                uStart = t0,
                uEnd = t1,
            }})
        end
    end

    for _, cell in ipairs(structure.wallCells) do
        local x, y = cell.x, cell.y
        if not structuralShaped then
            addFace(x, y, \"north\", {{ x = x, y = y }}, {{ x = x + 1, y = y }}, x, y - 1)
            addFace(x, y, \"south\", {{ x = x + 1, y = y + 1 }}, {{ x = x, y = y + 1 }}, x, y + 1)
            addFace(x, y, \"west\", {{ x = x, y = y + 1 }}, {{ x = x, y = y }}, x - 1, y)
            addFace(x, y, \"east\", {{ x = x + 1, y = y }}, {{ x = x + 1, y = y + 1 }}, x + 1, y)
        else
            local north = exposedAt(x, y - 1)
            local south = exposedAt(x, y + 1)
            local west = exposedAt(x - 1, y)
            local east = exposedAt(x + 1, y)
            local ne, se = north and east, south and east
            local sw, nw = south and west, north and west
            local r = structuralRadius

            addFace(x, y, \"north\",
                {{ x = x + (nw and r or 0), y = y }},
                {{ x = x + 1 - (ne and r or 0), y = y }}, x, y - 1,
                {{ uStart = nw and r or 0, uEnd = ne and (1 - r) or 1 }})
            addFace(x, y, \"east\",
                {{ x = x + 1, y = y + (ne and r or 0) }},
                {{ x = x + 1, y = y + 1 - (se and r or 0) }}, x + 1, y,
                {{ uStart = ne and r or 0, uEnd = se and (1 - r) or 1 }})
            addFace(x, y, \"south\",
                {{ x = x + 1 - (se and r or 0), y = y + 1 }},
                {{ x = x + (sw and r or 0), y = y + 1 }}, x, y + 1,
                {{ uStart = se and r or 0, uEnd = sw and (1 - r) or 1 }})
            addFace(x, y, \"west\",
                {{ x = x, y = y + 1 - (sw and r or 0) }},
                {{ x = x, y = y + (nw and r or 0) }}, x - 1, y,
                {{ uStart = sw and r or 0, uEnd = nw and (1 - r) or 1 }})

            if ne then addCornerArc(x, y, \"north\", x, y - 1,
                x + 1 - r, y + r, -math.pi * 0.5, 0) end
            if se then addCornerArc(x, y, \"east\", x + 1, y,
                x + 1 - r, y + 1 - r, 0, math.pi * 0.5) end
            if sw then addCornerArc(x, y, \"south\", x, y + 1,
                x + r, y + 1 - r, math.pi * 0.5, math.pi) end
            if nw then addCornerArc(x, y, \"west\", x - 1, y,
                x + r, y + r, math.pi, math.pi * 1.5) end
        end
    end
"""

    text = replace_once(text, old_loop, new_loop, "wall-cell emission loop")
    VIEWPORT.write_text(text, encoding="utf-8")
    print(f"patched {VIEWPORT.relative_to(ROOT)}")


def set_map_profile(profile: str, radius: float, segments: int) -> None:
    if profile not in {"square", "chamfer", "round"}:
        raise ValueError(profile)
    data = json.loads(MAP.read_text(encoding="utf-8"))
    data["tileset"] = "dungeon_default"
    data["tilesetOverride"] = {
        "structuralProfile": {
            "corner": profile,
            "radius": radius,
            "segments": segments,
        },
        # The first integrated spike isolates junction geometry. Height relief
        # remains a separate follow-up because its plane UV/domain needs to wrap
        # around generated profile segments deliberately rather than by accident.
        "heightMapScale": {"wall": 0, "floor": 0, "ceiling": 0},
    }
    MAP.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"map 13 -> dungeon_default + {profile} structuralProfile")


def decode_preview(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8", errors="replace")
    begin_marker = "PREVIEW BEGIN"
    end_marker = "PREVIEW END"
    begin = text.find(begin_marker)
    end = text.find(end_marker, begin + len(begin_marker))
    if begin < 0 or end < 0:
        raise RuntimeError("preview output markers not found")
    payload_text = text[begin + len(begin_marker):end].strip()
    payload = json.loads(payload_text)
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    image = payload.get("image")
    if not image:
        raise RuntimeError("preview payload has no image")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(image))
    print(f"decoded {output} ({output.stat().st_size} bytes) player="
          f"{payload.get('playerX')},{payload.get('playerY')} {payload.get('playerDir')}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("patch-renderer")
    set_profile = sub.add_parser("set-map-profile")
    set_profile.add_argument("profile", choices=["square", "chamfer", "round"])
    set_profile.add_argument("--radius", type=float, default=0.22)
    set_profile.add_argument("--segments", type=int, default=3)
    decode = sub.add_parser("decode-preview")
    decode.add_argument("source", type=Path)
    decode.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "patch-renderer":
        patch_renderer()
    elif args.command == "set-map-profile":
        set_map_profile(args.profile, args.radius, args.segments)
    elif args.command == "decode-preview":
        decode_preview(args.source, args.output)


if __name__ == "__main__":
    main()
