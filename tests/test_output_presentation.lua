local surface = require("presentation.surface")
local output = require("presentation.output")

local function near(actual, expected, epsilon, label)
    epsilon = epsilon or 1e-6
    assert(math.abs(actual - expected) <= epsilon,
        string.format("%s: expected %.8f, got %.8f", label, expected, actual))
end

local originalProfile = surface.getProfileId()
local originalMode = output.getMode()

surface.setProfile("wide")

-- Mobile nearest uses the same fractional fit as CRT so changing ASPECT cannot
-- collapse WIDE to 1x merely because the handset is only ~1.5x in logical
-- LÖVE units. Desktop keeps the historical integer-nearest contract below.
do
    local originalGetOS = love.system.getOS
    love.system.getOS = function() return "Android" end
    local scale, x, y = output.transformForMode("nearest", 856, 372)
    near(scale, 372 / 240, 1e-9, "Android wide nearest fills host height")
    near(x, (856 - 426 * scale) * 0.5, 1e-9, "Android wide nearest centering")
    near(y, 0, 1e-9, "Android wide nearest vertical fit")
    love.system.getOS = originalGetOS
end

-- Physical CRT calibration must include host DPI. This is the phone condition
-- that made 1.55 logical scale actually ~2.7 physical pixels per source pixel.
do
    local originalWindowDpi = love.window and love.window.getDPIScale
    local originalGraphicsDpi = love.graphics.getDPIScale
    if love.window then love.window.getDPIScale = function() return 1.75 end end
    love.graphics.getDPIScale = function() return 1.75 end
    near(output.physicalOutputScale(1.55), 2.7125, 1e-9,
        "CRT physical scale multiplies logical fit by host DPI")
    if love.window then love.window.getDPIScale = originalWindowDpi end
    love.graphics.getDPIScale = originalGraphicsDpi
end

-- Nearest remains the exact #199 integer contract.
do
    local scale, x, y = output.transformForMode("nearest", 1000, 600)
    assert(scale == 2, "nearest scale must remain integer")
    assert(x == 74, "nearest x offset changed")
    assert(y == 60, "nearest y offset changed")
end

-- Android's device surface deliberately permits fractional nearest output.
do
    local touch = require("presentation.touch_gamepad")
    surface.registerProfile("test_output_device", touch.deviceSurfaceSpec(2400, 1080))
    surface.setProfile("test_output_device")
    local scale, x, y = output.transformForMode("nearest", 2400, 1080)
    near(scale, 4.5, 1e-9, "device nearest fractional scale")
    near(x, 0.75, 1e-9, "device nearest centering")
    near(y, 0, 1e-9, "device nearest height fit")
    output.setMode("nearest")
    output.resize(2400, 1080)
    local rx, ry = output.hostToRender(x + 64 * scale, y + 144 * scale)
    near(rx, 64, 1e-9, "device nearest input x")
    near(ry, 144, 1e-9, "device nearest input y")
    surface.setProfile("wide")
end

-- CRT mode is the fractional-fit path.
do
    local scale, x, y = output.transformForMode("crt", 1000, 600)
    local expected = 1000 / 426
    near(scale, expected, 1e-9, "CRT fractional scale")
    near(x, 0, 1e-9, "CRT horizontal fit")
    near(y, (600 - 240 * expected) * 0.5, 1e-9, "CRT vertical centering")

    local rx = (500 - x) / scale
    local ry = (300 - y) / scale
    near(rx, 213, 1e-9, "host centre maps to render centre x")
    near(ry, 120, 1e-9, "host centre maps to render centre y")
end

-- Unlike nearest's historical >=1x rule, CRT may downscale so a large logical
-- surface is not cropped by a physically smaller host.
do
    local scale, x, y = output.transformForMode("crt", 320, 180)
    assert(scale < 1, "CRT small-host path should fit rather than crop")
    near(x, (320 - 426 * scale) * 0.5, 1e-9, "small host horizontal centering")
    near(y, 0, 1e-9, "small host vertical fit")
end

