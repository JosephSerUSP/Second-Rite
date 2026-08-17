"""Asset-class resolution and prompt assembly for tools/asset-gen.

classes.json is the registry; nothing here hardcodes a class. Geometry is
resolved (including the animation class's computed sheet width), filenames are
built from the class's pattern including the engine's [key=value] tokens, and
prompts come from prompts/<promptFile> with {{TOKEN}} substitution -- the same
templating convention tools/campaign-gen uses.
"""

import json
import os
import re

INSTALL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# ROOT remains the selected content root for the rest of asset-gen.  It starts
# at the repository root for the historical CLI and is switched by
# `asset-gen --project ...` before any command resolves a class.  TOOL_DIR and
# INSTALL_ROOT deliberately stay installation-owned: a Project can override
# art direction and prompts without copying the provider/post-processing code.
ROOT = INSTALL_ROOT
TOOL_DIR = os.path.join(INSTALL_ROOT, "tools", "asset-gen")

NEUTRAL_STYLE_BIBLE = (
    "Project-local art direction is authoritative. Keep the requested subject "
    "clear at its target resolution, use deliberate shapes and materials, and "
    "do not assume a genre, setting, palette, or house style."
)


def configure(project_root=None):
    """Select the content root used by this invocation.

    A Project is an authored root with a data/ directory. Refusing arbitrary
    folders here is intentional: a typo must not turn promotion into a write to
    an unexpected directory, and a Project run must never silently fall back to
    the install's Second Gate assets.
    """
    global ROOT
    if not project_root:
        ROOT = INSTALL_ROOT
        return ROOT
    candidate = os.path.abspath(os.path.expanduser(str(project_root)))
    if not os.path.isdir(candidate):
        raise ValueError(f"Project root does not exist: {candidate}")
    if not os.path.isdir(os.path.join(candidate, "data")):
        raise ValueError(f"{candidate} is not a Project: missing data/ directory")
    ROOT = candidate
    return ROOT


def is_project():
    return ROOT != INSTALL_ROOT


def project_config_path():
    if not is_project():
        return None
    return os.path.join(ROOT, "art", "asset-gen.json")


def project_config():
    """Read the optional Project-local art-gen contract.

    The file is intentionally separate from the game's data catalog. It is
    authoring/provenance policy, not runtime content, and belongs to the Project
    that owns the resulting art.
    """
    path = project_config_path()
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as err:
        raise ValueError(f"could not read Project art-gen config {path}: {err}") from err
    if not isinstance(value, dict):
        raise ValueError(f"Project art-gen config must be an object: {path}")
    return value


def deep_merge(base, override):
    """Return a recursive copy with Project values taking precedence."""
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def relative_to_root(path):
    return os.path.relpath(path, ROOT).replace("\\", "/")


