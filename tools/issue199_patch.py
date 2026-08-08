from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path, old, new):
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one replacement, found {count}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


def replace_range(path, start_marker, end_marker, replacement):
    text = read(path)
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{path}: missing start marker {start_marker!r}")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{path}: missing end marker {end_marker!r}")
    write(path, text[:start] + replacement + text[end:])


# ---------------------------------------------------------------------------
# main.lua: canonical composition remains 256x240; only the logical render
# surface and host scaling switch profiles. Existing CLI preview/golden tools
# stay canonical unless/until they explicitly opt into a surface profile.
# ---------------------------------------------------------------------------
replace_once(
    "main.lua",
    'local door_transition = require("presentation.door_transition")\n',
    'local door_transition = require("presentation.door_transition")\n'
    'local presentation_surface = require("presentation.surface")\n',
)
replace_once(
    "main.lua",
    '-- Game resolution dimensions\nlocal gameWidth, gameHeight = 256, 240\nlocal canvas\n',
    '-- Canonical authored composition dimensions. The logical render surface\n'
    '-- may be larger; presentation.surface owns that independent profile.\n'
    'local gameWidth, gameHeight = presentation_surface.compositionSize()\n'
    'local requestedSurfaceProfile = nil\n'
    'local canvas\n',
)
replace_once(
    "main.lua",
    '            elseif val == "developer" then\n'
    '                isDeveloperMode = true\n'
    '            elseif val:match("^campaign=") then\n',
    '            elseif val == "developer" then\n'
    '                isDeveloperMode = true\n'
    '            elseif val:match("^surface=") then\n'
    '                requestedSurfaceProfile = val:sub(#"surface=" + 1)\n'
    '            elseif val:match("^campaign=") then\n',
)
replace_once(
    "main.lua",
    '            "test_authored_storage",\n'
    '        }) do\n',
    '            "test_authored_storage",\n'
    '            "test_presentation_surface",\n'
    '        }) do\n',
)
replace_once(
    "main.lua",
    '    love.graphics.setDefaultFilter("nearest", "nearest")\n'
    '    canvas = love.graphics.newCanvas(gameWidth, gameHeight)\n'
    '    love.resize(love.graphics.getWidth(), love.graphics.getHeight())\n',
    '    -- Surface selection is a presentation concern. CLI fixtures above stay\n'
    '    -- on their existing canonical canvases; normal play may choose a wider\n'
    '    -- logical surface without changing authored UI coordinates. A command-\n'
    '    -- line `surface=<id>` overrides the optional system UI setting.\n'
    '    local surfaceProfile = requestedSurfaceProfile\n'
    '        or (config.ui and config.ui.renderSurfaceProfile)\n'
    '        or "classic"\n'
    '    presentation_surface.setProfile(surfaceProfile)\n'
    '    local renderWidth, renderHeight = presentation_surface.renderSize()\n'
    '    love.graphics.setDefaultFilter("nearest", "nearest")\n'
    '    canvas = love.graphics.newCanvas(renderWidth, renderHeight)\n'
    '    love.resize(love.graphics.getWidth(), love.graphics.getHeight())\n',
)
replace_once(
    "main.lua",
    '            local dotX = 32 * 8 - blueDot.cellW - 2   -- right edge of 256px virtual screen\n'
    '            small_battlers.draw(blueDotKey, dotX, 2, blueDot.cellW)\n',
    '            local dotX = presentation_surface.compositionWidth() - blueDot.cellW - 2\n'
    '            local dotY = 2\n'
    '            dotX, dotY = presentation_surface.compositionToRender(dotX, dotY)\n'
    '            small_battlers.draw(blueDotKey, dotX, dotY, blueDot.cellW)\n',
)
replace_once(
    "main.lua",
    'function love.resize(w, h)\n'
    '    scale = math.min(w / gameWidth, h / gameHeight)\n'
    '    scale = math.max(1, math.floor(scale))\n'
    '    scaleX = math.floor((w - gameWidth * scale) / 2)\n'
    '    scaleY = math.floor((h - gameHeight * scale) / 2)\n'
    'end\n',
    'function love.resize(w, h)\n'
    '    scale, scaleX, scaleY = presentation_surface.outputTransform(w, h)\n'
    'end\n',
)


