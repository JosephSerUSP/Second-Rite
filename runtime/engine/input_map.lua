-- SNES-style logical button map: A,B,X,Y,L,R,START,SELECT,UP,DOWN,LEFT,RIGHT,
-- each bound to exactly one physical keyboard key, rebindable in-game via the
-- `controls` scene. Persisted to data/input.json in the LOVE save directory
-- (read precedence) and the Project source directory when running from source,
-- so the two stay in sync.
local json = require("engine.data.json")

local input_map = {}

local PATH = require("engine.data.loader").root .. "/input.json"

local DEFAULTS = {
    A = "return", B = "escape", X = "x", Y = "z",
    L = "q", R = "e", START = "space", SELECT = "lshift",
    UP = "up", DOWN = "down", LEFT = "left", RIGHT = "right",
}

local SECONDARY_DEFAULTS = {
    -- Preserve the historical keyboard conveniences at the device adapter
    -- edge. Gameplay still receives only canonical logical buttons.
    B = "backspace",
    UP = "w", DOWN = "s", LEFT = "a", RIGHT = "d",
}

-- SNES button -> existing scene hook name. X, Y have no game hook to dispatch
-- to yet -- deliberately absent rather than pointing at invented placeholders;
-- resolveHook/keypressed callers treat a missing entry as unhandled.
input_map.BUTTON_TO_HOOK = {
    A = "on_select",
    B = "on_cancel",
    START = "on_select",
    L = "on_page",
    R = "on_page",
    SELECT = "on_inspect",
    UP = "on_up",
    DOWN = "on_down",
    LEFT = "on_left",
    RIGHT = "on_right",
}

local bindings = nil -- SNES button name -> LOVE key name
local keyToButton = nil -- reverse lookup cache, rebuilt whenever bindings change

local function copyDefaults()
    local t = {}
    for button, key in pairs(DEFAULTS) do t[button] = key end
    return t
end

local function rebuildReverse()
    keyToButton = {}
    for button, key in pairs(bindings) do
        keyToButton[key] = button
    end
    -- Add historical secondary bindings unless the physical key is already
    -- occupied by an authored/rebound primary mapping.
    for button, key in pairs(SECONDARY_DEFAULTS) do
        if not keyToButton[key] then
            keyToButton[key] = button
        end
    end
end

-- Loads data/input.json (love.filesystem read prefers the save-dir copy),
-- falling back to DEFAULTS when the file is missing or corrupt. Unknown
-- button names in the file are ignored; missing ones keep their default.
function input_map.load()
    local ok, contents = pcall(love.filesystem.read, PATH)
    local data = nil
    if ok and contents then
        local dOk, decoded = pcall(json.decode, contents)
        if dOk then data = decoded end
    end
    bindings = copyDefaults()
    if type(data) == "table" and type(data.bindings) == "table" then
        for button, key in pairs(data.bindings) do
            if DEFAULTS[button] ~= nil and type(key) == "string" and key ~= "" then
                bindings[button] = key
            end
        end
    end
    rebuildReverse()
    return bindings
end

function input_map.save()
    if not bindings then return end
    local body = json.encode({ bindings = bindings })
    -- getSource(), not getSourceDirectory(): the latter does not exist in
    -- LOVE 11; getSource() is the Project source root when running from source.
    local absPath = love.filesystem.getSource() .. "/" .. PATH
    local file, err = io.open(absPath, "w")
    if file then
        file:write(body)
        file:close()
    else
        print("input_map: failed to write to project file: " .. tostring(err))
    end
    love.filesystem.write(PATH, body)
end

function input_map.getBindings()
    if not bindings then input_map.load() end
    return bindings
end

-- Rebinds `button` (must be one of the fixed SNES button names) to `key`
-- and persists immediately. Returns false for an unknown button name.
function input_map.setBinding(button, key)
    if not bindings then input_map.load() end
    if DEFAULTS[button] == nil then return false end
    bindings[button] = key
    rebuildReverse()
    input_map.save()
    return true
end

-- Given a raw LOVE key name, returns the SNES
-- button name it's currently bound to, or nil if nothing is bound to it.
function input_map.resolveHook(key)
    if not bindings then input_map.load() end
    return keyToButton[key]
end

return input_map
