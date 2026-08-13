local loader = require("data.loader")
local session = require("engine.session")
local input_map = require("engine.input_map")
local scene_host = require("engine.scene_host")
local player_controller = require("engine.player_controller")
local run_record = require("engine.player_run_record")
local player_observation = require("presentation.player_observation")
local window_renderer = require("presentation.window_renderer")
local json = require("data.json")

local CANONICAL = {
    "A", "B", "X", "Y", "L", "R", "START", "SELECT",
    "UP", "DOWN", "LEFT", "RIGHT",
}

local expected = {}
for _, button in ipairs(CANONICAL) do expected[button] = true end

local bindingCount = 0
for button in pairs(input_map.getBindings()) do
    assert(expected[button], "input map exposes invented logical control: " .. tostring(button))
    bindingCount = bindingCount + 1
end
assert(bindingCount == #CANONICAL, "canonical logical control set changed")
for _, button in ipairs(CANONICAL) do
    assert(player_controller.isButton(button), "controller rejects canonical control: " .. button)
end
for _, button in ipairs({ "CONFIRM", "ATTACK", "MENU", "up", "" }) do
    assert(not player_controller.isButton(button), "controller accepts invented control: " .. button)
end

local s = session.GameSession.new(loader)
s:initializeStartingParty()
local ctx = { session = s, loader = loader, party = s.party or {} }

local function currentObservation()
    local sceneData = scene_host.getCurrentSceneData(ctx)
    assert(sceneData, "current Scene definition must be observable")
    return player_observation.capture(sceneData, scene_host.getCurrentState(), ctx)
end

local function findWindow(observation, id)
    for _, win in ipairs(observation.windows or {}) do
        if win.id == id then return win end
    end
    return nil
end

-- Real authored Scene proof: logical controller input converges on the ordinary
-- title hooks and the observation comes back through presentation resolution.
scene_host.init("title", ctx)
local titleLabels = loader.getTermList("title.options", {})
assert(#titleLabels >= 4, "title fixture needs the ordinary four menu choices")

local first = currentObservation()
assert(first.scene == "title", "first player observation must identify Title")
local titleWindow = assert(findWindow(first, "title_menu"), "title menu must be visible")
assert(titleWindow.selected == titleLabels[1], "initial selected title label disagrees with presentation")

local run = run_record.new({
    id = "player-membrane-fixture",
    project = { id = "second-rite-test" },
    runtime = { kind = "love2d" },
    start = { kind = "scene", id = "title" },
})
run_record.append(run, { frame = 0, observation = first })

for frame = 1, 3 do
    assert(player_controller.press("DOWN", ctx), "Title DOWN should be handled by authored Scene hook")
    run_record.append(run, {
        frame = frame,
        input = { button = "DOWN", phase = "press" },
        observation = currentObservation(),
    })
end

local onOptions = currentObservation()
titleWindow = assert(findWindow(onOptions, "title_menu"), "title menu vanished")
assert(titleWindow.selected == titleLabels[4], "three DOWN presses must select authored Options row")
assert(player_controller.press("A", ctx), "Title A should be handled by authored Scene hook")
local optionsObservation = currentObservation()
assert(scene_host.getCurrent() == "options" and optionsObservation.scene == "options",
    "A on Options must follow the ordinary authored Scene transition")
run_record.append(run, {
    frame = 4,
    input = { button = "A", phase = "press" },
    observation = optionsObservation,
})
run_record.finish(run, { status = "checkpoint", checkpoint = "options" })
assert(run.outcome.checkpoint == "options", "run recorder did not keep final checkpoint")

-- Recorder vocabulary is mechanically the same set the controller accepts.
local vocabularyRun = run_record.new({ project = { id = "vocab" }, runtime = { id = "test" } })
for i, button in ipairs(CANONICAL) do
    run_record.append(vocabularyRun, {
        frame = i,
        input = { button = button, phase = "press" },
        observation = { version = 1, scene = "fixture", windows = {} },
    })
end
local beforeInvalid = #vocabularyRun.steps
local acceptedInvented = pcall(run_record.append, vocabularyRun, {
    frame = 99,
    input = { button = "ATTACK", phase = "press" },
    observation = { version = 1, scene = "fixture", windows = {} },
})
assert(not acceptedInvented, "run record accepted an invented semantic control")
assert(#vocabularyRun.steps == beforeInvalid, "invalid input mutated the run record")

-- Negative fairness fixture. The authoritative presentation resolver is first
-- shown to contain hidden/full/offscreen material internally; the public player
-- projection must then remove every part the current presentation cannot prove
-- visible. FILTER_SECRET is removed even earlier by the renderer's own filter.
local fairnessScene = {
    id = "fairness_fixture",
    windows = {
        {
            id = "filtered_scroller",
            style = "list",
            rect = { x = 1, y = 1, w = 20, h = 6 },
            visibleRows = 2,
            content = {
                {
                    type = "list",
                    listId = "static:SAFE,FILTER_SECRET,VISIBLE2,OFFSCREEN_SECRET",
                    cursor = "1",
                    filter = "name ~= 'FILTER_SECRET'",
                    format = "{name}",
                },
            },
        },
        {
            id = "hidden_secret",
            style = "frame",
            rect = { x = 1, y = 8, w = 20, h = 4 },
            visible = "false",
            content = { { type = "text", text = "HIDDEN_SECRET" } },
        },
        {
            id = "revealing_secret",
            style = "frame",
            rect = { x = 1, y = 13, w = 20, h = 4 },
            content = { { type = "text", text = "SAFE PREFIX REVEAL_SECRET", reveal = "0" } },
        },
    },
}
local fairnessState = {
    id = "fairness_fixture",
    v = { privateBackingFact = "BACKING_SECRET" },
    winState = {},
    windowOrder = {},
}
local resolved = window_renderer.resolveDataState(fairnessScene, ctx, fairnessState)
local resolvedScroller = assert(findWindow(resolved, "filtered_scroller"), "resolved fixture list missing")
local resolvedRows = {}
for _, row in ipairs(resolvedScroller.rows or {}) do resolvedRows[row.text] = true end
assert(not resolvedRows.FILTER_SECRET, "renderer filter retained filtered secret row")
assert(resolvedRows.OFFSCREEN_SECRET, "fixture must contain an offscreen secret before projection")
local resolvedJson = json.encode(resolved)
assert(resolvedJson:find("HIDDEN_SECRET", 1, true), "fixture must contain hidden-window text before projection")
assert(resolvedJson:find("REVEAL_SECRET", 1, true), "fixture must contain unrevealed text before projection")

local fairObservation = player_observation.capture(fairnessScene, fairnessState, ctx)
local fairJson = json.encode(fairObservation)
assert(fairJson:find("SAFE", 1, true), "visible selected label was lost")
for _, secret in ipairs({
    "FILTER_SECRET", "OFFSCREEN_SECRET", "HIDDEN_SECRET", "REVEAL_SECRET", "BACKING_SECRET",
}) do
    assert(not fairJson:find(secret, 1, true), "player observation leaked " .. secret)
end
assert(not findWindow(fairObservation, "hidden_secret"), "hidden window crossed player membrane")

print("test_player_membrane: OK")
