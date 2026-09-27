-- tests/test_metro_stratum.lua
-- Comprehensive integration test suite for Stratum III (Sao Paulo Metro Stratum)
-- Covers:
-- 1. Loader & Tileset Integrity (Maps 32-37, tilesets, troops, zero injectProbability)
-- 2. Generic Mover Runtime Kinematics (multi-car consist, waypoints, door states, player carrying, barrier blocking)
-- 3. Save / Load Mover State Round-Trip (asserts mover state and player tracking survive save/load while moving)
-- 4. Authored Event & Choice Integration via director.GraphWalker:
--    - Substation Breaker (Map 34): negative vs positive choices, Page 1 -> Page 2 progression
--    - Foreman Locker (Map 34): acquiring track key
--    - Chacara Klabin Gate (Map 33): negative lock, unlock choice with key, Map 36 transfer
--    - Santa Cruz Shortcut (Maps 32 & 36): directional locking, lever unlock, reciprocal transfers
--    - Boss Tatuzao (Map 36): victory commands, flag setting, Page 2 progression
--    - Baldeacoes: verified transfers between lines

package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local exploration = require("engine.exploration")
local interpreter = require("engine.interpreter")
local director = require("engine.director")
local savegame = require("engine.savegame")
local moverRuntime = require("engine.mover_runtime")

if not loader.maps then
    loader.init()
end

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

local function newSession()
    local s = sessionModule.GameSession.new(loader)
    s:initializeStartingParty()
    return s
end

local function runWalkerToCompletion(walker, choices, ctx)
    local cIdx = 1
    while walker:getCurrentNode() do
        local node = walker:getCurrentNode()
        if node.type == "ACTION" and node.action == "RUN_IMMEDIATE" then
            interpreter.runImmediate(node.commands, ctx)
            walker:advance()
        elseif node.type == "CHOICE" then
            local pick = choices[cIdx] or 1
            cIdx = cIdx + 1
            walker:selectChoice(pick)
        else
            walker:advance()
        end
    end
end

print("[TEST] Starting Stratum III (Sao Paulo Metro) Integration Tests...")

--------------------------------------------------------------------------------
-- 1. Loader & Content Verification
--------------------------------------------------------------------------------
do
    print("\n--- 1. Content and Metadata Verification ---")
    for mapId = 32, 37 do
        local mIdx = loader.getMapIndex(mapId)
        check(mIdx ~= nil, "Map " .. mapId .. " registered in loader index")
        local mapData = loader.maps[mIdx]
        check(mapData ~= nil and mapData.name ~= nil, "Map " .. mapId .. " successfully loaded with valid metadata")
    end

    local requiredTilesets = {
        "metro_station_l1", "metro_station_l2", "metro_station_l3",
        "metro_station_l4", "metro_station_l5", "metro_station",
        "metro_stratum", "metro_wagon_interior"
    }
    for _, tsId in ipairs(requiredTilesets) do
        local ts = loader.getTileset(tsId)
        check(ts ~= nil, "Tileset '" .. tsId .. "' loaded")
        for _, feat in ipairs((ts and ts.features) or {}) do
            check(feat.injectProbability == 0, "Feature '" .. feat.id .. "' in '" .. tsId .. "' has injectProbability == 0")
        end
    end

    check(loader.troops["boss_tatuzao"] ~= nil, "Troop 'boss_tatuzao' registered")
    check(loader.troops["sentinel_talos"] ~= nil, "Troop 'sentinel_talos' registered")
    check(loader.troops["metro_shadow"] ~= nil, "Troop 'metro_shadow' registered")
    check(loader.troops["metro_ghouls"] ~= nil, "Troop 'metro_ghouls' registered")
end

