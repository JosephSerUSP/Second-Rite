-- Final logical-surface -> host-window presentation.
--
-- The game renderer owns the low-resolution logical Canvas. This module owns
-- only how that finished Canvas is reconstructed on the physical display.
-- Render-surface/aspect selection remains presentation.surface's job.
--
-- CRT is intentionally a two-stage path:
--   1. signal degradation at the native logical resolution (YIQ bandwidth),
--   2. beam/phosphor reconstruction at host resolution.
-- This keeps the expensive colour work proportional to the ~426x240 source
-- rather than to the physical display, while making source pixels behave like
-- samples feeding a luminous display instead of immutable square tiles.
local surface = require("presentation.surface")

local output = {}

local MODES = { nearest = true, crt = true }
local activeMode = "nearest"
local hostWidth, hostHeight
local signalShader = nil
local signalShaderError = nil
local crtShader = nil
local crtShaderError = nil
local signalCanvas = nil
local signalCanvasWidth, signalCanvasHeight
local activeParams = nil
local activeLabPreset = nil

local PUBLIC_PARAM_ORDER = {
    "beamStrength",
    "beamWidth",
    "beamDriveExpansion",
    "signalSpread",
    "lumaBleed",
    "compositeBleed",
    "chromaDelay",
    "ghostStrength",
    "bloomStrength",
    "halationStrength",
    "halationRadius",
    "convergencePixels",
    "grilleStrength",
    "slotMaskStrength",
    "curvature",
    "vignette",
    "noiseStrength",
}

-- Deliberately assertive shipping CRT defaults. These are not intended as
-- neutral emulation values: the project wants visible colour-bandwidth loss,
-- overlapping luminous source rows and highlight spread. The player-facing
-- submenu can move far beyond these defaults in either direction.
local CRT_DEFAULTS = {
    beamStrength = 0.82,
    beamStart = 0.03,
    beamCompensation = 0.42,
    beamDriveExpansion = 1.25,
    beamWidth = 0.82,
    horizontalSoftness = 0.22,
    signalSpread = 1.65,
    lumaBleed = 0.52,
    compositeBleed = 1.20,
    chromaDelay = 0.35,
    ghostStrength = 0.08,
    bloomStrength = 0.42,
    halationStrength = 0.24,
    halationRadius = 1.55,
    grilleStrength = 0.0,
    slotMaskStrength = 0.0,
    convergencePixels = 0.0,
    curvature = 0.0,
    vignette = 0.06,
    noiseStrength = 0.006,
}

