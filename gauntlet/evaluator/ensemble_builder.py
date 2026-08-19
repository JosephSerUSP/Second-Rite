# gauntlet/evaluator/ensemble_builder.py
# Generates the 6 comprehensive ensemble comparative evaluation sheets

import os
import glob
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List
from gauntlet.evaluator.contact_sheets import draw_checkerboard, get_font

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def get_latest_character_round_dir(char_name: str) -> str:
    """Finds the latest round directory for a character."""
    char_base = os.path.join(REPO_ROOT, "gauntlet", "characters", char_name)
    round_dirs = sorted(glob.glob(os.path.join(char_base, "round-*")))
    if not round_dirs:
        raise FileNotFoundError(f"No rounds found for character {char_name} in {char_base}")
    return round_dirs[-1]

def generate_ensemble_sheets(output_dir: str) -> Dict[str, str]:
    """
    Generates all 6 multi-character ensemble comparison sheets:
    1. Static Lineup (Color 2x + Native 1x + Anchor line)
    2. Silhouette Lineup (Pure black silhouettes on light background)
    3. Synchronized Idle Strips & GIF (16 frames each)
    4. Locomotion Style Grid (S, W, N, E walks for all 3)
    5. Signature Gesture Flourish Strips & GIF
    6. Native 1x vs 4x Pixel Readability Sheet
    """
    os.makedirs(output_dir, exist_ok=True)
    sheets = {}

    celina_dir = get_latest_character_round_dir("celina")
    agnes_dir = get_latest_character_round_dir("agnes")
    gambler_dir = get_latest_character_round_dir("gambler")

    celina_static = os.path.join(celina_dir, "static_front.png")
    agnes_static = os.path.join(agnes_dir, "static_front.png")
    gambler_static = os.path.join(gambler_dir, "static_front.png")

    # 1. Static Lineup
    static_lineup_path = os.path.join(output_dir, "ensemble_01_static_lineup.png")
    _build_static_lineup(
        [("Celina (Duelist)", celina_static), ("Agnes (Heavy Fighter)", agnes_static), ("The Gambler (Showman)", gambler_static)],
        static_lineup_path
    )
    sheets["static_lineup"] = static_lineup_path

    # 2. Silhouette Lineup
    sil_lineup_path = os.path.join(output_dir, "ensemble_02_silhouette_lineup.png")
    _build_silhouette_lineup(
        [("Celina", celina_static), ("Agnes", agnes_static), ("The Gambler", gambler_static)],
        sil_lineup_path
    )
    sheets["silhouette_lineup"] = sil_lineup_path

    # 3. Synchronized Idle Strip & GIF
    idle_strip_path = os.path.join(output_dir, "ensemble_03_idle_strip.png")
    _build_ensemble_idle_strip(celina_dir, agnes_dir, gambler_dir, idle_strip_path)
    sheets["idle_strip"] = idle_strip_path

    # 4. Locomotion Style Grid
    loco_grid_path = os.path.join(output_dir, "ensemble_04_locomotion_grid.png")
    _build_ensemble_locomotion_grid(celina_dir, agnes_dir, gambler_dir, loco_grid_path)
    sheets["locomotion_grid"] = loco_grid_path

    # 5. Gesture Strips & GIF
    gesture_strip_path = os.path.join(output_dir, "ensemble_05_gesture_strip.png")
    _build_ensemble_gesture_strip(celina_dir, agnes_dir, gambler_dir, gesture_strip_path)
    sheets["gesture_strip"] = gesture_strip_path

    # 6. Pixel Readability Sheet (1x vs 4x)
    pixel_sheet_path = os.path.join(output_dir, "ensemble_06_pixel_inspection.png")
    _build_ensemble_pixel_sheet(celina_static, agnes_static, gambler_static, pixel_sheet_path)
    sheets["pixel_inspection"] = pixel_sheet_path

    return sheets

