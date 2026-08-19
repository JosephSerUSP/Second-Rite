# gauntlet/pipeline/texture_builder.py
# Pure-Python procedural texture generator using Blender's native bpy.data.images (zero external dependencies)

import bpy

def create_celina_face_image(name: str = "Celina_Face_Atlas", width: int = 128, height: int = 128) -> bpy.types.Image:
    """
    Creates a 128x128 high-contrast stylized anime face atlas for 5.2-heads tall Celina:
    - Calibrated for 7.5-degree presentation pitch.
    - Saturated warm porcelain skin (#F6D2C0) with crisp jawline contour (#954E36)
    - Bold jet raven hairline & swept bangs (#05050A)
    - Arched duelist brows (Y=66-70)
    - Bold eyeliner & cyan irises with specular catchlights (Y=54-62)
    - Delicate nose point (Y=46) & compact ruby lips (Y=36-40)
    """
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)

    img = bpy.data.images.new(name, width, height, alpha=True)
    
    r_skin, g_skin, b_skin = 0.96, 0.80, 0.72
    r_shadow, g_shadow, b_shadow = 0.65, 0.38, 0.28
    r_hair, g_hair, b_hair = 0.02, 0.02, 0.04
    r_cyan, g_cyan, b_cyan = 0.0, 0.90, 1.0
    r_ruby, g_ruby, b_ruby = 0.92, 0.06, 0.16

    pixels = [1.0] * (width * height * 4)

    def set_pixel(x, y, r, g, b, a=1.0):
        if 0 <= x < width and 0 <= y < height:
            idx = (y * width + x) * 4
            pixels[idx] = r
            pixels[idx + 1] = g
            pixels[idx + 2] = b
            pixels[idx + 3] = a

    # 1. Base skin with chin/jaw shadow
    for y in range(height):
        for x in range(width):
            if y < 26 or (y < 36 and (x < 40 or x > 88)):
                set_pixel(x, y, r_shadow, g_shadow, b_shadow)
            else:
                set_pixel(x, y, r_skin, g_skin, b_skin)

    # 2. Forehead Hairline & Swept Bangs (Top Y=78-128)
    for y in range(74, height):
        for x in range(width):
            if y >= 92:
                set_pixel(x, y, r_hair, g_hair, b_hair)
            elif y >= 76 and (x < 36 or x > 92 or (y > 84 and 36 <= x <= 92)):
                set_pixel(x, y, r_hair, g_hair, b_hair)

    # Side Locks (X < 32 or X > 96 down to Y=26)
    for y in range(26, 92):
        for x in range(width):
            if x < 32 or x > 96:
                set_pixel(x, y, r_hair, g_hair, b_hair)

    # 3. Compact Arched Eyebrows (Y=66-70, centered)
    for x in range(46, 58):
        set_pixel(x, 66 + (x - 46) // 6, r_hair, g_hair, b_hair)
        set_pixel(x, 67 + (x - 46) // 6, r_hair, g_hair, b_hair)
    for x in range(70, 82):
        set_pixel(x, 66 + (82 - x) // 6, r_hair, g_hair, b_hair)
        set_pixel(x, 67 + (82 - x) // 6, r_hair, g_hair, b_hair)

    # 4. Stylized Bold Anime Eyes (Y=52-64, centered at X=54 and X=74)
    for center_x in [54, 74]:
        # Sclera (White base)
        for ey in range(53, 63):
            for ex in range(center_x - 6, center_x + 7):
                if (ex - center_x)**2 / 36 + (ey - 58)**2 / 20 <= 1.0:
                    set_pixel(ex, ey, 1.0, 1.0, 1.0)

        # Bold Upper Eyelash Bar (2px dark liner)
        for ex in range(center_x - 7, center_x + 8):
            set_pixel(ex, 62, r_hair, g_hair, b_hair)
            set_pixel(ex, 63, r_hair, g_hair, b_hair)

        # Cyan Iris & Dark Pupil
        for ey in range(54, 62):
            for ex in range(center_x - 4, center_x + 5):
                if (ex - center_x)**2 / 16 + (ey - 58)**2 / 16 <= 1.0:
                    if abs(ex - center_x) <= 1 and abs(ey - 58) <= 1:
                        set_pixel(ex, ey, 0.02, 0.05, 0.12)
                    elif ex == center_x - 1 and ey == 60:
                        set_pixel(ex, ey, 1.0, 1.0, 1.0) # Catchlight
                    else:
                        set_pixel(ex, ey, r_cyan, g_cyan, b_cyan)

    # 5. Soft Cheek Blush (Y=46-50, X=38-44 and X=84-90)
    for cx in [41, 87]:
        for by in range(46, 51):
            for bx in range(cx - 3, cx + 4):
                set_pixel(bx, by, 0.98, 0.62, 0.55)

    # 6. Delicate Nose Point (Y=46-48, X=63-65)
    set_pixel(64, 47, r_shadow, g_shadow, b_shadow)
    set_pixel(64, 48, r_shadow, g_shadow, b_shadow)

def create_agnes_face_image(name: str = "Agnes_Face_Atlas", width: int = 128, height: int = 128) -> bpy.types.Image:
    """
    Creates a 128x128 high-contrast stylized anime face atlas for 5.0-heads tall Agnes:
    - Warm earthy skin (#E8A880) with strong chiseled jawline contour (#944C2C)
    - Fiery auburn bangs and braided hair fringe (#882810)
    - Fierce determined dark brows (Y=66-70)
    - Emerald forest green irises with fierce anime highlights (Y=52-62)
    - Strong nose bridge shadow & determined closed mouth line (Y=36-40)
    """
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)

    img = bpy.data.images.new(name, width, height, alpha=True)
    
    r_skin, g_skin, b_skin = 0.90, 0.68, 0.52
    r_shadow, g_shadow, b_shadow = 0.60, 0.32, 0.20
    r_hair, g_hair, b_hair = 0.52, 0.16, 0.06
    r_green, g_green, b_green = 0.15, 0.85, 0.30
    r_lip, g_lip, b_lip = 0.75, 0.40, 0.35

    pixels = [1.0] * (width * height * 4)

    def set_pixel(x, y, r, g, b, a=1.0):
        if 0 <= x < width and 0 <= y < height:
            idx = (y * width + x) * 4
            pixels[idx] = r
            pixels[idx + 1] = g
            pixels[idx + 2] = b
            pixels[idx + 3] = a

    # 1. Base skin with strong angular jawline
    for y in range(height):
        for x in range(width):
            if y < 24 or (y < 38 and (x < 38 or x > 90)):
                set_pixel(x, y, r_shadow, g_shadow, b_shadow)
            else:
                set_pixel(x, y, r_skin, g_skin, b_skin)

    # 2. Auburn Hairline & Bangs (Top Y=76-128)
    for y in range(74, height):
        for x in range(width):
            if y >= 90:
                set_pixel(x, y, r_hair, g_hair, b_hair)
            elif y >= 76 and (x < 36 or x > 92 or (y > 84 and 36 <= x <= 92)):
                set_pixel(x, y, r_hair, g_hair, b_hair)

    # 3. Fierce Thick Eyebrows (Y=66-70)
    for x in range(44, 58):
        set_pixel(x, 66 + (x - 44) // 5, 0.25, 0.08, 0.03)
        set_pixel(x, 67 + (x - 44) // 5, 0.25, 0.08, 0.03)
        set_pixel(x, 68 + (x - 44) // 5, 0.25, 0.08, 0.03)
    for x in range(70, 84):
        set_pixel(x, 66 + (84 - x) // 5, 0.25, 0.08, 0.03)
        set_pixel(x, 67 + (84 - x) // 5, 0.25, 0.08, 0.03)
        set_pixel(x, 68 + (84 - x) // 5, 0.25, 0.08, 0.03)

    # 4. Determined Anime Eyes (Y=52-64, X=54 and X=74)
    for center_x in [54, 74]:
        for ey in range(53, 63):
            for ex in range(center_x - 6, center_x + 7):
                if (ex - center_x)**2 / 36 + (ey - 58)**2 / 20 <= 1.0:
                    set_pixel(ex, ey, 1.0, 1.0, 1.0)

        for ex in range(center_x - 7, center_x + 8):
            set_pixel(ex, 62, 0.15, 0.06, 0.02)
            set_pixel(ex, 63, 0.15, 0.06, 0.02)

        for ey in range(54, 62):
            for ex in range(center_x - 4, center_x + 5):
                if (ex - center_x)**2 / 16 + (ey - 58)**2 / 16 <= 1.0:
                    if abs(ex - center_x) <= 1 and abs(ey - 58) <= 1:
                        set_pixel(ex, ey, 0.04, 0.12, 0.04)
                    elif ex == center_x - 1 and ey == 60:
                        set_pixel(ex, ey, 1.0, 1.0, 1.0)
                    else:
                        set_pixel(ex, ey, r_green, g_green, b_green)

    # 5. Nose Bridge Shadow
    set_pixel(64, 46, r_shadow, g_shadow, b_shadow)
    set_pixel(64, 47, r_shadow, g_shadow, b_shadow)

    # 6. Determined Mouth Line (Y=36-39)
    for lx in range(60, 69):
        set_pixel(lx, 37, r_lip, g_lip, b_lip)
        set_pixel(lx, 38, 0.40, 0.18, 0.12)

    img.pixels.foreach_set(pixels)
    img.update()
    return img

def create_gambler_face_image(name: str = "Gambler_Face_Atlas", width: int = 128, height: int = 128) -> bpy.types.Image:
    """
    Creates a 128x128 high-contrast stylized anime face atlas for 5.2-heads tall Gambler:
    - Pale ivory porcelain skin (#FFF0E2) with sharp fedora brim shadow (#8A7060)
    - Smirking rakish eyes, dark pencil brows, thin mustache, and sly confident grin
    """
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)

    img = bpy.data.images.new(name, width, height, alpha=True)
    
    r_skin, g_skin, b_skin = 0.98, 0.92, 0.86
    r_shadow, g_shadow, b_shadow = 0.60, 0.48, 0.42
    r_hair, g_hair, b_hair = 0.04, 0.04, 0.06
    r_amber, g_amber, b_amber = 0.95, 0.70, 0.15

    pixels = [1.0] * (width * height * 4)

    def set_pixel(x, y, r, g, b, a=1.0):
        if 0 <= x < width and 0 <= y < height:
            idx = (y * width + x) * 4
            pixels[idx] = r
            pixels[idx + 1] = g
            pixels[idx + 2] = b
            pixels[idx + 3] = a

    # 1. Base skin with fedora brim shadow across top forehead (Y >= 72)
    for y in range(height):
        for x in range(width):
            if y >= 72 or y < 20 or (y < 32 and (x < 36 or x > 92)):
                set_pixel(x, y, r_shadow, g_shadow, b_shadow)
            else:
                set_pixel(x, y, r_skin, g_skin, b_skin)

    # 2. Sleek Dark Hairline (Top Y=88-128)
    for y in range(88, height):
        for x in range(width):
            set_pixel(x, y, r_hair, g_hair, b_hair)

    # 3. Arched Rakish Eyebrows (Y=64-68)
    for x in range(44, 58):
        set_pixel(x, 65 + (x - 44) // 5, r_hair, g_hair, b_hair)
        set_pixel(x, 66 + (x - 44) // 5, r_hair, g_hair, b_hair)
    for x in range(70, 84):
        set_pixel(x, 67 - (x - 70) // 5, r_hair, g_hair, b_hair)
        set_pixel(x, 68 - (x - 70) // 5, r_hair, g_hair, b_hair)

    # 4. Smirking Anime Eyes (Y=52-62, Amber irises, X=54 and X=74)
    for center_x in [54, 74]:
        for ey in range(53, 62):
            for ex in range(center_x - 6, center_x + 7):
                if (ex - center_x)**2 / 36 + (ey - 57)**2 / 16 <= 1.0:
                    set_pixel(ex, ey, 1.0, 1.0, 1.0)

        for ex in range(center_x - 7, center_x + 8):
            set_pixel(ex, 60, r_hair, g_hair, b_hair)
            set_pixel(ex, 61, r_hair, g_hair, b_hair)

        for ey in range(54, 60):
            for ex in range(center_x - 4, center_x + 5):
                if (ex - center_x)**2 / 16 + (ey - 57)**2 / 16 <= 1.0:
                    if abs(ex - center_x) <= 1 and abs(ey - 57) <= 1:
                        set_pixel(ex, ey, 0.04, 0.04, 0.06)
                    elif ex == center_x - 1 and ey == 58:
                        set_pixel(ex, ey, 1.0, 1.0, 1.0)
                    else:
                        set_pixel(ex, ey, r_amber, g_amber, b_amber)

    # 5. Thin Rakish Pencil Mustache (Y=44-47)
    for x in range(52, 77):
        if abs(x - 64) > 1:
            set_pixel(x, 45, r_hair, g_hair, b_hair)
            set_pixel(x, 46, r_hair, g_hair, b_hair)

    # 6. Sly Asymmetrical Grin (Y=35-39)
    for lx in range(58, 70):
        lip_y = 36 + (lx - 58) // 4
        set_pixel(lx, lip_y, 0.85, 0.35, 0.35)
        set_pixel(lx, lip_y + 1, 0.35, 0.08, 0.08)

    img.pixels.foreach_set(pixels)
    img.update()
    return img

    img.pixels.foreach_set(pixels)
    img.update()
    return img

    img.pixels.foreach_set(pixels)
    img.update()
    return img

    img.pixels.foreach_set(pixels)
    img.update()
    return img

    img.pixels.foreach_set(pixels)
    img.update()
    return img
