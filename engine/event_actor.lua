-- Camera-neutral runtime identity/state for Map Event actors.
--
-- Event ownership lives here: Map scoping and a stable world root. Semantic
-- animation behavior is shared with the player through engine.character_state.
-- Presentation still decides how clip/facing become sprite/model frames.
local character_state = require("engine.character_state")
local event_actor = {}

function event_actor.normalizeFacing(value)
    return character_state.normalizeFacing(value)
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
    return character_state.normalizeFacing(raw) or "S"
end

local function defaultState(ev)
    local state = character_state.new(authoredFacing(ev))
    state.rootX = ev and ev.x or nil
    state.rootY = ev and ev.y or nil
    return state
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

-- Immutable public view. Querying an Event does not allocate runtime state.
function event_actor.snapshot(session, ev)
    local state = activeState(session, ev)
    local semantic = character_state.snapshot(state)
    semantic.eventId = ev and ev.id or nil
    semantic.rootX = state.rootX
    semantic.rootY = state.rootY
    return semantic
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
    character_state.setFacing(stateFor(session, ev, true), facing)
    return event_actor.snapshot(session, ev)
end

function event_actor.setLocomotion(session, ev, locomotion)
    character_state.setLocomotion(stateFor(session, ev, true), locomotion)
    return event_actor.snapshot(session, ev)
end

-- Movement owns semantic motion facts, not animation clip names. Root movement
-- remains separate so interpolation/pathfinding can update it independently.
function event_actor.setMotion(session, ev, dx, dy)
    character_state.setMotion(stateFor(session, ev, true), dx, dy)
    return event_actor.snapshot(session, ev)
end

-- A one-shot may be duration-driven or completion-driven. When duration is
-- omitted, presentation/script integration explicitly completes the real clip.
function event_actor.playOneShot(session, ev, clip, duration)
    character_state.playOneShot(stateFor(session, ev, true), clip, duration)
    return event_actor.snapshot(session, ev)
end

function event_actor.holdPose(session, ev, clip)
    character_state.holdPose(stateFor(session, ev, true), clip)
    return event_actor.snapshot(session, ev)
end

function event_actor.completeOverride(session, ev)
    local hadOverride = character_state.completeOverride(stateFor(session, ev, true))
    return hadOverride, event_actor.snapshot(session, ev)
end

event_actor.clearOverride = event_actor.completeOverride

function event_actor.isOverrideActive(session, ev)
    return character_state.isOverrideActive(activeState(session, ev))
end

-- Only the current Map bucket advances. Off-map actors do not run hidden
-- animation clocks.
function event_actor.update(session, dt)
    requireSession(session, 2)
    if type(dt) ~= "number" or dt < 0 then
        error("event_actor.update: dt must be a non-negative number", 2)
    end
    local bucket = mapBucket(session, false)
    if not bucket then return end
    for _, state in pairs(bucket) do
        character_state.update(state, dt)
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
