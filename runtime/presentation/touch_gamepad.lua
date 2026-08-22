local surface = require("presentation.surface")
local user_settings = require("engine.user_settings")
local input_map = require("engine.input_map")
local virtual_input = require("engine.virtual_input")

local touch_gamepad = {}

local SETTING = "touchGamepadEnabled"
local safeInsets = { left = 0, top = 0, right = 0, bottom = 0 }
local hostInstalled = false
local decorated = setmetatable({}, { __mode = "k" })

local function isAndroid()
    if not (love and love.system and love.system.getOS) then return false end
    local ok, value = pcall(love.system.getOS)
    return ok and value == "Android"
end

function touch_gamepad.defaultEnabled()
    return isAndroid()
end

-- Representative mobile surfaces. Layout is derived from surface geometry, so
-- future device-sized profiles do not require new input semantics.
if not surface.getProfile("mobile_landscape") then
    surface.registerProfile("mobile_landscape", {
        renderWidth = 426, renderHeight = 240,
        compositionOriginX = 85, compositionOriginY = 0,
    })
end
if not surface.getProfile("mobile_portrait") then
    surface.registerProfile("mobile_portrait", {
        renderWidth = 256, renderHeight = 426,
        compositionOriginX = 0, compositionOriginY = 24,
    })
end

-- main.lua asks user_settings for renderSurfaceProfile before constructing its
-- canvas. Seed an Android-friendly surface only when the player has no stored
-- choice and has not explicitly disabled the virtual gamepad. A saved user
-- override always wins.
if isAndroid()
    and user_settings.get(SETTING, nil) ~= false
    and user_settings.get("renderSurfaceProfile", nil) == nil then
    local w, h = 0, 0
    if love and love.graphics and love.graphics.getDimensions then
        w, h = love.graphics.getDimensions()
    end
    user_settings.set("renderSurfaceProfile", (h > w) and "mobile_portrait" or "mobile_landscape")
end

function touch_gamepad.isEnabled()
    return user_settings.get(SETTING, touch_gamepad.defaultEnabled()) and true or false
end

