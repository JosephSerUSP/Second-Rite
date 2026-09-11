-- Metro pilot (Stratum III seed): generic mover primitive plus the Luz/Bras
-- puzzle chain. The mover assertions pin the engine contract; the puzzle
-- assertions run the AUTHORED event command trees (both branches) rather
-- than injecting flags synthetically.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local interpreter = require("engine.interpreter")
local exploration = require("engine.exploration")
local moverRuntime = require("engine.mover_runtime")
local conditions = require("engine.conditions")
local savegame = require("engine.savegame")

print("[TEST] Starting metro stratum pilot tests...")

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

local function newSession()
    local s = sessionModule.GameSession.new(loader)
    s:initializeStartingParty()
    return s
end

local function findEvent(mapData, id)
    for _, ev in ipairs(mapData.events or {}) do
        if ev.id == id then return ev end
    end
    return nil
end

-- Runs an authored command list the way the runtime does: CONDITIONAL_BRANCH
-- evaluates its REAL condition string and only the taken branch executes;
-- presentation-only TEXT is skipped; every other command must be
-- immediate-safe (LOAD_MAP/SET_FLAG/GAIN_GOLD are) and runs for real.
-- CHOICE/BATTLE have no headless meaning, so encountering one here fails
-- loudly instead of silently skipping authored gating.
local function runAuthored(commands, session)
    local ctx = { session = session, loader = loader, events = {},
        party = session.party }
    local immediate = {}
    local function flush()
        if #immediate > 0 then
            interpreter.runImmediate(immediate, ctx)
            immediate = {}
        end
    end
    local function walk(list)
        for _, cmd in ipairs(list or {}) do
            if cmd.cmd == "CONDITIONAL_BRANCH" then
                flush()
                local matched, result = conditions.evalPrefixed(
                    cmd.condition, session)
                check(matched == true,
                    "authored condition '" .. tostring(cmd.condition)
                    .. "' uses the shared prefix grammar")
                if result then
                    walk(cmd.commands)
                else
                    walk(cmd.elseCommands)
                end
            elseif cmd.cmd == "TEXT" then
                -- Presentation only; gating lives in the branch structure.
            elseif cmd.cmd == "CHOICE" or cmd.cmd == "BATTLE"
                or cmd.cmd == "CALL_COMMON_EVENT" then
                check(false, "authored gating must not depend on interactive '"
                    .. tostring(cmd.cmd) .. "' in headless-covered paths")
            else
                table.insert(immediate, cmd)
            end
        end
    end
    walk(commands)
    flush()
end

local function runEvent(mapData, id, session)
    local ev = findEvent(mapData, id)
    check(ev ~= nil, "event " .. id .. " exists on map " .. tostring(mapData.id))
    if ev then runAuthored(ev.commands, session) end
    return ev
end

-- 1. Maps are registered and loadable.
local idx32 = loader.getMapIndex(32)
local idx33 = loader.getMapIndex(33)
check(idx32 ~= nil, "map 32 (Luz Station Pilot) is registered")
check(idx33 ~= nil, "map 33 (Bras Substation Pilot) is registered")
local map32 = idx32 and loader.maps[idx32]
local map33 = idx33 and loader.maps[idx33]
check(map32 ~= nil and map32.id == 32, "map 32 loads with correct id")
check(map33 ~= nil and map33.id == 33, "map 33 loads with correct id")

-- 2. The engine primitive carries no project knowledge.
local moverPath = package.searchpath("engine.mover_runtime", package.path)
  or "engine/mover_runtime.lua"
local f = io.open(moverPath, "rb")
local moverSource = f and f:read("*a") or ""
if f then f:close() end
check(moverSource ~= "", "mover_runtime source is readable")
-- Project-specific leakage has concrete shapes: constructed asset paths,
-- track material names, platform-side logic, role/line suffix naming.
-- (A plain substring search would also match this very comment, so the
-- patterns below target code shapes instead.)
check(not moverSource:find("assets/models/"),
    "mover_runtime constructs no model paths")
check(not moverSource:lower():find("rails"),
    "mover_runtime names no track material")
check(not moverSource:find("car%.offset"),
    "mover_runtime uses generic dx/dy offsets, not train consist offsets")
check(not moverSource:find("dockDir"),
    "mover_runtime has no platform-side (dockDir) special case")
check(moverSource:find("playerOffsetX") ~= nil,
    "mover_runtime tracks a generic 2D player offset")

-- 3. Mover spec on map 32 is data, not hardcoding.
local shuttle = findEvent(map32, 1)
check(shuttle ~= nil and type(shuttle.mover) == "table",
    "map 32 event 1 carries a mover block")
check(shuttle.mover.type == "path", "mover type is 'path'")
check(shuttle.mover.carryPlayer == true, "mover carries the player")
check(shuttle.mover.mode == "ping_pong", "mover mode is 'ping_pong'")
check(type(shuttle.mover.speed) == "number" and shuttle.mover.speed > 0,
    "mover has a positive speed")
