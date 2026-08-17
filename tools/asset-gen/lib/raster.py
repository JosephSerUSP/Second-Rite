"""Deterministic Project-local raster authoring for small functional art.

The source of truth is a retained JSON spec under the selected Project. This
module intentionally knows only a small vocabulary of geometric primitives;
image-model providers remain in ``provider.py`` and the existing generation
pipeline remains in ``gen.py``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

from . import image_storage


VERSION = 1
MANIFEST_KIND = "project_raster_run"
TOOL_COMMAND = "python tools/asset-gen/gen.py --project <project-root> raster <spec>"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(root: Path, path: Path, label: str) -> Path:
    root = root.resolve()
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as err:
        raise ValueError(f"{label} must stay inside Project root: {path}") from err
    return path


def _project_path(root: Path, value: str, label: str, required_root: str | None = None) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty Project-relative path")
    path = _inside(root, root / value, label)
    if required_root:
        _inside(root / required_root, path, label)
    return path


def _palette_color(value, palette, mode):
    if isinstance(value, str) and value in palette:
        value = palette[value]
    if isinstance(value, str) and value.lower() == "transparent":
        return 0 if mode == "L" else ((0, 0, 0, 0) if mode == "RGBA" else (0, 0, 0))
    if mode == "L":
        if isinstance(value, int):
            return max(0, min(255, value))
        if isinstance(value, (list, tuple)):
            return int(round(sum(value[:3]) / min(3, len(value))))
        red, green, blue = ImageColor.getrgb(str(value))
        return int(round(0.299 * red + 0.587 * green + 0.114 * blue))
    if isinstance(value, int):
        return (value, value, value, 255)
    if isinstance(value, (list, tuple)):
        channels = list(value)
        if len(channels) == 3:
            channels.append(255)
        if len(channels) != 4:
            raise ValueError(f"RGBA colours need 3 or 4 channels: {value}")
        return tuple(max(0, min(255, int(channel))) for channel in channels)
    red, green, blue, alpha = ImageColor.getcolor(str(value), "RGBA")
    return (red, green, blue, alpha) if mode == "RGBA" else (red, green, blue)


def _points(value, label):
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError(f"{label} needs at least two [x, y] points")
    points = []
    for point in value:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(f"{label} contains an invalid point: {point}")
        points.append((int(point[0]), int(point[1])))
    return points


def _box(value, label):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{label} needs [left, top, right, bottom]")
    return tuple(int(part) for part in value)


def _draw_commands(image, commands, palette):
    draw = ImageDraw.Draw(image)
    mode = image.mode
    for command in commands or []:
        if not isinstance(command, dict):
            raise ValueError(f"raster command must be an object: {command}")
        op = command.get("op") or command.get("shape")
        fill = _palette_color(command.get("fill", "transparent"), palette, mode)
        outline = (_palette_color(command["outline"], palette, mode)
                   if "outline" in command else None)
        width = int(command.get("width", 1))
        if width < 1:
            raise ValueError(f"raster command width must be positive: {command}")
        if op == "rect":
            draw.rectangle(_box(command.get("box"), "rect.box"), fill=fill,
                           outline=outline, width=width)
        elif op == "ellipse":
            draw.ellipse(_box(command.get("box"), "ellipse.box"), fill=fill,
                         outline=outline, width=width)
        elif op == "polygon":
            draw.polygon(_points(command.get("points"), "polygon.points"), fill=fill,
                         outline=outline)
            if outline is not None and width > 1:
                draw.line(_points(command.get("points"), "polygon.points") +
                          [_points(command.get("points"), "polygon.points")[0]],
                          fill=outline, width=width)
        elif op == "line":
            draw.line(_points(command.get("points"), "line.points"), fill=fill, width=width,
                      joint="curve")
        elif op == "arc":
            draw.arc(_box(command.get("box"), "arc.box"), float(command.get("start", 0)),
                     float(command.get("end", 360)), fill=fill, width=width)
        elif op == "point":
            point = command.get("at")
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError(f"point.at needs [x, y]: {point}")
            point = (int(point[0]), int(point[1]))
            draw.point(point, fill=fill)
        else:
            raise ValueError(f"unknown raster primitive '{op}'")


def _render_asset(asset, palette):
    if not isinstance(asset, dict):
        raise ValueError(f"asset entry must be an object: {asset}")
    asset_id = str(asset.get("id") or "").strip()
    if not asset_id:
        raise ValueError("asset entry needs an id")
    size = asset.get("size")
    if not isinstance(size, list) or len(size) != 2 or any(int(part) <= 0 for part in size):
        raise ValueError(f"asset '{asset_id}' needs a positive size [width, height]")
    mode = asset.get("mode", "RGBA")
    if mode not in {"RGBA", "RGB", "L"}:
        raise ValueError(f"asset '{asset_id}' mode must be RGBA, RGB, or L")
    background = _palette_color(asset.get("background", "transparent"), palette, mode)
    image = Image.new(mode, (int(size[0]), int(size[1])), background)
    _draw_commands(image, asset.get("draw"), palette)
    return asset_id, image


def _png_bytes(image):
    return image_storage.png_bytes(image)


def _contact_sheet(rendered, labels, output=None):
    """Build a nearest-neighbour sheet with deterministic captions."""
    font = ImageFont.load_default()
    columns = 3
    card_width = 544
    cards = []
    for asset_id, image in rendered:
        scale = max(1, min(4, 480 // max(image.width, image.height)))
        preview = image.convert("RGBA").resize(
            (image.width * scale, image.height * scale), Image.Resampling.NEAREST)
        card = Image.new("RGB", (card_width, preview.height + 44), (28, 27, 31))
        x = (card_width - preview.width) // 2
        card.paste(preview.convert("RGB"), (max(0, x), 8))
        ImageDraw.Draw(card).text((10, preview.height + 18), labels[asset_id],
                                  fill=(235, 230, 218), font=font)
        cards.append(card)
    rows = []
    for start in range(0, len(cards), columns):
        row = cards[start:start + columns]
        row_height = max(card.height for card in row)
        canvas = Image.new("RGB", (card_width * len(row) + 8 * (len(row) - 1), row_height),
                           (14, 13, 16))
        x = 0
        for card in row:
            canvas.paste(card, (x, 0))
            x += card_width + 8
        rows.append(canvas)
    sheet = Image.new("RGB", (max(row.width for row in rows),
                               sum(row.height for row in rows) + 8 * (len(rows) - 1)),
                      (14, 13, 16))
    y = 0
    for row in rows:
        sheet.paste(row, (0, y))
        y += row.height + 8
    encoded = _png_bytes(sheet)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
    return encoded


def _load_spec(spec_path: Path):
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise ValueError(f"could not read raster spec {spec_path}: {err}") from err
    if not isinstance(spec, dict) or spec.get("version") != VERSION:
        raise ValueError(f"raster spec needs version {VERSION}: {spec_path}")
    if not isinstance(spec.get("assets"), list) or not spec["assets"]:
        raise ValueError("raster spec needs a non-empty assets list")
    if not isinstance(spec.get("palette"), dict) or not spec["palette"]:
        raise ValueError("raster spec needs a named palette")
    return spec


def _manifest_path(root, value, default):
    return _project_path(root, value or default, "manifest path")


def _contact_path(root, value, default):
    return _project_path(root, value or default, "contact-sheet path")


def generate(spec_path, project_root, contact_sheet=None, manifest_path=None, check=False):
    """Render or verify a Project-local raster spec and its evidence bundle."""
    root = Path(project_root).resolve()
    if not (root / "data").is_dir():
        raise ValueError(f"{root} is not a Project: missing data/ directory")
    spec = Path(spec_path).resolve()
    _inside(root, spec, "raster spec")
    if not spec.is_file():
        raise FileNotFoundError(f"raster spec not found: {spec}")
    data = _load_spec(spec)
    palette = data["palette"]
    rendered = []
    seen_ids = set()
    outputs = []
    for asset in data["assets"]:
        asset_id, image = _render_asset(asset, palette)
        if asset_id in seen_ids:
            raise ValueError(f"duplicate raster asset id: {asset_id}")
        seen_ids.add(asset_id)
        path = _project_path(root, asset.get("path"), f"asset '{asset_id}' path",
                             required_root="assets")
        if path.suffix.lower() != ".png":
            raise ValueError(f"asset '{asset_id}' output must be a PNG: {path}")
        rendered.append((asset_id, image))
        outputs.append((asset_id, path, image))

    contact = _contact_path(root, contact_sheet, data.get("contactSheet", "art/review/visual-contact-sheet.png"))
    manifest = _manifest_path(root, manifest_path, data.get("manifest", "art/provenance/raster-manifest.json"))
    spec_rel = os.path.relpath(spec, root).replace("\\", "/")
    output_rows = []
    output_bytes = {}
    for asset_id, path, image in outputs:
        encoded = _png_bytes(image)
        output_bytes[path] = encoded
        output_rows.append({
            "id": asset_id,
            "path": os.path.relpath(path, root).replace("\\", "/"),
            "size": [image.width, image.height],
            "mode": image.mode,
            "sha256": _sha256_bytes(encoded),
        })

    labels = {str(asset.get("id")): str(asset.get("label") or asset.get("id"))
              for asset in data["assets"]}
    # Render the sheet in memory too, so --check verifies the exact bytes rather
    # than merely checking that a stale contact sheet exists.
    contact_bytes = _contact_sheet(rendered, labels)

    manifest_data = {
        "manifestKind": MANIFEST_KIND,
        "manifestVersion": VERSION,
        "method": "programmatic-raster",
        "command": TOOL_COMMAND,
        "projectRoot": ".",
        "spec": spec_rel,
        "specSha256": _sha256_file(spec),
        "palette": palette,
        "outputs": output_rows,
        "contactSheet": {
            "path": os.path.relpath(contact, root).replace("\\", "/"),
            "sha256": _sha256_bytes(contact_bytes),
        },
    }
    manifest_bytes = (json.dumps(manifest_data, indent=2, ensure_ascii=True, sort_keys=False) + "\n").encode("utf-8")

    if check:
        if not manifest.is_file():
            raise ValueError(f"raster provenance manifest missing: {manifest}")
        if manifest.read_bytes() != manifest_bytes:
            raise ValueError(f"raster provenance manifest is stale: {manifest}")
        for path, expected in output_bytes.items():
            if not path.is_file() or path.read_bytes() != expected:
                raise ValueError(f"raster output is stale: {path}")
        if not contact.is_file() or contact.read_bytes() != contact_bytes:
            raise ValueError(f"raster contact sheet is stale: {contact}")
    else:
        for path, encoded in output_bytes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded)
        contact.parent.mkdir(parents=True, exist_ok=True)
        contact.write_bytes(contact_bytes)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_bytes(manifest_bytes)

    return {
        "outputs": [str(path) for _asset_id, path, _image in outputs],
        "contactSheet": str(contact),
        "manifest": str(manifest),
    }
