local json = require("data.json")

-- Player-chosen presentation settings, stored in LOVE's save directory.
--
-- Deliberately NOT data/system.json: that file is authored campaign data. It is
-- tracked in git, the editor dev server writes through to it, and it follows the
-- active campaign root -- so a player toggling a menu option would dirty the
-- repository and change with the campaign. These settings belong to the person
-- at the keyboard, not to a campaign, so they live beside save files.
--
-- Kept separate from savegame.lua for the same reason in the other direction: a
-- display choice must survive starting a new game and must not travel inside a
-- save slot, or loading someone else's save would change your screen.
local user_settings = {}

local FILE = "settings.json"
local values = nil

local function ensureLoaded()
    if values then return values end
    values = {}
    -- love.filesystem is absent in some headless tooling; settings are optional
    -- everywhere, so a missing filesystem means "no stored preferences" rather
    -- than an error.
    if not (love and love.filesystem) then return values end
    if not love.filesystem.getInfo(FILE) then return values end
    local contents = love.filesystem.read(FILE)
    if not contents then return values end
    local ok, decoded = pcall(json.decode, contents)
    -- A corrupt settings file must never stop the game from starting. Falling
    -- back to defaults loses a preference; erroring loses the whole session.
    if ok and type(decoded) == "table" then values = decoded end
    return values
end

function user_settings.get(key, default)
    local v = ensureLoaded()[key]
    if v == nil then return default end
    return v
end

function user_settings.set(key, value)
    ensureLoaded()[key] = value
    if not (love and love.filesystem) then return false end
    local ok, encoded = pcall(json.encode, values)
    if not ok then return false end
    local written = love.filesystem.write(FILE, encoded)
    return written and true or false
end

-- Test seam: drop the cache so a suite can exercise load behaviour.
function user_settings.reset()
    values = nil
end

return user_settings
