package.path = package.path .. ";../?.lua;?.lua"

if not _G.love then
    _G.love = {
        filesystem = {
            getInfo = function() return false end,
            read = function() return "{}" end
        }
    }
end

local session = require("engine.session")
local inventory = require("engine.inventory")
local loader = require("engine.data.loader")
local targeting = require("engine.targeting")
local usability = require("engine.usability")
local interpreter = require("engine.interpreter")
local progress = require("engine.progress")
local progression = require("engine.progression")
local scene_host = require("engine.scene_host")

loader.init()

local passed = 0
local failed = 0

local function test(name, fn)
    local ok, err = pcall(fn)
    if ok then
        print("  [PASS] " .. name)
        passed = passed + 1
    else
        print("  [FAIL] " .. name)
        print("         " .. tostring(err))
        failed = failed + 1
    end
end

local function rowFor(entry, param)
    for _, row in ipairs((entry and entry.rows) or {}) do
        if row.param == param then return row end
    end
end

print("=== Testing Item Menu Targeting, Usability & Effect Feedback ===")

test("targeting.expand handles 'none' spec", function()
    local exp = targeting.expand("none")
    assert(exp.side == "none", "side should be none")
    assert(exp.count == 0, "count should be 0")
end)

test("canUseItem validates no-target items (Mystic Egg, MP drinks)", function()
    local sess = session.GameSession.new(loader)
    sess.mp = sess.maxMp -- MP full

    local mpItem = loader.getItem(29) -- Mug of Ale
    assert(mpItem, "Mug of Ale item should exist")
    assert(mpItem.target == "none", "Mug of Ale target should be none")

    local ok, reason = usability.canUseItem(mpItem, nil, { session = sess, isField = true })
    assert(not ok, "Should not be usable when MP is full")
    assert(reason == "MP is already full", "Reason mismatch: " .. tostring(reason))

    sess.mp = 0
    local ok2, _ = usability.canUseItem(mpItem, nil, { session = sess, isField = true })
    assert(ok2, "Should be usable when MP is not full")
end)

