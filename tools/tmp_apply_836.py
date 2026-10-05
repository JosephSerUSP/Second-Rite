from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
viewport_path = ROOT / "runtime/presentation/viewport_3d.lua"
system_path = ROOT / "projects/hichaukitoden-game/data/system.json"

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)

s = viewport_path.read_text(encoding="utf-8")

s = replace_once(
    s,
    '''local function drawWorldSpace(session, authoredCamera, inspection)
    if not skyQuad then viewport_3d.init() end''',
    '''-- Renderer-only pass ownership for selective presentation. This is not a
-- gameplay taxonomy: structural geometry defaults to the environment pass,
-- ordinary billboards default to the live pass, and producers may attach an
-- explicit presentationPass when they have stronger presentation intent.
function viewport_3d.surfacePresentationPass(surfaceEntry)
    if type(surfaceEntry) == "table" and surfaceEntry.presentationPass then
        return surfaceEntry.presentationPass
    end
    if type(surfaceEntry) == "table" and surfaceEntry.category == "billboard" then
        return "live"
    end
    return "environment"
end

local function drawWorldSpace(session, authoredCamera, inspection, passOptions)
    passOptions = passOptions or {}
    local rasterScale = math.max(1, tonumber(passOptions.rasterScale) or 1)
    local worldPass = passOptions.presentationPass or "all"
    if not skyQuad then viewport_3d.init() end''',
    "drawWorldSpace signature")

s = replace_once(
    s,
    '''    local squareAuthoringCamera = session.roomBakeSquareCamera == true
    local compositionWidth = surface.compositionWidth()
    local compositionHeight = surface.compositionHeight()
    local canonicalCenterX, canonicalHorizonY = surface.compositionToRender(
        compositionWidth * 0.5, 70)''',
    '''    -- A supersampled render target is a denser raster of the SAME logical
    -- view, not a wider/taller camera. Resolve the WorldCamera in native logical
    -- pixels, then scale the pixel-valued projection fields below.
    local projectionTargetWidth = targetWidth / rasterScale
    local projectionTargetHeight = targetHeight / rasterScale
    local squareAuthoringCamera = session.roomBakeSquareCamera == true
    local compositionWidth = surface.compositionWidth()
    local compositionHeight = surface.compositionHeight()
    local canonicalCenterX, canonicalHorizonY = surface.compositionToRender(
        compositionWidth * 0.5, 70)''',
    "projection target setup")

s = replace_once(
    s,
    '''            targetWidth = targetWidth,
            targetHeight = targetHeight,''',
    '''            targetWidth = projectionTargetWidth,
            targetHeight = projectionTargetHeight,''',
    "projection frame native target")

s = replace_once(
    s,
    '''    local cameraX, cameraY, cameraZ = camera.x, camera.y, camera.z
    local cAngle = camera.angle''',
    '''    if rasterScale ~= 1 then
        camera.baseViewportWidth = camera.baseViewportWidth * rasterScale
        camera.baseViewportHeight = camera.baseViewportHeight * rasterScale
        camera.viewportCenterX = camera.viewportCenterX * rasterScale
        camera.viewportCenterY = camera.viewportCenterY * rasterScale
        camera.projectionWindowOffsetX = (camera.projectionWindowOffsetX or 0) * rasterScale
        camera.projectionWindowOffsetY = (camera.projectionWindowOffsetY or 0) * rasterScale
    end
    local cameraX, cameraY, cameraZ = camera.x, camera.y, camera.z
    local cAngle = camera.angle''',
    "scale camera raster fields")

s = replace_once(
    s,
    '''    local vertexSnapPixels = math.max(0, tonumber(psxCfg.vertexSnapPixels) or 0)''',
    '''    local vertexSnapPixels = math.max(0, tonumber(psxCfg.vertexSnapPixels) or 0) * rasterScale''',
    "scale vertex snapping")

