local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local exploration = require("engine.exploration")
local interpreter = require("engine.interpreter")
local director = require("engine.director")
local scene_host = require("engine.scene_host")
local validator = require("engine.validator_core")
local failFast = require("tests.fail_fast")

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

local function errors(fn)
    local ok, err = pcall(fn)
    return not ok, err
end

print("[TEST] Starting Map/Common SCENE_EVENT non-returning goto transfer tests (#708)...")

-- 1. Compilation: SCENE_EVENT is isolated from RUN_IMMEDIATE and sets next = nil
do
    local commands = {
        { cmd = "SET_VAR", name = "step1", value = "1" },
        { cmd = "SCENE_EVENT", kind = "goto", scene = "options", vars = { { name = "entryArg", value = "42" } } },
        { cmd = "SET_VAR", name = "step2", value = "2" },
    }
    local ctx = { loader = loader }
    local graph = interpreter.buildGraph("TestEvent", commands, ctx)
    check(graph ~= nil, "buildGraph compiles command list containing SCENE_EVENT")
    check(graph.nodes["node_1"] ~= nil and graph.nodes["node_1"].type == "ACTION" and graph.nodes["node_1"].action == "RUN_IMMEDIATE",
        "command before SCENE_EVENT is isolated in its own RUN_IMMEDIATE node")
    check(graph.nodes["node_1"].next == "node_2",
        "RUN_IMMEDIATE node chains to SCENE_EVENT node")
    check(graph.nodes["node_2"] ~= nil and graph.nodes["node_2"].type == "ACTION" and graph.nodes["node_2"].action == "SCENE_EVENT",
        "SCENE_EVENT compiles to dedicated ACTION node")
    check(graph.nodes["node_2"].next == nil,
        "SCENE_EVENT node is terminal (next == nil)")
    check(graph.nodes["node_2"].kind == "goto" and graph.nodes["node_2"].scene == "options",
        "SCENE_EVENT preserves kind and target scene")
end

-- 2. Execution in Map Event: mutates state, switches scene, terminal by construction
do
    local s = sessionModule.GameSession.new(loader)
    s:initializeStartingParty()
    exploration.loadMap(s, 1)

    scene_host.init("map", { session = s, loader = loader, party = s.party or {} })
    check(scene_host.getCurrent() == "map", "scene_host initialized on 'map'")

    local commands = {
        { cmd = "SET_FLAG", flag = "executedPrior", value = true },
        { cmd = "SCENE_EVENT", kind = "goto", scene = "options", vars = { { name = "targetVar", value = "100 + 23" } } },
        { cmd = "SET_FLAG", flag = "executedAfter", value = true },
    }

    local ictx = { session = s, loader = loader, party = s.party }
    local graph = interpreter.runInteractive(commands, ictx)
    local walker = director.GraphWalker.new(s, graph)

    -- Step 1: RUN_IMMEDIATE executes prior command
    local node = walker:getCurrentNode()
    check(node and node.type == "ACTION" and node.action == "RUN_IMMEDIATE", "walker starts on RUN_IMMEDIATE")
    local events = interpreter.runImmediate(node.commands, { session = s, loader = loader, party = s.party })
    walker:advance()

    -- Step 2: SCENE_EVENT execution (mirrors main.lua handleDialogueAction)
    local sceneNode = walker:getCurrentNode()
    check(sceneNode and sceneNode.type == "ACTION" and sceneNode.action == "SCENE_EVENT", "walker reaches SCENE_EVENT")

    local vars = nil
    if type(sceneNode.vars) == "table" then
        vars = {}
        local formulaEngine = require("engine.formula")
        local fctx = formulaEngine.makeContext(s.party, s)
        for _, a in ipairs(sceneNode.vars) do
            if type(a) == "table" and a.name then
                local val, ferr = formulaEngine.eval(a.value, fctx)
                if not ferr then vars[a.name] = val end
            end
        end
    end

    scene_host.goto_scene(sceneNode.scene, { session = s, loader = loader, party = s.party or {} }, vars)
    walker = nil -- invalidated on transition

    check(scene_host.getCurrent() == "options", "scene_host transitioned to 'options'")
    local state = scene_host.getCurrentState()
    check(state and state.v and state.v.targetVar == 123, "target scene received evaluated vars")
    check(s.flags.executedPrior == true, "prior command mutation occurred")
    check(s.flags.executedAfter == nil, "command after SCENE_EVENT never executed")
end

