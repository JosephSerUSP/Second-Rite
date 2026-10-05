-- Full-cadence selective world AA for #836.
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
