-- Final logical-surface -> host-window presentation.
--
-- The game renderer owns the low-resolution logical Canvas. This module owns
-- only how that finished Canvas is reconstructed on the physical display.
-- Render-surface/aspect selection remains presentation.surface's job.
local surface = require("presentation.surface")

local output = {}

local MODES = { nearest = true, crt = true }
local activeMode = "nearest"
local hostWidth, hostHeight
local crtShader = nil
local crtShaderError = nil

-- Original Thestra experiment for #1310. This is intentionally a small,
-- single-pass reconstruction shader rather than imported emulator shader code:
-- two explicit horizontal source taps, a luminance-neutral scanline/beam
-- envelope, no curvature, no phosphor mask, no temporal state.
local CRT_SHADER = [[
    extern vec2 sourceSize;
    extern number outputScale;

    vec4 effect(vec4 color, Image tex, vec2 tc, vec2 sc) {
        // Pixel centres are integer coordinates in this space.
        vec2 sourcePos = tc * sourceSize - vec2(0.5);
        vec2 base = floor(sourcePos);
        vec2 fracPart = fract(sourcePos);

        // Reconstruct horizontally between neighbouring source samples while
        // retaining one discrete source row. This softens fractional X scaling
        // without turning the low-resolution frame into ordinary bilinear blur.
        number row = floor(sourcePos.y + 0.5);
        number blendX = smoothstep(0.18, 0.82, fracPart.x);
        vec2 hi = max(sourceSize - vec2(1.0), vec2(0.0));
        vec2 leftPixel = clamp(vec2(base.x, row), vec2(0.0), hi);
        vec2 rightPixel = clamp(vec2(base.x + 1.0, row), vec2(0.0), hi);
        vec4 leftPx = Texel(tex, (leftPixel + vec2(0.5)) / sourceSize);
        vec4 rightPx = Texel(tex, (rightPixel + vec2(0.5)) / sourceSize);
        vec4 px = mix(leftPx, rightPx, blendX);

        // A source scanline is brightest around its centre and gently darker
        // near the row boundary. Fade the effect away at low host scales where
        // there are too few physical pixels to represent a beam cleanly.
        number phase = abs(fract(tc.y * sourceSize.y) - 0.5) * 2.0;
        number scaleWeight = clamp((outputScale - 1.5) / 2.0, 0.0, 1.0);
        number scanStrength = 0.16 * scaleWeight;
        number beam = 1.0 - scanStrength * smoothstep(0.25, 1.0, phase);

        // Modest compensation keeps the filter from reading as a dark overlay.
        number compensation = 1.0 + scanStrength * 0.35;
        px.rgb *= beam * compensation;
        return px * color;
    }
]]

local function dimensions()
    if hostWidth and hostHeight then return hostWidth, hostHeight end
    if love and love.graphics and love.graphics.getDimensions then
        return love.graphics.getDimensions()
    end
    local w, h = surface.renderSize()
    return w, h
end

local function buildCrtShader()
    if crtShader then return crtShader end
    if crtShaderError then return nil, crtShaderError end
    if not (love and love.graphics and love.graphics.newShader) then
        crtShaderError = "LÖVE shader support is unavailable"
        return nil, crtShaderError
    end
    local ok, shaderOrError = pcall(love.graphics.newShader, CRT_SHADER)
    if not ok then
        crtShaderError = tostring(shaderOrError)
        return nil, crtShaderError
    end
    crtShader = shaderOrError
    return crtShader
end

function output.shaderSource()
    return CRT_SHADER
end

function output.modeIds()
    return { "nearest", "crt" }
end

function output.isKnownMode(id)
    return MODES[id] == true
end

function output.getMode()
    return activeMode
end

-- Returns false and restores the safe nearest path when the requested shader
-- cannot be constructed on this graphics backend.
function output.setMode(id)
    if not MODES[id] then
        activeMode = "nearest"
        return false, "unknown output presentation mode '" .. tostring(id) .. "'"
    end
    if id == "crt" then
        local shader, err = buildCrtShader()
        if not shader then
            activeMode = "nearest"
            return false, "CRT shader unavailable: " .. tostring(err)
        end
    end
    activeMode = id
    return true
end

function output.resize(w, h)
    hostWidth = tonumber(w) or hostWidth
    hostHeight = tonumber(h) or hostHeight
end

-- Geometry is mode-specific but has ONE authority. Nearest delegates to the
-- established integer contract verbatim. CRT is allowed to use the largest
-- aspect-preserving fractional scale that fits the host, including <1x for an
-- unusually small host.
function output.transformForMode(mode, w, h)
    if mode == "nearest" then
        return surface.outputTransform(w, h)
    end
    if mode ~= "crt" then
        error("unknown output presentation mode '" .. tostring(mode) .. "'", 2)
    end

    local renderWidth, renderHeight = surface.renderSize()
    local scale = math.min(w / renderWidth, h / renderHeight)
    if scale <= 0 then scale = 1 end
    local offsetX = (w - renderWidth * scale) * 0.5
    local offsetY = (h - renderHeight * scale) * 0.5
    return scale, offsetX, offsetY
end

function output.transform(w, h)
    if w == nil or h == nil then w, h = dimensions() end
    return output.transformForMode(activeMode, w, h)
end

function output.hostToRender(x, y)
    local w, h = dimensions()
    local scale, offsetX, offsetY = output.transformForMode(activeMode, w, h)
    return surface.hostToRender(x, y, scale, offsetX, offsetY)
end

function output.hostToComposition(x, y)
    local rx, ry = output.hostToRender(x, y)
    return surface.renderToComposition(rx, ry)
end

function output.draw(canvas)
    local w, h = dimensions()
    local scale, offsetX, offsetY = output.transformForMode(activeMode, w, h)

    love.graphics.push("all")
    love.graphics.setColor(1, 1, 1, 1)

    if activeMode == "crt" then
        local shader, err = buildCrtShader()
        if not shader then
            -- A backend can disappear/reinitialize after mode selection. Keep
            -- boot/play safe and make the effective geometry nearest too.
            activeMode = "nearest"
            scale, offsetX, offsetY = output.transformForMode("nearest", w, h)
            love.graphics.setShader()
            print("[output] CRT disabled: " .. tostring(err))
        else
            shader:send("sourceSize", { canvas:getWidth(), canvas:getHeight() })
            shader:send("outputScale", scale)
            love.graphics.setShader(shader)
        end
    else
        love.graphics.setShader()
    end

    love.graphics.draw(canvas, offsetX, offsetY, 0, scale, scale)
    love.graphics.pop()
    return activeMode, scale, offsetX, offsetY
end

return output
