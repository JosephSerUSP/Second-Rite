# gauntlet/evaluator/contact_sheets.py

import os
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

def get_font(size: int = 14):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

def draw_checkerboard(width: int, height: int, cell_size: int = 16, c1=(35, 35, 40), c2=(50, 50, 58)) -> Image.Image:
    bg = Image.new("RGBA", (width, height), c1 + (255,))
    draw = ImageDraw.Draw(bg)
    for y in range(0, height, cell_size):
        for x in range(0, width, cell_size):
            if ((x // cell_size) + (y // cell_size)) % 2 == 1:
                draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=c2 + (255,))
    return bg

def create_silhouette_mask(img: Image.Image) -> Image.Image:
    """Returns a black silhouette with crisp alpha preserved."""
    img_rgba = img.convert("RGBA")
    r, g, b, a = img_rgba.split()
    black = Image.new("L", img.size, 0)
    return Image.merge("RGBA", (black, black, black, a))

def create_static_sheet(
    sprite_path: str,
    output_path: str,
    title: str = "Static Evaluation Sheet",
    standing_height_px: Optional[int] = None
) -> str:
    """
    Creates a comprehensive static inspection sheet:
    1. 192x192 Native on Dark Checkerboard
    2. 192x192 Native on Neutral Light Grey
    3. 192x192 Pure Silhouette Mask
    4. 4x Nearest-Neighbor Magnified View (768x768) with 128px standing height guide & anchor guide
    """
    orig = Image.open(sprite_path).convert("RGBA")
    w, h = orig.size # 192, 192

    # Magnified version (4x nearest neighbor = 768x768)
    scale = 4
    mag_w, mag_h = w * scale, h * scale
    mag_img = orig.resize((mag_w, mag_h), Image.NEAREST)

    # Checkerboard for magnified
    mag_bg = draw_checkerboard(mag_w, mag_h, cell_size=18, c1=(30, 32, 38), c2=(45, 48, 56))
    mag_bg.paste(mag_img, (0, 0), mag_img)
    draw_mag = ImageDraw.Draw(mag_bg)

    # Draw anchor crosshair on magnified (Anchor is (96, 176) * scale)
    ax, ay = 96 * scale, 176 * scale
    draw_mag.line([ax - 15, ay, ax + 15, ay], fill=(255, 60, 60, 220), width=2)
    draw_mag.line([ax, ay - 15, ax, ay + 15], fill=(255, 60, 60, 220), width=2)
    draw_mag.ellipse([ax - 4, ay - 4, ax + 4, ay + 4], outline=(255, 255, 60, 240), width=2)

    # Draw 128px height threshold line from anchor up (176 - 128 = 48)
    h_top = (176 - 128) * scale
    draw_mag.line([0, h_top, mag_w, h_top], fill=(60, 220, 255, 180), width=2)
    draw_mag.text((10, h_top - 18), "128px Max Standing Height Guide", fill=(60, 220, 255, 255), font=get_font(12))
    draw_mag.text((10, ay + 6), f"Ground Anchor (96, 176)", fill=(255, 100, 100, 255), font=get_font(12))

    # Native panels
    bg_dark = draw_checkerboard(w, h, cell_size=12, c1=(25, 27, 32), c2=(40, 43, 50))
    bg_dark.paste(orig, (0, 0), orig)

    bg_light = Image.new("RGBA", (w, h), (215, 218, 224, 255))
    bg_light.paste(orig, (0, 0), orig)

    sil = create_silhouette_mask(orig)
    bg_sil = Image.new("RGBA", (w, h), (240, 242, 245, 255))
    bg_sil.paste(sil, (0, 0), sil)

    # Layout canvas
    sheet_w = mag_w + w + 60
    sheet_h = max(mag_h, (h + 30) * 3) + 70
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (18, 19, 23, 255))
    draw_sheet = ImageDraw.Draw(sheet)

    # Title header
    font_title = get_font(16)
    font_sub = get_font(12)
    draw_sheet.text((20, 15), title, fill=(240, 240, 245, 255), font=font_title)
    sub_text = f"Native Canvas: 192x192 | Anchor: (96, 176) | Standing Height: {standing_height_px if standing_height_px else 'N/A'} px"
    draw_sheet.text((20, 38), sub_text, fill=(160, 170, 185, 255), font=font_sub)

    # Place magnified
    sheet.paste(mag_bg, (20, 60))

    # Place native columns
    col_x = 20 + mag_w + 20
    draw_sheet.text((col_x, 60), "1. Native (Dark BG)", fill=(200, 205, 215, 255), font=font_sub)
    sheet.paste(bg_dark, (col_x, 80))

    draw_sheet.text((col_x, 80 + h + 15), "2. Native (Light BG)", fill=(200, 205, 215, 255), font=font_sub)
    sheet.paste(bg_light, (col_x, 80 + h + 35))

    draw_sheet.text((col_x, 80 + (h + 15) * 2), "3. Silhouette Mask", fill=(200, 205, 215, 255), font=font_sub)
    sheet.paste(bg_sil, (col_x, 80 + (h + 35) * 2))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path)
    return output_path

