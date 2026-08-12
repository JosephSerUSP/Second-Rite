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
