-- Durable Actor Change transaction projection.
--
-- Gameplay mutation stays in the subsystem that owns it. A Scene that wants to
-- present persistent creature development opts specific hooks into observation
-- with `config.actorChangeReports = { "on_select", ... }`. The Scene host takes
-- an authoritative snapshot before that hook and asks progress.lua what changed
-- only after the complete authored transaction has resolved.
--
-- This is deliberately NOT a global mutation watcher. Current HP, states and
-- equipment are outside progress.snapshot(), and authored Scenes must opt in to
-- a transaction boundary. The one migration exception is the host fallback:
-- map/common-event execution still lives behind scene_host's legacy input
-- fallback, so that opaque transaction is bracketed as a whole until it becomes
-- authored Scene behavior too.
local progress = require("engine.progress")
local state_value = require("engine.state_value")

local actor_change = {}
local pending = {}

local function configured(sceneData)
    return sceneData and sceneData.config and sceneData.config.actorChangeReports
end

local function observesHook(sceneData, hookName)
    local spec = configured(sceneData)
    if spec == true then return true end
    if type(spec) ~= "table" then return false end
    for _, hook in ipairs(spec) do
        if hook == hookName then return true end
    end
    return false
end

local function clearProjection(v)
    v.actorChanges = nil
    v.actorChangeIndex = 1
    v.actorChangeCount = 0
    v.actorChangePresentedIndex = 0
    v.actorChangeRows = {}
    v.actorChangeName = ""
    v.actorChangeFromName = ""
    v.actorChangeToName = ""
    v.actorChangePortrait = ""
    v.actorChangeFromLevel = 0
    v.actorChangeToLevel = 0
    v.actorChangeExp = 0
    v.actorChangeExpNeeded = 0
    v.actorChangeNoteText = ""
    v.actorChangeKind = ""
    v.actorChangeTitle = ""
    v.actorChangeCounter = ""

    -- Compatibility projection consumed by the existing levelUpStats style.
    v.levelUpRows = {}
    v.levelUpName = ""
    v.levelUpPortrait = ""
    v.levelUpFromLevel = 0
    v.levelUpToLevel = 0
    v.levelUpExp = 0
    v.levelUpExpNeeded = 0
    v.levelUpNoteText = ""
    v.levelUpCounter = ""
end

local function publishReports(v, changes)
    v.actorChanges = state_value.copy(changes, "Actor Change reports")
    v.actorChangeIndex = 1
    v.actorChangeCount = #v.actorChanges
    progress.publish(v, v.actorChanges, 1)
    v.actorChangePresentedIndex = 1
end

local function queueReports(changes)
    if type(changes) ~= "table" or #changes == 0 then return false end
    local seed = {}
    publishReports(seed, changes)
    table.insert(pending, seed)
    return true
end

-- Called before one authored Scene hook. Nil means this hook is not a durable
-- change transaction; finish() still runs afterwards so paging/closing an
-- already-published inline report remains declarative Scene State.
function actor_change.begin(sceneData, hookName, session)
    if not session or not observesHook(sceneData, hookName) then return nil end
    return progress.snapshot(session)
end

-- Called after the hook has completely resolved. `actorChangePresentation =
-- "scene"` moves the detached result into the host queue instead of retaining
-- it on the source Scene. scene_host drains that queue only after the source
-- transaction and any authored transition events have settled.
function actor_change.finish(sceneData, v, session, before)
    if not configured(sceneData) or not v or not session then return false end

    local changes = before and progress.changes(session, before) or {}
    if #changes > 0 then
        local cfg = sceneData and sceneData.config
        if cfg and cfg.actorChangePresentation == "scene" then
            queueReports(changes)
            clearProjection(v)
            return false
        end
        publishReports(v, changes)
        return true
    end

    local entries = v.actorChanges
    if type(entries) ~= "table" or #entries == 0 then return false end

    -- The authored Scene closes the overlay by setting count to zero. Clear the
    -- retained reports here so stale durable changes cannot reappear later.
    if (tonumber(v.actorChangeCount) or 0) <= 0 then
        clearProjection(v)
        return false
    end

    local index = math.floor(tonumber(v.actorChangeIndex) or 1)
    index = math.max(1, math.min(#entries, index))
    v.actorChangeIndex = index
    v.actorChangeCount = #entries

    -- Do not republish every on_frame: progress.publish creates detached row
    -- tables, and replacing the levelUpStats source every frame would restart
    -- its roll animation indefinitely. Re-project only when the authored Scene
    -- actually pages to another report.
    if tonumber(v.actorChangePresentedIndex) ~= index then
        progress.publish(v, entries, index)
        v.actorChangePresentedIndex = index
    end
    return true
end

-- The legacy player-input fallback is the remaining map/common-event host. It
-- is intentionally bracketed as ONE transaction rather than instrumenting
-- GAIN_EXP, effects, scripts, or the interpreter globally. That preserves the
-- same ownership rule as authored Scenes: gameplay resolves first, then the
-- host projects whatever durable facts changed.
function actor_change.beginFallback(session)
    if not session then return nil end
    return progress.snapshot(session)
end

function actor_change.finishFallback(session, before)
    if not session or not before then return false end
    return queueReports(progress.changes(session, before))
end

-- Host-owned handoff queue. Returning a detached Scene-state seed instead of
-- pushing here keeps actor_change independent of scene_host and avoids a module
-- cycle. The queue is FIFO so nested synchronous transactions cannot overwrite
-- an earlier report.
function actor_change.takePending()
    if #pending == 0 then return nil end
    return table.remove(pending, 1)
end

function actor_change.resetPending()
    pending = {}
end

actor_change.clear = clearProjection
actor_change.observesHook = observesHook

return actor_change