def create_animation_strip(
    frame_paths: List[str],
    output_path: str,
    title: str = "Animation Strip",
    fps: int = 8,
    make_gif: bool = True
) -> Tuple[str, Optional[str]]:
    """
    Assembles a horizontal strip of animation frames with indices and timing guides.
    Optionally outputs an animated transparent GIF.
    """
    frames = [Image.open(p).convert("RGBA") for p in frame_paths]
    if not frames:
        raise ValueError("No frames provided for animation strip.")

    n = len(frames)
    w, h = frames[0].size
    pad = 8
    header_h = 50

    strip_w = n * w + (n + 1) * pad
    strip_h = h + header_h + pad + 25

    strip = Image.new("RGBA", (strip_w, strip_h), (20, 22, 26, 255))
    draw = ImageDraw.Draw(strip)

    draw.text((pad, 12), f"{title} — ({n} Frames @ {fps} FPS)", fill=(240, 240, 245, 255), font=get_font(15))

    font_idx = get_font(11)
    for i, frm in enumerate(frames):
        x = pad + i * (w + pad)
        y = header_h
        # Checkerboard under each frame
        bg = draw_checkerboard(w, h, cell_size=12, c1=(28, 30, 36), c2=(40, 43, 50))
        bg.paste(frm, (0, 0), frm)
        strip.paste(bg, (x, y))
        draw.text((x + 4, y + h + 4), f"F{i+1:02d}", fill=(180, 190, 205, 255), font=font_idx)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    strip.save(output_path)

    gif_path = None
    if make_gif:
        gif_path = os.path.splitext(output_path)[0] + ".gif"
        # Convert frames for GIF with transparency preservation
        duration_ms = int(1000 / fps)
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            disposal=2
        )

    return output_path, gif_path

