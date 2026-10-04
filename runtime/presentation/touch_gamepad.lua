local surface = require("presentation.surface")
local output = require("presentation.output")
local user_settings = require("engine.user_settings")
local virtual_input = require("engine.virtual_input")
local player_controller = require("engine.player_controller")

local touch_gamepad = {}

local SETTING = "touchGamepadEnabled"
local DEVICE_PROFILE = "mobile_device"
local MIN_CONTROL_GUTTER = 64
local MIN_CONTROL_ROWS = 90
local RESCUE_DOUBLE_TAP_SECONDS = 0.35
local RESCUE_DOUBLE_TAP_RADIUS = 48
local safeInsets = { left = 0, top = 0, right = 0, bottom = 0 }
local hostInstalled = false
local inputContext = nil
local decorated = setmetatable({}, { __mode = "k" })
local authoredSurfaceOptions = setmetatable({}, { __mode = "k" })
local rescueTap = { time = nil, x = nil, y = nil }
local rescueTouches = {}

local function isAndroid()
    if not (love and love.system and love.system.getOS) then return false end
    local ok, value = pcall(love.system.getOS)
    return ok and value == "Android"
end

function touch_gamepad.defaultEnabled()
    return isAndroid()
end

-- A touch-controlled surface must reserve the COMPLETE controller outside the
-- canonical 256x240 composition. Merely being a valid render surface is not
-- enough: Classic has no gutter and 4:3 has only 32 px per side, so selecting
-- either while touch is enabled would strand a phone user without buttons.
local function profileSupportsControls(id, hostWidth, hostHeight)
    local profile = surface.getProfile(id)
    if not profile then return false end
    local cw, ch = surface.compositionSize()
    local rw, rh = profile.renderWidth, profile.renderHeight
    local ox, oy = profile.compositionOriginX, profile.compositionOriginY
    local landscape = rw >= rh
    if hostWidth and hostHeight and landscape ~= (hostWidth >= hostHeight) then
        return false
    end
    if landscape then
        local leftW = ox
        local rightW = rw - (ox + cw)
        return leftW >= 40 and rightW >= 40
    end
    return rh - (oy + ch) >= MIN_CONTROL_ROWS
end

function touch_gamepad.profileSupportsControls(id, hostWidth, hostHeight)
    return profileSupportsControls(id, hostWidth, hostHeight)
end

-- Representative fixed profiles remain useful for desktop previews/tests, but
-- Android itself uses a device-matched logical surface. The canonical 256x240
-- composition never changes:
--   * host wider than classic -> add columns symmetrically at the sides;
--   * host tighter than classic -> add rows only BELOW the composition.
-- Controls inhabit only that added space.
if not surface.getProfile("mobile_landscape") then
    surface.registerProfile("mobile_landscape", {
        renderWidth = 426, renderHeight = 240,
        compositionOriginX = 85, compositionOriginY = 0,
    })
end
if not surface.getProfile("mobile_portrait") then
    surface.registerProfile("mobile_portrait", {
        renderWidth = 256, renderHeight = 426,
        compositionOriginX = 0, compositionOriginY = 0,
    })
end

function touch_gamepad.deviceSurfaceSpec(hostWidth, hostHeight)
    hostWidth = tonumber(hostWidth) or 0
    hostHeight = tonumber(hostHeight) or 0
    if hostWidth <= 0 or hostHeight <= 0 then
        error("mobile device surface requires positive host dimensions", 2)
    end

    local cw, ch = surface.compositionSize()
    local hostAspect = hostWidth / hostHeight
    local classicAspect = cw / ch
    local rw, rh, ox, oy

    if hostAspect >= classicAspect then
        -- A tablet can have less spare width than a phone. Reserve the whole
        -- three-cell D-pad before fitting the host; otherwise the controller
        -- disappears or its targets extend into the authored composition.
        rw = math.max(cw + 2 * MIN_CONTROL_GUTTER,
            math.floor(ch * hostAspect + 0.5))
        rh = math.max(ch, math.floor(rw / hostAspect + 0.5))
        ox = math.floor((rw - cw) / 2)
        oy = 0
    else
        rw = cw
        rh = math.max(ch + MIN_CONTROL_ROWS, math.floor(cw / hostAspect + 0.5))
        ox = 0
        oy = 0
    end

    return {
        renderWidth = rw,
        renderHeight = rh,
        compositionOriginX = ox,
        compositionOriginY = oy,
        fractionalOutputScale = true,
    }
