"""Generate sphere-map sheens (matcaps) on the local GPU.

A matcap is the cheapest material identity this renderer can express. The shader
computes no specular, reflection or refraction (SPEC 1.25), so a highlight is
*sampled* from a small image of a lit sphere, indexed by the screen-space
normal. That image is an unusually good fit for Stable Diffusion: it is a single
centred object on black, with no composition, perspective or narrative to get
wrong.

    python tools/asset-gen/make_matcaps.py --list
    python tools/asset-gen/make_matcaps.py gold ruby --variants 3
    python tools/asset-gen/make_matcaps.py --promote gold --variant 2

Nothing reaches assets/ until --promote, matching the rest of asset-gen.

Consumed by an MTL as:

    refl -type sphere assets/models/matcaps/gold.png

which the loader reads as `pass sphere add 1.0`.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO_ROOT = HERE.parents[1]

from lib import provider as provider_lib  # noqa: E402

OUT = HERE / "out" / "matcaps"
PROMOTE_DIR = REPO_ROOT / "assets" / "models" / "matcaps"

# Resolution is small on purpose. The sheen is sampled by normal direction and
# then quantized to the palette with everything else, so detail beyond this is
# thrown away; 128 keeps it in the same visual register as the rest of the art.
MATCAP_SIZE = 128

# The lighting these describe must match the item viewer's own light, or a
# sampled highlight sits on a different side of the object from the shaded one
# and the material reads as wrong without it being obvious why.
LIGHT_PHRASE = (
    "single key light from the upper left and slightly in front, soft falloff, "
    "dark background"
)

MATCAPS = {
    "gold": "a polished gold sphere, warm yellow metal, bright specular highlight",
    "silver": "a polished silver sphere, cool grey metal, sharp specular highlight",
    "bronze": "an oxidized bronze sphere, dull brown-green metal, soft highlight",
    "ruby": "a deep red faceted gemstone sphere, glassy, bright pinpoint highlight",
    "sapphire": "a deep blue faceted gemstone sphere, glassy, bright pinpoint highlight",
    "emerald": "a deep green faceted gemstone sphere, glassy, bright pinpoint highlight",
    "pearl": "a pearl sphere, soft iridescent white, broad gentle highlight",
    "obsidian": "a black volcanic glass sphere, near-black, one hard highlight",
    "glaze": "a glazed ceramic sphere, cream coloured, wet looking soft highlight",
}


def build_prompt(description: str) -> str:
    return (
        f"{description}, {LIGHT_PHRASE}, floating in empty black void, "
        "the sphere touches all four edges of the image, extreme close up, "
        "orthographic, no ground, no floor, no table, no horizon, no shadow, "
        "no text, no studio reflection"
    )


NEGATIVE = (
    "floor, ground, table, horizon, backdrop, studio, room, grey background, "
    "white background, shadow, multiple objects, small object, border, frame, "
    "text, watermark"
)


def autocrop_sphere(image: Image.Image) -> Image.Image:
    """Crop to the sphere itself.

    The model reliably renders a sphere and unreliably fills the frame with it.
    Since the shader indexes this image by normal direction, a sphere sitting in
    the middle of a larger frame maps the whole material onto the object's
    centre and leaves its edges unlit. Find the subject and blow it up to the
    full frame instead of hoping the prompt lands it there.
    """
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()

    # Background estimate: the median of the four corners, which is where the
    # subject is least likely to be.
    corners = [pixels[0, 0], pixels[width - 1, 0], pixels[0, height - 1], pixels[width - 1, height - 1]]
    background = tuple(sorted(channel[i] for channel in corners)[1] for i in range(3))

    def differs(pixel) -> bool:
        return sum(abs(pixel[i] - background[i]) for i in range(3)) > 60

    xs, ys = [], []
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if differs(pixels[x, y]):
                xs.append(x)
                ys.append(y)
    if not xs:
        return rgb

    left, right, top, bottom = min(xs), max(xs), min(ys), max(ys)
    # Square it off around the subject's centre, so the sphere is not stretched.
    size = max(right - left, bottom - top)
    cx, cy = (left + right) // 2, (top + bottom) // 2
    half = size // 2
    box = (max(cx - half, 0), max(cy - half, 0),
           min(cx + half, width), min(cy + half, height))
    if box[2] - box[0] < 16 or box[3] - box[1] < 16:
        return rgb
    return rgb.crop(box)


def flatten_on_black(image: Image.Image) -> Image.Image:
    """Composite an alpha cutout onto black and crop to what is actually there.

    Additive blending treats black as no contribution, so the area outside the
    sphere costs nothing. Cropping to the alpha bounding box is exact, unlike
    guessing the subject from colour.
    """
    rgba = image.convert("RGBA")
    box = rgba.getbbox()
    if box:
        rgba = rgba.crop(box)
    flat = Image.new("RGB", rgba.size, (0, 0, 0))
    flat.paste(rgba, mask=rgba.split()[3])
    return flat


def circular_mask(image: Image.Image, size: int = MATCAP_SIZE) -> Image.Image:
    """Crop to a centred circle on black.

    The shader samples this by normal, and normals at the silhouette map to the
    edge of the image. Anything in the corners is off-sphere and would show up
    as sheen on a surface facing away from the viewer, so the corners are
    forced to black -- which the additive blend then treats as no contribution.
    """
    image = image.convert("RGB").resize((size, size), Image.LANCZOS)
    pixels = image.load()
    centre = (size - 1) / 2.0
    radius = centre
    for y in range(size):
        for x in range(size):
            if math.hypot(x - centre, y - centre) > radius:
                pixels[x, y] = (0, 0, 0)
    return image


def load_provider(provider_id: str) -> dict:
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    providers = config["providers"]
    if provider_id not in providers:
        raise SystemExit(f"unknown provider {provider_id!r}; have {sorted(providers)}")
    entry = dict(providers[provider_id], id=provider_id)
    # The seamless-texture providers ask for tiling. A matcap is a single
    # centred sphere and must not wrap, so turn it off explicitly rather than
    # relying on it being a no-op in this Forge build.
    sampling = dict(entry.get("sampling") or {})
    sampling["tiling"] = False
    entry["sampling"] = sampling
    return entry


def generate(names: list[str], provider_id: str, variants: int, seed: int | None) -> None:
    provider = load_provider(provider_id)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names:
        if name not in MATCAPS:
            raise SystemExit(f"unknown matcap {name!r}; --list shows the set")
        prompt = build_prompt(MATCAPS[name])
        for variant in range(1, variants + 1):
            sampling = {"seed": seed + variant} if seed is not None else None
            print(f"[{name}] variant {variant} ...", flush=True)
            is_openai = provider["type"] == "openai-images"
            if is_openai:
                # gpt-image can return a real alpha channel, which removes the
                # failure mode entirely: rather than begging the model for a
                # black void and cropping whatever scene it invents, ask for
                # the sphere alone and composite it ourselves.
                image = provider_lib.generate(
                    provider, prompt, size="1024x1024", timeout=300,
                    transparent=True, quality=provider.get("quality"),
                )
            else:
                merged = dict(provider["sampling"])
                merged["negativePrompt"] = NEGATIVE
                if sampling:
                    merged.update(sampling)
                image = provider_lib.generate(
                    provider, prompt, size="512x512", timeout=300, sampling=merged
                )
            if isinstance(image, (bytes, bytearray)):
                import io

                image = Image.open(io.BytesIO(image))
            path = OUT / f"{name}-{variant}.png"
            if image.mode in ("RGBA", "LA") and image.getextrema()[-1][0] < 255:
                image = flatten_on_black(image)
            circular_mask(autocrop_sphere(image)).save(path)
            print(f"  wrote {path}")


def contact_sheet() -> Path:
    """One PNG of everything staged, so the set is judged together."""
    # Exclude the sheet itself, or each run folds the previous sheet back in as
    # though it were another matcap.
    files = sorted(p for p in OUT.glob("*.png") if p.name != "contact-sheet.png")
    if not files:
        raise SystemExit("nothing staged; generate first")
    columns = min(6, len(files))
    rows = math.ceil(len(files) / columns)
    cell = MATCAP_SIZE
    sheet = Image.new("RGB", (columns * cell, rows * cell), (18, 18, 22))
    for index, path in enumerate(files):
        sheet.paste(Image.open(path), ((index % columns) * cell, (index // columns) * cell))
    out = OUT / "contact-sheet.png"
    sheet.save(out)
    print(f"contact sheet: {out} ({len(files)} matcaps)")
    return out


def promote(name: str, variant: int) -> None:
    source = OUT / f"{name}-{variant}.png"
    if not source.exists():
        raise SystemExit(f"not staged: {source}")
    PROMOTE_DIR.mkdir(parents=True, exist_ok=True)
    target = PROMOTE_DIR / f"{name}.png"
    target.write_bytes(source.read_bytes())
    print(f"promoted {source.name} -> {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="matcaps to generate")
    parser.add_argument("--provider", default="forge-quality")
    parser.add_argument("--variants", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--sheet", action="store_true", help="contact sheet of staged output")
    parser.add_argument("--promote", metavar="NAME")
    parser.add_argument("--variant", type=int, default=1)
    args = parser.parse_args()

    if args.list:
        for name, description in MATCAPS.items():
            print(f"{name:10s} {description}")
        return 0
    if args.promote:
        promote(args.promote, args.variant)
        return 0
    if args.names:
        generate(args.names, args.provider, args.variants, args.seed)
    if args.sheet or args.names:
        contact_sheet()
    return 0


if __name__ == "__main__":
    sys.exit(main())
