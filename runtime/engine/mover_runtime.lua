-- runtime/engine/mover_runtime.lua
-- Generic kinematic platform mover: waypoint traversal, dwell windows,
-- door/state animation staging, and player carrying.
--
-- This module is deliberately project-agnostic. It knows waypoints,
-- speeds, modes, consist offsets, door visuals, and timing, and nothing
-- about any project's lines, stations, track materials, platform sides,
-- or model file naming. All of that is authored data on the Event's
-- `mover` block: waypoints, consist offsets, door models/sprites, timing.
--
-- Event.mover schema (all coordinates 0-indexed, matching event x/y).
-- (No project, line, station, or material names appear in this module.)
--   type = "path" (only type today)
--   waypoints = { { x, y, dwell? }, ... } (>= 2)
--   speed = tiles per second (> 0)
--   mode = "loop" | "ping_pong" | "once"
--   carryPlayer = true to carry the player while moving
--   initialWaypoint? (1-indexed, default 1)
--   consist? = { { dx?, dy?, doors?, model?, openModel?, halfModel?,
--                  closedModel?, sprite? }, ... }
--     dx/dy are tile offsets from the waypoint (default 0,0).
--     doors marks a boardable car. Visual selection is purely data:
--     openModel/halfModel/closedModel (or model fallback, or sprite).
--   doorAnimation? = { duration? } (seconds, default 0.6)
--   sway? = { frequency?, pitch? } (camera-only flourish, radians)
--
-- Save contract: session.movers is runtime state derived from authored
-- events plus dynamic phase. It round-trips through savegame via
-- serialize()/restore(); see savegame.serializeMap/restoreMap. Saving
-- while onboard or mid-transit restores the mover in the same phase with
-- the player still carried.

local mover_runtime = {}

local function dist(x1, y1, x2, y2)
    local dx = x2 - x1
    local dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)
end

local function defaultConsist(ev)
    return { { dx = 0, dy = 0, doors = true } }
end

local function carList(mover)
    return mover.consist or defaultConsist(nil)
end

-- World (0-indexed) cells occupied by each car at a given position.
local function carCellsAt(pos, consist)
    local cells = {}
    local px = pos and pos.x or 0
    local py = pos and pos.y or 0
    for i, car in ipairs(consist or defaultConsist(nil)) do
        cells[i] = {
            x = math.floor(px + (car.dx or 0) + 0.5),
            y = math.floor(py + (car.dy or 0) + 0.5),
            car = car,
        }
    end
    return cells
end

function mover_runtime.initMap(session, mapData)
    if not session or not mapData then return end
    session.movers = {}
    session.moverMapId = mapData.id
    session.moverCameraOverride = nil

    for _, ev in ipairs(mapData.events or {}) do
        if type(ev.mover) == "table" and ev.mover.type == "path"
            and type(ev.mover.waypoints) == "table"
            and #ev.mover.waypoints >= 2 then
            local spec = ev.mover
            local startIdx = tonumber(spec.initialWaypoint) or 1
            if startIdx < 1 or startIdx > #spec.waypoints then startIdx = 1 end
            local wp1 = spec.waypoints[startIdx]

            local nextIdx = startIdx + 1
            local initDir = 1
            if nextIdx > #spec.waypoints then
                if spec.mode == "loop" then
                    nextIdx = 1
                else
                    initDir = -1
                    nextIdx = math.max(1, startIdx - 1)
                end
            end

            local consist = spec.consist or defaultConsist(ev)
            local px = (session.playerX or 1) - 1
            local py = (session.playerY or 1) - 1
            local isOnboard = false
            local offX, offY = 0, 0
            if spec.carryPlayer == true then
                for _, cell in ipairs(carCellsAt(wp1, consist)) do
                    if cell.car.doors ~= false and px == cell.x and py == cell.y then
                        isOnboard = true
                        offX = px - wp1.x
                        offY = py - wp1.y
                        break
                    end
                end
            end

            table.insert(session.movers, {
                eventId = ev.id,
                consist = consist,
                waypoints = spec.waypoints,
                speed = tonumber(spec.speed) or 3.0,
                mode = spec.mode or "loop",
                carryPlayer = spec.carryPlayer == true,
                sway = spec.sway,
                doorAnimDuration = spec.doorAnimation
                    and tonumber(spec.doorAnimation.duration) or 0.6,
                hasDoorAnim = spec.doorAnimation ~= nil,
                segmentIdx = startIdx,
                nextIdx = nextIdx,
                direction = initDir,
                phase = "docked",
                timer = tonumber(wp1.dwell) or 4.0,
                doorState = "open",
                curX = wp1.x,
                curY = wp1.y,
                onboard = isOnboard,
                playerOffsetX = offX,
                playerOffsetY = offY,
                elapsed = 0,
            })
        end
    end
