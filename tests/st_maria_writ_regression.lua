local M = {}

function M.run(check)
    local loader = require("engine.data.loader")
    local session = require("engine.session")
    local interpreter = require("engine.interpreter")
    local exploration = require("engine.exploration")
    local conditions = require("engine.conditions")
    local savegame = require("engine.savegame")
    local json = require("engine.data.json")

    local town = loader.maps[1]
    local registrar, gate
    for _, ev in ipairs(town.events) do
        if ev.label == "Registrar Celina" then registrar = ev end
        if ev.name == "Labyrinth Gate" then gate = ev end
    end
    local writ = registrar.commands[1].elseCommands[3]
    local enter = loader.commonEvents["43"].commands
    local climb = loader.commonEvents["40"].commands[2].options[1].commands[1].commands

    check(writ.cmd == "CHANGE_ITEM" and tonumber(writ.item) == 198
            and gate.commands[1].condition == "hasItem:198"
            and enter[1].flag == "dungeon_entered"
            and enter[5].cmd == "LOAD_MAP" and tonumber(enter[5].mapId) == 2
            and climb[1].flag == "first_return"
            and climb[3].cmd == "LOAD_MAP" and tonumber(climb[3].mapId) == 1,
        "authored St. Maria Writ and transfer path is intact")

    local s = session.GameSession.new(loader)
    s:initializeStartingParty()
    exploration.loadMap(s, 1)
    local ctx = { session = s, loader = loader, party = s.party, events = {}, v = {} }
    local matched, allowed = conditions.evalPrefixed(gate.commands[1].condition, s)
    check(matched and not allowed, "the Labyrinth gate is closed before the Writ")

    interpreter.runImmediate({ writ }, ctx)
    matched, allowed = conditions.evalPrefixed(gate.commands[1].condition, s)
    check(s:hasItem(198) and matched and allowed, "Celina's Writ opens the gate")

    interpreter.runImmediate({ enter[1], enter[5] }, ctx)
    check(s.currentMapData.id == 2 and s.flags.dungeon_entered and s:hasItem(198),
        "entering the First Stratum keeps the Writ")

    interpreter.runImmediate({ climb[1], climb[3] }, ctx)
    matched, allowed = conditions.evalPrefixed(gate.commands[1].condition, s)
    check(s.currentMapData.id == 1 and s.flags.first_return and s:hasItem(198)
            and matched and allowed,
        "returning to St. Maria keeps the Writ")

    local decoded = json.decode(json.encode(savegame.serialize(s, loader, "town")))
    check(decoded.inventory["198"] == 1 and decoded.inventory[198] == nil,
        "JSON decoding exposes the Writ inventory key as a string")

    local restored = savegame.deserialize(decoded, loader)
    matched, allowed = conditions.evalPrefixed(gate.commands[1].condition, restored)
    check(restored.inventory[198] == 1 and restored.inventory["198"] == nil
            and restored:hasItem(198) and matched and allowed,
        "save/load restores the Writ and the authored gate accepts it")
end

return M
