"""Finalize Blender-exported item MTL files with Second Rite runtime passes.

Blender's OBJ exporter preserves ordinary MTL material data but cannot represent
Second Rite's small retro overlay vocabulary. Authoritative .blend materials may
therefore carry ``sr_runtime_passes_json`` as a JSON list. The Blender-side item
compiler collects those declarations and this module appends deterministic
``pass`` statements to the exported MTL.

The vocabulary mirrors presentation/retro_mesh_shader.lua and
presentation/obj_model.lua deliberately. Keeping validation here means a bad
source document fails during compilation rather than later as an invisible
runtime material.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

UV_SOURCES = {"uv", "sphere"}
BLEND_OPS = {"add", "subtract", "multiply", "screen", "mix"}
MAX_PASSES = 2


class RuntimePassError(ValueError):
    pass


def normalize_passes(value) -> list[dict]:
    if not isinstance(value, list):
        raise RuntimePassError("runtime passes must be a JSON list")
    if len(value) > MAX_PASSES:
        raise RuntimePassError(f"runtime material declares {len(value)} passes; maximum is {MAX_PASSES}")
    result = []
    for index, entry in enumerate(value):
        if not isinstance(entry, Mapping):
            raise RuntimePassError(f"runtime pass {index} must be an object")
        uv_source = str(entry.get("uvSource", ""))
        blend = str(entry.get("blend", ""))
        texture = str(entry.get("texture", "")).strip()
        try:
            strength = float(entry.get("strength"))
        except (TypeError, ValueError) as exc:
            raise RuntimePassError(f"runtime pass {index} strength must be numeric") from exc
        if uv_source not in UV_SOURCES:
            raise RuntimePassError(
                f"runtime pass {index} uvSource {uv_source!r} is unknown; expected {sorted(UV_SOURCES)}"
            )
        if blend not in BLEND_OPS:
            raise RuntimePassError(
                f"runtime pass {index} blend {blend!r} is unknown; expected {sorted(BLEND_OPS)}"
            )
        if strength < 0:
            raise RuntimePassError(f"runtime pass {index} strength must be non-negative")
        if not texture or any(ch in texture for ch in "\r\n"):
            raise RuntimePassError(f"runtime pass {index} needs one-line texture path")
        result.append({
            "uvSource": uv_source,
            "blend": blend,
            "strength": strength,
            "texture": texture,
        })
    return result


def pass_line(entry: Mapping) -> str:
    strength = format(float(entry["strength"]), ".6g")
    return f"pass {entry['uvSource']} {entry['blend']} {strength} {entry['texture']}"


def inject_runtime_passes(path: Path, passes_by_material: Mapping[str, list[dict]]) -> None:
    """Append source-authored runtime passes to matching ``newmtl`` sections."""
    if not passes_by_material:
        return
    if not path.is_file():
        raise RuntimePassError(f"runtime passes declared but MTL was not exported: {path}")

    normalized = {str(name): normalize_passes(passes) for name, passes in passes_by_material.items()}
    source_lines = path.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    output: list[str] = []
    current: str | None = None

    def flush_passes():
        if current is None or current not in normalized:
            return
        for entry in normalized[current]:
            output.append(pass_line(entry))
        seen.add(current)

    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("newmtl "):
            flush_passes()
            current = stripped[len("newmtl "):].strip()
        output.append(line)
    flush_passes()

    missing = sorted(set(normalized) - seen)
    if missing:
        raise RuntimePassError(f"runtime-pass material(s) absent from exported MTL: {missing}")

    path.write_text("\n".join(output) + "\n", encoding="utf-8")
