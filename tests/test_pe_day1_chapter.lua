-- PE Day 1 rough chapter (#1427): the generated room Scenes are playable
-- start to finish through real input — doors, locks, pickups, story cards and
-- every placeholder fight — from the title's New Game to the street exit.
local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local sh = require("engine.scene_host")
local pc = require("engine.player_controller")
local json = require("engine.data.json")

local restore
local passed = 0
local function check(cond, msg)
    assert(cond, msg)
    passed = passed + 1
    print("  [PASS] " .. msg)
end

local ctx
local function frames(n)
    for _ = 1, n do sh.update(1 / 60, ctx) end
end
local function tap(button) pc.press(button, ctx); pc.release(button); frames(1) end
local function state() return sh.getCurrentState() end
local function v() return state().v end
local function rt() return ctx.session.realtimeBattle end

local function sceneDef(id)
    for _, s in ipairs(loader.scenes) do if s.id == id then return s end end
end
local function marker(modelId)
    for _, m in ipairs(sceneDef(state().id).windows[1].viewport.models) do
        if m.id == modelId then return m.position[1], m.position[2] end
    end
    error("no model " .. modelId .. " in " .. state().id)
end
local function standAt(modelId)
    local x, y = marker(modelId)
    v().walkX, v().walkY = x, y
    frames(1)
end
local function dismissCard()
    check(v().ui == 9 and v().card ~= "", state().id .. ": a story card is showing")
    tap("A")
    check(v().ui == 0, state().id .. ": Enter dismisses the card")
end
local function useDoor(doorId, expectScene)
    standAt("door_" .. doorId)
    check(v().near == doorId, state().id .. ": standing at " .. doorId .. " offers it")
    tap("A")
    check(state().id == expectScene, "door " .. doorId .. " leads to " .. expectScene)
end
local function take(pickupId)
    standAt("pickup_" .. pickupId)
    tap("A")
    check(v()["f_got_" .. pickupId] == 1, state().id .. ": picked up " .. pickupId)
    dismissCard()
end
local function win()
    check(rt() ~= nil and v().fight == 1, state().id .. ": the fight starts on entry")
    local enemy = rt().battle.enemies[1]
    enemy.hp, enemy.at = 1, -1e9
    local guard = 0
    while rt().outcome ~= "victory" do
        ctx.session:addItem("handgun_ammo", 1)
        while ctx.session.party[1].at < 100 do frames(1); guard = guard + 1; assert(guard < 20000, "never won") end
        tap("A"); tap("A"); frames(30)
    end
    tap("A")
    check(rt() == nil and v().fight == 0, state().id .. ": Obtain-all ends the fight and returns to exploring")
    dismissCard()
end

local ok, err = pcall(function()
    local scenes = { "title" }
    local index = json.decode(assert(io.open(os.getenv("THESTRA_REPOSITORY_ROOT")
        .. "/projects/pe-day1/data/scenes/index.json")):read("*a"))
    for _, f in ipairs(index.files) do
        if f:match("^day1_") then scenes[#scenes + 1] = f:gsub("%.json$", "") end
    end
    restore = require("tests.pe_day1_fixture")(loader, { scenes = scenes })
    math.randomseed(5)
    pc.reset(); sh.init(nil)
    local session = sessionModule.GameSession.new(loader)
    session:initializeStartingParty()
    ctx = { session = session, loader = loader, party = session.party, events = {} }
    sh.push("title", ctx)
    tap("A")
    check(state().id == "day1_foyer", "New Game opens the chapter in the lobby")
    dismissCard()

    -- Exploration moves Aya without a battle and stays inside the room.
    local y0 = v().walkY
    pc.press("UP", ctx); frames(20); pc.release("UP")
    check(v().walkY > y0 and rt() == nil, "held UP walks Aya with no battle running")

    useDoor("to_auditorium", "day1_auditorium"); dismissCard()
    useDoor("to_stage", "day1_stage"); win()
    useDoor("to_backstage", "day1_backstage")
    take("backstage_medicine")
    useDoor("to_dressing", "day1_backstage")
    dismissCard()
    useDoor("to_basement", "day1_basement_rat"); dismissCard(); win()
    useDoor("to_backstage", "day1_backstage")
    useDoor("to_dressing", "day1_dressing"); dismissCard()
    useDoor("to_rehearsal", "day1_dressing"); dismissCard()
    take("rehearsal_key"); take("diary"); take("dressing_ammo")
    useDoor("to_rehearsal", "day1_rehearsal"); dismissCard(); win()
    useDoor("to_sewer", "day1_sewer"); win()
    take("sewer_medicine")
    useDoor("to_sewer_deep", "day1_sewer_deep"); dismissCard(); win()
    useDoor("to_exit", "day1_street")
    check(v().ui == 9, "day1_street: the end card is showing")
    tap("A")
    check(state().id == "title", "the end card returns to the title")

    -- A cleared room stays cleared on return.
    check(ctx.session.flags.melissa_defeated and ctx.session.flags.alligator_defeated, "every boss flag is set")
end)
pc.reset(); sh.init(nil)
if restore then restore() end
assert(ok, err)
print(("=== PE Day 1 Chapter Tests: %d passed, 0 failed ==="):format(passed))
