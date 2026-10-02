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

-- Nearest remains the exact #199 integer contract.
do
    local scale, x, y = output.transformForMode("nearest", 1000, 600)
    assert(scale == 2, "nearest scale must remain integer")
    assert(x == 74, "nearest x offset changed")
    assert(y == 60, "nearest y offset changed")
end

-- Android's device surface deliberately permits fractional nearest output.
-- The output seam must delegate that geometry too, rather than imposing the
-- desktop integer policy a second time after the branches are combined.
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

-- CRT mode is the experimental fractional fit path.
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

-- Unlike nearest's historical >=1x rule, experimental CRT may downscale so a
-- large logical surface is not cropped by a physically smaller host.
do
    local scale, x, y = output.transformForMode("crt", 320, 180)
    assert(scale < 1, "CRT small-host path should fit rather than crop")
    near(x, (320 - 426 * scale) * 0.5, 1e-9, "small host horizontal centering")
    near(y, 0, 1e-9, "small host vertical fit")
end

-- Native shader construction is part of the spike: if the current LÖVE backend
-- rejects the source, the unit suite should expose it immediately.
do
    local ok, err = output.setMode("crt")
    assert(ok, "CRT shader failed native compilation: " .. tostring(err))

    -- Exercise the actual inverse seam used by touch, not only the formula.
    output.resize(1000, 600)
    local rx, ry = output.hostToRender(500, 300)
    near(rx, 213, 1e-9, "CRT hostToRender centre x")
    near(ry, 120, 1e-9, "CRT hostToRender centre y")

    -- When this API is available, also validate the exact same source as GLES.
    -- Desktop GLES validation is evidence, not a substitute for Android.
    if love.graphics.validateShader then
        local valid, message = love.graphics.validateShader(true, output.shaderSource())
        assert(valid, "CRT shader failed GLES validation: " .. tostring(message))
    end
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