function touch_gamepad.setEnabled(value)
    value = value and true or false
    user_settings.set(SETTING, value)
    if not value then virtual_input.clear() end
    return value
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
    local cell = clamp(math.floor(math.min(rw / 10, lowerH / 5)), 20, 28)
    buttons[#buttons + 1] = rectButton("UP", dcx - cell / 2, dcy - cell * 1.5, cell, cell, "up")
    buttons[#buttons + 1] = rectButton("DOWN", dcx - cell / 2, dcy + cell * 0.5, cell, cell, "down")
    buttons[#buttons + 1] = rectButton("LEFT", dcx - cell * 1.5, dcy - cell / 2, cell, cell, "left")
    buttons[#buttons + 1] = rectButton("RIGHT", dcx + cell * 0.5, dcy - cell / 2, cell, cell, "right")

    local rr = clamp(math.floor(rw / 18), 13, 18)
    buttons[#buttons + 1] = circleButton("A", rw * 0.78, dcy - 4, rr, "A")
    buttons[#buttons + 1] = circleButton("B", rw * 0.65, dcy + rr * 1.35, rr, "B")

    local uw, uh = 34, 12
    local utilityY = math.min(usableBottom - uh, dcy + cell * 2.0)
    buttons[#buttons + 1] = rectButton("SELECT", rw * 0.40 - uw / 2, utilityY, uw, uh, "SEL")
    buttons[#buttons + 1] = rectButton("START", rw * 0.58 - uw / 2, utilityY, uw, uh, "START")
    buttons[#buttons + 1] = rectButton("L", safeInsets.left + 8, usableTop, 30, 12, "L")
    buttons[#buttons + 1] = rectButton("R", rw - safeInsets.right - 38, usableTop, 30, 12, "R")
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
    local hostW, hostH = love.graphics.getDimensions()
    local scale, offsetX, offsetY = surface.outputTransform(hostW, hostH)
    return surface.hostToRender(x, y, scale, offsetX, offsetY)
end

function touch_gamepad.touchpressed(id, x, y)
    if not touch_gamepad.isEnabled() then return false end
    local rx, ry = hostToRender(x, y)
    local button = touch_gamepad.hitTest(rx, ry)
    if not button then return false end
    virtual_input.press(id, button)
    return true
end

function touch_gamepad.touchmoved(id, x, y)
    if not touch_gamepad.isEnabled() then return false end
    local rx, ry = hostToRender(x, y)
    return virtual_input.move(id, touch_gamepad.hitTest(rx, ry))
end

function touch_gamepad.touchreleased(id)
    return virtual_input.release(id)
end

function touch_gamepad.clearTouches()
    virtual_input.clear()
end

local function findScene(ctx, id)
    local scenes = ctx and ctx.loader and ctx.loader.scenes
    if not scenes then return nil end
    for _, scene in ipairs(scenes) do
        if tostring(scene.id) == tostring(id) or scene.name == id then return scene end
    end
    return nil
end

-- The Options scene is authored campaign UI, while the virtual gamepad is a
-- host/platform feature. Add one host-owned row in memory rather than saving a
-- device preference into data/scenes.json.
function touch_gamepad.decorateOptions(scenes)
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
                    help = "Show or hide the touch controller. Defaults on for Android.",
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
                            item.formatRight = "{id == 'touch_gamepad' and (v.touchGamepad and 'ON' or 'OFF') or (" .. inner .. ")}"
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
    -- Captured after love.load has installed the real keyboard callback. Modern
    -- scenes consume semantic hooks directly below. The callback is only a
    -- compatibility bridge for legacy host-owned input (notably dialogue), and
    -- receives the player's CURRENT binding rather than a hardcoded W/Z/etc.
    local hostKeyPressed = love and love.keypressed

    scene_host.runHook = function(hookName, ctx)
        if ctx and ctx.loader then touch_gamepad.decorateOptions(ctx.loader.scenes) end
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

    local function dispatchLogicalButton(button, ctx)
        local hook = input_map.BUTTON_TO_HOOK[button]
        if hook and scene_host.runHook(hook, ctx) then return true end

        -- Dialogue/event input is still intentionally owned by main.lua rather
        -- than scene hooks. Re-enter that NORMAL host path only when the
        -- semantic scene path declines the action. No touch layout knows a
        -- keyboard literal: the compatibility key is resolved from the current
        -- rebindable map at dispatch time. Once dialogue becomes hook-driven,
        -- this bridge naturally stops being used for it.
        local bindings = input_map.getBindings()
        local key = bindings and bindings[button]
        if key and hostKeyPressed then
            hostKeyPressed(key, nil, false)
            return true
        end
        return false
    end

    scene_host.update = function(dt, ctx)
        if ctx and ctx.loader then touch_gamepad.decorateOptions(ctx.loader.scenes) end
        if touch_gamepad.isEnabled() then
            local config = require("engine.config")
            local ui = config.ui or {}
            virtual_input.update(dt, function(button)
                dispatchLogicalButton(button, ctx)
            end, ui.autoRepeatInitial or 0.30, ui.autoRepeatInterval or 0.06)
        else
            virtual_input.clear()
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
    love.graphics.setColor(0.08, 0.08, 0.10, down and 0.62 or 0.38)
    if button.shape == "circle" then
        love.graphics.circle("fill", button.x, button.y, button.r)
        love.graphics.setColor(1, 1, 1, 0.75)
        love.graphics.circle("line", button.x, button.y, button.r)
    else
        love.graphics.rectangle("fill", button.x, button.y, button.w, button.h, 2, 2)
        love.graphics.setColor(1, 1, 1, 0.70)
        love.graphics.rectangle("line", button.x, button.y, button.w, button.h, 2, 2)
    end

    love.graphics.setColor(1, 1, 1, 0.86)
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