end

local function sameDeviceSpec(profile, spec)
    return profile
        and profile.renderWidth == spec.renderWidth
        and profile.renderHeight == spec.renderHeight
        and profile.compositionOriginX == spec.compositionOriginX
        and profile.compositionOriginY == spec.compositionOriginY
        and profile.fractionalOutputScale == spec.fractionalOutputScale
end

function touch_gamepad.configureDeviceSurface(hostWidth, hostHeight)
    local spec = touch_gamepad.deviceSurfaceSpec(hostWidth, hostHeight)
    local previous = surface.getProfile(DEVICE_PROFILE)
    local changed = not sameDeviceSpec(previous, spec)
    if changed then
        surface.registerProfile(DEVICE_PROFILE, spec)
    end
    return DEVICE_PROFILE, changed, spec
end

-- Android can report an initial content size during love.load and then expand
-- once immersive/fullscreen system chrome settles. Keep DEVICE tied to the
-- ACTUAL host geometry rather than freezing whichever dimensions happened to
-- exist during boot.
function touch_gamepad.refreshAndroidSurface(hostWidth, hostHeight)
    if not isAndroid() then return false end
    local _, changed = touch_gamepad.configureDeviceSurface(hostWidth, hostHeight)
    return changed
end

-- Register DEVICE during boot so a saved profile resolves immediately. Later
-- native resize events keep the profile synchronized with the settled host.
function touch_gamepad.prepareAndroidSurface()
    if not isAndroid() then return nil end
    local w, h = love.graphics.getDimensions()
    local profile = touch_gamepad.configureDeviceSurface(w, h)
    -- Registration is independent of visibility: a saved DEVICE choice must
    -- still resolve after the user hides the controller. When touch IS enabled,
    -- however, preserving an unsafe explicit choice is a lockout bug: Classic
    -- and 4:3 cannot fit the complete controller. Repair old/saved choices to
    -- DEVICE before main.lua creates the game canvas.
    local current = user_settings.get("renderSurfaceProfile", nil)
    if touch_gamepad.isEnabled()
        and (current == nil or not profileSupportsControls(current, w, h)) then
        user_settings.set("renderSurfaceProfile", profile)
    end
    return profile
end

function touch_gamepad.isEnabled()
    return user_settings.get(SETTING, touch_gamepad.defaultEnabled()) and true or false
end

function touch_gamepad.setEnabled(value)
    value = value and true or false
    user_settings.set(SETTING, value)
    if not value then touch_gamepad.clearTouches() end
    if value then
        rescueTap.time, rescueTap.x, rescueTap.y = nil, nil, nil
    end
    return value
end

local function rescueNow()
    if love and love.timer and love.timer.getTime then return love.timer.getTime() end
    return os.clock()
end

-- Hidden touch controls must never be a one-way door on a touch-only device.
-- While the virtual gamepad is OFF, Android reserves touch input for one simple
-- escape hatch: two nearby taps in quick succession anywhere on the host.
-- Normal gameplay never sees this recognizer because it is inactive while the
-- controller is visible.
function touch_gamepad.rescueTap(id, x, y, now)
    if not isAndroid() or touch_gamepad.isEnabled() then return false end
    now = tonumber(now) or rescueNow()
    x, y = tonumber(x) or 0, tonumber(y) or 0
    rescueTouches[id] = true

    local previousTime = rescueTap.time
    local previousX, previousY = rescueTap.x, rescueTap.y
    local closeInTime = previousTime
        and now >= previousTime and (now - previousTime) <= RESCUE_DOUBLE_TAP_SECONDS
    local closeInSpace = false
    if closeInTime and previousX and previousY then
        local dx, dy = x - previousX, y - previousY
        closeInSpace = (dx * dx + dy * dy) <= RESCUE_DOUBLE_TAP_RADIUS * RESCUE_DOUBLE_TAP_RADIUS
    end

    if closeInTime and closeInSpace then
        touch_gamepad.setEnabled(true)
        local ok, scene_host = pcall(require, "engine.scene_host")
        local state = ok and scene_host.getCurrentState and scene_host.getCurrentState() or nil
        if state and state.v then state.v.touchGamepad = true end
        return true
    end

    rescueTap.time, rescueTap.x, rescueTap.y = now, x, y
    return true
end

