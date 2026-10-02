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
    near(x, 0, 1e-9, "small host horizontal fit")
    assert(y >= 0, "small host vertical offset should remain on-screen")
end

-- Native shader construction is part of the spike: if the current LÖVE backend
-- rejects the source, the unit suite should expose it immediately.
do
    local ok, err = output.setMode("crt")
    assert(ok, "CRT shader failed native compilation: " .. tostring(err))

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
print("output presentation tests passed")
