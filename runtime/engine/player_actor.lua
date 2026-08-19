-- Player-facing world-character state derived from existing exploration state.
--
-- This module does not move the player, own collision, or read input. It turns
-- the already-authoritative tile position + transition record into one stable,
-- interpolated world root and the same semantic character state used by Events.
local character_state = require("engine.character_state")

local player_actor = {}

local DIRS = {
    N = { dx = 0, dy = -1 },
    E = { dx = 1, dy = 0 },
    S = { dx = 0, dy = 1 },
    W = { dx = -1, dy = 0 },
}
local ORDER = { "N", "E", "S", "W" }

local function requireSession(session)
    if type(session) ~= "table" then
        error("player_actor: session table required", 3)
    end
    if type(session.playerX) ~= "number" or type(session.playerY) ~= "number" then
        error("player_actor: numeric playerX/playerY required", 3)
    end
    if not DIRS[session.playerDir] then
        error("player_actor: cardinal playerDir required", 3)
    end
end

local function dirIndex(dir)
    for i, value in ipairs(ORDER) do
        if value == dir then return i end
    end
    error("player_actor: unknown direction " .. tostring(dir), 3)
end

local function turnRight(dir)
    return ORDER[dirIndex(dir) % 4 + 1]
end

local function transitionFractions(session)
    local duration = tonumber(session.transitionDuration) or 0.15
    local remaining = tonumber(session.transitionTimer) or 0
    if remaining <= 0 then return 0, 1 end
    if duration <= 0 then
        error("player_actor: active transition requires positive transitionDuration", 3)
    end
    local remainingFraction = math.max(0, math.min(1, remaining / duration))
    return remainingFraction, 1 - remainingFraction
end

function player_actor.isMoving(session)
    requireSession(session)
    if not session.transitionTimer or session.transitionTimer <= 0 then return false end
    local kind = session.transitionDir
    return kind == "forward" or kind == "backward"
        or kind == "strafe_left" or kind == "strafe_right"
end

-- The authoritative visual/camera anchor. Exploration commits the destination
-- tile immediately; while its transition is active, reconstruct the prior root
-- and interpolate toward that destination using the same remaining-fraction
-- contract as the existing first-person camera.
function player_actor.root(session)
    requireSession(session)
    local x, y = session.playerX + 0.5, session.playerY + 0.5
    if not player_actor.isMoving(session) then return x, y end

    local remainingFraction = transitionFractions(session)
    local forward = DIRS[session.playerDir]
    local right = DIRS[turnRight(session.playerDir)]
    local kind = session.transitionDir
    if kind == "forward" then
        x, y = x - forward.dx * remainingFraction, y - forward.dy * remainingFraction
    elseif kind == "backward" then
        x, y = x + forward.dx * remainingFraction, y + forward.dy * remainingFraction
    elseif kind == "strafe_left" then
        x, y = x + right.dx * remainingFraction, y + right.dy * remainingFraction
    elseif kind == "strafe_right" then
        x, y = x - right.dx * remainingFraction, y - right.dy * remainingFraction
    end
    return x, y
end

function player_actor.snapshot(session)
    requireSession(session)
    local state = character_state.new(session.playerDir)
    character_state.setLocomotion(state, player_actor.isMoving(session) and "moving" or "idle")
    local semantic = character_state.snapshot(state)
    semantic.rootX, semantic.rootY = player_actor.root(session)
    local _, progress = transitionFractions(session)
    semantic.transitionProgress = player_actor.isMoving(session) and progress or 1
    semantic.transitionDir = session.transitionDir
    return semantic
end

return player_actor
