from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path, old, new):
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one replacement, found {count}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


# World shader pixel phase belongs to the canonical composition, not to the
# physical render surface. Otherwise Wide's 85px origin changes both ordered
# dither and vertex-snap phase inside the supposedly identical center crop.
replace_once(
    "presentation/retro_mesh_shader.lua",
    '    uniform float targetWidth;\n'
    '    uniform float targetHeight;\n'
    '    uniform float viewportCenterX;\n',
    '    uniform float targetWidth;\n'
    '    uniform float targetHeight;\n'
    '    uniform vec2 compositionOrigin;\n'
    '    uniform float viewportCenterX;\n',
)
replace_once(
    "presentation/retro_mesh_shader.lua",
    '            pixelX = floor(pixelX / vertexSnapPixels + 0.5) * vertexSnapPixels;\n'
    '            pixelY = floor(pixelY / vertexSnapPixels + 0.5) * vertexSnapPixels;\n',
    '            pixelX = floor((pixelX - compositionOrigin.x) / vertexSnapPixels + 0.5)\n'
    '                * vertexSnapPixels + compositionOrigin.x;\n'
    '            pixelY = floor((pixelY - compositionOrigin.y) / vertexSnapPixels + 0.5)\n'
    '                * vertexSnapPixels + compositionOrigin.y;\n',
)
replace_once(
    "presentation/retro_mesh_shader.lua",
    '    uniform vec3 fogColor;\n'
    '    uniform float ditherLevels;\n'
    '    uniform float roomBakePass;\n',
    '    uniform vec3 fogColor;\n'
    '    uniform float ditherLevels;\n'
    '    uniform vec2 compositionOrigin;\n'
    '    uniform float roomBakePass;\n',
)
# Only the world-shader occurrence is changed: item_model_view renders into its
# own local offscreen canvas and therefore intentionally uses local screen coords.
replace_once(
    "presentation/retro_mesh_shader.lua",
    '            float threshold = orderedDither(screen_coords) - 0.5;\n'
    '            fogged = floor(clamp(fogged + threshold / ditherLevels, 0.0, 1.0) * ditherLevels + 0.5) / ditherLevels;\n',
    '            float threshold = orderedDither(screen_coords - compositionOrigin) - 0.5;\n'
    '            fogged = floor(clamp(fogged + threshold / ditherLevels, 0.0, 1.0) * ditherLevels + 0.5) / ditherLevels;\n',
)

# Panorama UVs are screen-window samples. Keep their phase fixed to canonical
# composition coordinates as the surface expands, while peripheral pixels simply
# reveal samples outside the old crop.
replace_once(
    "presentation/viewport_3d.lua",
    '                local scrollOx = (t * (layer.scrollX or 0) * iw) % iw\n'
    '                local scrollOy = (t * (layer.scrollY or 0) * ih) % ih\n'
    '                if not panoramaQuad then panoramaQuad = love.graphics.newQuad(0, 0, 1, 1, 1, 1) end\n'
    '                panoramaQuad:setViewport(scrollOx + x, scrollOy + y, w, h, iw, ih)\n',
    '                local scrollOx = (t * (layer.scrollX or 0) * iw) % iw\n'
    '                local scrollOy = (t * (layer.scrollY or 0) * ih) % ih\n'
    '                local originX, originY = surface.compositionOrigin()\n'
    '                if not panoramaQuad then panoramaQuad = love.graphics.newQuad(0, 0, 1, 1, 1, 1) end\n'
    '                panoramaQuad:setViewport(scrollOx + x - originX, scrollOy + y - originY, w, h, iw, ih)\n',
)
replace_once(
    "presentation/viewport_3d.lua",
    '    -- The world now fills the whole 256x240 canvas rather than stopping at the\n'
    '    -- old 256x144 playfield (31.07.2026). The windowskin shells are\n',
    '    -- The world fills the current logical render surface rather than stopping\n'
    '    -- at the old 256x144 playfield (31.07.2026). The windowskin shells are\n',
)
replace_once(
    "presentation/viewport_3d.lua",
    '    shader:send("targetWidth", targetWidth)\n'
    '    shader:send("targetHeight", targetHeight)\n'
    '    shader:send("viewportCenterX", viewportCenterX)\n',
    '    shader:send("targetWidth", targetWidth)\n'
    '    shader:send("targetHeight", targetHeight)\n'
    '    shader:send("compositionOrigin", { surface.compositionOrigin() })\n'
    '    shader:send("viewportCenterX", viewportCenterX)\n',
)

# Leave no workflow/tool scaffolding in the production branch tree.
Path("tools/issue199_fixup.py").unlink()
Path(".github/workflows/issue199-fixup.yml").unlink()
print("issue 199 visual invariant fixups applied")