check(#shuttle.mover.waypoints >= 2, "mover has at least 2 waypoints")
check(#(shuttle.mover.consist or {}) == 2, "mover consist lists 2 cars")

-- 4. Mover lifecycle: board, ride, carry with offset, return, disembark.
local session = newSession()
exploration.loadMap(session, idx32)
check(session.currentMapData.id == 32, "player loads into map 32")
moverRuntime.initMap(session, session.currentMapData)
check(session.movers ~= nil and #session.movers == 1,
    "one mover initializes on map 32")
local mover = session.movers[1]
check(mover.phase == "docked", "mover starts docked")
check(mover.doorState == "open", "mover doors start open")
check(mover.curX == 3 and mover.curY == 4,
    "mover starts at the first waypoint (3, 4)")

-- Dock 1 cars sit at 0-indexed (2,4) and (4,4): 1-indexed (3,5) and (5,5).
check(moverRuntime.isBlocked(session, 3, 5) == false,
    "rear car door cell (3, 5) is boardable while docked open")
check(moverRuntime.isBlocked(session, 5, 5) == false,
    "front car door cell (5, 5) is boardable while docked open")

session.playerX, session.playerY = 3, 5
moverRuntime.update(session, 0.05)
check(mover.onboard == true, "player boards at the rear car")
check(mover.playerOffsetX == -1 and mover.playerOffsetY == 0,
    "boarding records the generic 2D offset (-1, 0)")

-- Walk along the consist to the front car while docked.
check(moverRuntime.isBlocked(session, 5, 5) == false,
    "an onboard player can walk the consist while docked open")
session.playerX = 5
moverRuntime.update(session, 0.05)
check(mover.onboard == true and mover.playerOffsetX == 1,
    "offset follows the player to the front car (+1)")

local placements = moverRuntime.getPlacements(session)
check(#placements == 2, "two car placements are published")
check(placements[1].sprite ~= nil or placements[1].model ~= nil,
    "placements carry authored visuals, never constructed paths")

-- Dwell expiry closes the doors, then the leg starts.
mover.timer = 0.01
moverRuntime.update(session, 0.05)
check(mover.phase == "closing", "dwell expiry enters closing")
moverRuntime.update(session, 0.7)
check(mover.phase == "moving", "doors close, then the mover departs")
check(mover.doorState == "closed", "doors are closed in transit")
check(mover.onboard == true, "the player is carried, not left behind")
check(moverRuntime.isBlocked(session, session.playerX, session.playerY) == true,
    "an onboard player cannot leave mid-transit")

-- Ride to the far dock; the +1 offset is preserved.
moverRuntime.update(session, (mover.transitDuration or 3.0) + 0.1)
if mover.phase == "opening" then moverRuntime.update(session, 0.7) end
check(mover.phase == "docked", "the shuttle docks at the far waypoint")
check(session.playerX == 13 and session.playerY == 5,
    "the player arrives with offset preserved (13, 5)")
check(mover.doorState == "open", "doors reopen at the far dock")

-- Ping-pong return.
mover.timer = 0.01
moverRuntime.update(session, 0.05)
if mover.phase == "closing" then moverRuntime.update(session, 0.7) end
check(mover.phase == "moving", "the shuttle departs back")
moverRuntime.update(session, (mover.transitDuration or 3.0) + 0.1)
if mover.phase == "opening" then moverRuntime.update(session, 0.7) end
check(mover.phase == "docked" and mover.curX == 3,
    "the shuttle returns to the first waypoint")

-- Step onto the adjacent platform and the ride releases.
check(moverRuntime.isBlocked(session, 5, 4) == false,
    "disembarking onto the adjacent platform is permitted")
session.playerX, session.playerY = 5, 4
moverRuntime.update(session, 0.05)
check(mover.onboard == false, "the player disembarks cleanly")

-- 5. Breaker powers the room (authored event, not a synthetic flag).
local sPower = newSession()
exploration.loadMap(sPower, idx33)
runEvent(map33, 1, sPower)
check(sPower.flags["metro_aux_power"] == true,
    "the authored breaker sets metro_aux_power")

-- 6. Locker: denied without power, granted with it.
local sLockerCold = newSession()
exploration.loadMap(sLockerCold, idx33)
runEvent(map33, 2, sLockerCold)
check(sLockerCold.flags["metro_track_key"] ~= true,
    "the locker refuses without auxiliary power")
runEvent(map33, 1, sLockerCold)
runEvent(map33, 2, sLockerCold)
check(sLockerCold.flags["metro_track_key"] == true,
    "the locker yields the track key once powered")

-- 7. Klabin gate: denied without the key, opens with it.
local sGateCold = newSession()
exploration.loadMap(sGateCold, idx33)
runEvent(map33, 3, sGateCold)
check(sGateCold.flags["metro_klabin_unlocked"] ~= true,
    "the Klabin gate refuses without the track key")
runEvent(map33, 1, sGateCold)
runEvent(map33, 2, sGateCold)
runEvent(map33, 3, sGateCold)
check(sGateCold.flags["metro_klabin_unlocked"] == true,
    "the Klabin gate opens with the track key")

-- 8. Vault: sealed before the gate, pays after it.
local sVaultCold = newSession()
exploration.loadMap(sVaultCold, idx33)
local goldBefore = sVaultCold.gold or 0
runEvent(map33, 4, sVaultCold)
check((sVaultCold.gold or 0) == goldBefore,
    "the vault pays nothing while the gate holds")
check(sVaultCold.flags["metro_master_pass"] ~= true,
    "no master pass while the gate holds")
runEvent(map33, 1, sVaultCold)
runEvent(map33, 2, sVaultCold)
runEvent(map33, 3, sVaultCold)
runEvent(map33, 4, sVaultCold)
check((sVaultCold.gold or 0) == goldBefore + 10000,
    "the vault pays 10000 gold once the gate opens")
check(sVaultCold.flags["metro_master_pass"] == true,
    "the vault grants the master pass")
check(sVaultCold.flags["metro_vault_cleared"] == true,
    "the vault sets its cleared flag")

-- 9. Titan seal: dormant before the gate, solved after; shortcut follows.
local sSealCold = newSession()
exploration.loadMap(sSealCold, idx33)
runEvent(map33, 5, sSealCold)
check(sSealCold.flags["metro_stratum_solved"] ~= true,
    "the seal stays dormant before the gate opens")
check(sSealCold.flags["metro_santacruz_unlocked"] ~= true,
    "no shortcut before the gate opens")
runEvent(map33, 1, sSealCold)
runEvent(map33, 2, sSealCold)
runEvent(map33, 3, sSealCold)
runEvent(map33, 5, sSealCold)
check(sSealCold.flags["metro_stratum_solved"] == true,
    "the seal records the stratum solved")
check(sSealCold.flags["metro_santacruz_unlocked"] == true,
    "the seal unlatches the Santa Cruz shortcut")

-- 10. Shortcut directionality through the authored event.
local sCutCold = newSession()
exploration.loadMap(sCutCold, idx33)
runEvent(map33, 7, sCutCold)
check(sCutCold.currentMapData.id == 33,
    "the shortcut holds shut without the titan flag")
runEvent(map33, 1, sCutCold)
runEvent(map33, 2, sCutCold)
runEvent(map33, 3, sCutCold)
runEvent(map33, 5, sCutCold)
runEvent(map33, 7, sCutCold)
check(sCutCold.currentMapData.id == 32,
    "the shortcut transfers 33 -> 32 once unlatched")

-- 11. Open transfers both ways through authored events.
local sRide = newSession()
exploration.loadMap(sRide, idx32)
runEvent(loader.maps[loader.getMapIndex(32)], 2, sRide)
check(sRide.currentMapData.id == 33, "stairs transfer 32 -> 33")
runEvent(loader.maps[loader.getMapIndex(33)], 6, sRide)
check(sRide.currentMapData.id == 32, "stairs transfer 33 -> 32")

-- 12. Boss troop wiring exists for the follow-up encounter.
local tatuzao = loader.troops and loader.troops["boss_tatuzao"]
check(tatuzao ~= nil, "boss_tatuzao troop is registered")
check(tatuzao ~= nil and #(tatuzao.members or {}) >= 1,
    "boss_tatuzao fields at least one member")

-- 13. Save/load round-trips a ride in motion.
local sSave = newSession()
exploration.loadMap(sSave, idx32)
moverRuntime.initMap(sSave, sSave.currentMapData)
sSave.playerX, sSave.playerY = 3, 5
moverRuntime.update(sSave, 0.05)
sSave.movers[1].timer = 0.01
moverRuntime.update(sSave, 0.05)
moverRuntime.update(sSave, 0.7)
check(sSave.movers[1].phase == "moving",
    "ride is moving before the save")
local payload = savegame.serialize(sSave, loader, "map")
check(payload ~= nil and payload.map ~= nil
    and payload.map.movers ~= nil,
    "the save payload carries mover state")
local decoded = savegame.deserialize(payload, loader)
check(decoded.movers ~= nil and #decoded.movers == 1,
    "mover state survives deserialization")
local rm = decoded.movers[1]
check(rm.phase == "moving" and rm.onboard == true,
    "phase and onboard flag restore mid-transit")
check(rm.playerOffsetX == sSave.movers[1].playerOffsetX,
    "the player offset restores exactly")
check(decoded.playerX == sSave.playerX
    and decoded.playerY == sSave.playerY,
    "the carried player position restores")
-- The restored ride keeps carrying to the far dock.
local ticks = 0
while decoded.movers[1].phase == "moving" and ticks < 600 do
    moverRuntime.update(decoded, 0.05)
    ticks = ticks + 1
end
if decoded.movers[1].phase == "opening" then
    moverRuntime.update(decoded, 0.7)
end
check(decoded.movers[1].phase == "docked",
    "the restored ride completes its leg")
-- This ride boarded the rear car (offset -1), so the far dock (11, 4)
-- delivers the player to 1-indexed (11, 5): offset preserved, not snapped.
check(decoded.playerX == 11 and decoded.playerY == 5,
    "the restored ride delivers the player with offset intact")

print("=== Metro stratum pilot: " .. passed .. " passed, " .. failed .. " failed ===")
assert(failed == 0, "metro stratum pilot tests failed")