--------------------------------------------------------------------------------
-- 2. Generic Mover Runtime Kinematics & Player Carrying
--------------------------------------------------------------------------------
do
    print("\n--- 2. Generic Mover Runtime Kinematics ---")
    local session = newSession()
    local map32Idx = loader.getMapIndex(32)
    exploration.loadMap(session, map32Idx, { x = 16, y = 9, dir = "S" }) -- Platform near Luz dock

    moverRuntime.initMap(session, session.currentMapData)
    check(session.movers ~= nil and #session.movers == 1, "Mover initialized on Map 32")

    local mover = session.movers[1]
    check(mover.phase == "docked", "Mover initially docked at platform")
    check(mover.doorState == "open", "Mover doors initially open")
    check(mover.curX == 15 and mover.curY == 9, "Mover position at Luz dock (15, 9)")
    check(#mover.consist == 3, "Mover consist has 3 multi-car units")

    -- Check consist offsets: rear (-3), center (0), lead (+3)
    check(mover.consist[1].offset.x == -3, "Consist car 1 (rear) offset is x=-3")
    check(mover.consist[2].offset.x == 0, "Consist car 2 (center) offset is x=0")
    check(mover.consist[3].offset.x == 3, "Consist car 3 (lead) offset is x=3")

    -- Boarding permissions:
    -- Player on platform (y=8 in 0-index, row 9 in 1-index)
    -- Target car doors at (12, 9), (15, 9), (18, 9) -> 1-indexed (13, 10), (16, 10), (19, 10)
    check(moverRuntime.isBlocked(session, 13, 10) == false, "Boarding permitted at Rear car door (13, 10)")
    check(moverRuntime.isBlocked(session, 16, 10) == false, "Boarding permitted at Center car door (16, 10)")
    check(moverRuntime.isBlocked(session, 19, 10) == false, "Boarding permitted at Lead car door (19, 10)")

    -- Stepping onto track trench where doors are not present:
    check(moverRuntime.isBlocked(session, 5, 10) == true, "Sunken track trench at unserviced cell (5, 10) is blocked")

    -- Step onto Center car (16, 10):
    session.playerX = 16
    session.playerY = 10
    moverRuntime.update(session, 0.05)
    check(mover.onboard == true, "Player boarded Center car")
    check(mover.playerOffsetX == 0 and mover.playerOffsetY == 0, "Player offset in Center car is (0, 0)")

    -- Walk inside car across open gangway to Rear car (13, 10):
    check(moverRuntime.isBlocked(session, 13, 10) == false, "Walking inside consist to Rear car is allowed")
    session.playerX = 13
    session.playerY = 10
    moverRuntime.update(session, 0.05)
    check(mover.onboard == true and mover.playerOffsetX == -3, "Player standing in Rear car (offset -3)")

    -- Dwell timer expires -> closing doors -> moving
    moverRuntime.update(session, (mover.timer or 14.0) + 0.1)
    if mover.phase == "closing" then
        moverRuntime.update(session, 0.1)
        check(mover.doorState == "half" or mover.doorState == "closed", "Doors animating closed")
        moverRuntime.update(session, 0.7)
    end
    check(mover.phase == "moving", "Train entered moving phase")
    check(mover.doorState == "closed", "Train doors closed for transit")
    check(mover.onboard == true, "Player onboard while moving")

    -- Mid-transit safety check: cannot step out into the dark tunnel
    check(moverRuntime.isBlocked(session, session.playerX, session.playerY - 1) == true, "Player blocked from leaping into tunnel in transit")

    -- Complete transit to waypoint 3 (curX = 30, y = 9)
    moverRuntime.update(session, (mover.transitDuration or 5.0) + 0.1)
    if mover.phase == "opening" then
        moverRuntime.update(session, 0.7)
    end
    check(mover.phase == "docked", "Train docked at waypoint 3")
    check(session.playerX == 28 and session.playerY == 10, "Player carried to destination with offset preserved (28, 10)")

    -- Ping-pong return journey back to Luz:
    moverRuntime.update(session, (mover.timer or 3.0) + 0.1)
    if mover.phase == "closing" then moverRuntime.update(session, 0.7) end
    check(mover.phase == "moving", "Train returning toward Luz station")
    moverRuntime.update(session, (mover.transitDuration or 5.0) + 0.1)
    if mover.phase == "opening" then moverRuntime.update(session, 0.7) end
    check(mover.phase == "docked", "Train arrived back at Luz station")
    check(mover.doorState == "open", "Doors opened at Luz platform")
    check(session.playerX == 13 and session.playerY == 10, "Player positioned at Luz in Rear car")

    -- Disembark onto platform (North: y=9 in 1-index)
    check(moverRuntime.isBlocked(session, 13, 9) == false, "Player permitted to step off train onto platform")
    session.playerX = 13
    session.playerY = 9
    moverRuntime.update(session, 0.05)
    check(mover.onboard == false, "Player successfully disembarked from train")
end

--------------------------------------------------------------------------------
-- 3. Save / Load Mover State Round-Trip
--------------------------------------------------------------------------------
do
    print("\n--- 3. Save / Load Mover State Round-Trip ---")
    local session = newSession()
    local map32Idx = loader.getMapIndex(32)
    exploration.loadMap(session, map32Idx, { x = 16, y = 9, dir = "S" })
    moverRuntime.initMap(session, session.currentMapData)

    local mover = session.movers[1]
    -- Board train in Center car
    session.playerX = 16
    session.playerY = 10
    moverRuntime.update(session, 0.05)
    check(mover.onboard == true, "Pre-save: Player boarded mover")

    -- Advance mover into moving phase mid-transit
    moverRuntime.update(session, (mover.timer or 14.0) + 0.1)
    if mover.phase == "closing" then moverRuntime.update(session, 0.7) end
    check(mover.phase == "moving", "Pre-save: Mover is in moving phase")

    -- Move halfway along the track
    local halfDuration = (mover.transitDuration or 4.0) * 0.5
    moverRuntime.update(session, halfDuration)

    local preSaveCurX = mover.curX
    local preSaveCurY = mover.curY
    local preSavePlayerX = session.playerX
    local preSavePlayerY = session.playerY
    local preSaveTimer = mover.timer
    local preSavePhase = mover.phase
    local preSaveSegment = mover.segmentIdx
    local preSaveNext = mover.nextIdx

    check(preSaveCurX > 15 and preSaveCurX < 30, "Pre-save: Mover is actively between waypoints (curX=" .. preSaveCurX .. ")")

    -- Serialize session to save payload
    local savePayload = savegame.serialize(session, loader, "map")
    check(savePayload ~= nil and savePayload.map ~= nil, "Session successfully serialized to save payload")
    check(savePayload.map.movers ~= nil and #savePayload.map.movers == 1, "Save payload captured active movers")

    local savedMover = savePayload.map.movers[1]
    check(savedMover.curX == preSaveCurX and savedMover.curY == preSaveCurY, "Save payload preserved mover position")
    check(savedMover.phase == "moving" and savedMover.onboard == true, "Save payload preserved moving phase and onboard flag")

    -- Restore into a brand new GameSession
    local restoreOk, restoredSession = pcall(savegame.deserialize, savePayload, loader)
    check(restoreOk and restoredSession ~= nil, "Save payload successfully deserialized")

    check(restoredSession.currentMapIndex == map32Idx, "Restored map index matches Map 32")
    check(restoredSession.playerX == preSavePlayerX and restoredSession.playerY == preSavePlayerY, "Restored player position matches mid-transit coords")
    check(restoredSession.restoredMovers ~= nil and #restoredSession.restoredMovers == 1, "restoredMovers primed in session")

    -- Advance restored session by tiny dt to trigger moverRuntime.initMap with restored state
    moverRuntime.update(restoredSession, 0.01)
    check(restoredSession.movers ~= nil and #restoredSession.movers == 1, "Restored session initialized movers")

    local rMover = restoredSession.movers[1]
    check(rMover.phase == "moving", "Restored mover resumed in 'moving' phase")
    check(rMover.doorState == "closed", "Restored mover doors remain closed in transit")
    check(rMover.onboard == true, "Restored mover carries player onboard")
    check(math.abs(rMover.curX - preSaveCurX) < 0.1, "Restored mover curX resumes from exact saved position")
    check(rMover.segmentIdx == preSaveSegment and rMover.nextIdx == preSaveNext, "Restored mover path waypoints preserved")

    -- Run restored mover to completion of current leg
    moverRuntime.update(restoredSession, (rMover.timer or 3.0) + 0.1)
    if rMover.phase == "opening" then moverRuntime.update(restoredSession, 0.7) end

    check(rMover.phase == "docked", "Restored mover successfully arrived and docked at destination")
    check(rMover.doorState == "open", "Restored mover doors opened at dock")
    check(restoredSession.playerX == 31 and restoredSession.playerY == 10, "Player safely arrived at destination waypoint (31, 10)")
end

--------------------------------------------------------------------------------
-- 4. Authored Event & Choice Integration via director.GraphWalker
--------------------------------------------------------------------------------
do
    print("\n--- 4. Authored Event & Choice Integration ---")
    local session = newSession()
    local ctx = { session = session, loader = loader }
    local map32Idx = loader.getMapIndex(32)

    -- A. Map 34: Auxiliary Substation Breaker (Event 11)
    print("  * Testing Map 34 Auxiliary Substation Breaker...")
    local map34Idx = loader.getMapIndex(34)
    exploration.loadMap(session, map34Idx, { x = 24, y = 2, dir = "S" })
    local breakerEv = nil
    for _, ev in ipairs(session.currentMapData.events) do
        if ev.id == 11 or (ev.name and ev.name:match("Breaker")) then breakerEv = ev; break end
    end
    check(breakerEv ~= nil, "Found Auxiliary Substation Breaker event")

    -- Negative Choice Test: Option 2 ("Nao mexer")
    session.flags.metro_aux_power = nil
    local p1 = exploration.resolvePage(breakerEv, session)
    local graphNeg = interpreter.runInteractive(p1.commands, ctx)
    local walkerNeg = director.GraphWalker.new(session, graphNeg)
    check(walkerNeg:getCurrentNode() ~= nil, "Breaker GraphWalker initialized")
    -- Advance through initial TEXT
    walkerNeg:advance()
    local choiceNode = walkerNeg:getCurrentNode()
    check(choiceNode and choiceNode.type == "CHOICE", "Breaker presented CHOICE node")
    check(#choiceNode.options == 2, "Breaker has 2 options")
    -- Select Option 2 ("Nao mexer")
    runWalkerToCompletion(walkerNeg, { 2 }, ctx)
    check(session.flags.metro_aux_power ~= true, "Negative choice: Breaker power NOT engaged")

    -- Positive Choice Test: Option 1 ("Engatar a chave-faca")
    local graphPos = interpreter.runInteractive(p1.commands, ctx)
    local walkerPos = director.GraphWalker.new(session, graphPos)
    walkerPos:advance() -- text
    runWalkerToCompletion(walkerPos, { 1 }, ctx)
    check(session.flags.metro_aux_power == true, "Positive choice: metro_aux_power engaged!")

    -- Page progression check: Page 2 is now active
    local p2 = exploration.resolvePage(breakerEv, session)
    check(p2 ~= p1 and #p2.commands == 1 and p2.commands[1].text:match("chave%-faca est"), "Breaker event progressed to Page 2")

    -- B. Map 34: Foreman's Tool Locker (Event 12)
    print("  * Testing Map 34 Foreman's Tool Locker...")
    local lockerEv = nil
    for _, ev in ipairs(session.currentMapData.events) do
        if ev.id == 12 or (ev.name and ev.name:match("Locker")) then lockerEv = ev; break end
    end
    check(lockerEv ~= nil, "Found Foreman's Tool Locker event")
    local lockerGraph = interpreter.runInteractive(lockerEv.commands, ctx)
    local lockerWalker = director.GraphWalker.new(session, lockerGraph)
    runWalkerToCompletion(lockerWalker, {}, ctx)
    check(session.flags.metro_track_key == true, "Acquired metro_track_key from Foreman locker")

    -- C. Map 33: Chacara Klabin Escalator Shaft Gate (Event 10)
    print("  * Testing Map 33 Chacara Klabin Gate...")
    local map33Idx = loader.getMapIndex(33)
    exploration.loadMap(session, map33Idx, { x = 28, y = 2, dir = "S" })
    local klabinEv = nil
    for _, ev in ipairs(session.currentMapData.events) do
        if ev.id == 10 or (ev.name and ev.name:match("Klabin")) then klabinEv = ev; break end
    end
    check(klabinEv ~= nil, "Found Chacara Klabin gate event")

    -- Negative Gate Test (without key): Page 1 is active (locked message)
    session.flags.metro_track_key = nil
    local kp1 = exploration.resolvePage(klabinEv, session)
    check(kp1.commands[1].text:match("bloqueio"), "Without key: Gate is locked (Page 1)")

    -- Positive Gate Test (with key): Page 2 is active
    session.flags.metro_track_key = true
    local kp2 = exploration.resolvePage(klabinEv, session)
    check(kp2.commands[1].text:match("Chave de Manobra"), "With key: Page 2 offers unlock prompt")

    -- GraphWalker Negative Choice: Option 2 ("Ainda nao")
    session.flags.metro_klabin_unlocked = nil
    local kgNeg = interpreter.runInteractive(kp2.commands, ctx)
    local kwNeg = director.GraphWalker.new(session, kgNeg)
    kwNeg:advance() -- text
    runWalkerToCompletion(kwNeg, { 2 }, ctx)
    check(session.flags.metro_klabin_unlocked ~= true, "Gate remains locked when player chooses 'Ainda nao'")

    -- GraphWalker Positive Choice: Option 1 ("Girar a Chave de Manobra")
    local kgPos = interpreter.runInteractive(kp2.commands, ctx)
    local kwPos = director.GraphWalker.new(session, kgPos)
    kwPos:advance() -- text
    runWalkerToCompletion(kwPos, { 1 }, ctx)
    check(session.flags.metro_klabin_unlocked == true, "Gate unlocked: metro_klabin_unlocked set to true")

    -- Page 3 Progression: offers descent to Line 5
    local kp3 = exploration.resolvePage(klabinEv, session)
    check(kp3.commands[1].text:match("Descer o po"), "Gate progressed to Page 3")
    local kgDesc = interpreter.runInteractive(kp3.commands, ctx)
    local kwDesc = director.GraphWalker.new(session, kgDesc)
    kwDesc:advance() -- text
    runWalkerToCompletion(kwDesc, { 1 }, ctx)
    check(session.currentMapData.id == 36, "Descent choice transitioned to Map 36 (Linha 5: Lilas)")

    -- D. Santa Cruz Shortcut (Map 32 vs Map 36 Directional Locking)
    print("  * Testing Santa Cruz Directional Shortcut Gate...")
    -- Initially on Map 32: Gate is locked from this side
    exploration.loadMap(session, map32Idx, { x = 27, y = 2, dir = "S" })
    local scGate32 = nil
    for _, ev in ipairs(session.currentMapData.events) do
        if ev.id == 20 or (ev.name and ev.name:match("Santa Cruz") and ev.pages) then scGate32 = ev; break end
    end
    check(scGate32 ~= nil, "Found Santa Cruz gate event on Map 32")
    session.flags.metro_santacruz_unlocked = nil
    local sc32_p1 = exploration.resolvePage(scGate32, session)
    check(sc32_p1.commands[1].text:match("OUTRO lado"), "Map 32 gate locked from the Linha 1 side (Page 1)")

    -- Travel to Map 36: internal release lever
    local map36Idx = loader.getMapIndex(36)
    exploration.loadMap(session, map36Idx, { x = 23, y = 2, dir = "S" })
    local scGate36 = nil
    for _, ev in ipairs(session.currentMapData.events) do
        if ev.id == 11 or (ev.name and ev.name:match("Tranca de Santa Cruz")) then scGate36 = ev; break end
    end
    check(scGate36 ~= nil, "Found Santa Cruz lever event on Map 36")

    local sc36_p1 = exploration.resolvePage(scGate36, session)
    local sc36Graph = interpreter.runInteractive(sc36_p1.commands, ctx)
    local sc36Walker = director.GraphWalker.new(session, sc36Graph)
    sc36Walker:advance() -- text
    runWalkerToCompletion(sc36Walker, { 1 }, ctx) -- Select Option 1 ("Puxar a alavanca")
    check(session.flags.metro_santacruz_unlocked == true, "Lever pulled: metro_santacruz_unlocked set to true")

    -- Now return to Map 32: Gate Page 2 is now active and grants transfer
    exploration.loadMap(session, map32Idx, { x = 27, y = 2, dir = "S" })
    local sc32_p2 = exploration.resolvePage(scGate32, session)
    check(sc32_p2.commands[1].text:match("destrancada"), "Map 32 gate now unlocked (Page 2)")
    local sc32Graph = interpreter.runInteractive(sc32_p2.commands, ctx)
    local sc32Walker = director.GraphWalker.new(session, sc32Graph)
    sc32Walker:advance()
    runWalkerToCompletion(sc32Walker, { 1 }, ctx) -- Select Option 1 ("Passar para Linha 5")
    check(session.currentMapData.id == 36, "Traversed unlocked shortcut from Map 32 directly to Map 36")

    -- E. Boss Tatuzao Encounter Victory Commands (Map 36, Event 9)
    print("  * Testing Boss Tatuzao Event & Victory...")
    local bossEv = nil
    for _, ev in ipairs(session.currentMapData.events) do
        if ev.id == 9 or (ev.name and ev.name:match("Tatuzao")) then bossEv = ev; break end
    end
    check(bossEv ~= nil, "Found Boss Tatuzao event on Map 36")
    session.flags.metro_stratum_solved = nil
    local bp1 = exploration.resolvePage(bossEv, session)
    local battleCmd = nil
    for _, cmd in ipairs(bp1.commands or {}) do
        if cmd.cmd == "BATTLE" then battleCmd = cmd; break end
    end
    check(battleCmd ~= nil and battleCmd.troop == "boss_tatuzao", "Boss event triggers BATTLE against 'boss_tatuzao'")
    check(battleCmd.onVictory ~= nil, "BATTLE has authored onVictory command tree")

    local initialGold = session.gold or 0
    local victoryGraph = interpreter.runInteractive(battleCmd.onVictory, ctx)
    local victoryWalker = director.GraphWalker.new(session, victoryGraph)
    runWalkerToCompletion(victoryWalker, {}, ctx)
    check(session.flags.metro_stratum_solved == true, "onVictory executed: metro_stratum_solved set")
    check((session.gold or 0) == initialGold + 5000, "onVictory executed: rewarded 5000 gold")

    local bp2 = exploration.resolvePage(bossEv, session)
    check(bp2.commands[1].text:match("inerte"), "Boss event progressed to Page 2 (carcaca inerte)")
end

--------------------------------------------------------------------------------
-- Summary
--------------------------------------------------------------------------------
print("\n==================================================")
print(string.format("STRATUM III (METRO SP) TESTS: %d passed, %d failed", passed, failed))
print("==================================================")
assert(failed == 0, "Stratum III tests failed")
