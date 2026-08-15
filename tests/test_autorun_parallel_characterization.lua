-- Headless characterization of the current Event/Scene timing boundaries.
--
-- This suite does not add Autorun, Parallel, Map processes, or scheduler
-- behavior. It records the seams a future implementation must not silently
-- reinterpret.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("data.loader")
local sessionModule = require("engine.session")
local exploration = require("engine.exploration")
local interpreter = require("engine.interpreter")
local director = require("engine.director")
local sceneHost = require("engine.scene_host")
local sceneUpdateContract = require("engine.scene_update_contract")
local savegame = require("engine.savegame")

loader.init()

local passed, failed = 0, 0
local function check(condition, message)
    if condition then
        passed = passed + 1
        print("  [PASS] " .. message)
    else
        failed = failed + 1
        print("  [FAIL] " .. message)
    end
end

local function newSession()
    local s = sessionModule.GameSession.new(loader)
    s:initializeStartingParty()
    return s
end

print("[TEST] Starting Autorun/Parallel current-model characterization...")

-- Pages are resolved on demand from one Map Event. The last matching Page
-- wins, and the result is an effective Event table rather than a resident
-- Page/interpreter object.
do
    local s = newSession()
    s.flags.page_one = true
    local raw = {
        id = "page_probe",
        x = 1, y = 2,
        trigger = "interact",
        commands = { { cmd = "SET_FLAG", flag = "base", value = true } },
        pages = {
            { condition = "flag:page_one", trigger = "step",
              commands = { { cmd = "SET_FLAG", flag = "first", value = true } } },
            { condition = "flag:page_one", trigger = "touch",
              commands = { { cmd = "SET_FLAG", flag = "second", value = true } } },
        },
    }
    local effective = exploration.resolvePage(raw, s)
    check(effective ~= raw and effective.trigger == "touch"
            and effective.commands[1].flag == "second",
        "Page resolution returns the last matching incarnation with its trigger and program")
    s.flags.page_one = nil
    local fallback = exploration.resolvePage(raw, s)
    check(fallback.trigger == "interact" and fallback.commands[1].flag == "base",
        "when no Page condition matches, the Event base remains the effective incarnation")
end

-- Immediate mode is synchronous. WAIT emits a presentation event; it does not
-- yield the command list or prevent later mutations from committing.
do
    local s = newSession()
    local events = interpreter.runImmediate({
        { cmd = "SET_FLAG", flag = "before_wait", value = true },
        { cmd = "WAIT", duration = 3 },
        { cmd = "SET_FLAG", flag = "after_wait", value = true },
    }, { session = s, loader = loader })
    check(s.flags.before_wait == true and s.flags.after_wait == true,
        "immediate WAIT does not suspend later command execution")
    check(#events == 1 and events[1].type == "wait" and events[1].duration == 3,
        "immediate WAIT emits one presentation wait event")
end

-- Interactive mode turns WAIT into a graph node. The caller owns the walker
-- and the external clock/input that advances it; the interpreter does not
-- create an OS thread or a background process.
do
    local s = newSession()
    local graph = interpreter.runInteractive({
        { cmd = "SET_FLAG", flag = "before_wait", value = true },
        { cmd = "WAIT", duration = 3 },
        { cmd = "SET_FLAG", flag = "after_wait", value = true },
    }, { session = s, loader = loader })
    local walker = director.GraphWalker.new(s, graph)
    local first = walker:getCurrentNode()
    walker:advance()
    local waitNode = walker:getCurrentNode()
    check(first and first.type == "ACTION" and first.action == "RUN_IMMEDIATE"
            and waitNode and waitNode.type == "ACTION"
            and waitNode.action == "WAIT_EVENT",
        "interactive mode separates immediate command runs from a suspending WAIT node")
    check(walker:getCurrentNode() == waitNode,
        "the interactive walker remains on WAIT until its host advances it")
end

-- CALL_COMMON_EVENT is a reusable procedure request in the interactive graph;
-- immediate mode rejects it because no synchronous caller owns its continuation
-- and interaction result.
do
    local s = newSession()
    local graph = interpreter.runInteractive({
        { cmd = "CALL_COMMON_EVENT", commonEventId = 1 },
    }, { session = s, loader = loader })
    local node = graph and graph.nodes[graph.initialNode]
    local ok = pcall(interpreter.runImmediate, {
        { cmd = "CALL_COMMON_EVENT", commonEventId = 1 },
    }, { session = s, loader = loader })
    check(node and node.type == "ACTION" and node.action == "CALL_COMMON_EVENT_ACTION",
        "Common Event invocation compiles as an interactive continuation node")
    check(not ok,
        "immediate mode refuses an interactive Common Event invocation")
