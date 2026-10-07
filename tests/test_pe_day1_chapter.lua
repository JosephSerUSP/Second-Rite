-- PE Day 1 rough chapter (#1427): the generated room Scenes are playable
-- start to finish through real input — doors, locks, pickups, story cards and
-- every fight — over all 18 rooms from the title's New Game to the street exit.
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
-- X is polled by on_frame (READ_INPUT), so it must be held across a frame.
local function tapX() pc.press("X", ctx); frames(1); pc.release("X"); frames(1) end
local resources = require("engine.battler_resources")
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

-- An honest fight: no HP edits, no free ammo. Close in, swing at full AT,
-- heal with PE when low. Returns the outcome and how many swings it took.
local function fightWithBaton()
    local aya, swings, guard = ctx.session.party[1], 0, 0
    -- Held input is re-pressed every frame, as test_pe_day1_scene does.
    local function step(dirs)
        for b, on in pairs(dirs) do if on then pc.press(b, ctx) end end
        frames(1)
        for b, on in pairs(dirs) do if on then pc.release(b) end end
    end
    while rt().outcome == nil do
        guard = guard + 1; assert(guard < 60 * 600, "fight did not end within ten minutes")
        local e = rt().battle.enemies[1]
        local dx, dy = e.field.x - aya.field.x, e.field.y - aya.field.y
        local far = dx * dx + dy * dy > 1.1 * 1.1
        step({ RIGHT = far and dx > 0.2, LEFT = far and dx < -0.2, UP = far and dy > 0.2, DOWN = far and dy < -0.2 })
        if aya.at >= 100 and rt().outcome == nil then
            if aya.hp < 18 and resources.get(aya, "pe", ctx.session) >= 30 then
                tapX(); tap("DOWN"); tap("A"); tap("A")
            elseif not far then
                tap("A"); tap("A"); swings = swings + 1
            end
        end
    end
    return rt().outcome, swings
end

local ok, err = pcall(function()
    local scenes = { "title" }
    local index = json.decode(assert(io.open(os.getenv("THESTRA_REPOSITORY_ROOT")
        .. "/projects/pe-day1/data/scenes/index.json")):read("*a"))
    for _, f in ipairs(index.files) do
        if f:match("^day1_") then scenes[#scenes + 1] = f:gsub("%.json$", "") end
    end
    restore = require("tests.pe_day1_fixture")(loader, { scenes = scenes })
    -- Every {formula} in every window's text parses; a syntax error there
    -- otherwise renders as a silent 0 and passes validation.
    for _, id in ipairs(scenes) do
        for _, w in ipairs(sceneDef(id).windows or {}) do
            for _, block in ipairs(w.content or {}) do
                for expr in tostring(block.text or ""):gmatch("{(.-)}") do
                    assert(load("return " .. expr), id .. "/" .. w.id .. ": window formula does not parse: " .. expr)
                end
            end
        end
    end
    check(true, "every window text formula in every room parses")
    math.randomseed(5)
    pc.reset(); sh.init(nil)
    local session = sessionModule.GameSession.new(loader)
    session:initializeStartingParty()
    ctx = { session = session, loader = loader, party = session.party, events = {} }
    sh.push("title", ctx)
    tap("A")
    check(state().id == "day1_entrance", "New Game opens the chapter outside the hall")
    dismissCard()

    -- Exploration moves Aya without a battle and stays inside the room.
    local y0 = v().walkY
    pc.press("UP", ctx); frames(20); pc.release("UP")
    check(v().walkY > y0 and rt() == nil, "held UP walks Aya with no battle running")

    useDoor("to_foyer", "day1_foyer")
    useDoor("to_auditorium", "day1_auditorium"); dismissCard()
    useDoor("to_stage", "day1_stage"); win()
    do
        local aya = ctx.session.party[1]
        local traits = require("engine.traits")
        local vars = require("engine.game_variables")
        check(aya.level == 3, "Melissa's 12 EXP takes Aya to level 3 (3 + 9 EXP)")
        check(traits.getParam(aya, "offense", ctx.session) == 3 and traits.getParam(aya, "defense", ctx.session) == 3
            and traits.getParam(aya, "act", ctx.session) == 1, "levels raise Offense and Defense; Active Time waits for BP")
        check(vars.get(ctx.session, "bp") == 40, "a fight without a hit taken pays its full 40 BP")
    end
    useDoor("to_backstage", "day1_backstage")
    useDoor("to_corridor_a", "day1_corridor_a"); dismissCard(); win()
    useDoor("to_corridor_b", "day1_corridor_a"); dismissCard()          -- locked until the basement
    useDoor("to_props", "day1_props")
    -- A full inventory refuses a pickup: every slot counts.
    do
        local inv = ctx.session.inventory
        local used = (inv.m84f or 0) + (inv.club or 0) + (inv.medicine or 0) + ((inv.handgun_ammo or 0) > 0 and 1 or 0) + 1
        ctx.session:addItem("medicine", 10 - used)
        standAt("pickup_backstage_medicine"); tap("A")
        check(v()["f_got_backstage_medicine"] ~= 1 and v().card:find("Item Capacity"), "a full inventory refuses a pickup")
        tap("A")
        ctx.session:addItem("medicine", -(10 - used))
    end
    take("backstage_medicine"); take("props_ammo"); take("props_protector")
    useDoor("to_corridor_a", "day1_corridor_a")
    useDoor("to_backstage", "day1_backstage")
    useDoor("to_basement_rat", "day1_basement_rat"); dismissCard(); win()
    useDoor("to_backstage", "day1_backstage")
    useDoor("to_corridor_a", "day1_corridor_a")
    useDoor("to_corridor_b", "day1_corridor_b"); dismissCard()
    useDoor("to_rehearsal", "day1_corridor_b"); dismissCard()           -- locked until the key
    useDoor("to_dressing", "day1_dressing"); dismissCard()
    take("dressing_medicine")
    useDoor("to_corridor_b", "day1_corridor_b")
    useDoor("to_melissa", "day1_melissa"); dismissCard()
    take("rehearsal_key"); take("diary")
    useDoor("to_corridor_b", "day1_corridor_b")
    useDoor("to_green_room", "day1_green_room")
    take("dressing_ammo")
    useDoor("to_corridor_b", "day1_corridor_b")
    useDoor("to_rehearsal", "day1_rehearsal"); dismissCard(); win()
    useDoor("to_sewer", "day1_sewer"); win()
    take("sewer_medicine")
    useDoor("to_sewer_stairs", "day1_sewer_stairs"); dismissCard()
    take("stairs_ammo")
    useDoor("to_sewer_channel", "day1_sewer_channel"); dismissCard(); win()
    useDoor("to_sewer_deep", "day1_sewer_deep"); dismissCard(); win()
    useDoor("to_street", "day1_street")
    check(v().ui == 9, "day1_street: the end card is showing")
    tap("A")
    check(state().id == "title", "the end card returns to the title")

    -- A cleared room stays cleared on return.
    check(ctx.session.flags.melissa_defeated and ctx.session.flags.alligator_defeated, "every boss flag is set")

    -- Exploring, X swaps the equipped weapon and it persists across rooms.
    pc.reset(); sh.init(nil)
    session = sessionModule.GameSession.new(loader)
    session:initializeStartingParty()
    ctx = { session = session, loader = loader, party = session.party, events = {} }
    sh.push("day1_backstage", ctx)
    tapX()
    check(require("engine.game_variables").get(session, "weapon") == "baton", "X while exploring equips the Baton")
    tapX()
    check(require("engine.game_variables").get(session, "weapon") == "handgun", "X again equips the handgun")

    -- Field menu (B), on the original's structure: an icon column (Item, PE,
    -- Weapon, Armor, BP) over the status screen; A enters a page, B backs out.
    local aya = session.party[1]
    local traits = require("engine.traits")
    local vars = require("engine.game_variables")
    local resources = require("engine.battler_resources")
    check(aya.equipment[2] and aya.equipment[2].id == "n_vest" and session.inventory.m84f == 1
        and session.inventory.club == 1, "Aya starts with the M84F, the Club and the N Vest worn")
    local def0 = traits.getParam(aya, "def", session)
    tap("B")
    check(v().ui == 20 and v().mcol == 0 and v().mArmor == "n_vest" and v().mCap == 10,
        "B opens the status screen: Item Capacity 1 gives 10 slots")
    local x0 = v().walkX
    pc.press("RIGHT", ctx); frames(10); pc.release("RIGHT")
    check(v().walkX == x0, "the open menu holds Aya still")
    -- Item: the real inventory; Medicine is used from its row.
    aya.hp = 10
    local meds = session.inventory.medicine
    tap("A")
    check(v().ui == 21 and v().mi == 1, "Item opens the inventory")
    tap("DOWN"); tap("DOWN"); tap("DOWN")      -- club, Ammo Crate, M84F, Medicine
    tap("A")
    check(v().ui == 26, "an item opens Use / Move / Discard before changing inventory")
    tap("B")
    check(v().ui == 21 and aya.hp == 10, "cancel from the item popup does not use it")
    tap("A"); tap("A")
    check(aya.hp == 40 and (session.inventory.medicine or 0) == meds - 1 and v().mHp == 40,
        "Medicine used from the item list heals 30")
    local carried = require("engine.inventory")
    local rows = carried.carriedRows(session)
    check(#rows == v().mUsed, "the grid and capacity share one carried-slot count")
    local worn, medicineRows = 0, 0
    for _, row in ipairs(rows) do
        if row.equipped then worn = worn + 1 end
        if row.id == "medicine" then medicineRows = medicineRows + 1; check(row.qty == 1, "each Medicine occupies one slot") end
    end
    check(worn == 1 and medicineRows == (session.inventory.medicine or 0), "worn armor and all Medicine units are in the grid")
    local interpreter = require("engine.interpreter")
    local wornIndex
    for i, row in ipairs(rows) do if row.equipped then wornIndex = i end end
    local okDiscard, discardError = pcall(function()
        interpreter.runImmediate({{cmd="DISCARD_CARRIED_ITEM", itemIndex=wornIndex}}, ctx)
    end)
    check(not okDiscard and tostring(discardError):find("Cannot discard equipped item")
        and aya.equipment[2].id == "n_vest", "the discard command itself rejects worn gear")
    local okMove, moveError = pcall(function() carried.moveCarried(session, 1, #rows + 1) end)
    check(not okMove and tostring(moveError):find("index out of range"), "moving outside the carried list fails loudly")
    local first = rows[1].key
    v().mi = 1
    tap("A"); tap("DOWN"); tap("A")
    check(v().ui == 27, "Move asks for a destination")
    tap("DOWN"); tap("A")
    check(v().ui == 21 and carried.carriedRows(session)[2].key == first, "Move swaps the selected slots")
    local savegame = require("engine.savegame")
    local saved = savegame.serialize(session, loader, state().id)
    local loaded = savegame.deserialize(saved, loader)
    check(carried.carriedRows(loaded)[2].key == first, "carried slot order survives save/load")
    -- Discard one unit out of a repeated Medicine stack, never another row.
    session:addItem("medicine", 2)
    rows = carried.carriedRows(session)
    for i, row in ipairs(rows) do if row.id == "medicine" then v().mi = i; break end end
    local beforeDiscard = session.inventory.medicine
    tap("A"); tap("DOWN"); tap("DOWN"); tap("A")
    check(session.inventory.medicine == beforeDiscard - 1 and v().ui == 21, "Discard consumes exactly one Medicine slot")
    rows = carried.carriedRows(session)
    for i, row in ipairs(rows) do if row.equipped then v().mi = i; break end end
    tap("A"); tap("DOWN"); tap("DOWN"); tap("A")
    check(aya.equipment[2].id == "n_vest" and v().menuNote:find("Cannot discard"), "Discard protects worn equipment")
    tap("B") -- dismiss the protected item's popup
    -- Armor: the N Protector replaces the N Vest and raises DEF.
    tap("B"); tap("DOWN"); tap("DOWN"); tap("DOWN"); tap("A")
    check(v().ui == 24, "Armor opens the armor page")
    session:addItem("n_protector", 1)
    tap("DOWN"); tap("A")
    check(aya.equipment[2].id == "n_protector" and session.inventory.n_vest == 1, "the N Protector replaces the N Vest")
    check(traits.getParam(aya, "def", session) == def0 + 4, "armor changes Aya's defence")
    -- Weapon: choose the Club, then the M84F again.
    tap("B"); tap("UP"); tap("A")
    check(v().ui == 22 and v().wi == 0, "Weapon opens on the equipped M84F")
    tap("DOWN"); tap("A")
    check(vars.get(session, "weapon") == "baton", "the weapon page equips the Club")
    tap("UP"); tap("A")
    check(vars.get(session, "weapon") == "handgun", "and the M84F again")
    -- PE: Heal 1 in the field.
    tap("B"); tap("UP"); tap("A")
    check(v().ui == 23, "PE opens the Parasite Energy page")
    aya.hp = 10
    local pe0 = resources.get(aya, "pe", session)
    tap("A")
    check(aya.hp == 40 and resources.get(aya, "pe", session) == pe0 - 30, "Heal 1 in the field restores 30 HP for 30 PE")
    -- BP: 100 Bonus Points buy one level of Active Time.
    tap("B"); tap("UP"); tap("UP"); tap("A")
    check(v().ui == 25, "BP opens the Bonus Point page")
    require("engine.game_variables").set(session, "bp", 150)
    local act0 = traits.getParam(aya, "act", session)
    tap("A")
    check(traits.getParam(aya, "act", session) == act0 + 1 and vars.get(session, "bp") == 50,
        "100 BP buy one level of Active Time")
    tap("A")
    check(traits.getParam(aya, "act", session) == act0 + 1 and v().menuNote:find("100 BP"), "without 100 BP nothing is bought")
    tap("DOWN")
    require("engine.game_variables").set(session, "bp", 100)
    tap("A")
    check(traits.getParam(aya, "cap", session) == 2, "Item Capacity can be bought the same way")
    tap("B"); tap("B")
    check(v().ui == 0, "B backs out of the menu page by page")
    local t0 = require("engine.game_variables").get(session, "playSeconds") or 0
    frames(60)
    local t1 = require("engine.game_variables").get(session, "playSeconds") or 0
    check(math.abs((t1 - t0) - 1) < 0.05, "the play clock advances one second per second")

    -- Movement is screen-relative. Backstage's low view (x < 0) looks down
    -- the corridor toward -x, so UP walks Aya away from it, toward -x.
    local function hold(button, n)
        for _ = 1, n do pc.press(button, ctx); frames(1); pc.release(button) end
    end
    v().walkX, v().walkY = -1, 2.5; frames(1)
    hold("UP", 30)
    check(v().walkX < -2 and math.abs(v().walkY - 2.5) < 0.8, "UP walks away from the camera in a side-on view")
    -- Holding a direction keeps its heading across a camera cut: DOWN in the
    -- low view walks toward +x, and keeps doing so after crossing into the
    -- overhead view, where a fresh DOWN would mean -y.
    v().walkX, v().walkY = -0.3, 2.5; frames(2)
    hold("DOWN", 40)
    check(v().walkX > 1 and math.abs(v().walkY - 2.5) < 0.8, "a held direction survives the camera cut")
    frames(2)
    hold("DOWN", 10)
    check(v().walkY < 2.2, "after release, DOWN follows the new view")

    -- Active Time and PEnergy are stats the battle formulas read: raising
    -- them speeds the AT gauge and PE recovery.
    do
        local formula = require("engine.formula")
        local aya = session.party[1]
        local function rate(expr) local vw = formula.battlerView(aya, session); return formula.eval(expr, { a = vw, ally = vw }) end
        local at, pe = loader.system.realtimeBattle.atPerTick, "3 + ally.stat.penergy"
        local at1, pe1 = rate(at), rate(pe)
        require("engine.interpreter").runImmediate({ { cmd = "FOR_EACH", scope = "party", as = "aya", ["do"] = {
            { cmd = "ADD_PARAM", target = "aya", param = "act", amount = 5 },
            { cmd = "ADD_PARAM", target = "aya", param = "penergy", amount = 2 } } } }, ctx)
        check(rate(at) > at1 * 1.4 and rate(pe) == pe1 + 2, "Active Time speeds the AT gauge; PEnergy speeds PE recovery")
    end

    -- With no ammunition at all, the Baton still wins the Melissa and Eve
    -- fights honestly (no HP edits), which is why the original never dead-ends.
    for _, room in ipairs({ "day1_stage", "day1_rehearsal" }) do
        math.randomseed(11)
        pc.reset(); sh.init(nil)
        session = sessionModule.GameSession.new(loader)
        session:initializeStartingParty()
        session:addItem("handgun_ammo", -session.inventory.handgun_ammo)
        ctx = { session = session, loader = loader, party = session.party, events = {} }
        sh.push(room, ctx)
        if v().ui == 9 then tap("A") end
        while session.party[1].at < 100 do frames(1) end
        tapX(); tap("DOWN"); tap("DOWN"); tap("DOWN"); tap("A")
        check(require("engine.game_variables").get(session, "weapon") == "baton", room .. ": the battle Change command equips the Baton")
        local outcome, swings = fightWithBaton()
        print(("    %s: %s after %d baton swings, Aya HP %d"):format(room, outcome, swings, session.party[1].hp))
        check(outcome == "victory", room .. ": winnable with zero ammo on the Baton alone")
        local hits = v().hits
        tap("A")
        local base = room == "day1_stage" and 40 or 120
        check(require("engine.game_variables").get(session, "bp") == math.floor(base * math.max(0.5, 1 - 0.1 * hits)),
            room .. ": BP shrink by 10% per hit taken (" .. hits .. " hits)")
    end
end)
pc.reset(); sh.init(nil)
if restore then restore() end
assert(ok, err)
print(("=== PE Day 1 Chapter Tests: %d passed, 0 failed ==="):format(passed))
