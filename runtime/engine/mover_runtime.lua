-- runtime/engine/mover_runtime.lua
-- Project-agnostic, generic runtime controller for kinematic movers (moving platforms,
-- elevators, minecarts, rafts, and transit vehicles).
-- Governs smooth waypoint path traversal, dwell windows, door/state animations,
-- and seamless player carrying without any game-specific or map-specific logic.

local mover_runtime = {}

local function dist(x1, y1, x2, y2)
    local dx = x2 - x1
    local dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)
end

local function normalizeOffset(off)
    if type(off) == "number" then
        return { x = off, y = 0 }
    elseif type(off) == "table" then
        return { x = tonumber(off.x or off[1]) or 0, y = tonumber(off.y or off[2]) or 0 }
    end
    return { x = 0, y = 0 }
end

local function normalizeFootprint(fp)
    if type(fp) == "table" then
        if fp.minX ~= nil and fp.maxX ~= nil and fp.minY ~= nil and fp.maxY ~= nil then
            return fp
        end
        if #fp > 0 then
            return fp
        end
    end
    return { minX = 0, maxX = 0, minY = 0, maxY = 0 }
end

local function isInsideFootprint(dx, dy, footprint)
    if footprint.minX ~= nil then
        return dx >= footprint.minX and dx <= footprint.maxX
           and dy >= footprint.minY and dy <= footprint.maxY
    elseif #footprint > 0 then
        for _, pt in ipairs(footprint) do
            local px = pt.dx or pt.x or pt[1] or 0
            local py = pt.dy or pt.y or pt[2] or 0
            if dx == px and dy == py then return true end
        end
    end
    return false
end

local function normalizeBoarding(boarding)
    if type(boarding) == "table" and #boarding > 0 then
        local list = {}
        for _, b in ipairs(boarding) do
            table.insert(list, {
                dx = tonumber(b.dx or b.x or b[1]) or 0,
                dy = tonumber(b.dy or b.y or b[2]) or 0,
            })
        end
        return list
    end
    return { { dx = 0, dy = 0 } }
end

function mover_runtime.initMap(session, mapData)
    if not session or not mapData then return end
    session.movers = {}
    session.moverMapId = mapData.id

    local restoredMap = {}
    if session.restoredMovers and type(session.restoredMovers) == "table" then
        for _, rm in ipairs(session.restoredMovers) do
            if rm.eventId then
                restoredMap[rm.eventId] = rm
            end
        end
    end

    for _, ev in ipairs(mapData.events or {}) do
        if ev.mover and ev.mover.type == "path" and ev.mover.waypoints and #ev.mover.waypoints >= 2 then
            local spec = ev.mover
            local startIdx = spec.initialWaypoint or 1
            if startIdx < 1 or startIdx > #spec.waypoints then startIdx = 1 end
            local wp1 = spec.waypoints[startIdx]
            local px = (session.playerX or 1) - 1
            local py = (session.playerY or 1) - 1

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

            local rawConsist = spec.consist or { { offset = 0, model = ev.model } }
            local consist = {}
            for ci, rawCar in ipairs(rawConsist) do
                local offset = normalizeOffset(rawCar.offset)
                local carFootprint = rawCar.footprint or spec.footprint
                local footprint = normalizeFootprint(carFootprint or { minX = 0, maxX = 0, minY = 0, maxY = 0 })
                local boarding = normalizeBoarding(rawCar.boarding or spec.boarding)
                table.insert(consist, {
                    index = ci,
                    offset = offset,
                    model = rawCar.model or ev.model,
                    stateModels = rawCar.stateModels or (spec.doorAnimation and spec.doorAnimation.states),
                    footprint = footprint,
                    boarding = boarding,
                })
            end

            local isOnboard = false
            local playerOffsetX = 0
            local playerOffsetY = 0
            for _, car in ipairs(consist) do
                local carX = wp1.x + car.offset.x
                local carY = wp1.y + car.offset.y
                local rdx = px - carX
                local rdy = py - carY
                if isInsideFootprint(rdx, rdy, car.footprint) then
                    isOnboard = true
                    playerOffsetX = px - wp1.x
                    playerOffsetY = py - wp1.y
                    break
                end
            end

            local restored = restoredMap[ev.id]

            local moverState = {
                eventId = ev.id,
                name = ev.name,
                spec = spec,
                model = ev.model,
                consist = consist,
                waypoints = spec.waypoints,
                speed = tonumber(spec.speed) or 3.0,
                mode = spec.mode or "loop",
                carryPlayer = spec.carryPlayer == true,
                sway = spec.sway,
                doorAnim = spec.doorAnimation,
                barrierMaterials = spec.barrierMaterials,

                -- State machine
                segmentIdx = (restored and restored.segmentIdx) or startIdx,
                nextIdx = (restored and restored.nextIdx) or nextIdx,
                direction = (restored and restored.direction) or initDir,
                phase = (restored and restored.phase) or "docked",
                timer = (restored and restored.timer) or tonumber(wp1.dwell) or 4.0,
                doorState = (restored and restored.doorState) or "open",
                curX = (restored and restored.curX) or wp1.x,
                curY = (restored and restored.curY) or wp1.y,
                onboard = (restored and restored.onboard) ~= nil and restored.onboard or isOnboard,
                playerOffsetX = (restored and (restored.playerOffsetX or restored.playerOffset)) or playerOffsetX,
                playerOffsetY = (restored and restored.playerOffsetY) or playerOffsetY,
                transitDuration = (restored and restored.transitDuration) or 1.0,
                elapsed = 0,
            }

            table.insert(session.movers, moverState)
        end
    end

    session.restoredMovers = nil