end

-- Scene WAIT is a Scene-local update gate. It is not an Event interpreter
-- lifetime and does not establish Map simulation semantics.
do
    local s = newSession()
    local fakeLoader = {
        scenes = {
            { id = "probe", kind = "probe", hooks = {
                on_frame = {
                    { cmd = "SET_VAR", name = "frames", value = "(v.frames or 0) + 1" },
                    { cmd = "WAIT", duration = 1 },
                },
            } },
        },
    }
    sceneHost.init("probe", { session = s, loader = fakeLoader })
    local ctx = { session = s, loader = fakeLoader, party = s.party }
    local state = sceneHost.getCurrentState()
    sceneHost.update(0.1, ctx)
    check(state.v.frames == 1 and state.waitTimer == 1,
        "Scene on_frame runs on an update tick and records its local wait timer")
    sceneHost.update(0.1, ctx)
    check(state.v.frames == 1,
        "Scene WAIT suppresses the next Scene hook tick while its timer remains")
    sceneHost.update(1, ctx)
    check(state.v.frames == 2,
        "Scene hook resumes after its timer expires")
    sceneHost.init(nil)
end

-- #386: fixed Scene timing is opt-in and chunking-invariant. The same 0.3
-- seconds of host time must produce the same three logical 0.1-second ticks
-- whether the host supplies one large update or three small ones.
do
    local function runChunks(chunks, maxCatchUp)
        local s = newSession()
        local fakeLoader = {
            scenes = {
                {
                    id = "fixed_probe", kind = "probe",
                    update = { mode = "fixed", step = 0.1, maxCatchUp = maxCatchUp or 8 },
                    hooks = {
                        on_frame = {
                            { cmd = "SET_VAR", name = "frames", value = "(v.frames or 0) + 1" },
                            { cmd = "SET_VAR", name = "lastDt", value = "v.time.dt" },
                            { cmd = "SET_VAR", name = "lastTick", value = "v.time.tick" },
                            { cmd = "SET_VAR", name = "lastElapsed", value = "v.time.elapsed" },
                        },
                    },
                },
            },
        }
        local ctx = { session = s, loader = fakeLoader, party = s.party }
        sceneHost.init("fixed_probe", ctx)
        local state = sceneHost.getCurrentState()
        for _, dt in ipairs(chunks) do sceneHost.update(dt, ctx) end
        local snapshot = {
            frames = state.v.frames,
            lastDt = state.v.lastDt,
            lastTick = state.v.lastTick,
            lastElapsed = state.v.lastElapsed,
            accumulator = state.updateAccumulator,
            leakedTime = state.v.time,
        }
        sceneHost.init(nil)
        return snapshot
    end

    local oneChunk = runChunks({ 0.3 })
    local threeChunks = runChunks({ 0.1, 0.1, 0.1 })
    check(oneChunk.frames == 3 and threeChunks.frames == 3
            and oneChunk.lastTick == threeChunks.lastTick
            and oneChunk.lastElapsed == threeChunks.lastElapsed,
        "fixed Scene produces equivalent logical history under different host dt chunking")
    check(oneChunk.lastDt == 0.1 and oneChunk.lastTick == 3
            and math.abs(oneChunk.lastElapsed - 0.3) < 1e-9,
        "fixed on_frame receives Scene-local v.time dt/tick/elapsed from logical time")
    check(oneChunk.leakedTime == nil and threeChunks.leakedTime == nil,
        "fixed v.time context is transient and does not become persistent Scene state")

    local substep = runChunks({ 0.05 })
    check(substep.frames == nil and math.abs(substep.accumulator - 0.05) < 1e-9,
        "host dt below fixed step accumulates without inventing a logical tick")

    local s = newSession()
    local backlogLoader = {
        scenes = {
            {
                id = "backlog", kind = "probe",
                update = { mode = "fixed", step = 0.1, maxCatchUp = 2 },
                hooks = { on_frame = {
                    { cmd = "SET_VAR", name = "frames", value = "(v.frames or 0) + 1" },
                } },
            },
        },
    }
    local backlogCtx = { session = s, loader = backlogLoader, party = s.party }
    sceneHost.init("backlog", backlogCtx)
    local backlogState = sceneHost.getCurrentState()
    sceneHost.update(0.5, backlogCtx)
    local afterFirst = backlogState.v.frames
    local backlogAfterFirst = backlogState.updateAccumulator
    sceneHost.update(0, backlogCtx)
    local afterSecond = backlogState.v.frames
    local backlogAfterSecond = backlogState.updateAccumulator
    sceneHost.update(0, backlogCtx)
    check(afterFirst == 2 and math.abs(backlogAfterFirst - 0.3) < 1e-9
            and afterSecond == 4 and math.abs(backlogAfterSecond - 0.1) < 1e-9
            and backlogState.v.frames == 5 and math.abs(backlogState.updateAccumulator) < 1e-9,
        "maxCatchUp bounds per-frame work while retaining undiscarded logical backlog")
    sceneHost.init(nil)