-- 3. Common Event called from Map Event: discards caller continuation
do
    local s = sessionModule.GameSession.new(loader)
    s:initializeStartingParty()
    exploration.loadMap(s, 1)

    scene_host.init("map", { session = s, loader = loader, party = s.party or {} })

    -- Register a mock common event that does SCENE_EVENT goto
    loader.commonEvents = loader.commonEvents or {}
    loader.commonEvents["999"] = {
        id = 999,
        name = "Ending Transfer CE",
        commands = {
            { cmd = "SET_FLAG", flag = "ceRan", value = true },
            { cmd = "SCENE_EVENT", kind = "goto", scene = "title" },
            { cmd = "SET_FLAG", flag = "ceAfter", value = true },
        }
    }

    local mapEventCommands = {
        { cmd = "CALL_COMMON_EVENT", commonEventId = 999 },
        { cmd = "SET_FLAG", flag = "mapCallerContinuation", value = true },
    }

    local ictx = { session = s, loader = loader, party = s.party }
    local graph = interpreter.runInteractive(mapEventCommands, ictx)
    local walker = director.GraphWalker.new(s, graph)

    local callNode = walker:getCurrentNode()
    check(callNode and callNode.type == "ACTION" and callNode.action == "CALL_COMMON_EVENT_ACTION",
        "walker starts on CALL_COMMON_EVENT_ACTION")

    -- Simulate main.lua CALL_COMMON_EVENT_ACTION handler:
    local ce = loader.commonEvents["999"]
    local prefix = "ce_999_test"
    local firstCeNode = interpreter.compileTop(walker.graph.nodes, ce.commands, prefix, callNode.next, ictx)
    walker:goToNode(firstCeNode)

    -- Step CE command 1: SET_FLAG
    local ceNode1 = walker:getCurrentNode()
    check(ceNode1 and ceNode1.type == "ACTION" and ceNode1.action == "RUN_IMMEDIATE", "CE starts with RUN_IMMEDIATE")
    interpreter.runImmediate(ceNode1.commands, { session = s, loader = loader, party = s.party })
    walker:advance()

    -- Step CE command 2: SCENE_EVENT
    local ceNode2 = walker:getCurrentNode()
    check(ceNode2 and ceNode2.type == "ACTION" and ceNode2.action == "SCENE_EVENT", "CE reaches SCENE_EVENT")
    check(ceNode2.next == nil, "CE SCENE_EVENT node is terminal (does not point to map caller continuation)")

    scene_host.goto_scene(ceNode2.scene, { session = s, loader = loader, party = s.party or {} })
    walker = nil

    check(scene_host.getCurrent() == "title", "scene_host transitioned to 'title'")
    check(s.flags.ceRan == true, "CE prior mutation occurred")
    check(s.flags.ceAfter == nil, "CE command after SCENE_EVENT never ran")
    check(s.flags.mapCallerContinuation == nil, "Map event caller continuation never ran")
end

-- 4. Validator: validates SCENE_EVENT in map and common contexts
do
    local function validateWithCommands(hostKind, cmds)
        local mock = {}
        for k, v in pairs(loader) do mock[k] = v end
        if hostKind == "map" then
            mock.maps = {
                {
                    id = 1, name = "Test Map", layout = { "###", "###" },
                    events = {
                        { id = 1, x = 0, y = 0, trigger = "action", commands = cmds }
                    }
                }
            }
        elseif hostKind == "common" then
            mock.commonEvents = {
                ["999"] = { id = 999, name = "Test CE", commands = cmds }
            }
        elseif hostKind == "scene" then
            mock.scenes = {
                { id = "test_scene", kind = "menu", hooks = { on_enter = cmds } }
            }
        end
        local ok, err = pcall(validator.run, mock)
        return ok, tostring(err)
    end

    local okMapGoto, errMapGoto = validateWithCommands("map", {
        { cmd = "SCENE_EVENT", kind = "goto", scene = "options" }
    })
    check(okMapGoto or not errMapGoto:find("SCENE_EVENT"), "validator accepts SCENE_EVENT kind='goto' in map context")

    local okMapPush, errMapPush = validateWithCommands("map", {
        { cmd = "SCENE_EVENT", kind = "push", scene = "options" }
    })
    check(not okMapPush and errMapPush:find("only supports kind='goto'"), "validator rejects SCENE_EVENT kind='push' in map context")

    local okMapPop, errMapPop = validateWithCommands("map", {
        { cmd = "SCENE_EVENT", kind = "pop" }
    })
    check(not okMapPop and errMapPop:find("only supports kind='goto'"), "validator rejects SCENE_EVENT kind='pop' in map context")

    local okCommonGoto, errCommonGoto = validateWithCommands("common", {
        { cmd = "SCENE_EVENT", kind = "goto", scene = "title" }
    })
    check(okCommonGoto or not errCommonGoto:find("SCENE_EVENT"), "validator accepts SCENE_EVENT kind='goto' in common context")

    local okCommonPush, errCommonPush = validateWithCommands("common", {
        { cmd = "SCENE_EVENT", kind = "push", scene = "title" }
    })
    check(not okCommonPush and errCommonPush:find("only supports kind='goto'"), "validator rejects SCENE_EVENT kind='push' in common context")

    local okScenePush, errScenePush = validateWithCommands("scene", {
        { cmd = "SCENE_EVENT", kind = "push", scene = "options" }
    })
    check(okScenePush or not errScenePush:find("SCENE_EVENT"), "validator accepts SCENE_EVENT kind='push' in scene context")

    local okScenePop, errScenePop = validateWithCommands("scene", {
        { cmd = "SCENE_EVENT", kind = "pop" }
    })
    check(okScenePop or not errScenePop:find("SCENE_EVENT"), "validator accepts SCENE_EVENT kind='pop' in scene context")
end

print(string.format("[TEST] Completed #708 tests: %d passed, %d failed", passed, failed))
if failed > 0 then
    error(string.format("%d tests failed in test_scene_event_map_transfer.lua", failed))
end