test("USE_ITEM command handles target: 'none' items without single-target selection (recruits exactly 1 with random name)", function()
    local sess = session.GameSession.new(loader)
    sess:addItem(11, 1) -- Mystic Egg (id 11)
    local hero = session.Battler.new(loader.getUnit("pixie"), 1)
    sess.party = { hero, session.Battler.new(loader.getUnit("high_pixie"), 1) }

    local ctx = {
        session = sess,
        loader = loader,
        sceneState = { tab = 1, state = 1, idx = 1 }
    }

    interpreter.runImmediate({ { cmd = "USE_ITEM", itemIndex = 1, target = 0 } }, ctx)

    assert(ctx.sceneState.lastItemResult and ctx.sceneState.lastItemResult.success == true, "USE_ITEM should succeed")
    assert(ctx.sceneState.state == 3, "State should transition to 3 (popup)")
    assert(ctx.sceneState.popupText:find("joins you"), "Popup text should mention recruitment feedback")
    assert((sess.inventory[11] or 0) == 0, "Item should be consumed")
    assert(#sess.party == 3, "Party count should increase from 2 to 3 (recruiting exactly 1 creature, not 4)")

    local eggBattler = sess.party[3]
    assert(eggBattler and eggBattler.actorData.id == "egg", "Recruited creature should be Egg actor (id 15)")
    local namesSet = {}
    for _, n in ipairs(eggBattler.actorData.names or {}) do namesSet[n] = true end
    assert(namesSet[eggBattler.name] == true, "Recruited Egg should receive a random name from names list, got: " .. tostring(eggBattler.name))
end)

test("USE_ITEM single-target item enters state 2 when usable", function()
    local sess = session.GameSession.new(loader)
    sess:addItem(1, 1) -- HP Tonic (id 1)
    local hero = session.Battler.new({ id = "hero", name = "Hero", hp = 10, maxHp = 50, level = 1 }, 1)
    hero.hp = 10
    sess.party = { hero }

    local ctx = {
        session = sess,
        loader = loader,
        sceneState = { tab = 1, state = 1, idx = 1 }
    }

    interpreter.runImmediate({ { cmd = "USE_ITEM", itemIndex = 1, target = 0 } }, ctx)

    assert(ctx.sceneState.state == 2, "State should transition to 2 (target selection)")
    assert(ctx.sceneState.targetIdx == 1, "Target index should default to 1")
    assert((sess.inventory[1] or 0) == 1, "Item should NOT be consumed before target pick")
end)

test("Detailed effect feedback for stat-up and skill learning", function()
    local sess = session.GameSession.new(loader)
    sess:addItem(45, 1) -- Tome: Wind Blade
    sess:addItem(46, 1) -- Whetstone Draught
    local hero = session.Battler.new({ id = "hero", name = "Hero", hp = 50, maxHp = 50, atk = 10, level = 1 }, 1)
    sess.party = { hero }

    -- Test Tome: Wind Blade (learn_skill)
    local ctx = {
        session = sess,
        loader = loader,
        sceneState = { tab = 1, state = 2, idx = 1, targetIdx = 1 }
    }

    interpreter.runImmediate({ { cmd = "USE_ITEM", itemIndex = 1, target = 1 } }, ctx)
    assert(ctx.sceneState.lastItemResult.success == true, "Learn skill item should succeed")
    assert(ctx.sceneState.popupText:find("Hero learns Wind Blade"), "Feedback text should include skill name: " .. tostring(ctx.sceneState.popupText))

    -- Test Whetstone Draught (param_plus ATK)
    ctx.sceneState.state = 1
    ctx.sceneState.idx = 1
    interpreter.runImmediate({ { cmd = "USE_ITEM", itemIndex = 1, target = 1 } }, ctx)
    assert(ctx.sceneState.lastItemResult.success == true, "Param plus item should succeed")
    assert(ctx.sceneState.popupText:find("ATK rises by 2"), "Feedback text should include stat boost details: " .. tostring(ctx.sceneState.popupText))
end)

test("carriedRows expands units, collapses authored stacks, keeps worn equipment, and preserves moves", function()
    local items = {
        [1] = { id = 1, name = "Tonic", icon = 1, type = "item", description = "heal" },
        [2] = { id = 2, name = "Ammo", icon = 2, type = "item", description = "rounds",
            meta = { carriedStack = true } },
    }
    local armor = { id = 6, name = "Bone Plate", icon = 6, type = "equipment", description = "armor" }
    local fake = {
        inventory = { [1] = 2, [2] = 12 },
        loader = { getItem = function(id) return items[id] end },
        party = { { equipment = { [2] = armor } } },
    }

    local rows = inventory.carriedRows(fake)
    assert(#rows == 4, "two ordinary units + one authored stack + worn equipment should make four rows")
    assert(rows[1].key == "item:1:1" and rows[2].key == "item:1:2",
        "ordinary quantities should occupy one stable row per unit")
    assert(rows[3].key == "item:2:1" and rows[3].qty == 12,
        "carriedStack should collapse the authored quantity into one row")
    assert(rows[4].key == "equip:1:2" and rows[4].equipped == true,
        "worn equipment must stay visible in the carried projection")

    inventory.moveCarried(fake, 4, 1)
    local moved = inventory.carriedRows(fake)
    assert(moved[1].key == "equip:1:2" and moved[4].key == "item:2:1",
        "moveCarried should persist row order by stable key")
    assert(fake.inventory[1] == 2 and fake.inventory[2] == 12,
        "moving carried rows must never mutate authoritative quantities")

    local ok = pcall(function() inventory.moveCarried(fake, 0, 1) end)
    assert(not ok, "moveCarried should reject out-of-range indices")
end)

test("Actor Change reports a permanent stat item without requiring a level-up", function()
    local sess = session.GameSession.new(loader)
    local hero = sess:recruitActor("pixie", 1)
    sess:addItem(46, 1) -- Whetstone Draught: permanent ATK +2

    local before = progress.snapshot(sess)
    local ctx = {
        session = sess,
        loader = loader,
        sceneState = { tab = 1, state = 2, idx = 1, targetIdx = 1 }
    }
    interpreter.runImmediate({ { cmd = "USE_ITEM", itemIndex = 1, target = 1 } }, ctx)

    local changes = progress.changes(sess, before)
    assert(#changes == 1, "stat-up item should produce exactly one durable Actor Change")
    assert(changes[1].kind == "attribute", "stat-only change should classify as attribute")
    assert(changes[1].fromLevel == changes[1].toLevel, "stat item should not pretend a level was gained")
    local atk = rowFor(changes[1], "atk")
    assert(atk and atk.delta == 2, "Actor Change should report the actual +2 ATK delta")
    assert(#changes[1].rows == 1, "stat-only report should omit unchanged parameters")
    assert(hero == sess.party[1], "reporting must not replace or mutate the creature")
end)

test("Actor Change reports skillbook learning as durable development", function()
    local sess = session.GameSession.new(loader)
    -- Pixie already knows Wind Blade, so use a real creature whose authored
    -- starting skill set does not contain it; this test is about learning,
    -- not the already-known no-op guarded by item usability.
    sess:recruitActor("cerberus", 1)
    sess:addItem(45, 1) -- Tome: Wind Blade

    local before = progress.snapshot(sess)
    local ctx = {
        session = sess,
        loader = loader,
        sceneState = { tab = 1, state = 2, idx = 1, targetIdx = 1 }
    }
    interpreter.runImmediate({ { cmd = "USE_ITEM", itemIndex = 1, target = 1 } }, ctx)

    local changes = progress.changes(sess, before)
    assert(#changes == 1, "skillbook should produce one durable Actor Change")
    assert(changes[1].kind == "skill", "skill-only change should classify as skill")
    assert(#changes[1].learnedSkills == 1 and changes[1].learnedSkills[1] == "Wind Blade",
        "Actor Change should name the learned skill")
    assert(changes[1].noteText:find("Wind Blade"), "presentation note should mention Wind Blade")
end)

test("Actor Change ignores equipment", function()
    local sess = session.GameSession.new(loader)
    local hero = sess:recruitActor("pixie", 1)
    local traits = require("engine.traits")
    local hp0 = traits.getParam(hero, "maxHp", sess)
    sess:addItem(6, 1) -- Bone Plate (Armor)
    local before = progress.snapshot(sess)
    interpreter.runImmediate({ { cmd = "EQUIP_ITEM", slot = 2, target = 1, itemIndex = 2 } },
        { session = sess, loader = loader, sceneState = {} })
    assert(hero.equipment[2] and hero.equipment[2].id == 6, "control: the armor is worn")
    assert(traits.getParam(hero, "maxHp", sess) == hp0 + 3, "control: the armor's +3 max HP applies")
    assert(#progress.changes(sess, before) == 0, "putting on armor must not be reported as Actor Change")
end)

test("Actor Change ignores ordinary HP healing", function()
    local sess = session.GameSession.new(loader)
    local hero = sess:recruitActor("pixie", 1)
    hero.hp = 1
    sess:addItem(1, 1) -- HP Tonic

    local before = progress.snapshot(sess)
    local ctx = {
        session = sess,
        loader = loader,
        sceneState = { tab = 1, state = 2, idx = 1, targetIdx = 1 }
    }
    interpreter.runImmediate({ { cmd = "USE_ITEM", itemIndex = 1, target = 1 } }, ctx)

    assert(hero.hp > 1, "control: HP Tonic should actually heal")
    assert(#progress.changes(sess, before) == 0,
        "transient HP recovery must not be misreported as durable Actor Change")
end)

test("Items Scene routes durable item use into Actor Change presentation", function()
    local sess = session.GameSession.new(loader)
    sess:recruitActor("pixie", 1)
    sess:addItem(46, 1) -- Whetstone Draught
    local ctx = { session = sess, loader = loader }

    scene_host.init("items", ctx)
    local v = scene_host.getCurrentState().v
    v.state = 2
    v.idx = 1
    v.targetIdx = 1

    assert(scene_host.runHook("on_select", ctx), "items on_select hook should be handled")

    assert(v.state == 3, "item semantics should retain the ordinary resolved-use state underneath the overlay")
    assert(v.actorChangeCount == 1 and v.actorChangeIndex == 1,
        "single-target durable item should publish one selected Actor Change")
    assert(v.actorChangeTitle == "ATTRIBUTE UP!",
        "stat-up item should receive the semantic Actor Change heading")
    assert(type(v.levelUpRows) == "table" and #v.levelUpRows == 1,
        "existing levelUpStats renderer should receive the changed stat row")
    assert(v.levelUpRows[1].param == "atk" and v.levelUpRows[1].delta == 2,
        "published Actor Change should contain the actual ATK delta")

    assert(scene_host.runHook("on_select", ctx), "select should dismiss the last Actor Change report")
    assert(v.actorChangeCount == 0 and v.actorChanges == nil,
        "dismissing the report should clear retained Actor Change data")
    assert(v.state == 1, "dismissing the report should return to normal item browsing")
end)

test("Items Scene leaves ordinary healing on the existing popup path", function()
    local sess = session.GameSession.new(loader)
    local hero = sess:recruitActor("pixie", 1)
    hero.hp = 1
    sess:addItem(1, 1) -- HP Tonic
    local ctx = { session = sess, loader = loader }

    scene_host.init("items", ctx)
    local v = scene_host.getCurrentState().v
    v.state = 2
    v.idx = 1
    v.targetIdx = 1

    assert(scene_host.runHook("on_select", ctx), "items on_select hook should be handled")

    assert(hero.hp > 1, "control: healing item should resolve normally")
    assert(v.state == 3, "non-durable item should retain ordinary popup state")
    assert((v.actorChangeCount or 0) == 0 and v.actorChanges == nil,
        "healing should not manufacture Actor Change entries")
    assert((v.popupTimer or 0) > 0, "ordinary healing feedback should keep its popup timer")
end)

test("map/common fallback reports an out-of-battle GRANT_XP transaction", function()
    local sess = session.GameSession.new(loader)
    local hero = sess:recruitActor("pixie", 1)
    local ctx = { session = sess, loader = loader, party = sess.party }

    scene_host.init("map", ctx)
    scene_host.getCurrentState().v.mode = 0 -- map's authored on_select delegates to host fallback

    local previous = scene_host.bindPlayerInput({
        fallback = function()
            interpreter.runImmediate({
                { cmd = "GRANT_XP", target = "target", amount = progression.nextLevelExp(hero.level) },
            }, {
                session = sess,
                loader = loader,
                target = hero,
                a = hero,
                events = {},
            })
            return true
        end,
    })

    local handled
    local ok, err = pcall(function()
        handled = scene_host.buttonpressed("A", ctx)
    end)
    scene_host.bindPlayerInput(previous)
    assert(ok, err)

    assert(handled == true, "fallback input should remain handled")
    assert(sess.party[1].level == 2, "control: authored GRANT_XP crosses the level threshold")
    assert(scene_host.getCurrent() == "actor_change" and scene_host.getPrevious() == "map",
        "resolved field-event development should open the generic Actor Change modal")
    local v = scene_host.getCurrentState().v
    assert(v.actorChangeTitle == "LEVEL UP!" and v.actorChangeFromLevel == 1 and v.actorChangeToLevel == 2,
        "fallback report should describe the complete resolved level transaction")

    assert(scene_host.runHook("on_select", ctx), "Actor Change modal should dismiss through authored input")
    assert(scene_host.getCurrent() == "map", "dismissing the report should return to the field map")
end)

print("=== Item Menu Tests Completed: " .. passed .. " passed, " .. failed .. " failed ===")
assert(failed == 0, "Some item menu unit tests failed!")
