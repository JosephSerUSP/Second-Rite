-- Follow the authored conversation with the actual compiler and GraphWalker.
local loader = require("engine.data.loader")
local interpreter = require("engine.interpreter")
local director = require("engine.director")
local quest = require("engine.quest")
loader.init()
local passed = 0
local function play(session, selections)
    local event
    for _, candidate in ipairs(loader.maps[loader.getMapIndex(29)].events) do
        if candidate.sprite == "assets/character/npc_laura.png" then event = candidate end
    end
    local ctx = {session=session, loader=loader, party=session.party}
    local graph = interpreter.runInteractive(assert(event).commands, ctx)
    local walker = director.GraphWalker.new(session, graph)
    local selected, shops = 0, 0
    for tick=1,120 do
        local node = walker:getCurrentNode()
        if not node then
            assert(selected == #selections, "Laura ended before the requested choices")
            return shops
        end
        if node.type == "CHOICE" then
            selected = selected + 1
            local label = assert(selections[selected], "Unexpected Laura menu")
            local index
            for i, option in ipairs(node.options) do if option.label == label then index=i end end
            assert(index, "Laura choice missing: "..label)
            walker:selectChoice(index)
        elseif node.type == "ACTION" then
            if node.action == "CALL_COMMON_EVENT_ACTION" then
                local commands = assert(loader.commonEvents[tostring(node.commonEventId)]).commands
                local first = interpreter.compileTop(graph.nodes, commands, "ce_"..tick, node.next, ctx)
                walker:goToNode(first)
            elseif node.action == "RUN_IMMEDIATE" then
                interpreter.runImmediate(node.commands, ctx); walker:advance()
            elseif node.action == "OFFER_QUEST" then
                quest.offer(session, loader, node.questId); walker:advance()
            elseif node.action == "COMPLETE_QUEST" then
                quest.complete(session, loader, node.questId); walker:advance()
            elseif node.action == "OPEN_SHOP" then
                assert(node.shopId == 8); shops = shops + 1; walker:advance()
            else error("Unhandled Laura action "..tostring(node.action)) end
        else walker:advance() end
    end
    error("Laura loops without returning to a choice or letting the player leave")
end
local function fresh()
    local session = require("engine.session").GameSession.new(loader)
    session:initializeStartingParty()
    return session
end
local function check(label, session, choices)
    local shops = play(session, choices)
    passed = passed + 1; print("  [PASS] "..label)
    return shops
end
check("Fresh greeting can be left", fresh(), {"Leave"})
local active = fresh(); quest.offer(active, loader, "shattered_blade_recovery")
check("Active blade quest without the blade can be left", active, {"Leave"})
check("Equipment topics and Back return to the main menu", fresh(),
    {"Ask about equipment", "Armor", "Weapons", "Back", "Leave"})
check("Quest offer returns to a usable main menu", fresh(),
    {"Found anything interesting?", "I'll keep an eye out.", "Leave"})
assert(check("Weapon shop returns to the main menu", fresh(), {"Buy Weapons", "Leave"}) == 1)
local ready = fresh(); quest.offer(ready, loader, "shattered_blade_recovery"); ready:addItem(26, 1)
check("Reforging completes once and still allows leaving", ready, {"Leave"})
assert(ready.flags.shattered_blade_reforged and ready.flags['quest:shattered_blade_recovery:completed'])
assert(not ready:hasItem(26, 1), "Reforging did not consume the quest blade")
check("Completed quest can be revisited without locking the menu", ready, {"Leave"})
print("=== Weaponsmith Dialogue: "..passed.." passed ===")