-- Developer comparison recipes remain launchable as crt-lab:<preset> and stay
-- absent from modeIds(). They now run through the same two-stage CRT pipeline
-- as the player-facing mode so comparisons exercise the shipping architecture.
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
    beamWidth = 0.58,
    horizontalSoftness = 0.18,
    signalSpread = 1.35,
    lumaBleed = 0.0,
    halationStrength = 0.0,
    bloomStrength = 0.0,
    halationRadius = 1.25,
    grilleStrength = 0.0,
    slotMaskStrength = 0.0,
    compositeBleed = 0.0,
    chromaDelay = 0.0,
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
        beamWidth = 0.66,
        horizontalSoftness = 0.16,
    },
    halation = {
        beamStrength = 0.30,
        beamStart = 0.12,
        beamCompensation = 0.50,
        beamWidth = 0.60,
        halationStrength = 0.28,
        halationRadius = 1.35,
    },
    aperture = {
        beamStrength = 0.31,
        beamStart = 0.10,
        beamCompensation = 0.52,
        beamWidth = 0.60,
        grilleStrength = 0.34,
    },
    ["slot-mask"] = {
        beamStrength = 0.27,
        beamStart = 0.12,
        beamCompensation = 0.48,
        beamWidth = 0.58,
        slotMaskStrength = 0.34,
    },
    composite = {
        beamStrength = 0.25,
        beamStart = 0.14,
        beamCompensation = 0.46,
        beamWidth = 0.58,
        horizontalSoftness = 0.26,
        signalSpread = 1.35,
        compositeBleed = 0.68,
        ghostStrength = 0.07,
        halationStrength = 0.12,
        halationRadius = 1.10,
    },
    integrated = {
        beamStrength = 0.38,
        beamStart = 0.07,
        beamCompensation = 0.58,
        beamDriveExpansion = 0.58,
        beamWidth = 0.66,
        horizontalSoftness = 0.12,
        signalSpread = 1.35,
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
        beamWidth = 0.60,
        convergencePixels = 2.0,
        halationStrength = 0.08,
    },
    curved = {
        beamStrength = 0.31,
        beamStart = 0.10,
        beamCompensation = 0.52,
        beamWidth = 0.60,
        halationStrength = 0.20,
        halationRadius = 1.25,
        curvature = 0.075,
        vignette = 0.26,
    },
    maximal = {
        beamStrength = 0.36,
        beamStart = 0.07,
        beamCompensation = 0.58,
        beamDriveExpansion = 0.45,
        beamWidth = 0.66,
        horizontalSoftness = 0.25,
        signalSpread = 1.45,
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

-- Native-resolution analogue signal stage. Luma and chroma bandwidth are
-- separated in YIQ; compositeBleed may exceed 1.0 on purpose, allowing the
-- player to over-smear colour well past a plausible television signal.
local CRT_SIGNAL_SHADER = [[
    extern vec2 sourceSize;
    extern number signalSpread;
    extern number horizontalSoftness;
    extern number lumaBleed;
    extern number compositeBleed;
    extern number chromaDelay;
    extern number ghostStrength;

    vec3 rgbToYiq(vec3 c) {
        return vec3(
            dot(c, vec3(0.299, 0.587, 0.114)),
            dot(c, vec3(0.596, -0.274, -0.322)),
            dot(c, vec3(0.211, -0.523, 0.312))
        );
    }

    vec3 yiqToRgb(vec3 c) {
        return vec3(
            c.x + 0.956 * c.y + 0.621 * c.z,
            c.x - 0.272 * c.y - 0.647 * c.z,
            c.x - 1.106 * c.y + 1.703 * c.z
        );
    }

    vec3 brightPart(vec3 rgb) {
        number peak = max(max(rgb.r, rgb.g), rgb.b);
        number amount = max(peak - 0.48, 0.0);
        return rgb * amount;
    }

    vec4 effect(vec4 color, Image tex, vec2 tc, vec2 sc) {
        vec2 dx = vec2(max(abs(signalSpread), 0.001) / sourceSize.x, 0.0);
        vec3 c0 = Texel(tex, tc).rgb;
        vec3 l1 = Texel(tex, tc - dx).rgb;
        vec3 r1 = Texel(tex, tc + dx).rgb;
        vec3 l2 = Texel(tex, tc - dx * 2.0).rgb;
        vec3 r2 = Texel(tex, tc + dx * 2.0).rgb;

        vec3 soft3 = (l1 + c0 * 2.0 + r1) * 0.25;
        vec3 soft5 = (l2 + l1 * 2.0 + c0 * 4.0 + r1 * 2.0 + r2) * 0.10;
        number kernelMix = clamp(horizontalSoftness * 2.0, 0.0, 1.0);
        vec3 soft = mix(soft3, soft5, kernelMix);

        vec3 baseYiq = rgbToYiq(c0);
        vec3 softYiq = rgbToYiq(soft);
        vec3 outYiq = baseYiq;
        outYiq.x = mix(baseYiq.x, softYiq.x, lumaBleed);
        outYiq.yz = mix(baseYiq.yz, softYiq.yz, compositeBleed);

        if (chromaDelay != 0.0) {
            vec2 delayUv = vec2(chromaDelay / sourceSize.x, 0.0);
            vec3 delayedYiq = rgbToYiq(Texel(tex, tc - delayUv).rgb);
            number delayMix = abs(chromaDelay) * 0.18;
            outYiq.yz += (delayedYiq.yz - outYiq.yz) * delayMix;
        }

        vec3 rgb = yiqToRgb(outYiq);
        if (ghostStrength != 0.0) {
            vec2 ghostUv = vec2((2.25 + abs(chromaDelay)) / sourceSize.x, 0.0);
            rgb += brightPart(Texel(tex, tc - ghostUv).rgb) * ghostStrength;
        }
        return vec4(max(rgb, vec3(0.0)), 1.0) * color;
    }
]]

-- Host-resolution beam/phosphor reconstruction. Two adjacent native source
-- rows contribute Gaussian-like footprints whose width grows with drive. The
-- output therefore ceases to be a grid of enlarged source rectangles: glyphs,
-- diagonals and highlights are shaped by overlap between luminous samples.
local CRT_SHADER = [[
    extern vec2 sourceSize;
    extern number physicalOutputScale;

    extern number beamStrength;
    extern number beamStart;
    extern number beamCompensation;
    extern number beamDriveExpansion;
    extern number beamWidth;
    extern number bloomStrength;
    extern number halationStrength;
    extern number halationRadius;
    extern number grilleStrength;
    extern number slotMaskStrength;
    extern number convergencePixels;
    extern number curvature;
    extern number vignette;
    extern number noiseStrength;

    vec2 warpedUv(vec2 uv) {
        vec2 p = uv * 2.0 - vec2(1.0);
        number r2 = dot(p, p);
        p *= 1.0 + curvature * r2;
        return p * 0.5 + vec2(0.5);
    }

    vec3 rowSample(Image tex, number sourceX, number row) {
        number bx = floor(sourceX);
        number fx = fract(sourceX);
        vec2 hi = max(sourceSize - vec2(1.0), vec2(0.0));
        vec2 lp = clamp(vec2(bx, row), vec2(0.0), hi);
        vec2 rp = clamp(vec2(bx + 1.0, row), vec2(0.0), hi);
        vec3 a = Texel(tex, (lp + vec2(0.5)) / sourceSize).rgb;
        vec3 b = Texel(tex, (rp + vec2(0.5)) / sourceSize).rgb;
        number blendX = smoothstep(0.10, 0.90, fx);
        return mix(a, b, blendX);
    }

    vec3 reconstructBeam(Image tex, vec2 uv) {
        vec2 sourcePos = uv * sourceSize - vec2(0.5);
        number row0 = floor(sourcePos.y);
        number row1 = row0 + 1.0;
        number fy = fract(sourcePos.y);
        vec3 c0 = rowSample(tex, sourcePos.x, row0);
        vec3 c1 = rowSample(tex, sourcePos.x, row1);
        vec3 linear = mix(c0, c1, fy);

        number drive = clamp(max(max(linear.r, linear.g), linear.b), 0.0, 2.0);
        number sigma = max(0.035,
            abs(beamWidth) * (1.0 + beamDriveExpansion * drive * 0.55));
        number invSigma2 = 1.0 / max(sigma * sigma, 0.001);
        number d0 = abs(sourcePos.y - row0);
        number d1 = abs(row1 - sourcePos.y);
        number w0 = exp2(-1.45 * d0 * d0 * invSigma2);
        number w1 = exp2(-1.45 * d1 * d1 * invSigma2);
        number centreNorm = 1.0 + exp2(-1.45 * invSigma2);
        vec3 emitted = (c0 * w0 + c1 * w1) / max(centreNorm, 0.001);

        // At low physical output scales there are not enough display pixels to
        // describe a beam envelope cleanly, so fade the reconstruction toward
        // ordinary vertical interpolation rather than generating moire mush.
        number scaleWeight = clamp((physicalOutputScale - 1.0) / 1.4, 0.0, 1.0);
        number amount = beamStrength * scaleWeight;
        emitted = mix(emitted, linear, beamStart);
        vec3 result = mix(linear, emitted, amount);
        result *= 1.0 + beamStrength * beamCompensation * scaleWeight * 0.22;
        return result;
    }

    vec3 brightPart(vec3 rgb) {
        number peak = max(max(rgb.r, rgb.g), rgb.b);
        number amount = max(peak - 0.45, 0.0);
        return rgb * amount;
    }

    vec4 effect(vec4 color, Image tex, vec2 tc, vec2 sc) {
        vec2 uv = warpedUv(tc);
        if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
            return vec4(0.0, 0.0, 0.0, 1.0) * color;
        }

        vec3 px = reconstructBeam(tex, uv);

        number convUv = convergencePixels
            / max(sourceSize.x * max(physicalOutputScale, 0.001), 1.0);
        if (convergencePixels != 0.0) {
            vec3 pr = reconstructBeam(tex, uv + vec2(convUv, 0.0));
            vec3 pb = reconstructBeam(tex, uv - vec2(convUv, 0.0));
            px.r = pr.r;
            px.b = pb.b;
        }

        if (bloomStrength != 0.0 || halationStrength != 0.0) {
            vec2 hs = vec2(max(abs(halationRadius), 0.05)) / sourceSize;
            vec3 halo =
                brightPart(Texel(tex, uv + vec2(hs.x, 0.0)).rgb)
                + brightPart(Texel(tex, uv - vec2(hs.x, 0.0)).rgb)
                + brightPart(Texel(tex, uv + vec2(0.0, hs.y)).rgb)
                + brightPart(Texel(tex, uv - vec2(0.0, hs.y)).rgb);
            halo *= 0.25;
            px += halo * bloomStrength;
            px += halo * vec3(1.10, 0.72, 0.56) * halationStrength;
        }

        number maskWeight = clamp((physicalOutputScale - 1.65) / 1.6, 0.0, 1.0);
        if (grilleStrength != 0.0) {
            number triad = mod(floor(sc.x), 3.0);
            vec3 grille = vec3(0.70);
            if (triad < 1.0) {
                grille = vec3(1.22, 0.70, 0.70);
            } else if (triad < 2.0) {
                grille = vec3(0.70, 1.22, 0.70);
            } else {
                grille = vec3(0.70, 0.70, 1.22);
            }
            px *= mix(vec3(1.0), grille, grilleStrength * maskWeight);
        }

        if (slotMaskStrength != 0.0) {
            number rowBand = mod(floor(sc.y / 2.0), 2.0);
            number slot = mod(floor(sc.x) + rowBand * 3.0, 6.0);
            vec3 slotRgb = vec3(0.66);
            if (slot < 2.0) {
                slotRgb = vec3(1.18, 0.66, 0.66);
            } else if (slot < 4.0) {
                slotRgb = vec3(0.66, 1.18, 0.66);
            } else {
                slotRgb = vec3(0.66, 0.66, 1.18);
            }
            number rowGap = mix(1.0, 0.78, step(2.0, mod(floor(sc.y), 4.0)));
            px *= mix(vec3(1.0), slotRgb * rowGap,
                slotMaskStrength * maskWeight);
        }

        if (vignette != 0.0) {
            vec2 p = tc * 2.0 - vec2(1.0);
            number edge = smoothstep(0.30, 1.25, dot(p, p));
            px *= 1.0 - vignette * edge;
        }

        if (noiseStrength != 0.0) {
            number n = fract(sin(dot(floor(sc.xy),
                vec2(12.9898, 78.233))) * 43758.5453);
            px *= 1.0 + (n - 0.5) * noiseStrength;
        }

        return vec4(max(px, vec3(0.0)), 1.0) * color;
    }
]]

