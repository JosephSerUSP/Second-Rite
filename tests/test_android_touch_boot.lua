local surface = require("presentation.surface")
local touch = require("presentation.touch_gamepad")
local settings = require("engine.user_settings")

local originalProfile = surface.getProfileId()
local originalOS = love.system.getOS
local originalDimensions = love.graphics.getDimensions
local ok, err = xpcall(function()
    love.system.getOS = function() return "Android" end
    love.graphics.getDimensions = function() return 1024, 768 end

    -- Registration survives hidden controls. Unsafe saved ASPECT choices are
    -- repaired only while touch is enabled: a phone must never boot into a
    -- surface whose controller layout is empty.
    settings.pinForCapture({touchGamepadEnabled = false, renderSurfaceProfile = "mobile_device"})
    assert(touch.prepareAndroidSurface() == "mobile_device")
    surface.setProfile(settings.get("renderSurfaceProfile"))
    settings.pinForCapture({touchGamepadEnabled = false, renderSurfaceProfile = "classic"})
    touch.prepareAndroidSurface()
    assert(settings.get("renderSurfaceProfile") == "classic",
        "hidden controller should preserve an explicit ASPECT preference")
    settings.pinForCapture({touchGamepadEnabled = true, renderSurfaceProfile = "classic"})
    touch.prepareAndroidSurface()
    assert(settings.get("renderSurfaceProfile") == "mobile_device",
        "touch-enabled boot must repair an unsafe saved ASPECT")
    settings.pinForCapture()
    touch.prepareAndroidSurface()
    assert(settings.get("renderSurfaceProfile") == "mobile_device", "fresh Android boot needs controls")

    -- Android can settle into a wider immersive content area after love.load.
    -- DEVICE must follow the later host instead of freezing the boot sample.
    love.graphics.getDimensions = function() return 704, 372 end
    touch.prepareAndroidSurface()
    local bootProfile = surface.getProfile("mobile_device")
    assert(bootProfile.renderWidth == 454 and bootProfile.renderHeight == 240,
        "boot sample pins the expected narrow intermediate DEVICE")
    local changed = touch.refreshAndroidSurface(856, 372)
    local settledProfile = surface.getProfile("mobile_device")
    assert(changed, "settled Android host must refresh DEVICE")
    assert(settledProfile.renderWidth == 552 and settledProfile.renderHeight == 240,
        "settled DEVICE must match the final handset aspect")
    assert(settledProfile.compositionOriginX == 148,
        "settled DEVICE recentres the canonical composition")
    assert(not touch.refreshAndroidSurface(856, 372),
        "identical resize must not churn the DEVICE profile")

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