# ---------------------------------------------------------------------------
# Scene compositor: 3D world/backdrop-map and full-surface transitions render
# before/after the composition transform. Static/location illustrations,
# pictures, dock and windows stay authored in canonical composition space.
# ---------------------------------------------------------------------------
replace_once(
    "engine/scene_host.lua",
    'local scene_transition = require("presentation.scene_transition")\n',
    'local scene_transition = require("presentation.scene_transition")\n'
    'local surface = require("presentation.surface")\n',
)
scene_block = r'''local function resolveBackdropFade(sceneData, state)
    local fade = sceneData.backdropFade
    if not fade then return 0 end
    local value = fade
    if type(fade) == "string" then
        local ok, result = pcall(require("engine.formula").eval, fade,
            { v = (state and state.v) or {} })
        value = (ok and type(result) == "number") and result or 0
    end
    if type(value) ~= "number" then return 0 end
    return math.max(0, math.min(1, value))
end

local function drawBackdropFade(sceneData, state, renderSurface)
    local value = resolveBackdropFade(sceneData, state)
    if value <= 0 then return end
    local width, height
    if renderSurface then
        width, height = surface.renderSize()
    else
        width, height = surface.compositionSize()
    end
    love.graphics.setColor(0, 0, 0, value)
    love.graphics.rectangle("fill", 0, 0, width, height)
    love.graphics.setColor(1, 1, 1, 1)
end

-- Render-surface backdrop: only real 3D world is allowed to expand. Authored
-- illustrations remain composition-space below, even when they represent a
-- location reached from the map.
local function drawRenderBackdrop(sceneData, ctx, state)
    if sceneData.backdrop ~= "map" then return false end
    local session = ctx.session
    if not (session and session.currentMapData and session.mapGrid) then return false end
    if session.locationArt then return false end
    require("presentation.viewport_3d").draw(session)
    drawBackdropFade(sceneData, state, true)
    return true
end

local function drawCompositionBackdrop(sceneData, ctx, state)
    if sceneData.backdropImage then
        require("presentation.static_backdrop").draw(sceneData.backdropImage)
    end
    if sceneData.backdrop ~= "map" then return false end
    local session = ctx.session
    if not (session and session.currentMapData and session.mapGrid and session.locationArt) then
        return false
    end
    require("presentation.location_renderer").draw(session.locationArt)
    drawBackdropFade(sceneData, state, false)
    return true
end

-- Every scene declares how it draws (scenes.json `draw`):
--   "windows" -- rendered entirely from its windows array
--   "world"   -- a world view (named by `world`) with windows layered on top
-- The old "no flag = fall back to legacy Lua drawing" rule was purged
-- 24.07.2026 once the last legacy-drawn scene (town) was deleted and map
-- became an explicit world scene, so there is no host-side fallback left:
-- a scene with an unrecognized draw mode is a data bug and says so.
function scene_host.draw(ctx)
    if #sceneStack == 0 then return false end
    local state = sceneStack[#sceneStack]
    local sceneData = getSceneData(ctx, state.id)
    if not sceneData then
        scene_transition.draw()
        return false
    end

    local renderBackdropDrawn = false
    if sceneData.draw == "world" then
        require("presentation.world_renderer").draw(sceneData.world, ctx)
        renderBackdropDrawn = true
    elseif sceneData.draw ~= "windows" then
        error("scene '" .. tostring(state.id) .. "' has no draw mode "
            .. "(expected \"windows\" or \"world\", got '"
            .. tostring(sceneData.draw) .. "')", 0)
    else
        renderBackdropDrawn = drawRenderBackdrop(sceneData, ctx, state)
    end

    -- A subtractive event fade dims the backdrop but not dock/windows. When
    -- that backdrop is expanded world it must cover the full render surface;
    -- composition-only art gets the same established effect inside the frame.
    if renderBackdropDrawn then
        require("presentation.subtractive_transition").draw()
    end

    surface.beginComposition()
    drawCompositionBackdrop(sceneData, ctx, state)
    require("presentation.image_picture_renderer").draw("backdrop")
    require("presentation.string_picture_renderer").draw("backdrop")
    if not renderBackdropDrawn then
        require("presentation.subtractive_transition").draw()
    end
    local window_renderer = require("presentation.window_renderer")
    -- The persistent dock owns the bottom windowskin shells. Scene windows draw
    -- above them, so battle commands can occupy a dock shell without the empty
    -- shell panel covering their controls.
    require("presentation.dock").draw(state, sceneData, ctx)
    window_renderer.draw(state, sceneData, ctx)
    surface.endComposition()

    -- Scene enter/exit fades are genuinely full-surface transitions: they cover
    -- peripheral world and the canonical composition together.
    scene_transition.draw()
    return true
end

'''
replace_range(
    "engine/scene_host.lua",
    "local function drawBackdropFade(sceneData, state)\n",
    "function scene_host.keypressed(key, ctx)\n",
    scene_block,
)


