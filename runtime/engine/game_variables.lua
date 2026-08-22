-- Persistent game/playthrough Variables and Switches (#407).
--
-- The owner is deliberately separate from ctx.v (Scene/process-local state)
-- and from domain facts such as inventory, quests and battlers. Switch is an
-- author-facing boolean affordance over the same typed value store rather than
-- a second persistence engine.
local state_value = require("engine.state_value")

local game_variables = {}

local function assertSession(session)
    if type(session) ~= "table" then
        error("game variables require a GameSession", 3)
    end
end

local function assertName(name)
    if type(name) ~= "string" or name == "" or name:match("^%s*$") then
        error("game variable name must be a non-empty string", 3)
    end
    if name:find("%z") then
        error("game variable name may not contain NUL", 3)
    end
    return name
end

local function ensure(session)
    assertSession(session)
    if session.gameVariables == nil then session.gameVariables = {} end
    if type(session.gameVariables) ~= "table" then
        error("GameSession.gameVariables must be a table", 3)
    end
    return session.gameVariables
end

function game_variables.get(session, name)
    name = assertName(name)
    local store = ensure(session)
    return state_value.copy(store[name], "variables." .. name)
end

function game_variables.has(session, name)
    name = assertName(name)
    return ensure(session)[name] ~= nil
end

function game_variables.set(session, name, value)
    name = assertName(name)
    local store = ensure(session)
    if value == nil then
        store[name] = nil
        return nil
    end
    local copied = state_value.copy(value, "variables." .. name)
    store[name] = copied
    -- Return another copy so the caller never receives the store's identity.
    return state_value.copy(copied, "variables." .. name)
end

function game_variables.unset(session, name)
    return game_variables.set(session, name, nil)
end

function game_variables.getSwitch(session, name)
    return game_variables.get(session, name) == true
end

function game_variables.setSwitch(session, name, value)
    if type(value) ~= "boolean" then
        error("Control Switch requires a boolean ON/OFF value", 2)
    end
    return game_variables.set(session, name, value)
end

-- Save/formula/inspection boundaries receive copies, never the live backing
-- table. This makes accidental mutation through a read path impossible.
function game_variables.snapshot(session)
    return state_value.copy(ensure(session), "variables")
end

function game_variables.restore(session, payload)
    assertSession(session)
    if payload == nil then
        session.gameVariables = {}
        return session.gameVariables
    end
    if type(payload) ~= "table" then
        error("saved gameVariables must be an object/table", 2)
    end
    local restored = state_value.copy(payload, "variables")
    -- The top-level owner is always name-keyed. Empty JSON arrays decode to an
    -- empty Lua table in the repository parser, which is harmless here; a
    -- non-empty numeric root is not a valid Variable namespace.
    for key in pairs(restored) do
        if type(key) ~= "string" then
            error("saved gameVariables root must use string variable names", 2)
        end
    end
    session.gameVariables = restored
    return session.gameVariables
end

return game_variables
