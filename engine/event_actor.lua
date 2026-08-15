-- Camera-neutral runtime state for Map Event actors.
--
-- Gameplay says what an actor is doing (root position, facing, locomotion and
-- temporary semantic overrides). Presentation decides how those facts become
-- sprite/model clips and frames. In particular, the root never includes visual
-- bob/shake/pivot offsets, so a camera can follow an Event without inheriting
-- animation jitter.
--
-- Runtime state is intentionally transient. Persistent authored/page changes
-- remain owned by exploration/eventOverrides/map state; frame clocks and
-- temporary poses do not become save-game authority by accident.
local event_actor = {}

local VALID_LOCOMOTION = {
    idle = true,
    moving = true,
}

local FACING_ALIASES = {
    N = "N", E = "E", S = "S", W = "W",
    north = "N", east = "E", south = "S", west = "W",
    up = "N", right = "E", down = "S", left = "W",
}

function event_actor.normalizeFacing(value)
    if value == nil then return nil end
    local text = tostring(value)
    return FACING_ALIASES[text] or FACING_ALIASES[text:lower()] or FACING_ALIASES[text:upper()]
end

local function requireSession(session, level)
    if type(session) ~= "table" then
        error("event_actor: session table required", level or 3)
    end
end

local function mapKey(session, explicit)
    if explicit ~= nil then return tostring(explicit) end
    local current = session.currentMapIndex
    if current == nil and session.currentMapData then
        current = session.currentMapData.id
    end
    if current == nil then current = "__unscoped__" end
    return tostring(current)
end

local function eventKey(ev, level)
    if type(ev) ~= "table" or ev.id == nil then
        error("event_actor: mutable event actors require an event id", level or 3)
    end
    return tostring(ev.id)
end

local function authoredFacing(ev)
    local raw = ev and (ev.facing or ev.direction or ev.dir)
    return event_actor.normalizeFacing(raw) or "S"
end

local function defaultState(ev)
    return {
        rootX = ev and ev.x or nil,
        rootY = ev and ev.y or nil,
        facing = authoredFacing(ev),
        locomotion = "idle",
        override = nil,
    }
end

local function mapBucket(session, create, explicitMap)
    requireSession(session, 4)
    local store = session.eventActorRuntime
    if not store and create then
        store = {}
        session.eventActorRuntime = store
    end
    if not store then return nil end

    local key = mapKey(session, explicitMap)
    local bucket = store[key]
    if not bucket and create then
        bucket = {}
        store[key] = bucket
    end
    return bucket
end

local function stateFor(session, ev, create)
    local bucket = mapBucket(session, create)
    if not bucket then return nil end
    local key = eventKey(ev, 4)
    local state = bucket[key]
    if not state and create then
        state = defaultState(ev)
        bucket[key] = state
    end
    return state
end

local function activeState(session, ev)
    requireSession(session, 4)
    if type(ev) ~= "table" then
        error("event_actor: event table required", 4)
    end
    if ev.id ~= nil then
        local bucket = mapBucket(session, false)
        if bucket then
            local state = bucket[tostring(ev.id)]
            if state then return state end
        end
    end
    return defaultState(ev)
end

local function resolvedClip(state)
    if state.override then return state.override.clip end
    if state.locomotion == "moving" then return "walk" end
    return "idle"
end

-- Immutable public view. Querying an Event does not allocate runtime state.
function event_actor.snapshot(session, ev)
    local state = activeState(session, ev)
    local override = state.override
    return {
        eventId = ev and ev.id or nil,
        rootX = state.rootX,
        rootY = state.rootY,
        facing = state.facing,
        locomotion = state.locomotion,
        clip = resolvedClip(state),
        overrideKind = override and override.kind or nil,
        overrideRemaining = override and override.remaining or nil,
    }
end

function event_actor.setRoot(session, ev, x, y)
    if type(x) ~= "number" or type(y) ~= "number" then
        error("event_actor.setRoot: x and y must be numbers", 2)
    end
    local state = stateFor(session, ev, true)
    state.rootX, state.rootY = x, y
    return event_actor.snapshot(session, ev)
end

