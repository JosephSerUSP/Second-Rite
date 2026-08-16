-- Per-Map-Event presentation controller runtime.
--
-- This is deliberately presentation state, not Event/gameplay state. The
-- reusable pure evaluator lives in engine.animation_controller; this adapter
-- binds it to the current Event actor facts and authored controller registry.
local controller = require("engine.animation_controller")
local event_actor = require("engine.event_actor")

local runtime = {}

local function requireSession(session, level)
    if type(session) ~= "table" then
        error("event_animation_controller: session table required", level or 3)
    end
end

local function mapKey(session)
    local id = session.currentMapIndex
    if id == nil and session.currentMapData then id = session.currentMapData.id end
    return tostring(id == nil and "__unscoped__" or id)
end

local function eventKey(ev, level)
    if type(ev) ~= "table" or ev.id == nil then
        error("event_animation_controller: Event id required", level or 3)
    end
    return tostring(ev.id)
end

local function definitions(session)
    local data = session.animationControllers
    if data == nil and session.loader then data = session.loader.animationControllers end
    if data == nil then
        local ok, loader = pcall(require, "data.loader")
        if ok then data = loader.animationControllers end
    end
    return controller.validateRegistry(data or {})
end

-- Only one Map bucket is retained. Leaving a Map discards its presentation
-- instances, so revisiting cannot resurrect stale one-shot/signal state.
local function store(session, create)
    requireSession(session, 4)
    local key = mapKey(session)
    local value = session.eventAnimationControllerRuntime
    if value and value.mapKey ~= key then
        value = nil
        session.eventAnimationControllerRuntime = nil
    end
    if not value and create then
        value = { mapKey = key, events = {} }
        session.eventAnimationControllerRuntime = value
    end
    return value
end

local function entryFor(session, ev, controllerId, create)
    if type(controllerId) ~= "string" or controllerId == "" then return nil end
    local defs = definitions(session)
    local definition = defs[controllerId]
    if not definition then
        error("event_animation_controller: unknown animation controller '"
            .. tostring(controllerId) .. "'", 3)
    end
    local bucket = store(session, create)
    if not bucket then return nil end
    local key = eventKey(ev, 4)
    local entry = bucket.events[key]
    if entry and entry.controllerId ~= controllerId then
        -- A Page/controller change is a presentation identity change. Reset.
        bucket.events[key] = nil
        entry = nil
    end
    if not entry and create then
        entry = {
            controllerId = controllerId,
            definition = definition,
            instance = controller.new(definition, controllerId),
            event = ev,
            interacting = false,
        }
        bucket.events[key] = entry
    elseif entry then
        -- Same controller across Page changes preserves ephemeral controller
        -- progress; only changing the resolved controller id resets it.
        entry.definition = definition
        entry.event = ev
    end
    return entry
end

function runtime.resolve(session, ev, controllerId)
    if controllerId == false or controllerId == nil or controllerId == "" then return nil end
    local entry = entryFor(session, ev, controllerId, true)
    return controller.snapshot(entry.instance, entry.definition)
end

function runtime.update(session, dt)
    requireSession(session, 2)
    if type(dt) ~= "number" or dt < 0 then
        error("event_animation_controller.update: dt must be a non-negative number", 2)
    end
    local bucket = store(session, false)
    if not bucket then return end
    for _, entry in pairs(bucket.events) do
        local actor = event_actor.snapshot(session, entry.event)
        controller.update(entry.instance, entry.definition, dt, {
            event = {
                moving = actor.locomotion == "moving",
                facing = actor.facing,
                interacting = entry.interacting == true,
                enabled = true,
            },
        })
    end
end

function runtime.signal(session, ev, controllerId, name)
    local entry = entryFor(session, ev, controllerId, true)
    if not entry then return false end
    controller.signal(entry.instance, name)
    return true
end

-- Backend-neutral completion seam. A sprite/model implementation reports that
-- the selected one-shot visual finished; the controller decides what state is
-- next on the following deterministic update.
function runtime.completeAnimation(session, ev, controllerId)
    local entry = entryFor(session, ev, controllerId, false)
    if not entry then return false end
    controller.completeAnimation(entry.instance)
    return true
end

function runtime.setInteracting(session, ev, controllerId, active)
    local entry = entryFor(session, ev, controllerId, true)
    if not entry then return false end
    entry.interacting = active == true
    return true
end

function runtime.snapshot(session, ev, controllerId)
    local entry = entryFor(session, ev, controllerId, false)
    if not entry then return nil end
    return controller.snapshot(entry.instance, entry.definition)
end

function runtime.reset(session)
    requireSession(session, 2)
    session.eventAnimationControllerRuntime = nil
end

-- Install explicit-dt advancement without forcing renderer.lua to know the
-- controller's ontology. The renderer owns frame cadence; Event actors and
-- presentation controllers consume that dt but remain distinct state layers.
function runtime.installRenderer(renderer)
    if type(renderer) ~= "table" or type(renderer.update) ~= "function" then
        error("event_animation_controller.installRenderer: renderer.update required", 2)
    end
    if renderer._eventAnimationControllerInstalled then return renderer end
    local baseUpdate = renderer.update
    renderer.update = function(dt, ...)
        local result = baseUpdate(dt, ...)
        local session = renderer.session
        if session then
            event_actor.update(session, dt)
            runtime.update(session, dt)
        end
        return result
    end
    renderer._eventAnimationControllerInstalled = true
    return renderer
end

return runtime