# ---------------------------------------------------------------------------
# Full-surface effects distinguish the render surface from modal/composition
# dimming. Classic is byte-for-byte geometry-equivalent (256x240, origin 0).
# ---------------------------------------------------------------------------
replace_once(
    "presentation/subtractive_fade.lua",
    'local util = require("presentation.util")\n',
    'local util = require("presentation.util")\nlocal surface = require("presentation.surface")\n',
)
replace_once(
    "presentation/subtractive_fade.lua",
    '    love.graphics.rectangle("fill", 0, 0,\n'
    '        ui.toPx(ui.screenWidthTiles or 32),\n'
    '        ui.toPx(ui.screenHeightTiles or 30))\n',
    '    local width, height\n'
    '    if marksModal == false then\n'
    '        width, height = surface.renderSize()\n'
    '    else\n'
    '        width, height = surface.compositionSize()\n'
    '    end\n'
    '    love.graphics.rectangle("fill", 0, 0, width, height)\n',
)
replace_once(
    "presentation/scene_transition.lua",
    'local util = require("presentation.util")\n',
    'local util = require("presentation.util")\nlocal surface = require("presentation.surface")\n',
)
replace_once(
    "presentation/scene_transition.lua",
    '        local screenW = ui.toPx(ui.screenWidthTiles or 32)\n'
    '        local screenH = ui.toPx(ui.screenHeightTiles or 30)\n',
    '        local screenW, screenH = surface.renderSize()\n',
)