end

-- Purely data-driven visual selection. No path construction, no naming
-- conventions: the authored per-car models win, in door-state order.
function mover_runtime.resolveModel(mover, car)
    if not mover or not car then return nil end
    if mover.doorState == "closed" and car.closedModel then
        return car.closedModel
    end
    if mover.doorState == "half" and car.halfModel then
        return car.halfModel
    end
    return car.openModel or car.model
end

function mover_runtime.getPlacements(session)
    if not session or not session.currentMapData then return {} end
    if not session.movers or session.moverMapId ~= session.currentMapData.id then
        mover_runtime.initMap(session, session.currentMapData)
    end
    if not session.movers or #session.movers == 0 then return {} end
    local placements = {}
    for _, mover in ipairs(session.movers) do
        for ci, car in ipairs(carList(mover)) do
            table.insert(placements, {
                cacheKey = tostring(mover.eventId) .. "_car_" .. ci,
                model = mover_runtime.resolveModel(mover, car),
                sprite = car.sprite,
                x = mover.curX + (car.dx or 0) + 1.5,
                y = mover.curY + (car.dy or 0) + 1.5,
                mover = mover,
            })
        end
    end
    return placements
end

-- 1-indexed target cell, matching exploration.tryMove. Returns true when
-- the mover footprint forbids the step; false defers to ordinary collision.
function mover_runtime.isBlocked(session, targetX, targetY)
    if not session or not session.movers or #session.movers == 0 then
        return false
    end
    local tx = targetX - 1
    local ty = targetY - 1

    for _, mover in ipairs(session.movers) do
        local consist = carList(mover)
        local curPos = { x = mover.curX, y = mover.curY }
        local cells = carCellsAt(curPos, consist)

        local function isCarCell(x, y)
            for _, c in ipairs(cells) do
                if c.x == x and c.y == y then return true, c end
            end
            return false, nil
        end

        local function adjacentToDoorCar(x, y)
            for _, c in ipairs(cells) do
                if c.car.doors ~= false then
                    if math.abs(c.x - x) + math.abs(c.y - y) == 1 then
                        return true
                    end
                end
            end
            return false
        end

        if mover.onboard then
            -- Locked in while closing/moving/opening or with doors shut.
            if mover.phase ~= "docked" or mover.doorState ~= "open" then
                return true
            end
            -- Docked with doors open: roam the cars or step to the
            -- immediately adjacent platform via a door car. Anything else
            -- is the void beyond the platform edge, not a legal disembark.
            local inCar = isCarCell(tx, ty)
            local canDisembark = adjacentToDoorCar(tx, ty)
            if not (inCar or canDisembark) then
                return true
            end
        else
            -- Outside player:
            local hitCar, carCell = isCarCell(tx, ty)
            if hitCar then
                -- A car cell is enterable only while this mover is docked with
                -- doors open, carries players, and this specific car has doors.
                local canBoard = mover.carryPlayer
                    and (carCell.car.doors ~= false)
                    and (mover.phase == "docked")
                    and (mover.doorState == "open")
                if not canBoard then
                    return true
                end
            end
        end
    end
    return false
end

function mover_runtime.startLeg(mover)
    local n = #mover.waypoints
    if mover.mode == "loop" then
        mover.nextIdx = (mover.segmentIdx % n) + 1
    elseif mover.mode == "ping_pong" then
        if mover.segmentIdx >= n then
            mover.direction = -1
        elseif mover.segmentIdx <= 1 then
            mover.direction = 1
        end
        mover.nextIdx = mover.segmentIdx + mover.direction
    else -- "once"
        if mover.segmentIdx < n then
            mover.nextIdx = mover.segmentIdx + 1
        else
            mover.phase = "docked"
            mover.doorState = "open"
            mover.timer = 999999
            return
        end
    end

    local p1 = mover.waypoints[mover.segmentIdx]
    local p2 = mover.waypoints[mover.nextIdx]
    local d = dist(p1.x, p1.y, p2.x, p2.y)
    mover.transitDuration = math.max(0.1, d / mover.speed)
    mover.timer = mover.transitDuration
end