-- Shipping CRT is now a two-stage reconstruction: native-resolution YIQ signal
-- degradation followed by host-resolution drive-dependent beam reconstruction.
do
    local beamSource = output.shaderSource()
    local signalSource = output.signalShaderSource()

    assert(beamSource:find("physicalOutputScale", 1, true),
        "CRT beam calibration must consume physical output scale")
    assert(beamSource:find("beamWidth", 1, true),
        "CRT reconstruction must expose a real beam-width control")
    assert(beamSource:find("beamDriveExpansion", 1, true),
        "CRT reconstruction must expose drive-dependent beam growth")
    assert(beamSource:find("reconstructBeam", 1, true),
        "CRT output must reconstruct adjacent source rows as beams")
    assert(not beamSource:find("extern number outputScale;", 1, true),
        "CRT shader must not regress to logical-only scale calibration")

    assert(signalSource:find("rgbToYiq", 1, true),
        "CRT signal pass must separate analogue luma/chroma")
    assert(signalSource:find("signalSpread", 1, true),
        "CRT signal pass must expose source-resolution bandwidth spread")
    assert(signalSource:find("lumaBleed", 1, true),
        "CRT signal pass must expose luma bandwidth loss")
    assert(signalSource:find("compositeBleed", 1, true),
        "CRT signal pass must expose chroma bandwidth loss")
    assert(signalSource:find("chromaDelay", 1, true),
        "CRT signal pass must expose chroma timing degradation")

    local defaults = output.publicCrtDefaults()
    assert(defaults.compositeBleed > 1 and defaults.lumaBleed > 0
        and defaults.beamWidth > 0 and defaults.beamDriveExpansion > 0,
        "shipping CRT defaults should be visibly signal/beam led, not a timid overlay")

    local ok, err = output.setMode("crt")
    assert(ok, "CRT pipeline failed native compilation: " .. tostring(err))

    output.resize(1000, 600)
    local rx, ry = output.hostToRender(500, 300)
    near(rx, 213, 1e-9, "CRT hostToRender centre x")
    near(ry, 120, 1e-9, "CRT hostToRender centre y")

    if love.graphics.validateShader then
        local validBeam, beamMessage = love.graphics.validateShader(true, beamSource)
        assert(validBeam, "CRT beam shader failed GLES validation: " .. tostring(beamMessage))
        local validSignal, signalMessage = love.graphics.validateShader(true, signalSource)
        assert(validSignal, "CRT signal shader failed GLES validation: " .. tostring(signalMessage))
    end
end

-- Player parameter edits serialize into the existing output-presentation
-- preference. Deliberately extreme values remain legal: the UI is an instrument,
-- not a safe-presets dialog.
do
    local custom = output.encodeCrtParameters({
        beamStrength = 2.4,
        beamWidth = 5.5,
        beamDriveExpansion = 7.0,
        signalSpread = 10.0,
        lumaBleed = 4.0,
        compositeBleed = 7.5,
        chromaDelay = -9.0,
        bloomStrength = 5.0,
        convergencePixels = -12.0,
        curvature = -0.5,
        noiseStrength = 0.8,
    })
    assert(custom:find("^crt:"), "custom CRT settings must serialize as a CRT mode spec")
    assert(output.isKnownMode(custom), "serialized CRT parameter mode must be restorable")

    local ok, err = output.setMode(custom)
    assert(ok, "extreme player CRT parameters should still compile: " .. tostring(err))
    assert(output.getMode() == custom, "custom CRT mode spec must survive selection for persistence")

    local p = output.crtParameters(custom)
    near(p.beamWidth, 5.5, 1e-9, "extreme beam width round-trip")
    near(p.compositeBleed, 7.5, 1e-9, "extreme chroma degradation round-trip")
    near(p.chromaDelay, -9.0, 1e-9, "negative chroma delay round-trip")
    near(p.convergencePixels, -12.0, 1e-9, "negative convergence round-trip")
    near(p.curvature, -0.5, 1e-9, "reverse curvature round-trip")

    local scale = output.transformForMode(custom, 1000, 600)
    near(scale, 1000 / 426, 1e-9, "custom CRT uses ordinary CRT geometry")
