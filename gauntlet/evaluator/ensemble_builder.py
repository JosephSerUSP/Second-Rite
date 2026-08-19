import os
import sys
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_character_round_dir(char_name: str) -> str:
    char_base = os.path.join(REPO_ROOT, "gauntlet", "characters", char_name)
    rounds = [d for d in os.listdir(char_base) if d.startswith("round-")]
    rounds.sort(key=lambda d: int(d.split('-')[1]) if '-' in d and d.split('-')[1].isdigit() else 0)
    if not rounds:
        raise FileNotFoundError(f"No rounds found for {char_name}")
    return os.path.join(char_base, rounds[-1])

def generate_ensemble_sheets(output_dir: str) -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    
    celina_dir = get_character_round_dir("celina")
    agnes_dir = get_character_round_dir("agnes")
    gambler_dir = get_character_round_dir("gambler")
    
    chars = [
        {"name": "Celina", "role": "Slender Duelist (5.5 Heads, 119.8px)", "dir": celina_dir, "color": "#4a90e2"},
        {"name": "Agnes", "role": "Grounded Heavy Brawler (5.0 Heads, 106.0px)", "dir": agnes_dir, "color": "#d97724"},
        {"name": "The Gambler", "role": "Theatrical Showman Rogue (5.2 Heads, 120.4px)", "dir": gambler_dir, "color": "#27ae60"}
    ]
    
    generated = {}
    
    # 1. ENSEMBLE STATIC LINEUP (1x scale + 4x NN crop with exact 192x192 template & ground anchor Y=176)
    w_single, h_single = 192, 192
    total_w = w_single * 3 + 80
    total_h = h_single + 100
    
    static_img = Image.new("RGBA", (total_w, total_h), (24, 28, 36, 255))
    draw = ImageDraw.Draw(static_img)
    
    # Ground Anchor Line Y=176
    anchor_y = 60 + 176
    draw.line([(0, anchor_y), (total_w, anchor_y)], fill=(255, 60, 60, 220), width=2)
    
    # Standing Height Ceiling (128px limit: Y = 176 - 128 = 48)
    limit_y = 60 + 176 - 128
    draw.line([(0, limit_y), (total_w, limit_y)], fill=(80, 180, 255, 180), width=1)
    
    draw.text((10, 42), "MAX STANDING HEIGHT (128px limit)", fill=(100, 200, 255, 255))
    draw.text((10, anchor_y + 4), "GROUND ANCHOR LINE (Y=176)", fill=(255, 100, 100, 255))
    
    for i, c in enumerate(chars):
        x_off = 40 + i * (w_single + 20)
        y_off = 60
        f_path = os.path.join(c["dir"], "static_front.png")
        if os.path.exists(f_path):
            sprite = Image.open(f_path).convert("RGBA")
            static_img.paste(sprite, (x_off, y_off), sprite)
        
        # Center anchor tick X=96
        draw.line([(x_off + 96, y_off), (x_off + 96, y_off + 192)], fill=(255, 255, 255, 40), width=1)
        draw.text((x_off + 10, 12), f"{c['name']}\n{c['role']}", fill=(240, 240, 240, 255))
        
    static_path = os.path.join(output_dir, "ensemble_static_lineup.png")
    static_img.save(static_path)
    generated["static_lineup"] = static_path
    
    # 2. ENSEMBLE SILHOUETTE LINEUP
    sil_img = Image.new("RGBA", (total_w, total_h), (20, 20, 20, 255))
    draw_sil = ImageDraw.Draw(sil_img)
    draw_sil.line([(0, anchor_y), (total_w, anchor_y)], fill=(160, 160, 160, 200), width=2)
    draw_sil.line([(0, limit_y), (total_w, limit_y)], fill=(100, 100, 100, 180), width=1)
    
    for i, c in enumerate(chars):
        x_off = 40 + i * (w_single + 20)
        y_off = 60
        f_path = os.path.join(c["dir"], "static_front.png")
        if os.path.exists(f_path):
            sprite = Image.open(f_path).convert("RGBA")
            alpha = sprite.split()[3]
            sil_sprite = Image.new("RGBA", sprite.size, (255, 255, 255, 255))
            sil_sprite.putalpha(alpha)
            sil_img.paste(sil_sprite, (x_off, y_off), sil_sprite)
            
        draw_sil.text((x_off + 10, 16), f"{c['name']} (Silhouette)", fill=(240, 240, 240, 255))
        
    sil_path = os.path.join(output_dir, "ensemble_silhouette_lineup.png")
    sil_img.save(sil_path)
    generated["silhouette_lineup"] = sil_path
    
    # 3. ENSEMBLE IDLE COMPARISON (Strip & Animated GIF)
    idle_strip_w = 16 * 192 + 60
    idle_strip_h = 3 * 192 + 80
    idle_sheet = Image.new("RGBA", (idle_strip_w, idle_strip_h), (20, 24, 30, 255))
    idle_draw = ImageDraw.Draw(idle_sheet)
    
    gif_frames = []
    for f_idx in range(1, 17):
        frame_comp = Image.new("RGBA", (w_single * 3 + 60, h_single + 70), (22, 26, 32, 255))
        f_draw = ImageDraw.Draw(frame_comp)
        
        # Ground and height guides
        f_draw.line([(0, 40 + 176), (w_single * 3 + 60, 40 + 176)], fill=(255, 60, 60, 180), width=1)
        f_draw.line([(0, 40 + 48), (w_single * 3 + 60, 40 + 48)], fill=(80, 180, 255, 120), width=1)
        
        for c_idx, c in enumerate(chars):
            idle_f_path = os.path.join(c["dir"], "idle", f"idle_{f_idx:02d}.png")
            if os.path.exists(idle_f_path):
                spr = Image.open(idle_f_path).convert("RGBA")
                idle_sheet.paste(spr, ( 50 + (f_idx - 1) * 192, 50 + c_idx * 192 ), spr)
                frame_comp.paste(spr, ( 20 + c_idx * 192, 40 ), spr)
                
            if f_idx == 1:
                idle_draw.text((10, 50 + c_idx * 192 + 80), c["name"], fill=(240, 240, 240, 255))
                
        f_draw.text((20, 10), f"Roster Idle Synchronization (Frame {f_idx:02d}/16) - Ground Anchor Y=176", fill=(220, 220, 220, 255))
        gif_frames.append(frame_comp)
        
    idle_strip_path = os.path.join(output_dir, "ensemble_idle_strip.png")
    idle_sheet.save(idle_strip_path)
    generated["idle_strip"] = idle_strip_path
    
    idle_gif_path = os.path.join(output_dir, "ensemble_idle_comparison.gif")
    gif_frames[0].save(idle_gif_path, save_all=True, append_images=gif_frames[1:], duration=100, loop=0)
    generated["idle_gif"] = idle_gif_path
    
    # 4. ENSEMBLE GESTURE COMPARISON (Strip & Animated GIF)
    gest_strip_w = 24 * 192 + 60
    gest_strip_h = 3 * 192 + 80
    gest_sheet = Image.new("RGBA", (gest_strip_w, gest_strip_h), (20, 24, 30, 255))
    gest_draw = ImageDraw.Draw(gest_sheet)
    
    gest_gif_frames = []
    for f_idx in range(1, 25):
        frame_comp = Image.new("RGBA", (w_single * 3 + 60, h_single + 70), (22, 26, 32, 255))
        f_draw = ImageDraw.Draw(frame_comp)
        
        f_draw.line([(0, 40 + 176), (w_single * 3 + 60, 40 + 176)], fill=(255, 60, 60, 180), width=1)
        f_draw.line([(0, 40 + 48), (w_single * 3 + 60, 40 + 48)], fill=(80, 180, 255, 120), width=1)
        
        for c_idx, c in enumerate(chars):
            gest_f_path = os.path.join(c["dir"], "gesture", f"gesture_{f_idx:02d}.png")
            if os.path.exists(gest_f_path):
                spr = Image.open(gest_f_path).convert("RGBA")
                gest_sheet.paste(spr, ( 50 + (f_idx - 1) * 192, 50 + c_idx * 192 ), spr)
                frame_comp.paste(spr, ( 20 + c_idx * 192, 40 ), spr)
                
            if f_idx == 1:
                gest_draw.text((10, 50 + c_idx * 192 + 80), f"{c['name']}", fill=(240, 240, 240, 255))
                
        f_draw.text((20, 10), f"Signature Gestures (Frame {f_idx:02d}/24) - Fencing Salute vs Ground Slam vs Card Fan", fill=(220, 220, 220, 255))
        gest_gif_frames.append(frame_comp)
        
    gest_strip_path = os.path.join(output_dir, "ensemble_gesture_strip.png")
    gest_sheet.save(gest_strip_path)
    generated["gesture_strip"] = gest_strip_path
    
    gest_gif_path = os.path.join(output_dir, "ensemble_gesture_clash.gif")
    gest_gif_frames[0].save(gest_gif_path, save_all=True, append_images=gest_gif_frames[1:], duration=90, loop=0)
    generated["gesture_gif"] = gest_gif_path
    
    # 5. ENSEMBLE LOCOMOTION COMPARISON (8 Directions across 3 Characters)
    dirs = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
    loco_w = len(dirs) * 192 + 120
    loco_h = 3 * 192 + 100
    loco_sheet = Image.new("RGBA", (loco_w, loco_h), (22, 26, 32, 255))
    loco_draw = ImageDraw.Draw(loco_sheet)
    
    for c_idx, c in enumerate(chars):
        row_y = 50 + c_idx * 192
        loco_draw.line([(0, row_y + 176), (loco_w, row_y + 176)], fill=(255, 60, 60, 160), width=1)
        loco_draw.line([(0, row_y + 48), (loco_w, row_y + 48)], fill=(80, 180, 255, 100), width=1)
        loco_draw.text((10, row_y + 80), f"{c['name']}\n{c['role']}", fill=(240, 240, 240, 255))
        
        for d_idx, d_name in enumerate(dirs):
            if c_idx == 0:
                loco_draw.text((120 + d_idx * 192 + 80, 15), d_name, fill=(240, 240, 240, 255))
                
            walk_path = os.path.join(c["dir"], "walk", d_name, f"walk_{d_name}_01.png")
            if os.path.exists(walk_path):
                spr = Image.open(walk_path).convert("RGBA")
                loco_sheet.paste(spr, (120 + d_idx * 192, row_y), spr)
                
    loco_path = os.path.join(output_dir, "ensemble_locomotion_comparison.png")
    loco_sheet.save(loco_path)
    generated["locomotion_grid"] = loco_path
    
    # 6. ENSEMBLE NATIVE 1X VS 4X PIXEL INSPECTION SHEET
    nn_w = 192 * 4 + 40
    nn_h = 192 * 4 + 120
    comp_w = 3 * (192 + 192 * 2 + 30) + 60
    comp_h = 192 * 2 + 120
    
    inspect_img = Image.new("RGBA", (comp_w, comp_h), (22, 26, 32, 255))
    ins_draw = ImageDraw.Draw(inspect_img)
    ins_draw.text((20, 15), "Native 1x Resolution vs 2x Nearest-Neighbor Pixel Cluster Inspection - Ground Anchor Y=176", fill=(240, 240, 240, 255))
    
    for i, c in enumerate(chars):
        x_base = 30 + i * (192 + 192 * 2 + 30)
        f_path = os.path.join(c["dir"], "static_front.png")
        if os.path.exists(f_path):
            spr = Image.open(f_path).convert("RGBA")
            # 1x native
            inspect_img.paste(spr, (x_base, 60), spr)
            # 2x nearest-neighbor
            spr_2x = spr.resize((192 * 2, 192 * 2), Image.NEAREST)
            inspect_img.paste(spr_2x, (x_base + 192 + 15, 60), spr_2x)
            
        ins_draw.text((x_base, 42), f"{c['name']} (1x & 2x NN)", fill=(200, 220, 240, 255))
        
    inspect_path = os.path.join(output_dir, "ensemble_pixel_inspection.png")
    inspect_img.save(inspect_path)
    generated["pixel_inspection"] = inspect_path
    
    return generated