function mover_runtime.update(session, dt)
    if not session or not session.currentMapData then return end
    local mapId = session.currentMapData.id
    if not session.movers or session.moverMapId ~= mapId then
        mover_runtime.initMap(session, session.currentMapData)
    end
    if not session.movers or #session.movers == 0 then
        session.moverCameraOverride = nil
        return
    end

    local px = (session.playerX or 1) - 1
    local py = (session.playerY or 1) - 1

    for _, mover in ipairs(session.movers) do
        mover.elapsed = (mover.elapsed or 0) + dt
        local curWp = mover.waypoints[mover.segmentIdx]
        local daDuration = mover.doorAnimDuration or 0.6
        local consist = carList(mover)
        local curPos = { x = mover.curX or curWp.x, y = mover.curY or curWp.y }
        local cells = carCellsAt(curPos, consist)

        -- Boarding / disembark detection (docked, doors open, and carryPlayer only).
        if not mover.onboard then
            if mover.carryPlayer and mover.phase == "docked" and mover.doorState == "open" then
                for _, c in ipairs(cells) do
                    if c.car.doors ~= false and px == c.x and py == c.y then
                        mover.onboard = true
                        mover.playerOffsetX = px - mover.curX
                        mover.playerOffsetY = py - mover.curY
                        break
                    end
                end
            end
        else
            if mover.phase == "docked" and mover.doorState == "open" then
                local inside = false
                for _, c in ipairs(cells) do
                    if px == c.x and py == c.y then
                        inside = true
                        mover.playerOffsetX = px - mover.curX
                        mover.playerOffsetY = py - mover.curY
                        break
                    end
                end
                if not inside then
                    mover.onboard = false
                    mover.playerOffsetX = 0
                    mover.playerOffsetY = 0
                    session.moverCameraOverride = nil
                end
            end
        end

        if mover.phase == "docked" then
            mover.curX = curWp.x
            mover.curY = curWp.y
            mover.doorState = "open"
            if mover.onboard then session.moverCameraOverride = nil end
            mover.timer = mover.timer - dt
            if mover.timer <= 0 then
                if mover.mode == "once" and mover.segmentIdx >= #mover.waypoints then
                    mover.timer = 999999
                    mover.phase = "docked"
                    mover.doorState = "open"
                else
                    if mover.hasDoorAnim then
                        mover.phase = "closing"
                        mover.timer = daDuration
                    else
                        mover.phase = "moving"
                        mover_runtime.startLeg(mover)
                    end
                end
            end
        elseif mover.phase == "closing" then
            mover.curX = curWp.x
            mover.curY = curWp.y
            mover.timer = mover.timer - dt
            if mover.timer > (daDuration * 0.5) then
                mover.doorState = "half"
            else
                mover.doorState = "closed"
            end
            if mover.timer <= 0 then
                mover.doorState = "closed"
                mover.phase = "moving"
                mover_runtime.startLeg(mover)
            end
        elseif mover.phase == "moving" then
            mover.timer = mover.timer - dt
            local startWp = mover.waypoints[mover.segmentIdx]
            local endWp = mover.waypoints[mover.nextIdx]
            local dur = mover.transitDuration or 1.0
            local t = 1.0 - math.max(0, math.min(1, mover.timer / dur))
            local easeT = t * t * (3 - 2 * t)
            mover.curX = startWp.x + (endWp.x - startWp.x) * easeT
            mover.curY = startWp.y + (endWp.y - startWp.y) * easeT

            if mover.onboard and mover.carryPlayer then
                local targetX = mover.curX + (mover.playerOffsetX or 0)
                local targetY = mover.curY + (mover.playerOffsetY or 0)
                session.playerX = math.floor(targetX + 0.5) + 1
                session.playerY = math.floor(targetY + 0.5) + 1
                local fracX = targetX - (session.playerX - 1)
                local fracY = targetY - (session.playerY - 1)
                local pitchSway = 0
                if mover.sway then
                    local amount = math.sin(t * math.pi)
                    local freq = mover.sway.frequency or 12.0
                    local pMax = mover.sway.pitch or 0.006
                    pitchSway = math.sin(mover.elapsed * freq) * pMax * amount
                end
                session.moverCameraOverride = {
                    dollyX = fracX,
                    dollyY = fracY,
                    pitch = pitchSway,
                }
            end

            if mover.timer <= 0 then
                mover.segmentIdx = mover.nextIdx
                local arrivedWp = mover.waypoints[mover.segmentIdx]
                mover.curX = arrivedWp.x
                mover.curY = arrivedWp.y
                if mover.onboard and mover.carryPlayer then
                    session.playerX = math.floor(
                        arrivedWp.x + (mover.playerOffsetX or 0) + 0.5) + 1
                    session.playerY = math.floor(
                        arrivedWp.y + (mover.playerOffsetY or 0) + 0.5) + 1
                    session.moverCameraOverride = nil
                end
                if mover.hasDoorAnim then
                    mover.phase = "opening"
                    mover.timer = daDuration
                else
                    mover.phase = "docked"
                    mover.doorState = "open"
                    mover.timer = tonumber(arrivedWp.dwell) or 4.0
                end
            end
        elseif mover.phase == "opening" then
            local arrivedWp = mover.waypoints[mover.segmentIdx]
            mover.curX = arrivedWp.x
            mover.curY = arrivedWp.y
            mover.timer = mover.timer - dt
            if mover.timer > (daDuration * 0.5) then
                mover.doorState = "half"
            else
                mover.doorState = "open"
            end
            if mover.timer <= 0 then
                mover.doorState = "open"
                mover.phase = "docked"
                mover.timer = tonumber(arrivedWp.dwell) or 4.0
            end
        end
    end