def project_path(value, label, required_root=None):
    """Resolve and validate a path owned by the selected Project."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty path")
    candidate = os.path.abspath(os.path.join(ROOT, value)) if not os.path.isabs(value) else os.path.abspath(value)
    owner = ROOT if required_root is None else os.path.join(ROOT, required_root)
    owner = os.path.abspath(owner)
    try:
        if os.path.commonpath([candidate, owner]) != owner:
            raise ValueError
    except ValueError as err:
        suffix = f" under {required_root}/" if required_root else ""
        raise ValueError(f"{label} must stay{suffix} inside the selected Project: {candidate}") from err
    return candidate


def load(name):
    with open(os.path.join(TOOL_DIR, name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def registry():
    reg = load("classes.json")
    if not is_project():
        return reg

    project = project_config()
    # A Project never inherits the root style bible. An omitted artDirection is
    # safe and neutral; a present one is the Project author's decision.
    direction = project.get("artDirection") or {}
    reg["styleBible"] = direction.get(
        "styleBible", project.get("styleBible", NEUTRAL_STYLE_BIBLE))
    reg["styleTags"] = direction.get("styleTags", project.get("styleTags", ""))
    reg["classes"] = {
        key: deep_merge(reg["classes"].get(key, {}), value)
        for key, value in (project.get("classes") or {}).items()
    } | {
        key: value for key, value in reg["classes"].items()
        if key not in (project.get("classes") or {})
    }
    for class_id, class_def in reg["classes"].items():
        project_path(class_def.get("dir"), f"Project class '{class_id}' output", "assets")
    return reg


def resolve(class_id, opts):
    """Build the full working context for one generation: geometry, prompt, paths.

    opts may override cell size and frame count (the animation class is authored
    per-effect), and those overrides flow into both the geometry and the
    filename tokens, so the sheet the engine reads always matches its name.
    """
    reg = registry()
    class_def = reg["classes"].get(class_id)
    if not class_def:
        known = ", ".join(sorted(reg["classes"]))
        raise KeyError(f"unknown asset class '{class_id}'. Known: {known}")

    geom = dict(class_def["geometry"])
    cell = list(opts.get("cell") or geom["cell"])
    frames = int(opts.get("frames") or geom["frames"])

    size = geom.get("size")
    if not size:
        # Sheets whose extent depends on the frame count (particle strips).
        size = [cell[0] * frames, cell[1]]
    size = list(size)

    request = class_def.get("request", {})
    grid_hint = list(opts.get("grid") or request.get("gridHint") or [1, 1])

    return {
        "id": class_id,
        "classDef": class_def,
        "styleBible": reg["styleBible"],
        "styleTags": reg.get("styleTags", ""),
        "size": size,
        "cell": cell,
        "frames": frames,
        "gridHint": grid_hint,
        "transparent": bool(geom.get("transparent")),
        "requestSize": opts.get("requestSize") or request.get("size", "1024x1024"),
        "dir": class_def["dir"],
        "root": ROOT,
    }


_TOKEN_GROUP = re.compile(r"\[[^\]]*\{[^}]+\}[^\]]*\]")


def filename(ctx, name, tokens=None):
    """Render the class's filename pattern for `name`.

    {Name} capitalises, {name} lowercases; [key={token}] groups whose token has
    no value are dropped whole, so `--fps 0` yields `Kappa.png` rather than a
    filename carrying an empty bracket the engine would then try to parse.
    """
    values = dict(ctx["classDef"].get("tokenDefaults") or {})
    values.update({k: v for k, v in (tokens or {}).items() if v not in (None, "")})
    values.update({"cw": ctx["cell"][0], "ch": ctx["cell"][1], "frames": ctx["frames"]})

    pattern = ctx["classDef"]["filename"]
    pattern = _TOKEN_GROUP.sub(
        lambda m: "" if any(
            key not in values for key in re.findall(r"\{(\w+)\}", m.group(0))
        ) else m.group(0),
        pattern,
    )
    safe = re.sub(r"[^\w\-]", "_", str(name)).strip("_") or "unnamed"
    values["Name"] = safe[:1].upper() + safe[1:]
    values["name"] = safe.lower()
    return pattern.format(**values)


def prompt(ctx, name, description, extra="", style="prose"):
    """Render the class's prompt. `style` picks which template a provider wants.

    "prose" is the default and is what the hosted models are given: they read
    instructions, including negative ones, and reward a paragraph.

    "tags" is for local Stable Diffusion 1.5, whose text encoder is a different
    animal. CLIP sees 75 tokens per chunk and weights the earliest most, so a
    paragraph of art direction buries the thing being drawn -- measured, the
    prose template runs to roughly 400 tokens and does not reach the material
    until token ~100. It also cannot represent negation at all: "no perspective"
    contributes "perspective". The tag template puts the material first in
    comma-separated keywords and leaves every prohibition to the provider's
    negative prompt, which is where SD can actually act on it.
    """
    class_def = ctx["classDef"]
    file_key = "promptFile" + ("Tags" if style == "tags" else "")
    filename = class_def.get(file_key, class_def["promptFile"])
    project = project_config() if is_project() else {}
    prompt_dir = project.get("promptDir", "art/prompts")
    if is_project() and not os.path.isabs(prompt_dir):
        prompt_dir = os.path.join(ROOT, prompt_dir)
    if is_project():
        prompt_dir = project_path(prompt_dir, "Project prompt directory")
    project_prompt = os.path.join(prompt_dir, filename) if is_project() else None
    if project_prompt and os.path.isfile(project_prompt):
        path = project_prompt
    elif is_project() and not project.get("allowSharedPrompts", False):
        raise FileNotFoundError(
            f"Project prompt missing: {project_prompt}; add the retained prompt "
            "under the Project or explicitly set allowSharedPrompts"
        )
    else:
        path = os.path.join(TOOL_DIR, "prompts", filename)
    with open(path, "r", encoding="utf-8") as handle:
        template = handle.read()

    grid = (f"{ctx['gridHint'][0]} columns x {ctx['gridHint'][1]} rows"
            if ctx["gridHint"] != [1, 1] else "a single image, no grid")
    replacements = {
        "STYLE_BIBLE": ctx["styleBible"],
        "STYLE_TAGS": ctx["styleTags"],
        "NAME": str(name),
        "DESCRIPTION": description or "",
        "GRID": grid,
        "FRAMES": str(ctx["frames"]),
        "CELL": f"{ctx['cell'][0]}x{ctx['cell'][1]}",
        "FINAL_SIZE": f"{ctx['size'][0]}x{ctx['size'][1]}",
        "EXPRESSIONS": ", ".join(ctx["classDef"].get("expressions", [])),
        "BACKGROUND": (
            "a perfectly flat pure magenta (#FF00FF) background with no shadow, "
            "gradient or vignette on it -- it will be keyed out to transparency"
            if ctx["transparent"] else
            "a fully painted background; the image is opaque edge to edge"
        ),
        "EXTRA": extra or "",
    }
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", value)
    return template.strip()
