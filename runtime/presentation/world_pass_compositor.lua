-- Full-cadence selective world AA for #836.
--
-- The environment remains live 3D. Only its colour raster is supersampled and
-- box-resolved. A separate native-resolution environment pass reconstructs
-- pristine depth, then live actors/events/effects render at native resolution
-- against that depth. This keeps architectural edges smooth while the
-- pass-ownership boundary stays deliberately hard.
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

-- Two presentation styles share this renderer, and the map's traversal decides
-- which one it is; there is no authored flag:
--   * first-person grid maps are realtime PS1 3D: native raster, affine texture
--     warp and dither, never supersampled;
--   * bounded-lane maps are live 3D pretending to be a pre-rendered backdrop:
--     supersampled environment colour and perspective-correct textures.
-- Literal layered_2d packages are real pre-renders and bypass both.
function compositor.isFakePrerendered(session)
    local traversal = session and session.townTraversal
    if not traversal then return false end
    local environment = traversal.environment
    return not (environment and environment.preRendered)
end

function compositor.isEligible(session)
    if not session then return false end
    if session.roomBakePass or session.roomBakeSquareCamera then return false end
    if session.profile3dVariant and session.profile3dVariant ~= "current" then return false end
    if not compositor.isFakePrerendered(session) then return false end
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

local function releaseTarget(target)
    if target and target.release then target:release() end
end

local function releaseTargets()
    if not targets then return end
    releaseTarget(targets.envColorSS)
    releaseTarget(targets.envDepthNative)
    targets = nil
end

local function ensureTargets(width, height, scale)
    if targets and targets.width == width and targets.height == height
            and targets.scale == scale then
        return targets
    end
    releaseTargets()
    local ssWidth, ssHeight = width * scale, height * scale
    local envColorSS = surface.newRasterCanvas(ssWidth, ssHeight)
    envColorSS:setFilter("nearest", "nearest")
    targets = {
        width = width,
        height = height,
        scale = scale,
        envColorSS = envColorSS,
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

local function colorCanvas(binding)
    if type(binding) == "table" then return binding[1] end
    return binding
end

-- viewport_3d historically exposed stats for one logical frame. Selective AA
-- turns that frame into three renderer calls, though: visible environment,
-- depth-only environment, then visible live content. The final call used to
-- overwrite the first one's counters, so a structural model that correctly
-- moved into the environment pass misleadingly reported modelDraws=0.
--
-- Keep the instrumentation contract scale-invariant by summing only the two
-- VISIBLE passes. The native depth rebuild is deliberately excluded because it
-- is an implementation pass, not another logical draw of the frame.
local function viewportFrameStats()
    local ok, viewport = pcall(require, "presentation.viewport_3d")
    if not ok or type(viewport) ~= "table"
            or type(viewport.getLastFrameStats) ~= "function" then
        return nil
    end
    local stats = viewport.getLastFrameStats()
    if type(stats) ~= "table" then return nil end
    return stats
end

local function mergeCategoryCounts(environment, live)
    local merged = {}
    for key, value in pairs(environment or {}) do merged[key] = value end
    for key, value in pairs(live or {}) do merged[key] = (merged[key] or 0) + value end
    return merged
end

function compositor.combineVisibleFrameStats(environmentStats, liveStats)
    if type(environmentStats) ~= "table" or type(liveStats) ~= "table"
            or environmentStats == liveStats then
        return liveStats
    end
    local environmentModelDraws = environmentStats.modelDraws or 0
    local liveModelDraws = liveStats.modelDraws or 0
    liveStats.environmentModelDraws = environmentModelDraws
    liveStats.liveModelDraws = liveModelDraws
    liveStats.modelDraws = environmentModelDraws + liveModelDraws
    liveStats.persistentBatchDraws = (environmentStats.persistentBatchDraws or 0)
        + (liveStats.persistentBatchDraws or 0)
    liveStats.dynamicMeshDraws = (environmentStats.dynamicMeshDraws or 0)
        + (liveStats.dynamicMeshDraws or 0)
    liveStats.dynamicByCategory = mergeCategoryCounts(
        environmentStats.dynamicByCategory, liveStats.dynamicByCategory)
    liveStats.selectiveAAVisiblePasses = 2
    return liveStats
end

function compositor.draw(session, authoredCamera, inspection, drawWorld)
    if not compositor.isEligible(session) then
        return drawWorld(session, authoredCamera, inspection, nil)
    end

    local activeBinding = love.graphics.getCanvas()
    local activeColor = colorCanvas(activeBinding)
    if not activeColor or not activeColor.getDimensions then
        return drawWorld(session, authoredCamera, inspection, nil)
    end

    local width, height = activeColor:getDimensions()
    local scale = compositor.resolveScale(session)
    local t = ensureTargets(width, height, scale)
    local pushed = false
    local ok, result = xpcall(function()
        love.graphics.push("all")
        pushed = true
        love.graphics.origin()
        love.graphics.setScissor()

        -- 1. High-resolution environment colour. Dither is intentionally off:
        -- screen-anchored PSX dither averaged through a 3x box filter is neither
        -- the native pattern nor the "expensive prerender" visual language.
        -- World-space effects deliberately do NOT draw here: in the ordinary
        -- renderer they resolve after live meshes against the same depth buffer.
        -- Baking them into this colour image would make a foreground flame or
        -- weather particle sit behind an actor regardless of world depth.
        --
        -- This pass only consumes depth while it is being rasterized; the
        -- supersampled depth is never read afterwards. Use LÖVE's internally
        -- managed depth/stencil attachment here, matching the ordinary world
        -- renderer's binding shape. Besides avoiding an unnecessary persistent
        -- depth Canvas, this keeps love.graphics.getCanvas() exposing the colour
        -- Canvas directly so viewport_3d can resolve the real supersample target
        -- dimensions instead of falling back to the native surface size.
        love.graphics.setCanvas({
            t.envColorSS,
            depth = true,
            stencil = true,
        })
        love.graphics.clear(0, 0, 0, 1, 0, 1)
        drawWorld(session, authoredCamera, inspection, {
            presentationPass = "environment",
            rasterScale = scale,
            ditherLevels = 0,
            drawBackground = true,
            drawWorldEffects = false,
            drawPost = false,
            preserveDepth = false,
        })
        local environmentStats = viewportFrameStats()

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
        -- before, depth-tests against the environment reconstructed above, and
        -- then draws world-space Effekseer against the resulting combined depth.
        -- That preserves today's actor/effect ordering while keeping both sides
        -- of that interaction on the native raster.
        drawWorld(session, authoredCamera, inspection, {
            presentationPass = "live",
            rasterScale = 1,
            drawBackground = false,
            drawWorldEffects = true,
            drawPost = true,
            preserveDepth = false,
        })
        compositor.combineVisibleFrameStats(environmentStats, viewportFrameStats())

        love.graphics.pop()
        pushed = false
        restoreState()
        -- Downstream map HUD / stencil consumers still expect an attached
        -- depth-stencil buffer. Keep our native attachment bound even though the
        -- live pass intentionally clears its contents before returning to 2D.
        love.graphics.setCanvas({
            activeColor,
            depthstencil = t.envDepthNative,
        })
    end, debug.traceback)

    if not ok then
        if pushed then pcall(love.graphics.pop) end
        restoreState()
        love.graphics.setCanvas(activeBinding)
        error(result, 0)
    end
    return result
end

return compositor