# ---------------------------------------------------------------------------
# World projection: X center and horizon are canonical-frame anchors translated
# into render coordinates. A centred Wide target therefore adds peripheral
# world without changing the canonical crop's projection scale or framing.
# ---------------------------------------------------------------------------
replace_once(
    "presentation/retro_mesh_shader.lua",
    '    uniform float targetHeight;\n'
    '    uniform float viewportCenterY;\n',
    '    uniform float targetHeight;\n'
    '    uniform float viewportCenterX;\n'
    '    uniform float viewportCenterY;\n',
)
replace_once(
    "presentation/retro_mesh_shader.lua",
    '        float viewportTop = (2.0 * viewportCenterY / targetHeight) - 1.0;\n'
    '        float ndcX = horizontal / (fovHalfX * safeDepth) * (baseViewportWidth / targetWidth);\n',
    '        float viewportCenter = (2.0 * viewportCenterX / targetWidth) - 1.0;\n'
    '        float viewportTop = (2.0 * viewportCenterY / targetHeight) - 1.0;\n'
    '        float ndcX = viewportCenter\n'
    '            + horizontal / (fovHalfX * safeDepth) * (baseViewportWidth / targetWidth);\n',
)
replace_once(
    "presentation/viewport_3d.lua",
    'local retroMeshShader = require("presentation.retro_mesh_shader")\n',
    'local retroMeshShader = require("presentation.retro_mesh_shader")\n'
    'local surface = require("presentation.surface")\n',
)
replace_once(
    "presentation/viewport_3d.lua",
    '    local targetWidth, targetHeight = 256, 240\n'
    '    local targetCanvas = love.graphics.getCanvas()\n'
    '    if targetCanvas then\n'
    '        targetWidth, targetHeight = targetCanvas:getDimensions()\n'
    '    end\n'
    '    local squareAuthoringCamera = session.roomBakeSquareCamera == true\n'
    '    local baseViewportWidth = squareAuthoringCamera and targetWidth or 256\n'
    '    local baseViewportHeight = squareAuthoringCamera and targetHeight or 144\n'
    '    local viewportWidth = targetWidth\n'
    '    local viewportHeight = targetHeight\n'
    '    local viewportCenterY = squareAuthoringCamera and targetHeight * 0.5 or 70\n',
    '    local targetWidth, targetHeight = surface.renderSize()\n'
    '    local targetCanvas = love.graphics.getCanvas()\n'
    '    if targetCanvas then\n'
    '        targetWidth, targetHeight = targetCanvas:getDimensions()\n'
    '    end\n'
    '    local squareAuthoringCamera = session.roomBakeSquareCamera == true\n'
    '    local compositionWidth = surface.compositionWidth()\n'
    '    local compositionHeight = surface.compositionHeight()\n'
    '    local canonicalCenterX, canonicalHorizonY = surface.compositionToRender(\n'
    '        compositionWidth * 0.5, 70)\n'
    '    local baseViewportWidth = squareAuthoringCamera and targetWidth or compositionWidth\n'
    '    local baseViewportHeight = squareAuthoringCamera and targetHeight or 144\n'
    '    local viewportWidth = targetWidth\n'
    '    local viewportHeight = targetHeight\n'
    '    local viewportCenterX = squareAuthoringCamera and targetWidth * 0.5 or canonicalCenterX\n'
    '    local viewportCenterY = squareAuthoringCamera and targetHeight * 0.5 or canonicalHorizonY\n',
)
replace_once(
    "presentation/viewport_3d.lua",
    '    shader:send("targetWidth", targetWidth)\n'
    '    shader:send("targetHeight", targetHeight)\n'
    '    shader:send("viewportCenterY", viewportCenterY)\n',
    '    shader:send("targetWidth", targetWidth)\n'
    '    shader:send("targetHeight", targetHeight)\n'
    '    shader:send("viewportCenterX", viewportCenterX)\n'
    '    shader:send("viewportCenterY", viewportCenterY)\n',
)
replace_once(
    "presentation/viewport_3d.lua",
    '            viewportCenterY = viewportCenterY,\n'
    '            targetHeight = targetHeight,\n'
    '            viewportWidth = viewportWidth, viewportHeight = viewportHeight,\n',
    '            viewportCenterX = viewportCenterX, viewportCenterY = viewportCenterY,\n'
    '            targetWidth = targetWidth, targetHeight = targetHeight,\n'
    '            compositionWidth = compositionWidth, compositionHeight = compositionHeight,\n'
    '            viewportWidth = viewportWidth, viewportHeight = viewportHeight,\n',
)


