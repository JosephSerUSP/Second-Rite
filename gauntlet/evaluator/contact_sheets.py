# gauntlet/evaluator/contact_sheets.py
# High-fidelity visual diagnostic contact sheets and animated GIF generator

import os
import glob
from typing import List, Dict, Optional
from PIL import Image, ImageDraw, ImageFont

def get_font(size: int = 14):
    try:
        # Try Windows standard font
        return ImageFont.truetype("arial.ttf", size)
    except IOError:
        return ImageFont.load_default()

def draw_checkerboard(width: int, height: int, tile_size: int = 8, color1=(30, 32, 38), color2=(42, 45, 54)) -> Image.Image:
    img = Image.new("RGBA", (width, height), color1)
    draw = ImageDraw.Draw(img)
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            if ((x // tile_size) + (y // tile_size)) % 2 == 1:
                draw.rectangle([x, y, x + tile_size, y + tile_size], fill=color2)
    return img

def create_static_sheet(
    sprite_path: str,
    output_path: str,
    title: str = "Static Inspection",
    standing_height_px: Optional[float] = None
) -> str:
    """
    Creates a master diagnostic inspection sheet:
    - Left: 4x Nearest-Neighbor enlargement on dark checkerboard with anchor & height markers.
    - Right Top: 1x Native Sprite on Dark BG.
    - Right Mid: 1x Native Sprite on Light BG.
    - Right Bot: Pure Black Silhouette Mask on Neutral BG.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sprite = Image.open(sprite_path).convert("RGBA")
    
    # 4x Nearest Neighbor
    sprite_4x = sprite.resize((192 * 4, 192 * 4), Image.NEAREST)
    
    # Main canvas
    canvas_w = 768 + 240 + 40
    canvas_h = 768 + 90
    sheet = Image.new("RGBA", (canvas_w, canvas_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(sheet)
    
    # Title & Header
    font_title = get_font(18)
    font_small = get_font(12)
    draw.text((20, 16), title, fill=(240, 240, 245), font=font_title)
    sub = f"Native Canvas: 192x192 | Anchor: (96, 176)"
    if standing_height_px:
        sub += f" | Standing Height: {standing_height_px:.1f} px (Budget <= 128 px)"
    draw.text((20, 42), sub, fill=(160, 165, 180), font=font_small)

    # 1. Left: 4x Box with Checkerboard
    box_x = 20
    box_y = 70
    bg_4x = draw_checkerboard(768, 768, tile_size=16)
    bg_4x.paste(sprite_4x, (0, 0), sprite_4x)
    sheet.paste(bg_4x, (box_x, box_y))
    
    draw_4x = ImageDraw.Draw(sheet)
    draw_4x.rectangle([box_x, box_y, box_x + 768, box_y + 768], outline=(60, 65, 80), width=1)
    
    # Height Budget Marker (128px ceiling from anchor Y=176 -> 176 - 128 = 48)
    # At 4x: (48 * 4) = 192 px from top
    ceiling_y = box_y + 48 * 4
    draw_4x.line([box_x, ceiling_y, box_x + 768, ceiling_y], fill=(0, 200, 255, 200), width=2)
    draw_4x.text((box_x + 10, ceiling_y - 18), "128px Max Standing Height Ceiling", fill=(0, 200, 255), font=font_small)

    # Ground Anchor Crosshair (Anchor is (96, 176) -> at 4x is (384, 704))
    anchor_x = box_x + 96 * 4
    anchor_y = box_y + 176 * 4
    draw_4x.line([anchor_x - 16, anchor_y, anchor_x + 16, anchor_y], fill=(255, 60, 60), width=2)
    draw_4x.line([anchor_x, anchor_y - 16, anchor_x, anchor_y + 16], fill=(255, 60, 60), width=2)
    draw_4x.ellipse([anchor_x - 6, anchor_y - 6, anchor_x + 6, anchor_y + 6], outline=(255, 255, 0), width=2)
    draw_4x.text((box_x + 10, box_y + 768 - 24), "Ground Anchor (96, 176)", fill=(255, 100, 100), font=font_small)

    # 2. Right Side Panels: 1x Native Dark, 1x Native Light, Silhouette
    right_x = box_x + 768 + 20
    
    # Panel 1: Native Dark
    draw.text((right_x, 70), "1. Native 1x (Dark BG)", fill=(200, 205, 220), font=font_small)
    bg_dark = draw_checkerboard(192, 192, tile_size=12, color1=(24, 25, 28), color2=(34, 36, 42))
    bg_dark.paste(sprite, (0, 0), sprite)
    sheet.paste(bg_dark, (right_x, 90))
    draw.rectangle([right_x, 90, right_x + 192, 90 + 192], outline=(60, 65, 80), width=1)

    # Panel 2: Native Light
    draw.text((right_x, 300), "2. Native 1x (Light BG)", fill=(200, 205, 220), font=font_small)
    bg_light = Image.new("RGBA", (192, 192), (210, 215, 225, 255))
    bg_light.paste(sprite, (0, 0), sprite)
    sheet.paste(bg_light, (right_x, 320))
    draw.rectangle([right_x, 320, right_x + 192, 320 + 192], outline=(60, 65, 80), width=1)

    # Panel 3: Silhouette Mask
    draw.text((right_x, 530), "3. Silhouette Mask", fill=(200, 205, 220), font=font_small)
    sil = Image.new("RGBA", (192, 192), (235, 240, 245, 255))
    # Extract alpha mask
    alpha = sprite.split()[3]
    black_shape = Image.new("RGBA", (192, 192), (0, 0, 0, 255))
    sil.paste(black_shape, (0, 0), alpha)
    sheet.paste(sil, (right_x, 550))
    draw.rectangle([right_x, 550, right_x + 192, 550 + 192], outline=(60, 65, 80), width=1)

    sheet.save(output_path, "PNG")
    return output_path

def create_animation_strip(
    frame_paths: List[str],
    output_path: str,
    title: str = "Animation Strip",
    fps: int = 10,
    make_gif: bool = True
) -> str:
    """
    Creates a horizontal inspection strip of all frames in an animation,
    plus an animated GIF for immediate motion playback.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    frames = [Image.open(p).convert("RGBA") for p in frame_paths]
    num_frames = len(frames)
    
    frame_w, frame_h = 192, 192
    pad_x = 8
    pad_y = 60
    
    total_w = pad_x * 2 + num_frames * frame_w + (num_frames - 1) * 4
    total_h = pad_y + frame_h + 30
    
    strip = Image.new("RGBA", (total_w, total_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(strip)
    
    font_title = get_font(16)
    font_small = get_font(11)
    draw.text((pad_x, 16), f"{title} — ({num_frames} Frames @ {fps} FPS)", fill=(240, 240, 245), font=font_title)
    
    cur_x = pad_x
    for i, frm in enumerate(frames):
        bg = draw_checkerboard(frame_w, frame_h, tile_size=10)
        bg.paste(frm, (0, 0), frm)
        strip.paste(bg, (cur_x, pad_y))
        
        # Ground anchor guide line
        draw.line([cur_x, pad_y + 176, cur_x + frame_w, pad_y + 176], fill=(255, 60, 60, 120), width=1)
        draw.rectangle([cur_x, pad_y, cur_x + frame_w, pad_y + frame_h], outline=(55, 60, 75), width=1)
        draw.text((cur_x + 4, pad_y + frame_h + 6), f"F{i+1:02d}", fill=(160, 165, 180), font=font_small)
        cur_x += frame_w + 4

    strip.save(output_path, "PNG")
    
    if make_gif and len(frames) > 0:
        gif_path = os.path.splitext(output_path)[0] + ".gif"
        duration_ms = int(1000 / fps)
        # Create RGB frames with dark checkerboard for clean transparent gif rendering
        gif_frames = []
        for frm in frames:
            g_bg = Image.new("RGBA", (frame_w, frame_h), (25, 27, 32, 255))
            g_bg.paste(frm, (0, 0), frm)
            gif_frames.append(g_bg.convert("RGB"))
        gif_frames[0].save(
            gif_path,
            save_all=True,
            append_images=gif_frames[1:],
            duration=duration_ms,
            loop=0
        )

    return output_path

def create_locomotion_grid(
    dir_frames: Dict[str, List[str]], # e.g. {"S": [...], "SW": [...], ...}
    output_path: str,
    title: str = "8-Direction Locomotion Grid"
) -> str:
    """
    Renders an 8x8 grid showing all 64 frames of locomotion.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    dirs = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
    
    frame_w, frame_h = 192, 192
    num_cols = 8
    pad_left = 60
    pad_top = 60
    cell_pad = 4
    
    total_w = pad_left + num_cols * (frame_w + cell_pad) + 20
    total_h = pad_top + len(dirs) * (frame_h + cell_pad) + 20
    
    grid = Image.new("RGBA", (total_w, total_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(grid)
    
    font_title = get_font(18)
    font_small = get_font(13)
    draw.text((20, 18), f"{title} — (8 Directions x 8 Frames = 64 Total)", fill=(240, 240, 245), font=font_title)
    
    for row_idx, d in enumerate(dirs):
        y = pad_top + row_idx * (frame_h + cell_pad)
        draw.text((15, y + frame_h // 2 - 8), d, fill=(255, 215, 0), font=font_small)
        
        frames = dir_frames.get(d, [])
        for col_idx in range(num_cols):
            x = pad_left + col_idx * (frame_w + cell_pad)
            if col_idx < len(frames):
                frm = Image.open(frames[col_idx]).convert("RGBA")
                bg = draw_checkerboard(frame_w, frame_h, tile_size=10)
                bg.paste(frm, (0, 0), frm)
                grid.paste(bg, (x, y))
                draw.line([x, y + 176, x + frame_w, y + 176], fill=(255, 60, 60, 100), width=1)
                draw.rectangle([x, y, x + frame_w, y + frame_h], outline=(55, 60, 75), width=1)

    grid.save(output_path, "PNG")
    return output_path

def create_lineup_sheet(
    characters: List[Dict[str, any]], # [{"name": "Celina", "path": "...", "height": 118.0}, ...]
    output_path: str,
    title: str = "Character Lineup & Silhouette Comparison"
) -> str:
    """
    Renders a comparative lineup sheet comparing current candidate with existing accepted characters.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    num_chars = len(characters)
    
    char_w = 192 * 2 # 2x scale for clear comparison
    char_h = 192 * 2
    pad_x = 30
    pad_y = 80
    
    total_w = pad_x * 2 + num_chars * char_w + (num_chars - 1) * 30
    total_h = pad_y + char_h + 240
    
    sheet = Image.new("RGBA", (total_w, total_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(sheet)
    
    font_title = get_font(20)
    font_label = get_font(14)
    font_small = get_font(12)
    
    draw.text((pad_x, 20), title, fill=(240, 240, 245), font=font_title)
    draw.text((pad_x, 48), "Cross-Character Scale, Silhouette Separation & Palette Independence", fill=(160, 165, 180), font=font_small)
    
    cur_x = pad_x
    for c in characters:
        name = c.get("name", "Unknown")
        path = c.get("path")
        height = c.get("height", 0.0)
        
        if os.path.exists(path):
            sprite = Image.open(path).convert("RGBA")
            sprite_2x = sprite.resize((char_w, char_h), Image.NEAREST)
            
            # 1. 2x Color Sprite
            bg = draw_checkerboard(char_w, char_h, tile_size=12)
            bg.paste(sprite_2x, (0, 0), sprite_2x)
            sheet.paste(bg, (cur_x, pad_y))
            draw.rectangle([cur_x, pad_y, cur_x + char_w, pad_y + char_h], outline=(65, 70, 85), width=1)
            
            # 2. 1x Native View below
            native_bg = Image.new("RGBA", (192, 192), (30, 32, 38, 255))
            native_bg.paste(sprite, (0, 0), sprite)
            sheet.paste(native_bg, (cur_x, pad_y + char_h + 15))
            draw.rectangle([cur_x, pad_y + char_h + 15, cur_x + 192, pad_y + char_h + 15 + 192], outline=(65, 70, 85), width=1)
            
            # 3. 1x Silhouette Mask beside native
            sil = Image.new("RGBA", (192, 192), (230, 235, 240, 255))
            alpha = sprite.split()[3]
            black_shape = Image.new("RGBA", (192, 192), (0, 0, 0, 255))
            sil.paste(black_shape, (0, 0), alpha)
            sheet.paste(sil, (cur_x + 192, pad_y + char_h + 15))
            draw.rectangle([cur_x + 192, pad_y + char_h + 15, cur_x + char_w, pad_y + char_h + 15 + 192], outline=(65, 70, 85), width=1)
            
            # Label
            draw.text((cur_x, pad_y + char_h + 15 + 192 + 8), f"{name} (Standing: {height:.1f}px)", fill=(255, 220, 100), font=font_label)

        cur_x += char_w + 30

    # Common Ground Anchor Line across 2x sprites
    anchor_y_2x = pad_y + 176 * 2
    draw.line([pad_x, anchor_y_2x, cur_x - 30, anchor_y_2x], fill=(255, 60, 60, 200), width=2)
    draw.text((pad_x + 5, anchor_y_2x + 4), "Ground Anchor Line (Y=176)", fill=(255, 100, 100), font=font_small)

    sheet.save(output_path, "PNG")
    return output_path