end

-- Save contract: plain-data snapshot per mover, matched by eventId.
function mover_runtime.serialize(session)
    if not session or not session.movers or #session.movers == 0 then
        return nil
    end
    local out = {}
    for _, m in ipairs(session.movers) do
        table.insert(out, {
            eventId = m.eventId,
            segmentIdx = m.segmentIdx,
            nextIdx = m.nextIdx,
            direction = m.direction,
            phase = m.phase,
            timer = m.timer,
            doorState = m.doorState,
            curX = m.curX,
            curY = m.curY,
            onboard = m.onboard,
            playerOffsetX = m.playerOffsetX,
            playerOffsetY = m.playerOffsetY,
            transitDuration = m.transitDuration,
            elapsed = m.elapsed,
        })
    end
    return out
end

function mover_runtime.restore(session, mapData, data)
    mover_runtime.initMap(session, mapData)
    if type(data) ~= "table" then return end
    local byId = {}
    for _, m in ipairs(session.movers or {}) do
        byId[m.eventId] = m
    end
    for _, saved in ipairs(data) do
        if type(saved) == "table" then
            local m = byId[saved.eventId]
            if m then
                if tonumber(saved.segmentIdx) and m.waypoints[tonumber(saved.segmentIdx)] then
                    m.segmentIdx = tonumber(saved.segmentIdx)
                end
                if tonumber(saved.nextIdx) and m.waypoints[tonumber(saved.nextIdx)] then
                    m.nextIdx = tonumber(saved.nextIdx)
                end
                m.direction = (saved.direction == -1) and -1 or 1
                if saved.phase == "docked" or saved.phase == "closing"
                    or saved.phase == "moving" or saved.phase == "opening" then
                    m.phase = saved.phase
                end
                if tonumber(saved.timer) then m.timer = tonumber(saved.timer) end
                if saved.doorState == "open" or saved.doorState == "half"
                    or saved.doorState == "closed" then
                    m.doorState = saved.doorState
                end
                if tonumber(saved.curX) then m.curX = tonumber(saved.curX) end
                if tonumber(saved.curY) then m.curY = tonumber(saved.curY) end
                m.onboard = saved.onboard == true
                m.playerOffsetX = tonumber(saved.playerOffsetX) or 0
                m.playerOffsetY = tonumber(saved.playerOffsetY) or 0
                if tonumber(saved.transitDuration) then
                    m.transitDuration = tonumber(saved.transitDuration)
                end
                m.elapsed = tonumber(saved.elapsed) or 0
            end
        end
    end
    -- Reconcile: a restored onboard flag is only meaningful if the saved
    -- player position still sits on (or adjacent to) the restored consist.
    -- Otherwise a stale flag would lock movement on load.
    local px = (session.playerX or 1) - 1
    local py = (session.playerY or 1) - 1
    for _, m in ipairs(session.movers or {}) do
        if m.onboard then
            local curWp = m.waypoints[m.segmentIdx]
            local ok = false
            if curWp then
                for _, c in ipairs(carCellsAt(
                    { x = m.curX, y = m.curY }, carList(m))) do
                    if math.abs(c.x - px) + math.abs(c.y - py) <= 1 then
                        ok = true
                        break
                    end
                end
            end
            if not ok then
                m.onboard = false
                m.playerOffsetX = 0
                m.playerOffsetY = 0
            end
        end
    end
end

return mover_runtime