end

-- #386: Scene WAIT consumes logical time in fixed mode. One 0.5 host update
-- and five 0.1 host updates therefore resume the hook at the same logical ticks.
do
    local function waitFrames(chunks)
        local s = newSession()
        local fakeLoader = {
            scenes = {
                {
                    id = "fixed_wait", kind = "probe",
                    update = { mode = "fixed", step = 0.1, maxCatchUp = 8 },
                    hooks = { on_frame = {
                        { cmd = "SET_VAR", name = "frames", value = "(v.frames or 0) + 1" },
                        { cmd = "WAIT", duration = 0.2 },
                    } },
                },
            },
        }
        local ctx = { session = s, loader = fakeLoader, party = s.party }
        sceneHost.init("fixed_wait", ctx)
        local state = sceneHost.getCurrentState()
        for _, dt in ipairs(chunks) do sceneHost.update(dt, ctx) end
        local frames, tick = state.v.frames, state.timeTick
        sceneHost.init(nil)
        return frames, tick
    end
    local largeFrames, largeTick = waitFrames({ 0.5 })
    local smallFrames, smallTick = waitFrames({ 0.1, 0.1, 0.1, 0.1, 0.1 })
    check(largeFrames == 3 and smallFrames == 3 and largeTick == 5 and smallTick == 5,
        "fixed Scene WAIT resumes identically under equivalent host-time chunking")
end

-- #386: catch-up belongs to one Scene instance. A transition during the first
-- logical tick ends the outgoing Scene's burst immediately; the incoming Scene
-- does not inherit the old accumulator or receive surprise ticks.
do
    local s = newSession()
    local fakeLoader = {
        scenes = {
            {
                id = "from", kind = "probe",
                update = { mode = "fixed", step = 0.1, maxCatchUp = 8 },
                hooks = { on_frame = {
                    { cmd = "SET_VAR", name = "frames", value = "(v.frames or 0) + 1" },
                    { cmd = "SCENE_EVENT", kind = "goto", scene = "to" },
                } },
            },
            {
                id = "to", kind = "probe",
                update = { mode = "fixed", step = 0.1, maxCatchUp = 8 },
                hooks = { on_enter = {
                    { cmd = "SET_VAR", name = "entered", value = "(v.entered or 0) + 1" },
                }, on_frame = {
                    { cmd = "SET_VAR", name = "frames", value = "(v.frames or 0) + 1" },
                } },
            },
        },
    }
    local ctx = { session = s, loader = fakeLoader, party = s.party }
    sceneHost.init("from", ctx)
    local outgoing = sceneHost.getCurrentState()
    sceneHost.update(0.5, ctx)
    local incoming = sceneHost.getCurrentState()
    check(outgoing.v.frames == 1 and sceneHost.getCurrent() == "to"
            and incoming.v.entered == 1 and incoming.v.frames == nil
            and incoming.updateAccumulator == 0,
        "Scene transition stops outgoing fixed catch-up and does not transfer backlog")
    sceneHost.init(nil)
end

-- #386 authored clock config fails before runtime use instead of accepting
-- unknown timing modes, non-positive steps, or unbounded catch-up values.
do
    local badMode = not pcall(sceneUpdateContract.resolve,
        { id = "bad_mode", update = { mode = "host", step = 0.1 } })
    local badStep = not pcall(sceneUpdateContract.resolve,
        { id = "bad_step", update = { mode = "fixed", step = 0 } })
    local badCatchUp = not pcall(sceneUpdateContract.resolve,
        { id = "bad_catch", update = { mode = "fixed", step = 0.1, maxCatchUp = 1.5 } })
    check(badMode and badStep and badCatchUp,
        "authored fixed Scene update contract rejects invalid mode/step/maxCatchUp")
end

