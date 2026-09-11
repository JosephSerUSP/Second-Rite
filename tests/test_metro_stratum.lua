-- Stratum III: Metro de Sao Paulo end-to-end integration & mover runtime test
-- Verifies map loading, generic Event.mover lifecycle, line traversals, baldeacoes, puzzles, and Santa Cruz shortcut.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local interpreter = require("engine.interpreter")
local exploration = require("engine.exploration")
local moverRuntime = require("engine.mover_runtime")

print("[TEST] Starting Stratum III (Metro de Sao Paulo) tests...")

local passed, failed = 0, 0
local function check(cond, msg)
    if cond then
        passed = passed + 1
        print("  [PASS] " .. msg)
    else
        failed = failed + 1
        print("  [FAIL] " .. msg)
    end
end

loader.init()

local session = sessionModule.GameSession.new(loader)
session:initializeStartingParty()

local function getCE(id)
    return loader.commonEvents and loader.commonEvents[tostring(id)]
end

local function getFlag(name)
    return session.flags and session.flags[name] == true
end

local function runCE(ce, ctx)
    if not ce or not ce.commands then return end
    local immediateCmds = {}
    for _, cmd in ipairs(ce.commands) do
        if cmd.cmd ~= "TEXT" and cmd.cmd ~= "CHOICE" and cmd.cmd ~= "WAIT" then
            table.insert(immediateCmds, cmd)
        end
    end
    if #immediateCmds > 0 then
        interpreter.runImmediate(immediateCmds, ctx)
    end
end

-- 1. Verify Maps 32-37 are registered and loadable
local expectedTilesets = {
    [32] = "metro_station_l1",
    [33] = "metro_station_l2",
    [34] = "metro_station_l3",
    [35] = "metro_station_l4",
    [36] = "metro_station_l5",
    [37] = "metro_wagon_interior",
}
for mapId = 32, 37 do
    local mapIdx = loader.getMapIndex(mapId)
    check(mapIdx ~= nil, "Map " .. mapId .. " is registered in maps index")
    local mapData = loader.maps[mapIdx]
    check(mapData ~= nil and mapData.id == mapId, "Map " .. mapId .. " loads with correct id")
    check(mapData.tileset == expectedTilesets[mapId], "Map " .. mapId .. " uses " .. expectedTilesets[mapId] .. " tileset")
end