end

-- Strong named experiments stay developer-only. They compile and share CRT
-- geometry, but do not leak into the ordinary player output-mode list.
do
    local publicModes = output.modeIds()
    assert(#publicModes == 2 and publicModes[1] == "nearest" and publicModes[2] == "crt",
        "CRT lab presets leaked into player-facing output mode list")

    local presetIds = output.crtLabPresetIds()
    local labModes = output.crtLabModeIds()
    assert(#presetIds == 9, "expected nine CRT lab presets")
    assert(#labModes == #presetIds, "CRT lab mode/preset count drifted")

    local expectedScale = 1000 / 426
    for i, presetId in ipairs(presetIds) do
        local modeId = labModes[i]
        assert(modeId == "crt-lab:" .. presetId, "CRT lab mode naming drifted")
        assert(output.isKnownMode(modeId), "CRT lab mode should be developer-runnable: " .. modeId)

        local scale, x, y = output.transformForMode(modeId, 1000, 600)
        near(scale, expectedScale, 1e-9, modeId .. " fractional scale")
        near(x, 0, 1e-9, modeId .. " horizontal fit")
        near(y, (600 - 240 * expectedScale) * 0.5, 1e-9,
            modeId .. " vertical centering")

        local ok, err = output.setMode(modeId)
        assert(ok, modeId .. " pipeline failed native compilation: " .. tostring(err))
    end

    local composite = output.crtLabPreset("composite")
    assert(composite and composite.compositeBleed == 0.68 and composite.lumaBleed == 0,
        "Composite must remain the unchanged chroma-led comparison anchor")

    local integrated = output.crtLabPreset("integrated")
    assert(integrated and integrated.curvature == 0 and integrated.grilleStrength == 0
        and integrated.lumaBleed > 0 and integrated.compositeBleed > 0
        and integrated.bloomStrength > 0 and integrated.beamDriveExpansion > 0,
        "integrated CRT candidate must combine flat luma/chroma/beam reconstruction")

    local maximal = output.crtLabPreset("maximal")
    assert(maximal and maximal.curvature > 0 and maximal.grilleStrength > 0
        and maximal.compositeBleed > 0 and maximal.halationStrength > 0,
        "maximal CRT lab preset must combine the major experiment families")
    maximal.curvature = 99
    assert(output.crtLabPreset("maximal").curvature ~= 99,
        "CRT lab preset accessor must not expose mutable authority")
    assert(output.crtLabPreset("not-a-preset") == nil,
        "unknown CRT lab preset should not resolve")

    local signalSource = output.signalShaderSource()
    local beamSource = output.crtLabShaderSource()
    assert(signalSource:find("lumaBleed", 1, true),
        "CRT signal shader must expose luma bandwidth integration")
    assert(signalSource:find("compositeBleed", 1, true),
        "CRT signal shader must expose chroma bandwidth integration")
    assert(beamSource:find("bloomStrength", 1, true),
        "CRT beam shader must expose neutral bright-pixel bloom")
    assert(beamSource:find("beamDriveExpansion", 1, true),
        "CRT beam shader must expose drive-dependent beam width")
    assert(beamSource:find("halationStrength", 1, true),
        "CRT beam shader must expose halation")
    assert(beamSource:find("grilleStrength", 1, true),
        "CRT beam shader must expose a mask experiment")
    assert(beamSource:find("convergencePixels", 1, true),
        "CRT beam shader must expose convergence drift")
    assert(beamSource:find("curvature", 1, true),
        "CRT beam shader must expose curved-glass geometry")
end

-- Unknown modes fail safely to the shipping nearest path.
do
    local ok = output.setMode("definitely-not-a-mode")
    assert(ok == false, "unknown output mode must be refused")
    assert(output.getMode() == "nearest", "unknown output mode must restore nearest")
end

surface.setProfile(originalProfile)
output.setMode(originalMode)
if love.graphics.getDimensions then
    output.resize(love.graphics.getDimensions())
end
print("output presentation tests passed")