s = replace_once(
    s,
    '''    local fogBands = math.max(0, math.floor(tonumber(fog.psxBands) or tonumber(psxCfg.fogBands) or 0))
    local ditherLevels = math.max(0, tonumber(psxCfg.ditherLevels) or 0)''',
    '''    local fogBands = math.max(0, math.floor(tonumber(fog.psxBands) or tonumber(psxCfg.fogBands) or 0))
    local configuredDitherLevels = math.max(0, tonumber(psxCfg.ditherLevels) or 0)
    local ditherLevels = passOptions.ditherLevels ~= nil
        and math.max(0, tonumber(passOptions.ditherLevels) or 0)
        or configuredDitherLevels''',
    "dither override")

s = replace_once(
    s,
    '''            grp = { texture = texture, vertices = {}, category = category }''',
    '''            grp = {
                texture = texture,
                vertices = {},
                category = category,
                presentationPass = category == "billboard" and "live" or "environment",
            }''',
    "dynamic group pass")

s = replace_once(
    s,
    '''    local function queuePlacedModels(placedGroups)''',
    '''    local function queuePlacedModels(placedGroups, presentationPass)''',
    "placed model queue signature")

s = replace_once(
    s,
    '''                drawable.depth = (placed.centerX - cameraX) * dirX
                    + (placed.centerY - cameraY) * dirY
                drawable.sequence = #surfaces + 1
                surfaces[#surfaces + 1] = drawable''',
    '''                drawable.depth = (placed.centerX - cameraX) * dirX
                    + (placed.centerY - cameraY) * dirY
                drawable.sequence = #surfaces + 1
                drawable.presentationPass = presentationPass
                    or drawable.presentationPass or "environment"
                surfaces[#surfaces + 1] = drawable''',
    "placed model pass tag")

s = replace_once(
    s,
    '''                    queuePlacedModels(ensurePlacedModel(modelSpec, cacheKey, worldX, worldY, "x", nil, nil, worldZ))''',
    '''                    queuePlacedModels(
                        ensurePlacedModel(modelSpec, cacheKey, worldX, worldY, "x", nil, nil, worldZ),
                        "live")''',
    "event model live pass")

s = replace_once(
    s,
    '''            table.insert(surfaces, {
                mesh = batch.mesh,
                glow = glowForTexture[batch.texture],
                depth = depthTotal / #batch.selected,
                sequence = #surfaces + 1,
            })''',
    '''            table.insert(surfaces, {
                mesh = batch.mesh,
                glow = glowForTexture[batch.texture],
                depth = depthTotal / #batch.selected,
                sequence = #surfaces + 1,
                presentationPass = "environment",
            })''',
    "structural batch pass")

s = replace_once(
    s,
    '''    love.graphics.push("all")
    love.graphics.intersectScissor(0, 0, viewportWidth, viewportHeight)
    drawFogBackground(fog, viewportWidth, viewportHeight)
    if mapData and mapData.ceilingStyle == "sky" then
        drawSkyBackdrop(atlas, viewportWidth, viewportHeight, cAngle)
    end''',
    '''    love.graphics.push("all")
    love.graphics.intersectScissor(0, 0, viewportWidth, viewportHeight)
    if passOptions.drawBackground ~= false then
        if rasterScale ~= 1 then
            love.graphics.push()
            love.graphics.scale(rasterScale, rasterScale)
            drawFogBackground(fog, viewportWidth / rasterScale, viewportHeight / rasterScale)
            if mapData and mapData.ceilingStyle == "sky" then
                drawSkyBackdrop(atlas, viewportWidth / rasterScale, viewportHeight / rasterScale, cAngle)
            end
            love.graphics.pop()
        else
            drawFogBackground(fog, viewportWidth, viewportHeight)
            if mapData and mapData.ceilingStyle == "sky" then
                drawSkyBackdrop(atlas, viewportWidth, viewportHeight, cAngle)
            end
        end
    end''',
    "background scaling/pass")