def create_locomotion_grid(
    direction_frames: dict, # e.g. {"S": [paths], "SW": [...], ...}
    output_path: str,
    title: str = "8-Direction Locomotion Grid (64 Frames)"
) -> str:
    """
    Creates an 8-row x 8-frame locomotion overview sheet.
    Directions in order: S, SW, W, NW, N, NE, E, SE
    """
    dir_order = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
    cols = 8
    rows = len(dir_order)
    w, h = 192, 192
    pad = 6
    label_w = 60
    header_h = 50

    grid_w = label_w + cols * (w + pad) + pad
    grid_h = header_h + rows * (h + pad) + pad

    grid = Image.new("RGBA", (grid_w, grid_h), (18, 20, 24, 255))
    draw = ImageDraw.Draw(grid)

    draw.text((pad, 14), title, fill=(245, 245, 250, 255), font=get_font(16))

    font_dir = get_font(14)
    font_f = get_font(10)

    for r, dname in enumerate(dir_order):
        y = header_h + r * (h + pad)
        draw.text((pad + 10, y + h // 2 - 10), dname, fill=(255, 215, 80, 255), font=font_dir)
        paths = direction_frames.get(dname, [])
        for c in range(cols):
            x = label_w + c * (w + pad)
            if c < len(paths):
                frm = Image.open(paths[c]).convert("RGBA")
                bg = draw_checkerboard(w, h, cell_size=10, c1=(26, 28, 34), c2=(38, 41, 48))
                bg.paste(frm, (0, 0), frm)
                grid.paste(bg, (x, y))
                draw.text((x + 3, y + h - 14), f"{dname}-{c+1}", fill=(160, 170, 180, 255), font=font_f)
            else:
                draw.rectangle([x, y, x + w, y + h], fill=(24, 25, 30, 255), outline=(40, 42, 50, 255))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    grid.save(output_path)
    return output_path

def create_lineup_sheet(
    characters: List[dict], # [{"name": "Celina", "path": "...", "height": 124}, ...]
    output_path: str,
    title: str = "Ensemble Lineup Comparison"
) -> str:
    """
    Renders a multi-character side-by-side comparison with:
    - Full color native + 2x scaled side-by-side
    - Pure silhouette lineup
    - Ground anchor alignment and 128px height ceiling line
    """
    n = len(characters)
    scale = 2
    w, h = 192, 192
    scaled_w, scaled_h = w * scale, h * scale
    pad = 20
    header_h = 60

    total_w = pad + n * (scaled_w + pad)
    total_h = header_h + scaled_h * 2 + pad * 3

    sheet = Image.new("RGBA", (total_w, total_h), (16, 17, 21, 255))
    draw = ImageDraw.Draw(sheet)

    draw.text((pad, 16), title, fill=(245, 245, 250, 255), font=get_font(18))
    draw.text((pad, 40), "Lineup Scale: 2x Nearest Neighbor | Anchor: (96, 176) | Height limit: 128px", fill=(160, 170, 185, 255), font=get_font(12))

    font_name = get_font(14)
    font_guide = get_font(11)

    # Row 1: Full Color Lineup
    row1_y = header_h + pad
    # Row 2: Silhouette Lineup
    row2_y = row1_y + scaled_h + pad

    # Guide lines across rows
    # Anchor line in row 1 and row 2
    ay_rel = 176 * scale
    draw.line([pad, row1_y + ay_rel, total_w - pad, row1_y + ay_rel], fill=(255, 70, 70, 160), width=1)
    draw.line([pad, row2_y + ay_rel, total_w - pad, row2_y + ay_rel], fill=(255, 70, 70, 160), width=1)

    # 128px ceiling line
    ceil_rel = (176 - 128) * scale
    draw.line([pad, row1_y + ceil_rel, total_w - pad, row1_y + ceil_rel], fill=(60, 200, 255, 160), width=1)
    draw.line([pad, row2_y + ceil_rel, total_w - pad, row2_y + ceil_rel], fill=(60, 200, 255, 160), width=1)

    for i, c in enumerate(characters):
        x = pad + i * (scaled_w + pad)
        cname = c.get("name", f"Char {i+1}")
        cpath = c.get("path")
        cheight = c.get("height", "N/A")

        if os.path.exists(cpath):
            img = Image.open(cpath).convert("RGBA")
            img_scaled = img.resize((scaled_w, scaled_h), Image.NEAREST)

            bg_color = draw_checkerboard(scaled_w, scaled_h, cell_size=16, c1=(26, 28, 34), c2=(38, 41, 48))
            bg_color.paste(img_scaled, (0, 0), img_scaled)
            sheet.paste(bg_color, (x, row1_y))

            sil = create_silhouette_mask(img)
            sil_scaled = sil.resize((scaled_w, scaled_h), Image.NEAREST)
            bg_sil = Image.new("RGBA", (scaled_w, scaled_h), (235, 238, 242, 255))
            bg_sil.paste(sil_scaled, (0, 0), sil_scaled)
            sheet.paste(bg_sil, (x, row2_y))

            draw.text((x + 8, row1_y + 8), f"{cname} ({cheight}px)", fill=(255, 220, 90, 255), font=font_name)
            draw.text((x + 8, row2_y + 8), f"{cname} Silhouette", fill=(30, 30, 40, 255), font=font_name)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path)
    return output_path