local function copyTable(source)
    local copy = {}
    for key, value in pairs(source or {}) do copy[key] = value end
    return copy
end

local function dimensions()
    if hostWidth and hostHeight then return hostWidth, hostHeight end
    if love and love.graphics and love.graphics.getDimensions then
        return love.graphics.getDimensions()
    end
    local w, h = surface.renderSize()
    return w, h
end

local function buildSignalShader()
    if signalShader then return signalShader end
    if signalShaderError then return nil, signalShaderError end
    if not (love and love.graphics and love.graphics.newShader) then
        signalShaderError = "LÖVE shader support is unavailable"
        return nil, signalShaderError
    end
    local ok, shaderOrError = pcall(love.graphics.newShader, CRT_SIGNAL_SHADER)
    if not ok then
        signalShaderError = tostring(shaderOrError)
        return nil, signalShaderError
    end
    signalShader = shaderOrError
    return signalShader
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

local function ensureSignalCanvas(w, h)
    if signalCanvas and signalCanvasWidth == w and signalCanvasHeight == h then
        return signalCanvas
    end
    if not (love and love.graphics and love.graphics.newCanvas) then
        return nil, "LÖVE Canvas support is unavailable"
    end
    local ok, canvasOrError = pcall(love.graphics.newCanvas, w, h)
    if not ok then return nil, tostring(canvasOrError) end
    signalCanvas = canvasOrError
    signalCanvasWidth, signalCanvasHeight = w, h
    if signalCanvas.setFilter then signalCanvas:setFilter("nearest", "nearest") end
    return signalCanvas
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
    local resolved = copyTable(CRT_LAB_DEFAULTS)
    for key, value in pairs(authored) do resolved[key] = value end
    return resolved