s = replace_once(
    s,
    '''    shader:send("compositionOrigin", { surface.compositionOrigin() })''',
    '''    local compositionOriginX, compositionOriginY = surface.compositionOrigin()
    shader:send("compositionOrigin", {
        compositionOriginX * rasterScale,
        compositionOriginY * rasterScale,
    })''',
    "composition origin scale")

# Wrap the existing surface draw loop rather than duplicating its substantial logic.
loop_anchor = '    local modelDrawStarted = love.timer.getTime()\n'
loop_start = s.index('    for _, g in ipairs(surfaces) do\n', s.index(loop_anchor))
loop_end = s.index('    profile.modelDrawLoopMs', loop_start)
loop = s[loop_start:loop_end]
first = '    for _, g in ipairs(surfaces) do\n'
if not loop.startswith(first) or not loop.endswith('    end\n'):
    raise SystemExit("surface draw loop shape changed")
body = loop[len(first):-len('    end\n')]
wrapped = (
    first
    + '        if worldPass == "all" or viewport_3d.surfacePresentationPass(g) == worldPass then\n'
    + textwrap.indent(body, '    ')
    + '        end\n'
    + '    end\n'
)
s = s[:loop_start] + wrapped + s[loop_end:]

s = replace_once(
    s,
    '''    if #(structure.worldEffectHandles or {}) > 0 or structure.ambientEffectHandle then''',
    '''    if passOptions.drawWorldEffects ~= false
            and (#(structure.worldEffectHandles or {}) > 0 or structure.ambientEffectHandle) then''',
    "world effects pass")

s = replace_once(
    s,
    '''            compositionWidth = compositionWidth, compositionHeight = compositionHeight,''',
    '''            compositionWidth = compositionWidth * rasterScale,
            compositionHeight = compositionHeight * rasterScale,''',
    "effekseer composition scale")

s = replace_once(
    s,
    '''    love.graphics.clear(false, false, 1)''',
    '''    if not passOptions.preserveDepth then
        love.graphics.clear(false, false, 1)
    end''',
    "depth preservation")

s = replace_once(
    s,
    '''    require("presentation.door_transition").draw()
end

function viewport_3d.draw(session, authoredCamera, inspection)
    -- `authoredCamera` is the current Scene's presentation default, never Map state.
    return drawWorldSpace(session, authoredCamera, inspection)
end''',
    '''    if passOptions.drawPost ~= false then
        require("presentation.door_transition").draw()
    end
end

function viewport_3d.draw(session, authoredCamera, inspection)
    -- `authoredCamera` is the current Scene's presentation default, never Map state.
    -- Selective environment AA is a presentation composition around the existing
    -- world draw; the ordinary path remains byte-for-byte reachable at scale 1.
    return require("presentation.world_pass_compositor").draw(
        session, authoredCamera, inspection, drawWorldSpace)
end''',
    "public compositor seam")

viewport_path.write_text(s, encoding="utf-8")

system = system_path.read_text(encoding="utf-8")
system = replace_once(
    system,
    '''      "fogBands": 8,
      "ditherLevels": 31''',
    '''      "fogBands": 8,
      "ditherLevels": 31,
      "environmentSupersample": 3''',
    "game environment supersample setting")
system_path.write_text(system, encoding="utf-8")