-- Insets are logical render-surface pixels. Native platform glue can populate
-- these later without reflowing the canonical 256x240 game UI.
function touch_gamepad.setSafeInsets(left, top, right, bottom)
    safeInsets.left = math.max(0, tonumber(left) or 0)
    safeInsets.top = math.max(0, tonumber(top) or 0)
    safeInsets.right = math.max(0, tonumber(right) or 0)
    safeInsets.bottom = math.max(0, tonumber(bottom) or 0)
end

local function rectButton(button, x, y, w, h, glyph)
    return { button = button, shape = "rect", x = x, y = y, w = w, h = h, glyph = glyph }
end

local function circleButton(button, x, y, r, glyph)
    return { button = button, shape = "circle", x = x, y = y, r = r, glyph = glyph }
end

local function clamp(value, lo, hi)
    return math.max(lo, math.min(hi, value))
end

local function landscapeLayout(rw, rh, ox, oy, cw, ch)
    local buttons = {}
    local leftW = ox
    local rightX = ox + cw
    local rightW = rw - rightX
    if leftW < 40 or rightW < 40 then return buttons end

    local cell = clamp(math.floor(math.min(leftW / 3, rh / 8)), 18, 28)
    local dcx = safeInsets.left + (leftW - safeInsets.left) * 0.5
    local dcy = clamp(rh * 0.60, safeInsets.top + cell * 1.6,
        rh - safeInsets.bottom - cell * 1.6)
    buttons[#buttons + 1] = rectButton("UP", dcx - cell / 2, dcy - cell * 1.5, cell, cell, "up")
    buttons[#buttons + 1] = rectButton("DOWN", dcx - cell / 2, dcy + cell * 0.5, cell, cell, "down")
    buttons[#buttons + 1] = rectButton("LEFT", dcx - cell * 1.5, dcy - cell / 2, cell, cell, "left")
    buttons[#buttons + 1] = rectButton("RIGHT", dcx + cell * 0.5, dcy - cell / 2, cell, cell, "right")

    local rr = clamp(math.floor(rightW * 0.18), 12, 17)
    local acy = clamp(rh * 0.58, safeInsets.top + rr, rh - safeInsets.bottom - rr)
    local bcy = clamp(rh * 0.70, safeInsets.top + rr, rh - safeInsets.bottom - rr)
    buttons[#buttons + 1] = circleButton("A", rightX + rightW * 0.68, acy, rr, "A")
    buttons[#buttons + 1] = circleButton("B", rightX + rightW * 0.34, bcy, rr, "B")

    local utilityW, utilityH = math.min(30, leftW - 10), 12
    buttons[#buttons + 1] = rectButton("L", 5 + safeInsets.left, 6 + safeInsets.top, utilityW, utilityH, "L")
    buttons[#buttons + 1] = rectButton("R", rw - safeInsets.right - utilityW - 5,
        6 + safeInsets.top, utilityW, utilityH, "R")
    buttons[#buttons + 1] = rectButton("SELECT", dcx - utilityW / 2,
        rh - safeInsets.bottom - utilityH - 5, utilityW, utilityH, "SEL")
    buttons[#buttons + 1] = rectButton("START", rightX + (rightW - utilityW) / 2,
        rh - safeInsets.bottom - utilityH - 5, utilityW, utilityH, "START")
    return buttons
end

local function portraitLayout(rw, rh, ox, oy, cw, ch)
    local buttons = {}
    local lowerY = oy + ch
    local lowerH = rh - lowerY
    if lowerH < 90 then return buttons end

    local usableTop = lowerY + 8
    local usableBottom = rh - safeInsets.bottom - 8
    local dcy = usableTop + (usableBottom - usableTop) * 0.43
    local dcx = safeInsets.left + (rw - safeInsets.left - safeInsets.right) * 0.25
    local cell = clamp(math.floor(math.min(rw / 10, lowerH / 5)), 24, 32)
    buttons[#buttons + 1] = rectButton("UP", dcx - cell / 2, dcy - cell * 1.5, cell, cell, "up")
    buttons[#buttons + 1] = rectButton("DOWN", dcx - cell / 2, dcy + cell * 0.5, cell, cell, "down")
    buttons[#buttons + 1] = rectButton("LEFT", dcx - cell * 1.5, dcy - cell / 2, cell, cell, "left")
    buttons[#buttons + 1] = rectButton("RIGHT", dcx + cell * 0.5, dcy - cell / 2, cell, cell, "right")

    local rr = clamp(math.floor(rw / 13), 18, 22)
    buttons[#buttons + 1] = circleButton("A", rw * 0.78, dcy - 4, rr, "A")
    buttons[#buttons + 1] = circleButton("B", rw * 0.65, dcy + rr * 1.35, rr, "B")

    local uw, uh = 46, 18
    local utilityY = math.min(usableBottom - uh, dcy + cell * 2.0)
    buttons[#buttons + 1] = rectButton("SELECT", rw * 0.40 - uw / 2, utilityY, uw, uh, "SEL")
    buttons[#buttons + 1] = rectButton("START", rw * 0.60 - uw / 2, utilityY, uw, uh, "START")
    buttons[#buttons + 1] = rectButton("L", safeInsets.left + 8, usableTop, 40, 18, "L")
    buttons[#buttons + 1] = rectButton("R", rw - safeInsets.right - 48, usableTop, 40, 18, "R")
    return buttons
end

function touch_gamepad.layout()
    local rw, rh = surface.renderSize()
    local ox, oy = surface.compositionOrigin()
    local cw, ch = surface.compositionSize()
    local orientation = rw >= rh and "landscape" or "portrait"
    local buttons = orientation == "landscape"
        and landscapeLayout(rw, rh, ox, oy, cw, ch)
        or portraitLayout(rw, rh, ox, oy, cw, ch)
    return {
        orientation = orientation,
        renderWidth = rw, renderHeight = rh,
        compositionX = ox, compositionY = oy,
        compositionWidth = cw, compositionHeight = ch,
        buttons = buttons,
    }
end

local function inside(button, x, y)
    if button.shape == "circle" then
        local dx, dy = x - button.x, y - button.y
        return dx * dx + dy * dy <= button.r * button.r
    end
    return x >= button.x and y >= button.y
        and x < button.x + button.w and y < button.y + button.h
end

function touch_gamepad.hitTest(renderX, renderY)
    if not touch_gamepad.isEnabled() then return nil end
    if surface.isInsideComposition(renderX, renderY) then return nil end
    for _, button in ipairs(touch_gamepad.layout().buttons) do
        if inside(button, renderX, renderY) then return button.button end
    end
    return nil
end

local function hostToRender(x, y)
    -- Inverse input mapping must consume the exact transform used by the
    -- final output stage. CRT may be fractional while nearest stays integer.
    return output.hostToRender(x, y)
end

function touch_gamepad.touchpressed(id, x, y)
    if not touch_gamepad.isEnabled() then
        return touch_gamepad.rescueTap(id, x, y)
    end
    local rx, ry = hostToRender(x, y)
    local button = touch_gamepad.hitTest(rx, ry)
    if not button then return false end
    if not virtual_input.press(id, button) then return false end
    if inputContext then player_controller.press(button, inputContext) end
    return true
end

function touch_gamepad.touchmoved(id, x, y)
    if rescueTouches[id] then return true end
    if not touch_gamepad.isEnabled() then return isAndroid() end
    local rx, ry = hostToRender(x, y)
    local previous = virtual_input.touchButton(id)
    local button = touch_gamepad.hitTest(rx, ry)
    local changed = virtual_input.move(id, button)
    if not changed then return false end
    if previous and previous ~= button and not virtual_input.isDown(previous) then
        player_controller.release(previous)
    end
    if button and button ~= previous and inputContext then
        player_controller.press(button, inputContext)
    end
    return true
end

function touch_gamepad.touchreleased(id)
    if rescueTouches[id] then
        rescueTouches[id] = nil
        return true
    end
    local button = virtual_input.touchButton(id)
    local released = virtual_input.release(id)
    if button and released and not virtual_input.isDown(button) then
        player_controller.release(button)
    end
    return released
end

function touch_gamepad.clearTouches()
    local buttons = virtual_input.downButtons()
    virtual_input.clear()
    for _, button in ipairs(buttons) do player_controller.release(button) end
end

local function findScene(ctx, id)
    local scenes = ctx and ctx.loader and ctx.loader.scenes
    if not scenes then return nil end
    for _, scene in ipairs(scenes) do
        if tostring(scene.id) == tostring(id) or scene.name == id then return scene end
    end
    return nil
end

local function appendDeviceAspect(loader)
    if not (loader and isAndroid()) then return end
    local renderSurfaces = loader.engine and loader.engine.renderSurfaces
    local options = renderSurfaces and renderSurfaces.options
    if type(options) ~= "table" or not surface.getProfile(DEVICE_PROFILE) then return end

    -- Keep an immutable copy of the Project-authored order. decorateOptions is
    -- called repeatedly, so filtering the already-filtered table would slowly
    -- erase choices and make toggling the controller non-reversible.
    local authored = authoredSurfaceOptions[loader]
    if not authored then
        authored = {}
        for _, id in ipairs(options) do
            if id ~= DEVICE_PROFILE then authored[#authored + 1] = id end
        end
        authoredSurfaceOptions[loader] = authored
    end

    local w, h = love.graphics.getDimensions()
    for i = #options, 1, -1 do options[i] = nil end
    for _, id in ipairs(authored) do
        if not touch_gamepad.isEnabled() or profileSupportsControls(id, w, h) then
            options[#options + 1] = id
        end
    end
    -- DEVICE is the host-matched safe choice in either orientation.
    options[#options + 1] = DEVICE_PROFILE
end

-- #1307 integration: Options remains authored campaign UI, while the virtual
-- gamepad and handset-sized DEVICE surface are host/platform features. Extend
-- the in-memory loader only; portable Project data remains device-independent.
-- source keeps the old scenes-only unit seam working.
function touch_gamepad.decorateOptions(source)
    local loader = type(source) == "table" and source.scenes and source or nil
    local scenes = loader and loader.scenes or source
    if loader then appendDeviceAspect(loader) end

    for _, scene in ipairs(scenes or {}) do
        local commands = scene.config and scene.config.optionsCommands
        if type(commands) == "table" and not decorated[scene] then
            local existingIndex = nil
            for i, command in ipairs(commands) do
                if command.id == "touch_gamepad" then existingIndex = i; break end
            end
            local originalCount = #commands
            if not existingIndex then
                commands[#commands + 1] = {
                    id = "touch_gamepad",
                    name = "VIRTUAL GAMEPAD",
                    help = "Show or hide the touch controller. On Android, double-tap anywhere to restore it when hidden.",
                }
            end
            decorated[scene] = {
                originalCount = originalCount,
                index = existingIndex or #commands,
            }

            for _, window in ipairs(scene.windows or {}) do
                for _, item in ipairs(window.content or {}) do
                    if item.listId == "config:optionsCommands" then
                        local old = item.formatRight
                        local inner = "''"
                        if type(old) == "string" and old:sub(1, 1) == "{" and old:sub(-1) == "}" then
                            inner = old:sub(2, -2)
                        end
                        if not tostring(old):find("touch_gamepad", 1, true) then
                            item.formatRight = "{id == 'touch_gamepad' and (sceneState.touchGamepad and 'ON' or 'OFF') or id == 'aspect' and sceneState.aspect == 'mobile_device' and 'DEVICE' or (" .. inner .. ")}";
                        end
                    end
                end
            end
            return scene
        end
    end
    return nil
end

local function installHost()
    if hostInstalled then return end
    local scene_host = require("engine.scene_host")
    local originalRunHook = scene_host.runHook
    local originalUpdate = scene_host.update
    scene_host.runHook = function(hookName, ctx)
        if ctx and ctx.loader then touch_gamepad.decorateOptions(ctx.loader) end
        local state = scene_host.getCurrentState()
        local scene = state and findScene(ctx, state.id) or nil
        local meta = scene and decorated[scene] or nil
        if meta and state then
            local idx = tonumber(state.v.idx) or 1
            if hookName == "on_down" and idx == meta.originalCount
                and meta.index > meta.originalCount then
                state.v.idx = meta.index
                return true
            elseif hookName == "on_up" and idx == meta.index
                and meta.index > meta.originalCount then
                state.v.idx = meta.originalCount
                return true
            elseif hookName == "on_select" and idx == meta.index then
                state.v.touchGamepad = touch_gamepad.setEnabled(not touch_gamepad.isEnabled())
                return true
            end
        end

        local handled = originalRunHook(hookName, ctx)
        if meta and state and hookName == "on_enter" then
            state.v.touchGamepad = touch_gamepad.isEnabled()
        end
        return handled
    end

    scene_host.update = function(dt, ctx)
        inputContext = ctx
        if ctx and ctx.loader then touch_gamepad.decorateOptions(ctx.loader) end
        if not touch_gamepad.isEnabled() and virtual_input.activeTouchCount() > 0 then
            touch_gamepad.clearTouches()
        end
        return originalUpdate(dt, ctx)
    end

    hostInstalled = true
end

local function drawArrow(direction, x, y, size)
    local s = size
    if direction == "up" then
        love.graphics.polygon("fill", x, y - s, x - s, y + s, x + s, y + s)
    elseif direction == "down" then
        love.graphics.polygon("fill", x, y + s, x - s, y - s, x + s, y - s)
    elseif direction == "left" then
        love.graphics.polygon("fill", x - s, y, x + s, y - s, x + s, y + s)
    else
        love.graphics.polygon("fill", x + s, y, x - s, y - s, x - s, y + s)
    end
end

local function drawButton(button)
    local down = virtual_input.isDown(button.button)
    if down then
        -- Deliberately invert the control while held. A subtle alpha change was
        -- effectively invisible on a phone; this must read as tactile feedback.
        love.graphics.setColor(0.92, 0.92, 0.96, 0.82)
    else
        love.graphics.setColor(0.08, 0.08, 0.10, 0.42)
    end
    if button.shape == "circle" then
        love.graphics.circle("fill", button.x, button.y, button.r)
        love.graphics.setColor(1, 1, 1, down and 1 or 0.75)
        love.graphics.circle("line", button.x, button.y, button.r)
    else
        love.graphics.rectangle("fill", button.x, button.y, button.w, button.h, 2, 2)
        love.graphics.setColor(1, 1, 1, down and 1 or 0.70)
        love.graphics.rectangle("line", button.x, button.y, button.w, button.h, 2, 2)
    end

    if down then
        love.graphics.setColor(0.06, 0.06, 0.08, 1)
    else
        love.graphics.setColor(1, 1, 1, 0.90)
    end
    if button.glyph == "up" or button.glyph == "down"
        or button.glyph == "left" or button.glyph == "right" then
        local cx = button.x + button.w / 2
        local cy = button.y + button.h / 2
        drawArrow(button.glyph, cx, cy,
            math.max(3, math.floor(math.min(button.w, button.h) / 5)))
    else
        local text = tostring(button.glyph or button.button)
        local x, y, w
        if button.shape == "circle" then
            x, y, w = button.x - button.r, button.y - 6, button.r * 2
        else
            x, y, w = button.x, button.y + math.floor((button.h - 10) / 2), button.w
        end
        love.graphics.printf(text, x, y, w, "center")
    end
end

function touch_gamepad.draw()
    installHost()
    if not touch_gamepad.isEnabled() then return end
    local layout = touch_gamepad.layout()
    if #layout.buttons == 0 then return end

    love.graphics.push("all")
    love.graphics.setColor(0, 0, 0, 0.12)
    if layout.orientation == "landscape" then
        local ox = layout.compositionX
        local rightX = ox + layout.compositionWidth
        if ox > 0 then love.graphics.rectangle("fill", 0, 0, ox, layout.renderHeight) end
        if rightX < layout.renderWidth then
            love.graphics.rectangle("fill", rightX, 0,
                layout.renderWidth - rightX, layout.renderHeight)
        end
    else
        local lowerY = layout.compositionY + layout.compositionHeight
        if lowerY < layout.renderHeight then
            love.graphics.rectangle("fill", 0, lowerY,
                layout.renderWidth, layout.renderHeight - lowerY)
        end
    end
    for _, button in ipairs(layout.buttons) do drawButton(button) end
    love.graphics.pop()
end

-- LÖVE 0.10+ touch callbacks report x/y in host-window pixels. Convert those
-- through #199's output transform before controller hit testing.
local previousPressed = love and love.touchpressed
local previousMoved = love and love.touchmoved
local previousReleased = love and love.touchreleased
local previousFocus = love and love.focus
if love then
    love.touchpressed = function(id, x, y, dx, dy, pressure)
        if touch_gamepad.touchpressed(id, x, y) then return end
        if previousPressed then return previousPressed(id, x, y, dx, dy, pressure) end
    end
    love.touchmoved = function(id, x, y, dx, dy, pressure)
        local consumed = touch_gamepad.touchmoved(id, x, y)
        if consumed then return end
        if previousMoved then return previousMoved(id, x, y, dx, dy, pressure) end
    end
    love.touchreleased = function(id, x, y, dx, dy, pressure)
        local consumed = touch_gamepad.touchreleased(id)
        if consumed then return end
        if previousReleased then return previousReleased(id, x, y, dx, dy, pressure) end
    end
    love.focus = function(focused)
        if not focused then touch_gamepad.clearTouches() end
        if previousFocus then return previousFocus(focused) end
    end
end

return touch_gamepad