end

local function isPublicCrtMode(id)
    return id == "crt" or (type(id) == "string" and id:match("^crt:") ~= nil)
end

local function resolvedPublicParams(id)
    if not isPublicCrtMode(id) then return nil end
    local resolved = copyTable(CRT_DEFAULTS)
    if id == "crt" then return resolved end

    local suffix = id:sub(5)
    for key, raw in suffix:gmatch("([%a][%w_]*)=([^;]+)") do
        if CRT_DEFAULTS[key] ~= nil then
            local value = tonumber(raw)
            if value and value == value and value > -1000 and value < 1000 then
                resolved[key] = value
            end
        end
    end
    return resolved
end

local function resolvedParamsForMode(id)
    local lab = labPresetFromMode(id)
    if lab then return resolvedLabPreset(lab), lab end
    return resolvedPublicParams(id), nil
end

local function ensureCrtPipeline()
    local signal, signalErr = buildSignalShader()
    if not signal then return nil, "CRT signal shader unavailable: " .. tostring(signalErr) end
    local beam, beamErr = buildCrtShader()
    if not beam then return nil, "CRT beam shader unavailable: " .. tostring(beamErr) end
    return true
end

function output.shaderSource()
    return CRT_SHADER
end

function output.signalShaderSource()
    return CRT_SIGNAL_SHADER
