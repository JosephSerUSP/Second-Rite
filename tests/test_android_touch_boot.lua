local surface = require("presentation.surface")
local touch = require("presentation.touch_gamepad")
local settings = require("engine.user_settings")

local originalProfile = surface.getProfileId()
local originalOS = love.system.getOS
local originalDimensions = love.graphics.getDimensions
local ok, err = xpcall(function()
    love.system.getOS = function() return "Android" end
    love.graphics.getDimensions = function() return 1024, 768 end

    -- Registration must survive hidden controls, and boot must preserve an
    -- explicit ASPECT preference rather than resetting it to DEVICE.
    settings.pinForCapture({touchGamepadEnabled = false, renderSurfaceProfile = "mobile_device"})
    assert(touch.prepareAndroidSurface() == "mobile_device")
    surface.setProfile(settings.get("renderSurfaceProfile"))
    settings.pinForCapture({renderSurfaceProfile = "classic"})
    touch.prepareAndroidSurface()
    assert(settings.get("renderSurfaceProfile") == "classic", "boot overwrote ASPECT preference")
    settings.pinForCapture()
    touch.prepareAndroidSurface()
    assert(settings.get("renderSurfaceProfile") == "mobile_device", "fresh Android boot needs controls")

    -- Check the complete hit-target rectangles, not only their centres. The
    -- first candidate gave 4:3 tablets no controls at all.
    for _, host in ipairs({{2400,1080}, {1024,768}, {1280,960}, {1100,1000},
            {1080,2400}, {1000,1000}, {1050,1000}}) do
        surface.registerProfile("audit_mobile_host", touch.deviceSurfaceSpec(host[1], host[2]))
        surface.setProfile("audit_mobile_host")
        local layout = touch.layout()
        assert(#layout.buttons >= 8, "device has no usable touch controller")
        for _, button in ipairs(layout.buttons) do
            local x, y, w, h = button.x, button.y, button.w, button.h
            if button.shape == "circle" then
                x, y, w, h = x - button.r, y - button.r, button.r * 2, button.r * 2
            end
            assert(x >= 0 and y >= 0 and x + w <= layout.renderWidth
                and y + h <= layout.renderHeight, "touch target extends beyond device surface")
            assert(x + w <= layout.compositionX or x >= layout.compositionX + layout.compositionWidth
                or y + h <= layout.compositionY or y >= layout.compositionY + layout.compositionHeight,
                "touch target overlaps authored composition")
        end
    end
end, debug.traceback)
love.system.getOS = originalOS
love.graphics.getDimensions = originalDimensions
settings.reset()
surface.setProfile(originalProfile)
assert(ok, err)
print("Android touch boot and complete target geometry tests passed")