compositor = r'''-- Full-cadence selective world AA for #836.
--
-- The environment remains live 3D. Only its colour raster is supersampled and
-- box-resolved. A separate native-resolution environment pass reconstructs
-- pristine depth, then live actors/events render at native resolution against
-- that depth. This keeps architectural edges smooth while the pass-ownership
-- boundary stays deliberately hard.
local surface = require("presentation.surface")

local compositor = {}
local targets = nil
local boxShader = nil

local function psxRendering(session)
    return session and session.loader and session.loader.system
        and session.loader.system.dungeon
        and session.loader.system.dungeon.psxRendering or {}
end

function compositor.resolveScale(session)
    local value = tonumber(psxRendering(session).environmentSupersample) or 1
    value = math.floor(value + 0.5)
    if value <= 1 then return 1 end
    return math.max(2, math.min(4, value))
end

function compositor.isEligible(session)
    if not session then return false end
    if session.roomBakePass or session.roomBakeSquareCamera then return false end
    if session.profile3dVariant and session.profile3dVariant ~= "current" then return false end
    local environment = session.townTraversal and session.townTraversal.environment
    if environment and environment.preRendered then return false end
    return compositor.resolveScale(session) > 1
end

local function ensureBoxShader()
    if boxShader then return boxShader end
    boxShader = love.graphics.newShader([[
        uniform vec2 sourceTexel;
        uniform float taps;
        vec4 effect(vec4 c, Image t, vec2 uv, vec2 sc) {
            vec4 sum = vec4(0.0);
            for (int y = 0; y < 4; y++) {
                if (float(y) >= taps) break;
                for (int x = 0; x < 4; x++) {
                    if (float(x) >= taps) break;
                    sum += Texel(t, uv + vec2(
                        (float(x) + 0.5) * sourceTexel.x,
                        (float(y) + 0.5) * sourceTexel.y));
                }
            }
            return (sum / (taps * taps)) * c;
        }
    ]])
    return boxShader
end

local function newDepth(width, height)
    return surface.newRasterCanvas(width, height, {
        format = "depth24stencil8",
    })
end

local function ensureTargets(width, height, scale)
    if targets and targets.width == width and targets.height == height
            and targets.scale == scale then
        return targets
    end
    local ssWidth, ssHeight = width * scale, height * scale
    local envColorSS = surface.newRasterCanvas(ssWidth, ssHeight)
    envColorSS:setFilter("nearest", "nearest")
    targets = {
        width = width,
        height = height,
        scale = scale,
        envColorSS = envColorSS,
        envDepthSS = newDepth(ssWidth, ssHeight),
        envDepthNative = newDepth(width, height),
    }
    return targets
end

local function restoreState()
    love.graphics.setShader()
    love.graphics.setDepthMode()
    love.graphics.setColorMask(true, true, true, true)
    love.graphics.setBlendMode("alpha")
    love.graphics.setColor(1, 1, 1, 1)
end

function compositor.draw(session, authoredCamera, inspection, drawWorld)
    if not compositor.isEligible(session) then
        return drawWorld(session, authoredCamera, inspection, nil)
    end

    local activeColor = love.graphics.getCanvas()
    if not activeColor then
        return drawWorld(session, authoredCamera, inspection, nil)
    end

    local width, height = activeColor:getDimensions()
    local scale = compositor.resolveScale(session)
    local t = ensureTargets(width, height, scale)
    local ok, result = xpcall(function()
        love.graphics.push("all")
        love.graphics.origin()
        love.graphics.setScissor()

        -- 1. High-resolution environment colour. Dither is intentionally off:
        -- screen-anchored PSX dither averaged through a 3x box filter is neither
        -- the native pattern nor the "expensive prerender" visual language.
        love.graphics.setCanvas({
            t.envColorSS,
            depthstencil = t.envDepthSS,
        })
        love.graphics.clear(0, 0, 0, 1, 0, 1)
        drawWorld(session, authoredCamera, inspection, {
            presentationPass = "environment",
            rasterScale = scale,
            ditherLevels = 0,
            drawBackground = true,
            drawWorldEffects = true,
            drawPost = false,
            preserveDepth = false,
        })

        -- 2. Resolve colour into the real native frame. LÖVE's ordinary linear
        -- minification point-samples this particular integer reduction, so use
        -- the explicit box resolve already proven by tools/spikes/841.
        love.graphics.setCanvas({
            activeColor,
            depthstencil = t.envDepthNative,
        })
        love.graphics.clear(false, 0, 1)
        local shader = ensureBoxShader()
        shader:send("sourceTexel", {
            1 / t.envColorSS:getWidth(),
            1 / t.envColorSS:getHeight(),
        })
        shader:send("taps", scale)
        love.graphics.setShader(shader)
        love.graphics.setBlendMode("replace", "premultiplied")
        love.graphics.setColor(1, 1, 1, 1)
        love.graphics.draw(t.envColorSS, 0, 0, 0, 1 / scale, 1 / scale)
        love.graphics.setShader()
        love.graphics.setBlendMode("alpha")

        -- 3. Rebuild the environment's spatial authority at native resolution,
        -- colour-disabled. This is the hard, un-antialiased occlusion mask.
        love.graphics.setColorMask(false, false, false, false)
        drawWorld(session, authoredCamera, inspection, {
            presentationPass = "environment",
            rasterScale = 1,
            drawBackground = false,
            drawWorldEffects = false,
            drawPost = false,
            preserveDepth = true,
        })
        love.graphics.setColorMask(true, true, true, true)

        -- 4. Native live layer. It uses the same PSX mesh shader/settings as
        -- before, but depth-tests against the environment reconstructed above.
        drawWorld(session, authoredCamera, inspection, {
            presentationPass = "live",
            rasterScale = 1,
            drawBackground = false,
            drawWorldEffects = false,
            drawPost = true,
            preserveDepth = false,
        })

        love.graphics.pop()
        restoreState()
        -- Downstream map HUD / stencil consumers still expect an attached
        -- depth-stencil buffer. Keep our native authoritative attachment bound.
        love.graphics.setCanvas({
            activeColor,
            depthstencil = t.envDepthNative,
        })
    end, debug.traceback)

    if not ok then
        restoreState()
        love.graphics.setCanvas(activeColor)
        error(result, 0)
    end
    return result
end

return compositor
'''
(ROOT / "runtime/presentation/world_pass_compositor.lua").write_text(compositor, encoding="utf-8")

