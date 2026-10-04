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
local crtLabShader = nil
local crtLabShaderError = nil
local activeLabPreset = nil

-- Original Thestra experiment for #1310. This is intentionally a small,
-- single-pass reconstruction shader rather than imported emulator shader code:
-- two explicit horizontal source taps, a luminance-neutral scanline/beam
-- envelope, no curvature, no phosphor mask, no temporal state.
local CRT_SHADER = [[
    extern vec2 sourceSize;
    extern number physicalOutputScale;

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

        // A source scanline is brightest around its centre and visibly darker
        // near the row boundary. Calibrate against PHYSICAL source-pixel scale:
        // on high-DPI Android, 1.55 logical host units can still be ~2.7 display
        // pixels. Using logical scale here made the CRT path collapse into little
        // more than pleasant horizontal smoothing on real phones.
        number phase = abs(fract(tc.y * sourceSize.y) - 0.5) * 2.0;
        number scaleWeight = clamp((physicalOutputScale - 1.25) / 2.0, 0.0, 1.0);
        number scanStrength = 0.22 * scaleWeight;
        number beam = 1.0 - scanStrength * smoothstep(0.18, 1.0, phase);

        // Compensation keeps the stronger beam envelope from simply reading as
        // a dark overlay while retaining an obvious CRT scan structure.
        number compensation = 1.0 + scanStrength * 0.45;
        px.rgb *= beam * compensation;
        return px * color;
    }
]]


-- Developer-only CRT lab for #1310. These presets are intentionally absent
-- from modeIds(): they are visual-development experiments, not player-facing
-- display modes. Launch with output=crt-lab:<preset>.
local CRT_LAB_PRESET_ORDER = {
    "heavy-beam",
    "halation",
    "aperture",
    "slot-mask",
    "composite",
    "integrated",
    "convergence",
    "curved",
    "maximal",
}

local CRT_LAB_DEFAULTS = {
    beamStrength = 0.28,
    beamStart = 0.14,
    beamCompensation = 0.48,
    beamDriveExpansion = 0.0,
    horizontalSoftness = 0.18,
    lumaBleed = 0.0,
    halationStrength = 0.0,
    bloomStrength = 0.0,
    halationRadius = 1.25,
    grilleStrength = 0.0,
    slotMaskStrength = 0.0,
    compositeBleed = 0.0,
    ghostStrength = 0.0,
    convergencePixels = 0.0,
    curvature = 0.0,
    vignette = 0.0,
    noiseStrength = 0.0,
}

local CRT_LAB_PRESETS = {
    ["heavy-beam"] = {
        beamStrength = 0.42,
        beamStart = 0.06,
        beamCompensation = 0.62,
        horizontalSoftness = 0.16,
    },
    halation = {
        beamStrength = 0.30,
        beamStart = 0.12,
        beamCompensation = 0.50,
        halationStrength = 0.28,
        halationRadius = 1.35,
    },
    aperture = {
        beamStrength = 0.31,
        beamStart = 0.10,
        beamCompensation = 0.52,
        grilleStrength = 0.34,
    },
    ["slot-mask"] = {
        beamStrength = 0.27,
        beamStart = 0.12,
        beamCompensation = 0.48,
        slotMaskStrength = 0.34,
    },
    composite = {
        beamStrength = 0.25,
        beamStart = 0.14,
        beamCompensation = 0.46,
        horizontalSoftness = 0.26,
        compositeBleed = 0.68,
        ghostStrength = 0.07,
        halationStrength = 0.12,
        halationRadius = 1.10,
    },
    integrated = {
        -- Composite is the perceptual anchor, but this candidate spreads luma
        -- and bright-beam energy too so colour bleed is no longer doing nearly
        -- all of the pixel integration by itself.
        beamStrength = 0.38,
        beamStart = 0.07,
        beamCompensation = 0.58,
        beamDriveExpansion = 0.58,
        horizontalSoftness = 0.12,
        lumaBleed = 0.34,
        compositeBleed = 0.62,
        ghostStrength = 0.045,
        bloomStrength = 0.22,
        halationStrength = 0.18,
        halationRadius = 1.25,
    },
    convergence = {
        beamStrength = 0.29,
        beamStart = 0.11,
        beamCompensation = 0.50,
        convergencePixels = 2.0,
        halationStrength = 0.08,
    },
    curved = {
        beamStrength = 0.31,
        beamStart = 0.10,
        beamCompensation = 0.52,
        halationStrength = 0.20,
        halationRadius = 1.25,
        curvature = 0.075,
        vignette = 0.26,
    },
    maximal = {
        beamStrength = 0.36,
        beamStart = 0.07,
        beamCompensation = 0.58,
        horizontalSoftness = 0.25,
        halationStrength = 0.24,
        halationRadius = 1.45,
        grilleStrength = 0.20,
        compositeBleed = 0.52,
        ghostStrength = 0.05,
        convergencePixels = 1.15,
        curvature = 0.045,
        vignette = 0.22,
        noiseStrength = 0.018,
    },
}