function event_actor.setFacing(session, ev, facing)
    local normalized = event_actor.normalizeFacing(facing)
    if not normalized then
        error("event_actor.setFacing: expected N/E/S/W (or cardinal alias), got "
            .. tostring(facing), 2)
    end
    local state = stateFor(session, ev, true)
    state.facing = normalized
    return event_actor.snapshot(session, ev)
end

function event_actor.setLocomotion(session, ev, locomotion)
    local value = type(locomotion) == "string" and locomotion:lower() or locomotion
    if not VALID_LOCOMOTION[value] then
        error("event_actor.setLocomotion: expected 'idle' or 'moving', got "
            .. tostring(locomotion), 2)
    end
    local state = stateFor(session, ev, true)
    state.locomotion = value
    return event_actor.snapshot(session, ev)
end

-- Movement owns semantic motion facts, not animation clip names. Cardinal
-- motion updates facing; stopping preserves the last facing. Root movement is
-- deliberately separate so interpolation/pathfinding can move the stable root
-- at whatever cadence it owns without teaching this module a movement model.
function event_actor.setMotion(session, ev, dx, dy)
    if type(dx) ~= "number" or type(dy) ~= "number" then
        error("event_actor.setMotion: dx and dy must be numbers", 2)
    end
    if dx ~= 0 and dy ~= 0 then
        error("event_actor.setMotion: diagonal motion is not a single cardinal facing", 2)
    end

    local state = stateFor(session, ev, true)
    if dx == 0 and dy == 0 then
        state.locomotion = "idle"
    else
        state.locomotion = "moving"
        if dx > 0 then state.facing = "E"
        elseif dx < 0 then state.facing = "W"
        elseif dy > 0 then state.facing = "S"
        else state.facing = "N" end
    end
    return event_actor.snapshot(session, ev)
end

local function requireClip(clip, operation)
    if type(clip) ~= "string" or clip == "" then
        error("event_actor." .. operation .. ": non-empty semantic clip required", 3)
    end
end

-- A one-shot may be duration-driven or completion-driven. When duration is
-- omitted, presentation/script integration explicitly calls completeOverride
-- when its real asset clip finishes; the engine therefore never guesses FPS.
function event_actor.playOneShot(session, ev, clip, duration)
    requireClip(clip, "playOneShot")
    if duration ~= nil and (type(duration) ~= "number" or duration <= 0) then
        error("event_actor.playOneShot: duration must be a positive number when supplied", 2)
    end
    local state = stateFor(session, ev, true)
    state.override = {
        kind = "one_shot",
        clip = clip,
        remaining = duration,
    }
    return event_actor.snapshot(session, ev)
end

function event_actor.holdPose(session, ev, clip)
    requireClip(clip, "holdPose")
    local state = stateFor(session, ev, true)
    state.override = {
        kind = "pose",
        clip = clip,
    }
    return event_actor.snapshot(session, ev)
end

function event_actor.completeOverride(session, ev)
    local state = stateFor(session, ev, true)
    local hadOverride = state.override ~= nil
    state.override = nil
    return hadOverride, event_actor.snapshot(session, ev)
end

event_actor.clearOverride = event_actor.completeOverride

function event_actor.isOverrideActive(session, ev)
    return activeState(session, ev).override ~= nil
end

-- Only timed one-shots advance here. Held poses and completion-driven clips do
-- not own hidden clocks. Off-map actors also do not advance while their Map is
-- inactive; update touches only the current map bucket.
function event_actor.update(session, dt)
    requireSession(session, 2)
    if type(dt) ~= "number" or dt < 0 then
        error("event_actor.update: dt must be a non-negative number", 2)
    end
    local bucket = mapBucket(session, false)
    if not bucket then return end
    for _, state in pairs(bucket) do
        local override = state.override
        if override and override.kind == "one_shot" and override.remaining ~= nil then
            override.remaining = override.remaining - dt
            if override.remaining <= 0 then
                state.override = nil
            end
        end
    end
end

function event_actor.resetMap(session, explicitMap)
    requireSession(session, 2)
    local store = session.eventActorRuntime
    if not store then return false end
    local key = mapKey(session, explicitMap)
    local existed = store[key] ~= nil
    store[key] = nil
    return existed
end

function event_actor.reset(session)
    requireSession(session, 2)
    session.eventActorRuntime = nil
end

return event_actor
