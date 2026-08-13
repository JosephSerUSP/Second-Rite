local json = require("data.json")

-- Player-chosen presentation settings, stored in LOVE's save directory.
--
-- Deliberately NOT data/system.json: that file is authored Project data. It is
-- tracked in git and written by the editor, so a player toggling a menu option
-- would dirty the Project. These settings belong to the person at the keyboard,
-- not to authored game data, so they live beside save files.
--
-- Kept separate from savegame.lua for the same reason in the other direction: a
-- display choice must survive starting a new game and must not travel inside a
-- save slot, or loading someone else's save would change your screen.
local user_settings = {}

local FILE = "settings.json"
local values = nil
local pinned = false

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
    -- A pinned harness must not edit the operator's real preferences as a side
    -- effect of photographing the game.
    if pinned then return false end
    if not (love and love.filesystem) then return false end
    local ok, encoded = pcall(json.encode, values)
    if not ok then return false end
    local written = love.filesystem.write(FILE, encoded)
    return written and true or false
end

-- Harness seam: adopt an explicit settings table and stop persisting.
--
-- A golden gate photographs the GAME, but these settings belong to whoever is
-- at the keyboard -- so without this, a preference stored on the capturing
-- machine decides what the reference frames contain. That is not theoretical:
-- a stored touchGamepadEnabled drew the virtual controller over every wide
-- frame in G5, reddening the whole set against references that predate it,
-- with nothing in the repository to explain the diff. G6 already pins its
-- equivalent (the editor's stored theme); this is the same pin for G5.
--
-- Writes become no-ops while pinned, so a capture can never edit the
-- operator's real preferences on its way past.
function user_settings.pinForCapture(overrides)
    values = {}
    for key, value in pairs(overrides or {}) do values[key] = value end
    pinned = true
    return values
end

function user_settings.isPinned()
    return pinned
end

-- Test seam: drop the cache so a suite can exercise load behaviour.
function user_settings.reset()
    values = nil
    pinned = false
end

return user_settings