end

function output.crtLabShaderSource()
    return CRT_SHADER
end

function output.modeIds()
    return { "nearest", "crt" }
end

function output.publicCrtParameterIds()
    local ids = {}
    for i, id in ipairs(PUBLIC_PARAM_ORDER) do ids[i] = id end
    return ids
end

function output.publicCrtDefaults()
    return copyTable(CRT_DEFAULTS)
end

function output.crtParameters(id)
    return resolvedPublicParams(id or activeMode)
end

function output.encodeCrtParameters(params)
    local values = copyTable(CRT_DEFAULTS)
    for key, value in pairs(params or {}) do
        if values[key] ~= nil and tonumber(value) then values[key] = tonumber(value) end
    end
    local parts = {}
    for _, key in ipairs(PUBLIC_PARAM_ORDER) do
        parts[#parts + 1] = key .. "=" .. string.format("%.4g", values[key])
    end
    return "crt:" .. table.concat(parts, ";")
end

function output.crtLabPresetIds()
    local ids = {}
    for i, id in ipairs(CRT_LAB_PRESET_ORDER) do ids[i] = id end
    return ids
end

function output.crtLabModeIds()
    local ids = {}
    for i, id in ipairs(CRT_LAB_PRESET_ORDER) do ids[i] = "crt-lab:" .. id end
    return ids
end

function output.crtLabPreset(id)
    return resolvedLabPreset(id)
end

function output.isKnownMode(id)
    return MODES[id] == true or isPublicCrtMode(id) or labPresetFromMode(id) ~= nil
end

function output.getMode()
    return activeMode
end

-- Returns false and restores the safe nearest path when the requested shader
-- cannot be constructed on this graphics backend.
function output.setMode(id)
    if id == "nearest" then
        activeMode = "nearest"
        activeParams = nil
        activeLabPreset = nil
        return true
    end

    local params, labPreset = resolvedParamsForMode(id)
    if not params then
        activeMode = "nearest"
        activeParams = nil
        activeLabPreset = nil
        return false, "unknown output presentation mode '" .. tostring(id) .. "'"
    end

    local ok, err = ensureCrtPipeline()
    if not ok then
        activeMode = "nearest"
        activeParams = nil
        activeLabPreset = nil
        return false, err
    end

    activeMode = id
    activeParams = params
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
-- logical surface. CRT/custom-CRT/lab modes all use the same fractional fit.
function output.transformForMode(mode, w, h)
    if mode == "nearest" then
        if isAndroid() then return fractionalFit(w, h) end
        return surface.outputTransform(w, h)
    end
    if not isPublicCrtMode(mode) and not labPresetFromMode(mode) then
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

local function sendSignalUniforms(shader, params, w, h)
    shader:send("sourceSize", { w, h })
    shader:send("signalSpread", params.signalSpread)
    shader:send("horizontalSoftness", params.horizontalSoftness)
    shader:send("lumaBleed", params.lumaBleed)
    shader:send("compositeBleed", params.compositeBleed)
    shader:send("chromaDelay", params.chromaDelay)
    shader:send("ghostStrength", params.ghostStrength)
end

local function sendBeamUniforms(shader, params, w, h, physicalScale)
    shader:send("sourceSize", { w, h })
    shader:send("physicalOutputScale", physicalScale)
    shader:send("beamStrength", params.beamStrength)
    shader:send("beamStart", params.beamStart)
    shader:send("beamCompensation", params.beamCompensation)
    shader:send("beamDriveExpansion", params.beamDriveExpansion)
    shader:send("beamWidth", params.beamWidth)
    shader:send("bloomStrength", params.bloomStrength)
    shader:send("halationStrength", params.halationStrength)
    shader:send("halationRadius", params.halationRadius)
    shader:send("grilleStrength", params.grilleStrength)
    shader:send("slotMaskStrength", params.slotMaskStrength)
    shader:send("convergencePixels", params.convergencePixels)
    shader:send("curvature", params.curvature)
    shader:send("vignette", params.vignette)
    shader:send("noiseStrength", params.noiseStrength)
end

local function disableCrt(w, h, reason)
    activeMode = "nearest"
    activeParams = nil
    activeLabPreset = nil
    local scale, offsetX, offsetY = output.transformForMode("nearest", w, h)
    love.graphics.setShader()
    print("[output] CRT disabled: " .. tostring(reason))
    return scale, offsetX, offsetY
end

function output.draw(canvas)
    local w, h = dimensions()
    local scale, offsetX, offsetY = output.transformForMode(activeMode, w, h)

    love.graphics.push("all")
    love.graphics.setColor(1, 1, 1, 1)

    if activeMode == "nearest" then
        love.graphics.setShader()
        love.graphics.draw(canvas, offsetX, offsetY, 0, scale, scale)
        love.graphics.pop()
        return activeMode, scale, offsetX, offsetY
    end

    local params = activeParams
    if not params then
        params, activeLabPreset = resolvedParamsForMode(activeMode)
        activeParams = params
    end
    local signal, signalErr = buildSignalShader()
    local beam, beamErr = buildCrtShader()
    local degraded, canvasErr = ensureSignalCanvas(canvas:getWidth(), canvas:getHeight())
    if not params or not signal or not beam or not degraded then
        scale, offsetX, offsetY = disableCrt(w, h,
            signalErr or beamErr or canvasErr or "invalid CRT parameters")
        love.graphics.draw(canvas, offsetX, offsetY, 0, scale, scale)
        love.graphics.pop()
        return activeMode, scale, offsetX, offsetY
    end

    -- Stage 1: process the video signal at native source resolution. Preserve
    -- whatever canvas the host had bound so output.draw remains composable.
    local previousCanvas = love.graphics.getCanvas and love.graphics.getCanvas() or nil
    love.graphics.setCanvas(degraded)
    love.graphics.clear(0, 0, 0, 1)
    love.graphics.setColor(1, 1, 1, 1)
    sendSignalUniforms(signal, params, canvas:getWidth(), canvas:getHeight())
    love.graphics.setShader(signal)
    love.graphics.draw(canvas, 0, 0)

    if previousCanvas then love.graphics.setCanvas(previousCanvas) else love.graphics.setCanvas() end

    -- Stage 2: reconstruct the degraded signal into luminous beams on the host.
    love.graphics.setColor(1, 1, 1, 1)
    sendBeamUniforms(beam, params, degraded:getWidth(), degraded:getHeight(),
        output.physicalOutputScale(scale))
    love.graphics.setShader(beam)
    love.graphics.draw(degraded, offsetX, offsetY, 0, scale, scale)

    love.graphics.pop()
    return activeMode, scale, offsetX, offsetY
end

return output