-- #394: image-picture transforms are authored numeric-or-formula values. The
-- engine resolves them with the ordinary formula evaluator at command execution
-- time, after preceding SET_VAR writes, and presentation receives numbers only.
do
    local s = newSession()
    local json = require("data.json")
    local fixtureText = assert(love.filesystem.read("tests/fixtures/scene_picture_formula_probe.json"))
    local fixture = json.decode(fixtureText)
    local fakeLoader = { scenes = { fixture } }
    local shown, moved
    local previousPresentation = interpreter.bindPresentation({
        showImagePicture = function(spec) shown = spec end,
        moveImagePicture = function(spec) moved = spec end,
    })

    local ctx = { session = s, loader = fakeLoader, party = s.party }
    sceneHost.init("picture_formula_probe", ctx)
    local state = sceneHost.getCurrentState()
    check(state.v.ballX == 32 and state.v.ballY == 16,
        "authored Scene fixture owns picture X/Y in Scene-local v")
    check(shown and shown.x == 32 and shown.y == 16
            and shown.opacity == 1 and shown.scale == 1 and shown.rotation == 0
            and type(shown.x) == "number" and type(shown.y) == "number",
        "SHOW_IMAGE_PICTURE resolves all coherent transform formulas before presentation")

    sceneHost.runHook("on_right", ctx)
    check(state.v.ballX == 112 and state.v.ballY == 47,
        "ordinary SET_VAR arithmetic/clamp updates the Scene-local position state")
    check(moved and moved.x == 112 and moved.y == 47
            and type(moved.x) == "number" and type(moved.y) == "number",
        "MOVE_IMAGE_PICTURE consumes v/arithmetic/clamp expressions as numeric presentation values")

    moved = nil
    interpreter.runImmediate({ {
        cmd = "MOVE_IMAGE_PICTURE", id = 1, x = 9, y = 11,
        opacity = 0.5, scale = 2, rotation = 0.25, duration = 0,
    } }, { session = s, loader = loader, v = {} })
    check(moved and moved.x == 9 and moved.y == 11 and moved.opacity == 0.5
            and moved.scale == 2 and moved.rotation == 0.25,
        "literal numeric image transforms preserve their authored values")

    local function rejects(x)
        return not pcall(interpreter.runImmediate, { {
            cmd = "MOVE_IMAGE_PICTURE", id = 1, x = x, duration = 0,
        } }, { session = s, loader = loader, v = { ballX = 12 } })
    end
    check(rejects("v."), "malformed picture transform formulas fail loudly")
    check(rejects("v.missing + 1"), "unknown picture variables fail loudly instead of becoming zero")
    check(rejects("'not a number'"), "non-numeric picture formula results fail loudly")
    check(rejects("rawSession.gold"),
        "picture formula context does not gain privileged raw session access")

    interpreter.bindPresentation(previousPresentation)
    sceneHost.init(nil)

    -- The renderer still receives and interpolates the same numeric targets;
    -- formula knowledge was not moved into presentation.
    local imagePictures = require("presentation.image_picture_renderer")
    imagePictures.clear()
    imagePictures.show({
        id = 394, path = "assets/system/Cursor.png", x = 0, y = 0,
        opacity = 1, scale = 1, rotation = 0, anchor = "left", layer = "screen",
    })
    imagePictures.move({ id = 394, x = 100, y = 40, duration = 2, easing = "linear" })
    imagePictures.update(1)
    local halfway = imagePictures.get(394)
    check(halfway and halfway.x == 50 and halfway.y == 20 and halfway.motion ~= nil,
        "existing image-picture interpolation remains intact at mid-move")
    imagePictures.update(1)
    local finished = imagePictures.get(394)
    check(finished and finished.x == 100 and finished.y == 40 and finished.motion == nil,
        "existing image-picture interpolation still completes at the numeric target")
    imagePictures.clear()
end

-- Saves serialize GameSession/Map state, not an in-flight Event graph, walker,
-- Scene-local interpreter continuation, or scheduler process.
do
    local s = newSession()
    exploration.loadMap(s, 1)
    local payload = savegame.serialize(s, loader, "map")
    check(payload.map and payload.scene == "map" and payload.interpreter == nil
            and payload.eventProgram == nil and payload.processes == nil,
        "current save payload contains Map/session state but no Event continuation or process state")
end

print(string.format("=== Autorun/Parallel current model: %d passed, %d failed ===", passed, failed))
if failed > 0 then
    require("tests.fail_fast")("Autorun/Parallel current-model characterization failed", failed)
end
