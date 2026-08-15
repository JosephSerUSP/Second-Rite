local interpreter = require("engine.interpreter")
local input_map = require("engine.input_map")
local scene_update_contract = require("engine.scene_update_contract")

local scene_host = {}

-- State container for the active scenes
-- Each element is { id = sceneId, v = {}, windows = {}, focusedWindow = nil }
local sceneStack = {}

-- Window definitions registered by kind (via scene_host.register).
-- Populated by calling registerKindWindows from scene modules.
-- Keyed by kind string (e.g. "battle"), value is a table of window defs.
local windowDefsByKind = {}

-- Presentation dependency-inversion seam (#150). Runtime engine code owns the
-- scene facts; presentation installs callbacks that consume those facts. The
-- host itself never requires a presentation module, so headless callers can
-- load and drive it with this table left empty.
local presentation = {}

function scene_host.bindPresentation(adapter)
    local previous = presentation
    presentation = adapter or {}
    return previous
end

local function publishTransition(kind, anim, defaultDuration)
    if not anim or not presentation.transition then return end
    presentation.transition({
        kind = kind,
        effect = anim.effect or "fade",
        duration = anim.duration or defaultDuration,
        color = anim.color,
    })
end

local function getSceneData(ctx, id)
    if not ctx or not ctx.loader or not ctx.loader.scenes then return nil end
    -- Two-pass matching: first pass prefers exact id/name match,
    -- second pass falls back to kind match.
    -- This prevents ambiguity when multiple scenes share a kind (e.g. "menu").
    for _, scene in ipairs(ctx.loader.scenes) do
        if tostring(scene.id) == tostring(id) or scene.name == id then
            return scene
        end
    end
    -- Second pass: match by kind (lowest priority)
    for _, scene in ipairs(ctx.loader.scenes) do
        if scene.kind == id then
            return scene
        end
    end
    return nil
end

-- Initialize the host with an active session and loader
function scene_host.init(startScene, ctx)
    sceneStack = {}
    if startScene then
        scene_host.push(startScene, ctx)
    end
end

function scene_host.getCurrent()
    if #sceneStack == 0 then return nil end
    return sceneStack[#sceneStack].id
end

function scene_host.getPrevious()
    if #sceneStack < 2 then return nil end
    return sceneStack[#sceneStack - 1].id
end

function scene_host.getCurrentState()
    if #sceneStack == 0 then return nil end
    return sceneStack[#sceneStack]
end

function scene_host.getPreviousState()
    if #sceneStack < 2 then return nil end
    return sceneStack[#sceneStack - 1]
end

-- Register window definitions for a scene kind.
-- Called by scene modules (e.g. battle.registerKindWindows) during push.
-- Stored defs are merged into the scene state's windows table on push.
function scene_host.register(kind, windowDefs)
    windowDefsByKind[kind] = windowDefs
end

-- Consume a D2 window command event into the scene's runtime window state,
-- which the generic window renderer (presentation/window_renderer.lua) draws
-- for scenes that opt in with "draw": "windows".
local function applyWindowEvent(state, ev)
    if not state.winState then
        state.winState = {}
        state.windowOrder = {}
    end
    local function ensure(id)
        if not id then return nil end
        if not state.winState[id] then
            state.winState[id] = {}
            table.insert(state.windowOrder, id)
        end
        return state.winState[id]
    end
    if ev.type == "open_window" then
        local w = ensure(ev.windowId)
        if w then w.open = true end
    elseif ev.type == "close_window" then
        local w = state.winState[ev.windowId]
        if w then w.open = false end
    elseif ev.type == "set_list" then
        local w = ensure(ev.windowId)
        if w then
            w.listId = ev.listId
            w.format = ev.format
            w.filter = ev.filter
            w.priority = ev.priority
            w.highlight = ev.highlight
            w.sprite = ev.sprite
            w.gaugeValue = ev.gaugeValue
            w.gaugeMax = ev.gaugeMax
            w.gaugeColor = ev.gaugeColor
            w.gaugeFill = ev.gaugeFill
            w.slot = ev.slot
            w.member = ev.member
        end
    elseif ev.type == "set_text" then
        local w = ensure(ev.windowId)
        if w then w.text = ev.text end
    elseif ev.type == "set_cursor" then
        local w = ensure(ev.windowId)
        if w then
            w.cursor = ev.index
            -- Keep the raw formula so the renderer can re-evaluate the
            -- cursor against live scene variables every frame.
            w.cursorFormula = ev.indexFormula
        end
    elseif ev.type == "focus_window" then
        state.focusedWindow = ev.windowId
    end
end

function scene_host.runHook(hookName, ctx)
    if #sceneStack == 0 then return false end
    local state = sceneStack[#sceneStack]

    local sceneData = getSceneData(ctx, state.id)
    if not sceneData or not sceneData.hooks then
        return false -- No data or no hooks for this scene, fallback
    end

    local cmds = sceneData.hooks[hookName]
    if not cmds then
        return false -- Hook is absent, fallback to legacy Lua block
    end

    -- We have a hook, execute it in immediate mode
    -- Ensure ctx.v is scoped to the scene instance
    ctx.v = state.v

    -- Expose the scene definition generically so SCRIPT commands can read
    -- scene config and scene-local named scripts (D13) — no per-kind context.
    ctx.scene = sceneData

    -- Reset cascade guard: sequential IF blocks check v._guard == 0
    -- and set v._guard = 1 when they match, preventing state cascades
    -- (e.g. IF v.state==1 sets state=2, then IF v.state==2 fires immediately)
    state.v._guard = 0

    -- Save old events list to avoid accumulating transition events across nested hook/push calls
    local oldEvents = ctx.events
    local oldHookHandled = ctx.hookHandled
    local oldHookFallback = ctx.hookFallback
    ctx.events = {}
    ctx.hookHandled = false
    ctx.hookFallback = false

    local events = interpreter.runImmediate(cmds, ctx)

    -- Consume SCENE_EVENT (scene_change) and update the stack
    -- Wait to process these until after the loop so we don't recurse deeply
    -- or mutate sceneStack while iterating.
    local transitions = {}
    if events then
        for _, ev in ipairs(events) do
            if ev.type == "wait" then
                state.waitTimer = ev.duration
            elseif ev.type == "scene_change" then
                table.insert(transitions, ev)
            elseif ev.type == "open_window" or ev.type == "close_window"
                or ev.type == "set_list" or ev.type == "set_text"
                or ev.type == "set_cursor" or ev.type == "focus_window" then
                applyWindowEvent(state, ev)
            elseif ev.type == "run_common_event" then
                -- An item asked for a common event (effects.lua cannot start
                -- one: CALL_COMMON_EVENT is interactive). Deferred with the
                -- scene transitions rather than run here, so the graph starts
                -- after this hook finishes and its own scene change lands on a
                -- settled stack instead of mid-hook.
                table.insert(transitions, ev)
            end
        end
    end

    -- If there was an old events list, append the new events to it
    -- so that the caller (like the golden harness) can still see them.
    if oldEvents then
        for _, ev in ipairs(events) do
            table.insert(oldEvents, ev)
        end
        ctx.events = oldEvents
    end

    for _, ev in ipairs(transitions) do
        if ev.type == "run_common_event" then
            interpreter.startCommonEvent(ev.id)
        elseif ev.kind == "pop" then
            scene_host.pop(ctx)
        elseif ev.kind == "push" and ev.scene then
            scene_host.push(ev.scene, ctx, ev.vars)
        elseif ev.kind == "goto" and ev.scene then
            scene_host.goto_scene(ev.scene, ctx, ev.vars)
        end
    end

    local fallback = ctx.hookFallback
    ctx.hookHandled = oldHookHandled
    ctx.hookFallback = oldHookFallback
    return not fallback
end

-- vars (optional): pre-resolved values from a SCENE_EVENT push/goto, seeded
-- into the new scene's v BEFORE on_enter so its setup hooks can read them
-- (e.g. the ritual scene's ritualMode/targetIndex).
function scene_host.push(id, ctx, vars)
    table.insert(sceneStack, {
        id = id,
        v = {},
        waitTimer = 0,
        windows = {},
        focusedWindow = nil,
        -- #386 fixed-clock fields are inert for legacy Scenes. Keeping them on
        -- the Scene instance means clock state never becomes global runtime
        -- state and never leaks across push/goto boundaries.
        updateAccumulator = 0,
        timeTick = 0,
        timeElapsed = 0,
        updateConfig = nil,
    })
    if vars then
        local pushed = sceneStack[#sceneStack]
        for k, val in pairs(vars) do pushed.v[k] = val end
    end

    local state = sceneStack[#sceneStack]
    local sceneData = getSceneData(ctx, id)
    state.updateConfig = scene_update_contract.resolve(sceneData)

    -- Merge registered window definitions for this scene's kind
    if sceneData and sceneData.kind then
        -- Let the scene module (engine/scenes/<kind>.lua, if one exists)
        -- register its window defs first. Resolved generically by kind —
        -- no per-kind hardcoding (D13); kinds without a module are fine.
        local ok, sceneModule = pcall(require, "engine.scenes." .. sceneData.kind)
        if ok and type(sceneModule) == "table" and sceneModule.registerKindWindows then
            sceneModule.registerKindWindows(scene_host)
        end
        -- Merge any stored window definitions into the scene state
        local kindDefs = windowDefsByKind[sceneData.kind]
        if kindDefs then
            for k, v in pairs(kindDefs) do
                state.windows[k] = v
            end
        end
    end

    if sceneData and sceneData.anim and sceneData.anim.enter then
        publishTransition("enter", sceneData.anim.enter, 0.2)
    end

    if ctx then
        scene_host.runHook("on_enter", ctx)
    end
end

function scene_host.pop(ctx)
    if #sceneStack > 0 then
        local state = sceneStack[#sceneStack]
        local sceneData = getSceneData(ctx, state.id)
        if sceneData and sceneData.anim and sceneData.anim.exit then
            publishTransition("exit", sceneData.anim.exit, 0.15)
        end
        if ctx then
            scene_host.runHook("on_exit", ctx)
        end
        table.remove(sceneStack)
    end
end

function scene_host.goto_scene(id, ctx, vars)
    -- Dock continuity across this transition is not handled here any more:
    -- the dock is a persistent surface that simply notices the incoming
    -- scene wants the same variant and doesn't re-animate (dock.lua).
    --
    -- IMPORTANT PRESERVED BEHAVIOR (#150): goto is pop + push, so it publishes
    -- EXIT and then ENTER synchronously. The current presentation transition
    -- manager has one active slot; therefore ENTER replaces EXIT when both are
    -- authored. That oddity is now explicit so a future queue/crossfade redesign
    -- can improve it deliberately instead of this ownership move changing feel
    -- by accident.
    scene_host.pop(ctx)
    scene_host.push(id, ctx, vars)
end

-- A fixed Scene's timing view is deliberately transient and Scene-local. The
-- ordinary Formula/SCRIPT surfaces already receive v, so exposing `v.time`
-- during `on_frame` gives authored code dt/tick/elapsed without adding raw host
-- state, global clocks, or a second scripting API. Restore any authored `time`
-- variable immediately after the hook so this is a logical-tick capability,
-- not persistent Scene state.
local function runTimedFrameHook(state, step, ctx)
    local values = {
        dt = step,
        tick = state.timeTick,
        elapsed = state.timeElapsed,
    }
    local timeView = setmetatable({}, {
        __index = values,
        __newindex = function()
            error("Scene v.time is read-only during a fixed on_frame tick", 2)
        end,
        __metatable = false,
    })
    local oldVTime = state.v.time
    local oldCtxTime = ctx.time
    state.v.time = timeView
    ctx.time = timeView
    local ok, handled = pcall(scene_host.runHook, "on_frame", ctx)
    state.v.time = oldVTime
    ctx.time = oldCtxTime
    if not ok then error(handled, 0) end
    return handled
end

local function updateLegacy(dt, ctx)
    if #sceneStack > 0 then
        local state = sceneStack[#sceneStack]
        if state.waitTimer and state.waitTimer > 0 then
            state.waitTimer = math.max(0, state.waitTimer - dt)
            if state.waitTimer > 0 then return true end
        end
    end
    -- Preserve the pre-#386 contract exactly: one host update means one
    -- authored on_frame attempt for every Scene that does not opt into fixed
    -- logical time.
    return scene_host.runHook("on_frame", ctx)
end

local function updateFixed(state, sceneData, dt, ctx)
    local config = state.updateConfig
    local step = config.step
    state.updateAccumulator = state.updateAccumulator + math.max(0, dt or 0)

    -- A fixed Scene that owns on_frame still owns this host update even when
    -- not enough wall time has accumulated for a logical tick yet. Otherwise
    -- the legacy Lua update beneath scene_host.update would run on those frames
    -- and reintroduce host-cadence-dependent behavior.
    local handled = sceneData and sceneData.hooks and sceneData.hooks.on_frame ~= nil or false
    local ticks = 0
    local epsilon = step * 1e-9

    while state.updateAccumulator + epsilon >= step and ticks < config.maxCatchUp do
        state.updateAccumulator = state.updateAccumulator - step
        if state.updateAccumulator < 0 and state.updateAccumulator > -epsilon then
            state.updateAccumulator = 0
        end
        ticks = ticks + 1
        state.timeTick = state.timeTick + 1
        -- Derive elapsed from the integer tick rather than repeatedly adding a
        -- float, so equal logical histories have equal authored elapsed time.
        state.timeElapsed = state.timeTick * step

        local shouldRunHook = true
        if state.waitTimer and state.waitTimer > 0 then
            state.waitTimer = math.max(0, state.waitTimer - step)
            if state.waitTimer > 0 then shouldRunHook = false end
        end

        if shouldRunHook then
            local tickHandled = runTimedFrameHook(state, step, ctx)
            if not tickHandled then
                handled = false
                break
            end
            handled = true
        end

        -- A push/pop/goto during this logical tick changes the active Scene.
        -- Never spend the outgoing Scene's accumulated backlog on the incoming
        -- Scene, and never continue running hooks on an instance that left the
        -- top of the stack.
        if sceneStack[#sceneStack] ~= state then break end
    end

    return handled
end

function scene_host.update(dt, ctx)
    if presentation.update then presentation.update(dt) end
    if #sceneStack == 0 then return false end

    local state = sceneStack[#sceneStack]
    if not state.updateConfig then return updateLegacy(dt, ctx) end
    local sceneData = getSceneData(ctx, state.id)
    return updateFixed(state, sceneData, dt, ctx)
end

-- Presentation is injected, following the same dependency direction as
-- interpreter.bindPresentation: the engine supplies scene state/definition and
-- presentation decides how to render it. Unbound/headless callers simply get
-- false without loading graphics modules.
function scene_host.draw(ctx)
    if #sceneStack == 0 then return false end
    if not presentation.draw then return false end
    local state = sceneStack[#sceneStack]
    local sceneData = getSceneData(ctx, state.id)
    return presentation.draw(state, sceneData, ctx)
end

function scene_host.keypressed(key, ctx)
    -- Raw key capture (e.g. the `controls` scene rebinding a button):
    -- while the current scene's v._capturingKey is set, the very next
    -- physical key -- WASD/arrows/escape included -- is routed to a
    -- scene-local on_raw_key hook instead of normal WASD-normalize +
    -- hook dispatch below. Scoped to this one need; not a generic hook.
    if #sceneStack > 0 then
        local state = sceneStack[#sceneStack]
        if state.v and state.v._capturingKey then
            local sceneData = getSceneData(ctx, state.id)
            if sceneData and sceneData.hooks and sceneData.hooks.on_raw_key then
                ctx.v = state.v
                ctx.v.rawKey = key
                return scene_host.runHook("on_raw_key", ctx)
            end
        end
    end



    -- Resolve the physical key to a logical SNES button via the rebindable
    -- input map, then to the existing hook that button drives. Defaults
    -- (data/input.json) reproduce the previous hardcoded mapping exactly.
    local button = input_map.resolveHook(key)
    if not button then
        return false
    end
    local hookName = input_map.BUTTON_TO_HOOK[button]
    if not hookName then
        -- X, Y, SELECT: bound but no game hook consumes them yet.
        return false
    end
    -- Page-flip hook for scenes with multiple info pages (e.g. the
    -- ritual scene's stats/art pages). Scenes that don't define it
    -- fall through unhandled, as with any absent hook.
    return scene_host.runHook(hookName, ctx)
end

return scene_host