end

function mover_runtime.resolveModel(mover, car)
    if not mover then return nil end
    local state = mover.doorState or "open"
    if car and car.stateModels and car.stateModels[state] then
        return car.stateModels[state]
    end
    local da = mover.doorAnim
    if da then
        if state == "closed" and da.closedModel then return da.closedModel end
        if state == "half" and da.halfModel then return da.halfModel end
        if state == "open" and da.openModel then return da.openModel end
        if da.states and da.states[state] then return da.states[state] end
    end
    if car and car.model then return car.model end
    return mover.model
end

function mover_runtime.getPlacements(session)
    local placements = {}
    if not session or not session.movers then return placements end

    for _, mover in ipairs(session.movers) do
        local consist = mover.consist or {}
        for ci, car in ipairs(consist) do
            local mx = mover.curX + car.offset.x
            local my = mover.curY + car.offset.y
            local modelPath = mover_runtime.resolveModel(mover, car)
            if modelPath then
                table.insert(placements, {
                    mover = mover,
                    model = modelPath,
                    x = mx,
                    y = my,
                    cacheKey = tostring(mover.eventId) .. "_car_" .. ci,
                })
            end
        end
    end

    return placements
end

function mover_runtime.isBlocked(session, targetX, targetY)
    if not session or not session.movers or #session.movers == 0 then
        return false
    end

    local tx = targetX - 1
    local ty = targetY - 1
    local px = (session.playerX or 1) - 1
    local py = (session.playerY or 1) - 1

    for _, mover in ipairs(session.movers) do
        local consist = mover.consist or {}

        if mover.onboard then
            -- Player is onboard this mover.
            if mover.phase ~= "docked" or mover.doorState ~= "open" then
                -- In transit or doors not open: player MUST remain inside consist footprint.
                local inFootprint = false
                for _, car in ipairs(consist) do
                    local carX = mover.curX + car.offset.x
                    local carY = mover.curY + car.offset.y
                    if isInsideFootprint(tx - carX, ty - carY, car.footprint) then
                        inFootprint = true
                        break
                    end
                end
                if not inFootprint then
                    return true -- Blocked: cannot step out of mover in transit!
                else
                    return false -- Allowed: moving inside consist while in transit!
                end
            else
                -- Mover is docked and doors open.
                local inFootprint = false
                for _, car in ipairs(consist) do
                    local carX = mover.curX + car.offset.x
                    local carY = mover.curY + car.offset.y
                    if isInsideFootprint(tx - carX, ty - carY, car.footprint) then
                        inFootprint = true
                        break
                    end
                end
                if inFootprint then
                    return false -- Allowed: walking inside consist while docked!
                else
                    -- Stepping out! Allowed only from a designated boarding tile.
                    local fromBoarding = false
                    for _, car in ipairs(consist) do
                        local carX = mover.curX + car.offset.x
                        local carY = mover.curY + car.offset.y
                        for _, door in ipairs(car.boarding) do
                            if px == carX + door.dx and py == carY + door.dy then
                                fromBoarding = true
                                break
                            end
                        end
                        if fromBoarding then break end
                    end
                    if not fromBoarding then
                        return true -- Blocked: stepping off through car walls/windows!
                    else
                        return false -- Allowed to step off train onto platform!
                    end
                end
            end

        else
            -- Player is outside. Check if attempting to step into this mover.
            for wi, wp in ipairs(mover.waypoints) do
                for _, car in ipairs(consist) do
                    local carX = wp.x + car.offset.x
                    local carY = wp.y + car.offset.y
                    if isInsideFootprint(tx - carX, ty - carY, car.footprint) then
                        -- Target is inside this car's footprint at waypoint wi
                        local isDoor = false
                        for _, door in ipairs(car.boarding) do
                            if tx == carX + door.dx and ty == carY + door.dy then
                                isDoor = true
                                break
                            end
                        end
                        if isDoor then
                            if mover.segmentIdx == wi and mover.phase == "docked" and mover.doorState == "open" then
                                return false -- Allowed to board!
                            else
                                return true -- Blocked: doors closed or mover not docked here
                            end
                        else
                            return true -- Blocked: attempted to step into car wall/window
                        end
                    end
                end
            end
        end

        -- Check data-driven barrier materials (e.g. sunken track trench, chasm, water)
        if mover.barrierMaterials and #mover.barrierMaterials > 0 then
            local mat = session.currentMapData and session.currentMapData.materials
            local cellMat = mat and mat[targetY] and mat[targetY][targetX]
            if cellMat then
                for _, bm in ipairs(mover.barrierMaterials) do
                    if cellMat == bm then
                        return true -- Blocked by barrier material!
                    end
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
        mover.elapsed = mover.elapsed + dt
        local curWp = mover.waypoints[mover.segmentIdx]
        local daDuration = (mover.doorAnim and mover.doorAnim.duration) or 0.6
        local consist = mover.consist or {}

        -- Detect player boarding or disembarking
        if not mover.onboard then
            if mover.phase == "docked" and mover.doorState == "open" then
                for _, car in ipairs(consist) do
                    for _, door in ipairs(car.boarding) do
                        local doorX = curWp.x + car.offset.x + door.dx
                        local doorY = curWp.y + car.offset.y + door.dy
                        if px == doorX and py == doorY then
                            mover.onboard = true
                            mover.playerOffsetX = px - curWp.x
                            mover.playerOffsetY = py - curWp.y
                            break
                        end
                    end
                    if mover.onboard then break end
                end
            end
        else
            -- Onboard: detect disembarking
            if mover.phase == "docked" and mover.doorState == "open" then
                local isStillInside = false
                for _, car in ipairs(consist) do
                    local carX = curWp.x + car.offset.x
                    local carY = curWp.y + car.offset.y
                    if isInsideFootprint(px - carX, py - carY, car.footprint) then
                        isStillInside = true
                        mover.playerOffsetX = px - curWp.x
                        mover.playerOffsetY = py - curWp.y
                        break
                    end
                end
                if not isStillInside then
                    mover.onboard = false
                    mover.playerOffsetX = 0
                    mover.playerOffsetY = 0
                    session.moverCameraOverride = nil
                end
            end
        end

        -- State machine
        if mover.phase == "docked" then
            mover.curX = curWp.x
            mover.curY = curWp.y
            mover.doorState = "open"
            if mover.onboard then session.moverCameraOverride = nil end

            mover.timer = mover.timer - dt
            if mover.timer <= 0 then
                if mover.doorAnim then
                    mover.phase = "closing"
                    mover.timer = daDuration
                else
                    mover.phase = "moving"
                    mover_runtime.startLeg(mover)
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
            local easeT = t * t * (3 - 2 * t) -- Smooth cubic acceleration & deceleration

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
                    session.playerX = math.floor(arrivedWp.x + (mover.playerOffsetX or 0) + 0.5) + 1
                    session.playerY = math.floor(arrivedWp.y + (mover.playerOffsetY or 0) + 0.5) + 1
                    session.moverCameraOverride = nil
                end

                if mover.doorAnim then
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

return mover_runtime