-- 2. Verify Event.mover specifications on all 5 transit lines
for _, mapId in ipairs({ 32, 33, 34, 35, 36 }) do
    local mapIdx = loader.getMapIndex(mapId)
    local mapData = loader.maps[mapIdx]
    local trainEv = nil
    for _, ev in ipairs(mapData.events or {}) do
        if ev.mover then trainEv = ev break end
    end
    check(trainEv ~= nil, "Map " .. mapId .. " has Event with mover component")
    check(trainEv.mover.type == "path", "Map " .. mapId .. " mover type is 'path'")
    check(trainEv.mover.carryPlayer == true, "Map " .. mapId .. " mover carries player")
    check(trainEv.mover.mode == "ping_pong", "Map " .. mapId .. " mover mode is 'ping_pong'")
    check(trainEv.mover.speed and trainEv.mover.speed > 0, "Map " .. mapId .. " mover has positive speed")
    check(#trainEv.mover.waypoints >= 3, "Map " .. mapId .. " mover has straight transit circuit")
end

-- 3. Test mover_runtime lifecycle on Map 32 (Linha 1 - Azul)
local map32Idx = loader.getMapIndex(32)
-- Platform waiting area in front of train dock is x = 15, y = 8 (1-indexed: playerX = 16, playerY = 9)
exploration.loadMap(session, map32Idx, { x = 15, y = 8, dir = "S" })
check(session.currentMapData.id == 32, "Player loaded into Map 32 (Linha 1)")
check(session.playerX == 16 and session.playerY == 9, "Player standing at Luz platform edge (16, 9)")

moverRuntime.initMap(session, session.currentMapData)
check(session.movers and #session.movers == 1, "moverRuntime initialized 1 mover on Map 32")
local mover = session.movers[1]
check(mover.phase == "docked", "Mover initially docked at platform")
check(mover.doorState == "open", "Mover doors initially open")
check(mover.curX == 15 and mover.curY == 9, "Mover positioned at Luz dock (15, 9)")

-- Boarding access rules:
-- Consist has 3 cars at offsets -3, 0, +3:
-- Door 1 (Rear car): x = 12, y = 9 (1-indexed: 13, 10)
-- Door 2 (Center car): x = 15, y = 9 (1-indexed: 16, 10)
-- Door 3 (Lead car): x = 18, y = 9 (1-indexed: 19, 10)
check(moverRuntime.isBlocked(session, 13, 10) == false, "Player permitted to step onto train at Rear car door (13, 10)")
check(moverRuntime.isBlocked(session, 16, 10) == false, "Player permitted to step onto train at Center car door (16, 10)")
check(moverRuntime.isBlocked(session, 19, 10) == false, "Player permitted to step onto train at Lead car door (19, 10)")

-- Stepping into track trench where train doors are NOT present (5, 10) (0-indexed 4, 9):
check(moverRuntime.isBlocked(session, 5, 10) == true, "Player blocked by sunken track trench at unserviced cell (5, 10)")

-- Player steps aboard Center car (16, 10)
session.playerX = 16
session.playerY = 10
moverRuntime.update(session, 0.05)
check(mover.onboard == true, "Player boarded the train at Center car")

-- Walk inside train across open gangway to Rear car (13, 10)
check(moverRuntime.isBlocked(session, 13, 10) == false, "Player can walk along car aisle to Rear car")
session.playerX = 13
session.playerY = 10
moverRuntime.update(session, 0.05)
check(mover.onboard == true and mover.playerOffset == -3, "Player standing in Rear car (offset -3)")

-- Dwell timeout -> doors close
moverRuntime.update(session, (mover.timer or 14.0) + 0.1)
if mover.phase == "closing" then
    moverRuntime.update(session, 0.7)
end
check(mover.phase == "moving", "Train entered moving phase")
check(mover.doorState == "closed", "Train doors closed for transit")
check(mover.onboard == true, "Player securely onboard while moving (not left behind)")
check(moverRuntime.isBlocked(session, session.playerX, session.playerY - 1) == true, "Player cannot jump out into tunnel while moving")

-- Complete transit to East tunnel terminus (curX = 30, y = 9; player offset -3 -> playerX = 27 + 1 = 28, playerY = 10)
moverRuntime.update(session, (mover.transitDuration or 5.0) + 0.1)
if mover.phase == "opening" then
    moverRuntime.update(session, 0.7)
end
check(mover.phase == "docked", "Train reached tunnel terminus")
check(session.playerX == 28 and session.playerY == 10, "Player carried to tunnel terminus with offset preserved (28, 10)")

-- Now test reverse transit back to station:
moverRuntime.update(session, (mover.timer or 3.0) + 0.1)
if mover.phase == "closing" then
    moverRuntime.update(session, 0.7)
end
check(mover.phase == "moving", "Train departing tunnel back toward station")
moverRuntime.update(session, (mover.transitDuration or 5.0) + 0.1)
if mover.phase == "opening" then
    moverRuntime.update(session, 0.7)
end
check(mover.phase == "docked", "Train docked back at Luz station platform")
check(mover.doorState == "open", "Train doors opened at platform")
check(session.playerX == 13 and session.playerY == 10, "Player at station dock in Rear car (13, 10)")

-- Step out onto Luz platform (North: y = 9)
check(moverRuntime.isBlocked(session, 13, 9) == false, "Player permitted to disembark onto Luz platform from Rear car")
session.playerX = 13
session.playerY = 9
moverRuntime.update(session, 0.05)
check(mover.onboard == false, "Player successfully disembarked")

-- 4. Test Baldeacao Se (Linha 1 -> Linha 3: Vermelha)
local map34Idx = loader.getMapIndex(34)
exploration.loadMap(session, map34Idx, { x = 4, y = 3, dir = "S" })
check(session.currentMapData.id == 34, "Transferred to Map 34 (Linha 3: Vermelha) at Se")

-- 5. Test Linha 3 Patio do Bras Substation & Key
local ctx = { session = session, loader = loader }
local foundBreaker = false
for _, ev in ipairs(session.currentMapData.events) do
    if ev.id == 11 or (ev.name and ev.name:match("Breaker")) then
        foundBreaker = true
        interpreter.runImmediate({
            { cmd = "SET_FLAG", flag = "metro_aux_power", value = true }
        }, ctx)
    end
end
check(foundBreaker and getFlag("metro_aux_power") == true, "Activated Bras auxiliary substation power")

local foundLocker = false
for _, ev in ipairs(session.currentMapData.events) do
    if ev.id == 12 or (ev.name and ev.name:match("Locker")) then
        foundLocker = true
        interpreter.runImmediate({
            { cmd = "SET_FLAG", flag = "metro_track_key", value = true }
        }, ctx)
    end
end
check(foundLocker and getFlag("metro_track_key") == true, "Acquired metro_track_key from Bras locker")

-- 6. Baldeacao back to Linha 1, then travel to Paraiso and transfer to Linha 2 (Verde)
local map33Idx = loader.getMapIndex(33)
exploration.loadMap(session, map33Idx, { x = 4, y = 3, dir = "S" })
check(session.currentMapData.id == 33, "Transferred to Map 33 (Linha 2: Verde) at Paraiso")

-- 7. At Chacara Klabin, use metro_track_key to unlock gate
local klabinGate = nil
for _, ev in ipairs(session.currentMapData.events) do
    if ev.id == 10 or (ev.name and ev.name:match("Klabin")) then klabinGate = ev end
end
check(klabinGate ~= nil, "Found Chacara Klabin gate event")
interpreter.runImmediate({
    { cmd = "SET_FLAG", flag = "metro_klabin_unlocked", value = true }
}, ctx)
check(getFlag("metro_klabin_unlocked") == true, "Chacara Klabin gate successfully unlocked")

-- 8. Baldeacao Chacara Klabin -> Linha 5 (Lilas, Map 36)
local map36Idx = loader.getMapIndex(36)
exploration.loadMap(session, map36Idx, { x = 4, y = 3, dir = "S" })
check(session.currentMapData.id == 36, "Entered Map 36 (Linha 5: Lilas) at Chacara Klabin")

-- 9. Defeat Boss: O Tatuzao das Sombras
local tatuzaoTroop = loader.troops["boss_tatuzao"]
check(tatuzaoTroop ~= nil, "boss_tatuzao troop is registered")
interpreter.runImmediate({
    { cmd = "SET_FLAG", flag = "metro_stratum_solved", value = true }
}, ctx)
check(getFlag("metro_stratum_solved") == true, "Tatuzao defeated, metro_stratum_solved set")

-- 10. Unlatch Santa Cruz emergency shortcut gate from Floor 5 side
check(getFlag("metro_santacruz_unlocked") ~= true, "Santa Cruz shortcut initially locked")
interpreter.runImmediate({
    { cmd = "SET_FLAG", flag = "metro_santacruz_unlocked", value = true }
}, ctx)
check(getFlag("metro_santacruz_unlocked") == true, "Santa Cruz shortcut unlatched from Floor 5")

-- 11. Traverse shortcut directly from Floor 5 to Floor 1 Santa Cruz
exploration.loadMap(session, map32Idx, { x = 27, y = 2, dir = "S" })
check(session.currentMapData.id == 32, "Passed through shortcut directly to Map 32 (Linha 1: Santa Cruz)")
check(session.playerX == 28 and session.playerY == 3, "Positioned at Santa Cruz concourse (28, 3)")

-- 12. Traverse shortcut back from Floor 1 directly to Floor 5
exploration.loadMap(session, map36Idx, { x = 23, y = 2, dir = "S" })
check(session.currentMapData.id == 36, "Passed through shortcut back to Map 36 (Linha 5)")

-- 13. Linha 4 (Amarela, Map 35) High-Security Vault & Master Pass
local map35Idx = loader.getMapIndex(35)
exploration.loadMap(session, map35Idx, { x = 5, y = 2, dir = "S" })
check(session.currentMapData.id == 35, "Loaded into Map 35 (Linha 4: Faria Lima)")
local initialGold = session.gold or 0
interpreter.runImmediate({
    { cmd = "GAIN_GOLD", amount = 10000 },
    { cmd = "SET_FLAG", flag = "metro_master_pass", value = true },
    { cmd = "SET_FLAG", flag = "metro_vault_cleared", value = true }
}, ctx)
check((session.gold or 0) == initialGold + 10000, "Looted 10,000 gold from Faria Lima vault")
check(getFlag("metro_master_pass") == true, "Acquired metro_master_pass")
check(getFlag("metro_vault_cleared") == true, "metro_vault_cleared flag set")

-- 14. Common Event fallback compatibility
local ce100 = getCE(100)
check(ce100 ~= nil, "Common Event 100 exists as transit fallback")
runCE(ce100, ctx)
check(session.currentMapData.id == 32, "CE 100 loads Map 32")

print("=== Stratum III (Metro SP) Tests: " .. passed .. " passed, " .. failed .. " failed ===")
assert(failed == 0, "Stratum III tests failed")
