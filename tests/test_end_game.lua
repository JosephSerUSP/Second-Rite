-- #708: Map/Common Event programs need a canonical authored ending that
-- returns to title without leaving a stale GraphWalker continuation behind.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local interpreter = require("engine.interpreter")
local director = require("engine.director")
local sceneHost = require("engine.scene_host")

print("[TEST] Starting END_GAME tests...")

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

loader.init()

local function newSession()
    local s = sessionModule.GameSession.new(loader)
    s:initializeStartingParty()
    return s
end

local endDef
for _, def in ipairs((loader.engine and loader.engine.commands) or {}) do
    if def.id == "END_GAME" then
        endDef = def
        break
    end
end
local contexts = {}
for _, id in ipairs((endDef and endDef.contexts) or {}) do contexts[id] = true end
check(endDef ~= nil and #(endDef.params or {}) == 0,
    "END_GAME is a registered zero-arity command")
check(endDef and endDef.interactive == true
        and #(endDef.contexts or {}) == 2
        and contexts.map == true and contexts.common == true
        and contexts.scene ~= true and contexts.battle_phase ~= true,
    "END_GAME is authorable exactly in Map/Common Event contexts")
check(interpreter.isImplemented("END_GAME"),
    "registry implementation coverage recognizes END_GAME")

do
    local s = newSession()
    local ctx = { session = s, loader = loader, recoverParty = function() end }
    local graph = interpreter.runInteractive({
        { cmd = "SET_FLAG", flag = "before_end", value = true },
        { cmd = "END_GAME" },
        { cmd = "SET_FLAG", flag = "after_end", value = true },
    }, ctx)
    local walker = director.GraphWalker.new(s, graph)
    local before = walker:getCurrentNode()
    check(before and before.type == "ACTION" and before.action == "RUN_IMMEDIATE"
            and before.commands and #before.commands == 1,
        "Map Event compilation stops the immediate batch before END_GAME")
    interpreter.runImmediate(before.commands, { session = s, loader = loader, party = s.party })
    walker:advance()
    local terminal = walker:getCurrentNode()
    check(s.flags.before_end == true and s.flags.after_end ~= true,
        "commands before END_GAME commit while commands after it have not run")
    check(terminal and terminal.type == "ACTION" and terminal.action == "END_GAME"
            and terminal.next == nil,
        "END_GAME compiles as a terminal action node with no continuation")
    walker:advance()
    check(walker:getCurrentNode() == nil and s.flags.after_end ~= true,
        "advancing a reached END_GAME cannot resume the old Map Event tail")
end

do
    local s = newSession()
    local ctx = { session = s, loader = loader, recoverParty = function() end }
    local graph = interpreter.runInteractive({
        { cmd = "CALL_COMMON_EVENT", commonEventId = 9001 },
        { cmd = "SET_FLAG", flag = "caller_after_end", value = true },
    }, ctx)
    local walker = director.GraphWalker.new(s, graph)
    local callNode = walker:getCurrentNode()
    local firstCommon = interpreter.compileTop(walker.graph.nodes, {
        { cmd = "SET_FLAG", flag = "common_before_end", value = true },
        { cmd = "END_GAME" },
        { cmd = "SET_FLAG", flag = "common_after_end", value = true },
    }, "ce_end_probe", callNode.next, {
        session = s, loader = loader, recoverParty = function() end,
    })
    walker:goToNode(firstCommon)
    local before = walker:getCurrentNode()
    interpreter.runImmediate(before.commands, { session = s, loader = loader, party = s.party })
    walker:advance()
    local terminal = walker:getCurrentNode()
    check(s.flags.common_before_end == true
            and s.flags.common_after_end ~= true
            and s.flags.caller_after_end ~= true,
        "Common Event work before END_GAME commits without returning to caller work")
    check(terminal and terminal.action == "END_GAME" and terminal.next == nil,
        "an injected Common Event END_GAME discards its caller continuation")
    walker:advance()
    check(walker:getCurrentNode() == nil
            and s.flags.common_after_end ~= true
            and s.flags.caller_after_end ~= true,
        "Common Event END_GAME cannot resume either common or caller tail")
end

do
    local s = newSession()
    local ok = pcall(interpreter.runImmediate, {
        { cmd = "END_GAME" },
    }, { session = s, loader = loader, party = s.party })
    check(not ok,
        "immediate/battle-style execution refuses the interactive END_GAME command")
end

do
    local s = newSession()
    local fakeLoader = {
        scenes = {
            {
                id = "map_probe", kind = "probe",
                hooks = { on_select = {
                    { cmd = "SCENE_EVENT", kind = "goto", scene = "title_probe" },
                } },
            },
            { id = "title_probe", kind = "probe", hooks = {} },
        },
    }
    local ctx = { session = s, loader = fakeLoader, party = s.party }
    sceneHost.init("map_probe", ctx)
    sceneHost.runHook("on_select", ctx)
    check(sceneHost.getCurrent() == "title_probe",
        "the existing scene_change seam is consumed by scene_host for Return-to-Title")
    sceneHost.init(nil)
end

print(string.format("=== END_GAME: %d passed, %d failed ===", passed, failed))
if failed > 0 then
    require("tests.fail_fast")("END_GAME tests failed", failed)
end