local CRT_LAB_SHADER = [[
    extern vec2 sourceSize;
    extern number physicalOutputScale;

    extern number beamStrength;
    extern number beamStart;
    extern number beamCompensation;
    extern number beamDriveExpansion;
    extern number horizontalSoftness;
    extern number lumaBleed;
    extern number halationStrength;
    extern number bloomStrength;
    extern number halationRadius;
    extern number grilleStrength;
    extern number slotMaskStrength;
    extern number compositeBleed;
    extern number ghostStrength;
    extern number convergencePixels;
    extern number curvature;
    extern number vignette;
    extern number noiseStrength;

    number luminance(vec3 rgb) {
        return dot(rgb, vec3(0.2126, 0.7152, 0.0722));
    }

    vec2 warpedUv(vec2 uv) {
        vec2 p = uv * 2.0 - vec2(1.0);
        number r2 = dot(p, p);
        p *= 1.0 + curvature * r2;
        return p * 0.5 + vec2(0.5);
    }

    vec4 reconstruct(Image tex, vec2 uv) {
        vec2 sourcePos = uv * sourceSize - vec2(0.5);
        vec2 base = floor(sourcePos);
        vec2 fracPart = fract(sourcePos);
        number row = floor(sourcePos.y + 0.5);

        number lo = clamp(horizontalSoftness, 0.02, 0.45);
        number hiBlend = 1.0 - lo;
        number blendX = smoothstep(lo, hiBlend, fracPart.x);
        vec2 hi = max(sourceSize - vec2(1.0), vec2(0.0));
        vec2 leftPixel = clamp(vec2(base.x, row), vec2(0.0), hi);
        vec2 rightPixel = clamp(vec2(base.x + 1.0, row), vec2(0.0), hi);
        vec4 leftPx = Texel(tex, (leftPixel + vec2(0.5)) / sourceSize);
        vec4 rightPx = Texel(tex, (rightPixel + vec2(0.5)) / sourceSize);
        return mix(leftPx, rightPx, blendX);
    }

    vec3 brightPart(vec3 rgb) {
        number peak = max(max(rgb.r, rgb.g), rgb.b);
        number amount = max(peak - 0.52, 0.0);
        return rgb * amount;
    }

    vec4 effect(vec4 color, Image tex, vec2 tc, vec2 sc) {
        vec2 uv = warpedUv(tc);
        if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
            return vec4(0.0, 0.0, 0.0, 1.0) * color;
        }

        vec4 px = reconstruct(tex, uv);

        // Optional RGB convergence drift is expressed in physical output pixels
        // so it has comparable visual weight at 720p, 1080p and high-DPI output.
        number convUv = convergencePixels
            / max(sourceSize.x * max(physicalOutputScale, 0.001), 1.0);
        if (convergencePixels > 0.0) {
            vec4 pr = reconstruct(tex, uv + vec2(convUv, 0.0));
            vec4 pb = reconstruct(tex, uv - vec2(convUv, 0.0));
            px.r = pr.r;
            px.b = pb.b;
        }

        // Composite-like signal bandwidth loss. Chroma and luma are authored
        // separately so a candidate can let neighbouring source pixels fuse in
        // brightness as well as colour instead of relying on chroma smear alone.
        if (compositeBleed > 0.0 || lumaBleed > 0.0) {
            vec2 signalDx = vec2(1.35 / sourceSize.x, 0.0);
            vec3 left = reconstruct(tex, uv - signalDx).rgb;
            vec3 right = reconstruct(tex, uv + signalDx).rgb;
            vec3 soft = (left + px.rgb * 2.0 + right) * 0.25;
            number y0 = luminance(px.rgb);
            number ys = luminance(soft);
            vec3 chroma0 = px.rgb - vec3(y0);
            vec3 chromaSoft = soft - vec3(ys);
            number y = mix(y0, ys, lumaBleed);
            px.rgb = vec3(y) + mix(chroma0, chromaSoft, compositeBleed);

            if (ghostStrength > 0.0) {
                vec3 delayed = reconstruct(
                    tex, uv - vec2(2.35 / sourceSize.x, 0.0)).rgb;
                px.rgb += brightPart(delayed) * ghostStrength;
            }
        }

        // Cheap single-pass phosphor bloom / halation: the same four bright
        // neighbours can contribute neutral light spread and a warmer glass-like
        // halo independently. This lets a strong recipe reinforce brightness
        // without making every edge disproportionately orange.
        if (halationStrength > 0.0 || bloomStrength > 0.0) {
            vec2 haloStep = vec2(halationRadius) / sourceSize;
            vec3 halo =
                brightPart(reconstruct(tex, uv + vec2(haloStep.x, 0.0)).rgb)
                + brightPart(reconstruct(tex, uv - vec2(haloStep.x, 0.0)).rgb)
                + brightPart(reconstruct(tex, uv + vec2(0.0, haloStep.y)).rgb)
                + brightPart(reconstruct(tex, uv - vec2(0.0, haloStep.y)).rgb);
            halo *= 0.25;
            px.rgb += halo * bloomStrength;
            px.rgb += halo * vec3(1.10, 0.72, 0.56) * halationStrength;
        }

        // Source-line beam envelope. Bright drive widens the effective beam in
        // the integrated candidate: highlights bridge more of the dark scanline
        // boundary while low-level pixels retain stronger separation, closer to
        // the way a CRT spot grows with drive instead of every source pixel
        // remaining the same hard-edged rectangle.
        number phase = abs(fract(uv.y * sourceSize.y) - 0.5) * 2.0;
        number scaleWeight = clamp((physicalOutputScale - 1.25) / 2.0, 0.0, 1.0);
        number scanStrength = beamStrength * scaleWeight;
        number drive = clamp(max(max(px.r, px.g), px.b), 0.0, 1.0);
        number localScanStrength = scanStrength
            * (1.0 - beamDriveExpansion * drive * 0.72);
        number beam = 1.0 - localScanStrength
            * smoothstep(beamStart, 1.0, phase);
        px.rgb *= beam * (1.0 + scanStrength * beamCompensation);

        // Host-pixel mask experiments. They are intentionally independent of
        // source scanlines: this is exactly the phone-panel/moire variable that
        // #1310 needs to judge separately.
        number maskWeight = clamp((physicalOutputScale - 1.75) / 1.75, 0.0, 1.0);
        if (grilleStrength > 0.0) {
            number triad = mod(floor(sc.x), 3.0);
            vec3 grille = vec3(0.72);
            if (triad < 1.0) {
                grille = vec3(1.18, 0.72, 0.72);
            } else if (triad < 2.0) {
                grille = vec3(0.72, 1.18, 0.72);
            } else {
                grille = vec3(0.72, 0.72, 1.18);
            }
            px.rgb *= mix(vec3(1.0), grille,
                grilleStrength * maskWeight);
        }

        if (slotMaskStrength > 0.0) {
            number rowBand = mod(floor(sc.y / 2.0), 2.0);
            number slot = mod(floor(sc.x) + rowBand * 3.0, 6.0);
            vec3 slotRgb = vec3(0.68);
            if (slot < 2.0) {
                slotRgb = vec3(1.16, 0.68, 0.68);
            } else if (slot < 4.0) {
                slotRgb = vec3(0.68, 1.16, 0.68);
            } else {
                slotRgb = vec3(0.68, 0.68, 1.16);
            }
            number rowGap = mix(1.0, 0.80, step(2.0, mod(floor(sc.y), 4.0)));
            slotRgb *= rowGap;
            px.rgb *= mix(vec3(1.0), slotRgb,
                slotMaskStrength * maskWeight);
        }

        if (vignette > 0.0) {
            vec2 p = tc * 2.0 - vec2(1.0);
            number edge = smoothstep(0.32, 1.25, dot(p, p));
            px.rgb *= 1.0 - vignette * edge;
        }

        if (noiseStrength > 0.0) {
            number n = fract(sin(dot(floor(sc.xy),
                vec2(12.9898, 78.233))) * 43758.5453);
            px.rgb *= 1.0 + (n - 0.5) * noiseStrength;
        }

        return vec4(max(px.rgb, vec3(0.0)), px.a) * color;
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

local function buildCrtLabShader()
    if crtLabShader then return crtLabShader end
    if crtLabShaderError then return nil, crtLabShaderError end
    if not (love and love.graphics and love.graphics.newShader) then
        crtLabShaderError = "LÖVE shader support is unavailable"
        return nil, crtLabShaderError
    end
    local ok, shaderOrError = pcall(love.graphics.newShader, CRT_LAB_SHADER)
    if not ok then
        crtLabShaderError = tostring(shaderOrError)
        return nil, crtLabShaderError
    end
    crtLabShader = shaderOrError
    return crtLabShader
end

local function labPresetFromMode(id)
    if type(id) ~= "string" then return nil end
    local presetId = id:match("^crt%-lab:(.+)$")
    if presetId and CRT_LAB_PRESETS[presetId] then return presetId end
    return nil
end

local function resolvedLabPreset(id)
    local authored = CRT_LAB_PRESETS[id]
    if not authored then return nil end
    local resolved = {}
    for key, value in pairs(CRT_LAB_DEFAULTS) do resolved[key] = value end
    for key, value in pairs(authored) do resolved[key] = value end
    return resolved
end

function output.shaderSource()
    return CRT_SHADER
end

function output.crtLabShaderSource()
    return CRT_LAB_SHADER
end

function output.modeIds()
    return { "nearest", "crt" }
end

function output.crtLabPresetIds()
    local ids = {}
    for i, id in ipairs(CRT_LAB_PRESET_ORDER) do ids[i] = id end
    return ids
end

function output.crtLabModeIds()
    local ids = {}
    for i, id in ipairs(CRT_LAB_PRESET_ORDER) do
        ids[i] = "crt-lab:" .. id
    end
    return ids
end

function output.crtLabPreset(id)
    return resolvedLabPreset(id)
end

function output.isKnownMode(id)
    return MODES[id] == true or labPresetFromMode(id) ~= nil
end

function output.getMode()
    return activeMode
end

-- Returns false and restores the safe nearest path when the requested shader
-- cannot be constructed on this graphics backend.
function output.setMode(id)
    local labPreset = labPresetFromMode(id)
    if not MODES[id] and not labPreset then
        activeMode = "nearest"
        activeLabPreset = nil
        return false, "unknown output presentation mode '" .. tostring(id) .. "'"
    end
    if id == "crt" then
        local shader, err = buildCrtShader()
        if not shader then
            activeMode = "nearest"
            activeLabPreset = nil
            return false, "CRT shader unavailable: " .. tostring(err)
        end
    elseif labPreset then
        local shader, err = buildCrtLabShader()
        if not shader then
            activeMode = "nearest"
            activeLabPreset = nil
            return false, "CRT lab shader unavailable: " .. tostring(err)
        end
    end
    activeMode = id
    activeLabPreset = labPreset
    return true
end

function output.resize(w, h)
    hostWidth = tonumber(w) or hostWidth
    hostHeight = tonumber(h) or hostHeight
end

local function fractionalFit(w, h)
    local renderWidth, renderHeight = surface.renderSize()
    local scale = math.min(w / renderWidth, h / renderHeight)
    if scale <= 0 then scale = 1 end
    return scale,
        (w - renderWidth * scale) * 0.5,
        (h - renderHeight * scale) * 0.5
end

local function isAndroid()
    if not (love and love.system and love.system.getOS) then return false end
    local ok, osName = pcall(love.system.getOS)
    return ok and osName == "Android"
end

function output.hostDpiScale()
    local scale = nil
    if love and love.window and love.window.getDPIScale then
        local ok, value = pcall(love.window.getDPIScale)
        if ok then scale = tonumber(value) end
    end
    if (not scale or scale <= 0) and love and love.graphics and love.graphics.getDPIScale then
        local ok, value = pcall(love.graphics.getDPIScale)
        if ok then scale = tonumber(value) end
    end
    return (scale and scale > 0) and scale or 1
end

function output.physicalOutputScale(logicalScale)
    return (tonumber(logicalScale) or 1) * output.hostDpiScale()
end

-- Geometry is mode-specific but has ONE authority. Desktop/static nearest keeps
-- the historical integer contract. Android always fractionally fits the chosen
-- logical surface: DEVICE already did this, but WIDE falling back to 1x on a
-- 1.55x-capable phone made the whole game suddenly tiny when CRT was disabled.
-- CRT uses the same largest aspect-preserving fractional fit everywhere.
function output.transformForMode(mode, w, h)
    if mode == "nearest" then
        if isAndroid() then return fractionalFit(w, h) end
        return surface.outputTransform(w, h)
    end
    if mode ~= "crt" and not labPresetFromMode(mode) then
        error("unknown output presentation mode '" .. tostring(mode) .. "'", 2)
    end

    return fractionalFit(w, h)
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
            activeLabPreset = nil
            scale, offsetX, offsetY = output.transformForMode("nearest", w, h)
            love.graphics.setShader()
            print("[output] CRT disabled: " .. tostring(err))
        else
            shader:send("sourceSize", { canvas:getWidth(), canvas:getHeight() })
            shader:send("physicalOutputScale", output.physicalOutputScale(scale))
            love.graphics.setShader(shader)
        end
    elseif activeLabPreset then
        local shader, err = buildCrtLabShader()
        local preset = resolvedLabPreset(activeLabPreset)
        if not shader or not preset then
            activeMode = "nearest"
            activeLabPreset = nil
            scale, offsetX, offsetY = output.transformForMode("nearest", w, h)
            love.graphics.setShader()
            print("[output] CRT lab disabled: " .. tostring(err or "invalid preset"))
        else
            shader:send("sourceSize", { canvas:getWidth(), canvas:getHeight() })
            shader:send("physicalOutputScale", output.physicalOutputScale(scale))
            for key, value in pairs(preset) do shader:send(key, value) end
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