test = r'''local compositor = require("presentation.world_pass_compositor")
local viewport = require("presentation.viewport_3d")

local passed, failed = 0, 0
local function check(condition, message)
    if condition then
        passed = passed + 1
    else
        failed = failed + 1
        io.stderr:write("FAIL: " .. message .. "\n")
    end
end

local function sessionWithScale(value)
    return {
        loader = {
            system = {
                dungeon = {
                    psxRendering = {
                        environmentSupersample = value,
                    },
                },
            },
        },
    }
end

check(compositor.resolveScale(sessionWithScale(nil)) == 1,
    "selective environment AA defaults off")
check(compositor.resolveScale(sessionWithScale(3)) == 3,
    "3x environment supersampling resolves")
check(compositor.resolveScale(sessionWithScale(9)) == 4,
    "environment supersampling is bounded to 4x")
check(compositor.resolveScale(sessionWithScale(1)) == 1,
    "1x uses the ordinary world path")

local eligible = sessionWithScale(3)
check(compositor.isEligible(eligible),
    "ordinary live-3D session accepts selective AA")
eligible.roomBakePass = "depth"
check(not compositor.isEligible(eligible),
    "room bake diagnostics bypass selective AA")

local prerendered = sessionWithScale(3)
prerendered.townTraversal = { environment = { preRendered = { mode = "layered_2d" } } }
check(not compositor.isEligible(prerendered),
    "literal layered prerender stays on its existing renderer")

check(viewport.surfacePresentationPass({ category = "billboard" }) == "live",
    "ordinary billboards default to the live pass")
check(viewport.surfacePresentationPass({ category = "wall_clip" }) == "environment",
    "structural dynamic geometry defaults to environment")
check(viewport.surfacePresentationPass({ presentationPass = "live", category = "wall_clip" }) == "live",
    "explicit renderer pass ownership wins")
check(viewport.surfacePresentationPass({ model = true }) == "environment",
    "unclassified placed models retain environment default")

print(string.format("WORLD PASS COMPOSITOR TESTS: %d passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
'''
(ROOT / "tests/test_world_pass_compositor.lua").write_text(test, encoding="utf-8")

print("Selective AA patch applied.")