# ---------------------------------------------------------------------------
# Native Effekseer draws bypass LOVE transforms. Give screen effects an
# orthographic region matching the canonical frame inside the render target,
# and make world-effect X framing expand rather than stretch in Wide.
# ---------------------------------------------------------------------------
replace_once(
    "presentation/effekseer.lua",
    'local effekseer = {}\n',
    'local effekseer = {}\nlocal surface = require("presentation.surface")\n',
)
replace_once(
    "presentation/effekseer.lua",
    'local GAME_W, GAME_H = 256, 240\n'
    'local screenW, screenH = GAME_W, GAME_H\n',
    'local GAME_W, GAME_H = 256, 240\n'
    'local screenW, screenH = GAME_W, GAME_H\n'
    'local screenOriginX, screenOriginY = 0, 0\n',
)
ortho = r'''local function orthoScreen(w, h, zn, zf, originX, originY)
    originX, originY = originX or 0, originY or 0
    local m = {
        2 / w, 0, 0, 0,
        0, 2 / h, 0, 0,
        0, 0, 1 / (zn - zf), 0,
        0, 0, zn / (zn - zf), 1,
    }
    m[13] = (2 * originX / w) - 1
    m[14] = (2 * originY / h) - 1
    return m
end

'''
replace_range(
    "presentation/effekseer.lua",
    "local function orthoScreen(w, h, zn, zf)\n",
    "-- Row-vector matrices matching Effekseer's Matrix44 layout.",
    ortho,
)
world_camera = r'''local function worldCameraMatrices(camera)
    local rx, ry = camera.rightX, camera.rightY
    local fx, fy = camera.dirX, camera.dirY
    local cx, cy, cz = camera.x, camera.y, camera.z
    local view = {
        rx, 0, -fx, 0,
        0,  1, 0,   0,
        ry, 0, -fy, 0,
        -(cx * rx + cy * ry), -cz, cx * fx + cy * fy, 1,
    }
    local zn, zf = camera.nearPlane or 0.05, camera.farPlane or 32
    local targetWidth = camera.targetWidth or camera.viewportWidth or GAME_W
    local targetHeight = camera.targetHeight or camera.viewportHeight or GAME_H
    local centerX = camera.viewportCenterX or targetWidth * 0.5
    local centerY = camera.viewportCenterY or targetHeight * 0.5
    local offsetX = (2 * centerX / targetWidth) - 1
    local offsetY = (2 * centerY / targetHeight) - 1
    -- Preserve the existing Classic effect projection exactly, then scale its
    -- NDC footprint by canonical/target size when the render surface expands.
    local scaleX = (camera.compositionWidth or GAME_W) / targetWidth
    local scaleY = (camera.compositionHeight or GAME_H) / targetHeight
    local projection = {
        scaleX / camera.fovHalfX, 0, 0, 0,
        0, -scaleY / camera.fovHalfY, 0, 0,
        -offsetX, -offsetY, zf / (zn - zf), -1,
        0, 0, zn * zf / (zn - zf), 0,
    }
    return view, projection
end

'''
replace_range(
    "presentation/effekseer.lua",
    "local function worldCameraMatrices(camera)\n",
    "local function toBuf(buf, m)\n",
    world_camera,
)
replace_once(
    "presentation/effekseer.lua",
    '    toBuf(viewBuf, IDENTITY)\n'
    '    toBuf(projBuf, orthoScreen(GAME_W, GAME_H, -512, 512))\n',
    '    local renderW, renderH = surface.renderSize()\n'
    '    screenOriginX, screenOriginY = surface.compositionOrigin()\n'
    '    screenW, screenH = renderW, renderH\n'
    '    toBuf(viewBuf, IDENTITY)\n'
    '    toBuf(projBuf, orthoScreen(screenW, screenH, -512, 512,\n'
    '        screenOriginX, screenOriginY))\n',
)
replace_once(
    "presentation/effekseer.lua",
    'function effekseer.setViewport(w, h)\n'
    '    if not effekseer.available() then return end\n'
    '    screenW, screenH = w, h\n'
    '    toBuf(projBuf, orthoScreen(w, h, -512, 512))\n'
    'end\n',
    'function effekseer.setViewport(w, h)\n'
    '    if not effekseer.available() then return end\n'
    '    screenW, screenH = w, h\n'
    '    screenOriginX, screenOriginY = 0, 0\n'
    '    toBuf(projBuf, orthoScreen(w, h, -512, 512, 0, 0))\n'
    'end\n',
)
replace_once(
    "presentation/effekseer.lua",
    '    toBuf(viewBuf, IDENTITY)\n'
    '    toBuf(projBuf, orthoScreen(screenW, screenH, -512, 512))\n'
    '    skipNextScreenDraw = true\n',
    '    toBuf(viewBuf, IDENTITY)\n'
    '    toBuf(projBuf, orthoScreen(screenW, screenH, -512, 512,\n'
    '        screenOriginX, screenOriginY))\n'
    '    skipNextScreenDraw = true\n',
)


# Temporary runner removes itself and its workflow in the implementation
# commit, leaving only production/test changes in the branch tree.
Path("tools/issue199_patch.py").unlink()
Path(".github/workflows/issue199-patch.yml").unlink()
print("issue 199 patch applied")