def _build_static_lineup(chars: List[tuple], output_path: str):
    num_chars = len(chars)
    char_w = 192 * 2
    char_h = 192 * 2
    pad_x = 40
    pad_y = 70
    
    total_w = pad_x * 2 + num_chars * char_w + (num_chars - 1) * 40
    total_h = pad_y + char_h + 260
    
    sheet = Image.new("RGBA", (total_w, total_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(sheet)
    font_title = get_font(20)
    font_label = get_font(15)
    font_small = get_font(12)
    
    draw.text((pad_x, 18), "ENSEMBLE STATIC LINEUP — Full Color & Ground Anchor Alignment", fill=(240, 240, 245), font=font_title)
    draw.text((pad_x, 44), "Scale Hierarchy, Palette Separation & Body Type Independence (Budget <= 128px)", fill=(160, 165, 180), font=font_small)
    
    cur_x = pad_x
    for name, path in chars:
        sprite = Image.open(path).convert("RGBA")
        sprite_2x = sprite.resize((char_w, char_h), Image.NEAREST)
        
        # 2x Box
        bg = draw_checkerboard(char_w, char_h, tile_size=12)
        bg.paste(sprite_2x, (0, 0), sprite_2x)
        sheet.paste(bg, (cur_x, pad_y))
        draw.rectangle([cur_x, pad_y, cur_x + char_w, pad_y + char_h], outline=(65, 70, 85), width=1)
        
        # 1x Native below
        native_bg = Image.new("RGBA", (192, 192), (28, 30, 36, 255))
        native_bg.paste(sprite, (0, 0), sprite)
        sheet.paste(native_bg, (cur_x, pad_y + char_h + 20))
        draw.rectangle([cur_x, pad_y + char_h + 20, cur_x + 192, pad_y + char_h + 20 + 192], outline=(65, 70, 85), width=1)
        
        # Label
        draw.text((cur_x, pad_y + char_h + 20 + 192 + 10), name, fill=(255, 220, 100), font=font_label)
        cur_x += char_w + 40

    # Common Ground Anchor Line across 2x sprites
    anchor_y_2x = pad_y + 176 * 2
    draw.line([pad_x, anchor_y_2x, cur_x - 40, anchor_y_2x], fill=(255, 60, 60, 220), width=2)
    draw.text((pad_x + 6, anchor_y_2x + 4), "Ground Anchor Line (Y=176)", fill=(255, 100, 100), font=font_small)

    sheet.save(output_path, "PNG")

def _build_silhouette_lineup(chars: List[tuple], output_path: str):
    num_chars = len(chars)
    char_w = 192 * 2
    char_h = 192 * 2
    pad_x = 40
    pad_y = 70
    
    total_w = pad_x * 2 + num_chars * char_w + (num_chars - 1) * 40
    total_h = pad_y + char_h + 60
    
    sheet = Image.new("RGBA", (total_w, total_h), (225, 230, 238, 255))
    draw = ImageDraw.Draw(sheet)
    font_title = get_font(20)
    font_label = get_font(15)
    
    draw.text((pad_x, 18), "ENSEMBLE SILHOUETTE LINEUP — Pure Black Masks on High-Contrast Field", fill=(20, 22, 28), font=font_title)
    
    cur_x = pad_x
    for name, path in chars:
        sprite = Image.open(path).convert("RGBA")
        sprite_2x = sprite.resize((char_w, char_h), Image.NEAREST)
        alpha = sprite_2x.split()[3]
        
        sil_bg = Image.new("RGBA", (char_w, char_h), (245, 248, 252, 255))
        black_shape = Image.new("RGBA", (char_w, char_h), (0, 0, 0, 255))
        sil_bg.paste(black_shape, (0, 0), alpha)
        
        sheet.paste(sil_bg, (cur_x, pad_y))
        draw.rectangle([cur_x, pad_y, cur_x + char_w, pad_y + char_h], outline=(180, 185, 200), width=1)
        draw.text((cur_x + 10, pad_y + char_h + 12), name, fill=(30, 35, 45), font=font_label)
        cur_x += char_w + 40

    anchor_y_2x = pad_y + 176 * 2
    draw.line([pad_x, anchor_y_2x, cur_x - 40, anchor_y_2x], fill=(220, 40, 40, 200), width=2)
    sheet.save(output_path, "PNG")

def _build_ensemble_idle_strip(c_dir: str, a_dir: str, g_dir: str, output_path: str):
    c_files = sorted(glob.glob(os.path.join(c_dir, "idle", "*.png")))[:16]
    a_files = sorted(glob.glob(os.path.join(a_dir, "idle", "*.png")))[:16]
    g_files = sorted(glob.glob(os.path.join(g_dir, "idle", "*.png")))[:16]
    
    frame_w, frame_h = 192, 192
    pad_left = 160
    pad_top = 70
    num_frames = 16
    
    total_w = pad_left + num_frames * (frame_w + 2) + 20
    total_h = pad_top + 3 * (frame_h + 6) + 30
    
    sheet = Image.new("RGBA", (total_w, total_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(sheet)
    font_title = get_font(20)
    font_label = get_font(14)
    font_small = get_font(11)
    
    draw.text((20, 18), "ENSEMBLE IDLE STRIPS — Synchronized 16-Frame Breathing & Posture Comparison", fill=(240, 240, 245), font=font_title)
    
    rows = [
        ("Celina\n(Restrained)", c_files),
        ("Agnes\n(Grounded)", a_files),
        ("The Gambler\n(Theatrical)", g_files)
    ]
    
    for r_idx, (label, files) in enumerate(rows):
        y = pad_top + r_idx * (frame_h + 6)
        draw.text((20, y + frame_h // 2 - 16), label, fill=(255, 215, 0), font=font_label)
        
        for f_idx in range(num_frames):
            x = pad_left + f_idx * (frame_w + 2)
            if f_idx < len(files):
                frm = Image.open(files[f_idx]).convert("RGBA")
                bg = draw_checkerboard(frame_w, frame_h, tile_size=10)
                bg.paste(frm, (0, 0), frm)
                sheet.paste(bg, (x, y))
                draw.line([x, y + 176, x + frame_w, y + 176], fill=(255, 60, 60, 100), width=1)
                draw.rectangle([x, y, x + frame_w, y + frame_h], outline=(55, 60, 75), width=1)

    sheet.save(output_path, "PNG")

def _build_ensemble_locomotion_grid(c_dir: str, a_dir: str, g_dir: str, output_path: str):
    """Shows representative 8-frame walk cycles in S, W, N, E for all 3 characters."""
    dirs = ["S", "W", "N", "E"]
    frame_w, frame_h = 192, 192
    pad_left = 180
    pad_top = 70
    
    total_w = pad_left + 8 * (frame_w + 2) + 20
    total_h = pad_top + (len(dirs) * 3) * (frame_h + 4) + 30
    
    grid = Image.new("RGBA", (total_w, total_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(grid)
    font_title = get_font(20)
    font_label = get_font(13)
    
    draw.text((20, 18), "ENSEMBLE LOCOMOTION COMPARISON — S, W, N, E Walks across Celina, Agnes, Gambler", fill=(240, 240, 245), font=font_title)
    
    chars = [("Celina", c_dir), ("Agnes", a_dir), ("Gambler", g_dir)]
    row_idx = 0
    for d in dirs:
        for cname, cdir in chars:
            y = pad_top + row_idx * (frame_h + 4)
            draw.text((20, y + frame_h // 2 - 8), f"{cname} [{d}]", fill=(255, 215, 0), font=font_label)
            
            dfiles = sorted(glob.glob(os.path.join(cdir, "walk", d, "*.png")))[:8]
            for col_idx, fpath in enumerate(dfiles):
                x = pad_left + col_idx * (frame_w + 2)
                frm = Image.open(fpath).convert("RGBA")
                bg = draw_checkerboard(frame_w, frame_h, tile_size=10)
                bg.paste(frm, (0, 0), frm)
                grid.paste(bg, (x, y))
                draw.line([x, y + 176, x + frame_w, y + 176], fill=(255, 60, 60, 100), width=1)
                draw.rectangle([x, y, x + frame_w, y + frame_h], outline=(55, 60, 75), width=1)
            row_idx += 1

    grid.save(output_path, "PNG")

def _build_ensemble_gesture_strip(c_dir: str, a_dir: str, g_dir: str, output_path: str):
    c_files = sorted(glob.glob(os.path.join(c_dir, "gesture", "*.png")))[:24]
    a_files = sorted(glob.glob(os.path.join(a_dir, "gesture", "*.png")))[:24]
    g_files = sorted(glob.glob(os.path.join(g_dir, "gesture", "*.png")))[:24]
    
    frame_w, frame_h = 192, 192
    pad_left = 180
    pad_top = 70
    num_frames = 24
    
    total_w = pad_left + num_frames * (frame_w + 2) + 20
    total_h = pad_top + 3 * (frame_h + 6) + 30
    
    sheet = Image.new("RGBA", (total_w, total_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(sheet)
    font_title = get_font(20)
    font_label = get_font(13)
    
    draw.text((20, 18), "ENSEMBLE SIGNATURE GESTURE COMPARISON — 24-Frame Signature Flourishes", fill=(240, 240, 245), font=font_title)
    
    rows = [
        ("Celina: Duelist Salute\n(Rapier draw & salute)", c_files),
        ("Agnes: Shield Slam\n(Heavy bash & battle cry)", a_files),
        ("The Gambler: Card Trick\n(Bow & card fan flourish)", g_files)
    ]
    
    for r_idx, (label, files) in enumerate(rows):
        y = pad_top + r_idx * (frame_h + 6)
        draw.text((20, y + frame_h // 2 - 16), label, fill=(255, 215, 0), font=font_label)
        
        for f_idx in range(num_frames):
            x = pad_left + f_idx * (frame_w + 2)
            if f_idx < len(files):
                frm = Image.open(files[f_idx]).convert("RGBA")
                bg = draw_checkerboard(frame_w, frame_h, tile_size=10)
                bg.paste(frm, (0, 0), frm)
                sheet.paste(bg, (x, y))
                draw.line([x, y + 176, x + frame_w, y + 176], fill=(255, 60, 60, 100), width=1)
                draw.rectangle([x, y, x + frame_w, y + frame_h], outline=(55, 60, 75), width=1)

    sheet.save(output_path, "PNG")

def _build_ensemble_pixel_sheet(c_path: str, a_path: str, g_path: str, output_path: str):
    """4x nearest-neighbor detail comparison for all 3 side-by-side."""
    char_w = 192 * 4
    char_h = 192 * 4
    pad_x = 30
    pad_y = 70
    
    total_w = pad_x * 2 + 3 * char_w + 2 * 30
    total_h = pad_y + char_h + 100
    
    sheet = Image.new("RGBA", (total_w, total_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(sheet)
    font_title = get_font(20)
    font_label = get_font(16)
    
    draw.text((pad_x, 18), "ENSEMBLE 4X NEAREST-NEIGHBOR PIXEL INSPECTION — Clean Silhouette & Material Planes", fill=(240, 240, 245), font=font_title)
    
    chars = [("Celina (Slender Duelist)", c_path), ("Agnes (Heavy Fighter)", a_path), ("The Gambler (Showman)", g_path)]
    cur_x = pad_x
    for name, path in chars:
        sprite = Image.open(path).convert("RGBA")
        sprite_4x = sprite.resize((char_w, char_h), Image.NEAREST)
        
        bg = draw_checkerboard(char_w, char_h, tile_size=16)
        bg.paste(sprite_4x, (0, 0), sprite_4x)
        sheet.paste(bg, (cur_x, pad_y))
        draw.rectangle([cur_x, pad_y, cur_x + char_w, pad_y + char_h], outline=(65, 70, 85), width=1)
        
        # Guide line at 128px max height ceiling (48 * 4 = 192 from top)
        ceiling_y = pad_y + 48 * 4
        draw.line([cur_x, ceiling_y, cur_x + char_w, ceiling_y], fill=(0, 200, 255, 180), width=2)
        
        # Ground anchor crosshair
        anchor_x = cur_x + 96 * 4
        anchor_y = pad_y + 176 * 4
        draw.line([anchor_x - 20, anchor_y, anchor_x + 20, anchor_y], fill=(255, 60, 60), width=2)
        draw.line([anchor_x, anchor_y - 20, anchor_x, anchor_y + 20], fill=(255, 60, 60), width=2)
        
        draw.text((cur_x + 10, pad_y + char_h + 15), name, fill=(255, 220, 100), font=font_label)
        cur_x += char_w + 30

    sheet.save(output_path, "PNG")
