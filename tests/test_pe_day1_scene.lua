-- PE Day 1 basement_rat (#1424): the ported Scene drives the real-time
-- scheduler through its own input hooks. Domain facts come from rt.*; the
-- Scene keeps only menus and presentation.
local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local sh = require("engine.scene_host")
local pc = require("engine.player_controller")
local resources = require("engine.battler_resources")

local restore
local passed = 0
local function check(cond, msg)
    assert(cond, msg)
    passed = passed + 1
    print("  [PASS] " .. msg)
end

local ctx
local function frames(n, input)
    for _ = 1, n do
        if input then pc.press(input, ctx) end
        sh.update(1 / 60, ctx)
        if input then pc.release(input) end
    end
end
local function tap(button) pc.press(button, ctx); pc.release(button) end
local function tapX() pc.press("X", ctx); frames(1); pc.release("X"); frames(1) end
local function rt() return ctx.session.realtimeBattle end
local function aya() return ctx.session.party[1] end
local function untilReady()
    local guard = 0
    while aya().at < 100 do frames(1); guard = guard + 1; assert(guard < 2000, "AT never filled") end
end
local function begin()
    math.randomseed(3)
    pc.reset(); sh.init(nil)
    local session = sessionModule.GameSession.new(loader)
    session:initializeStartingParty()
    ctx = { session = session, loader = loader, party = session.party, events = {} }
    sh.push("basement_rat", ctx)
    rt().battle.enemies[1].at = -1e9
end

local ok, err = pcall(function()
    restore = require("tests.pe_day1_fixture")(loader, { scenes = { "basement_rat" } })

    begin()
    check(rt() ~= nil and rt().battle.enemies[1].hp == 20, "entering the scene starts the basement_rat battle")
    local v = sh.getCurrentState().v
    for _, field in ipairs({ "hp", "ehp", "atb", "pe", "ammo", "medicine", "px", "ex" }) do
        assert(v[field] == nil, "domain field sceneState." .. field .. " must not exist")
    end
    check(true, "no domain facts live in scene state")

    -- Held movement drives the scheduler's player position.
    local x0 = aya().field.x
    frames(30, "RIGHT")
    check(aya().field.x > x0, "held RIGHT moves Aya through the scheduler")

    -- The command menu pauses the battle clock.
    untilReady()
    tapX()
    v = sh.getCurrentState().v
    check(v.ui == 1, "X at full AT opens the command menu")
    local tick = rt().tick
    frames(30)
    check(rt().tick == tick and rt().paused, "the battle clock is paused while the menu is open")

    -- P. Energy -> Heal 1 pays from Aya's own PE.
    aya().hp = 10
    tap("DOWN"); tap("A")
    check(sh.getCurrentState().v.ui == 3, "the PE menu opens")
    tap("A")
    check(aya().hp == 40 and (resources.get(aya(), "pe", ctx.session)) == 70,
        "Heal 1 from the menu restores 30 HP for 30 PE")
    frames(2)
    check(not rt().paused and sh.getCurrentState().v.ui == 0, "resolving a command resumes the battle")

    -- Item -> Medicine through Battle:applyItem.
    untilReady()
    aya().hp = 20
    tapX(); tap("DOWN"); tap("DOWN"); tap("A"); tap("A")
    check(aya().hp == aya():getMaxHp(ctx.session) and (ctx.session.inventory.medicine or 0) == 0,
        "Medicine from the menu heals and is consumed")

    -- Enter at full AT aims, Enter again fires one round.
    untilReady()
    local ammo = ctx.session.inventory.handgun_ammo
    tap("A")
    check(sh.getCurrentState().v.ui == 2, "Enter at full AT aims")
    tap("A")
    check(ctx.session.inventory.handgun_ammo == ammo - 1, "Enter again fires one round")

    -- Escape from the menu ends the battle; Enter replays from a fresh session.
    untilReady()
    tapX(); tap("DOWN"); tap("DOWN"); tap("DOWN"); tap("A")
    check(rt().outcome == "escaped", "Escape from the menu ends the battle as escaped")
    tap("A")
    check(rt() and rt().outcome == nil and rt().battle.enemies[1].hp == 20
        and ctx.session.inventory.handgun_ammo == 11, "Enter replays a fresh encounter")

    -- Esc outside a menu ends the battle and leaves the scene.
    tap("B")
    check(ctx.session.realtimeBattle == nil, "Esc discards the real-time battle on leaving")
end)
pc.reset(); sh.init(nil)
if restore then restore() end
assert(ok, err)
print(("=== PE Day 1 Scene Tests: %d passed, 0 failed ==="):format(passed))
