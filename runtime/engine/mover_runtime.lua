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

function mover_runtime.initMap(session, mapData)
    if not session or not mapData then return end
    session.movers = {}
    session.moverMapId = mapData.id

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

            local consist = spec.consist or { { offset = 0, doors = true, model = ev.model } }
            local isOnboard = false
            local playerOffset = 0
            for _, car in ipairs(consist) do
                local carX = wp1.x + (car.offset or 0)
                local carY = wp1.y
                if px >= carX - 1 and px <= carX + 1 and py == carY then
                    isOnboard = true
                    playerOffset = px - wp1.x
                    break
                end
            end

            table.insert(session.movers, {
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

                -- State machine: "docked" -> "closing" -> "moving" -> "opening" -> "docked"
                segmentIdx = startIdx,
                nextIdx = nextIdx,
                direction = initDir,
                phase = "docked",
                timer = tonumber(wp1.dwell) or 4.0,
                doorState = "open",
                curX = wp1.x,
                curY = wp1.y,
                onboard = isOnboard,
                playerOffset = playerOffset,
                elapsed = 0,
            })
        end
    end
end

function mover_runtime.resolveModel(mover, baseModel)
    local targetModel = baseModel or mover.model
    local da = mover.doorAnim
    if not targetModel then return nil end

    local lineSuffix = targetModel:match("(_l%d)") or ""
    local carRole = ""
    if targetModel:find("_lead") then
        carRole = "_lead"
    elseif targetModel:find("_rear") then
        carRole = "_rear"
    end

    local stateSuffix = ""
    if mover.doorState == "closed" then
        stateSuffix = "_closed"
    elseif mover.doorState == "half" then
        stateSuffix = "_half"
    end

    if stateSuffix == "" then
        if carRole ~= "" then
            return "assets/models/metro/metro_wagon" .. carRole .. lineSuffix .. ".obj"
        elseif da and da.openModel then
            return da.openModel
        end
    else
        if carRole ~= "" then
            return "assets/models/metro/metro_wagon" .. carRole .. stateSuffix .. lineSuffix .. ".obj"
        elseif mover.doorState == "closed" and da and da.closedModel then
            return da.closedModel
        elseif mover.doorState == "half" and da and da.halfModel then
            return da.halfModel
        end
    end
    return targetModel
end

function mover_runtime.getPlacements(session)
    if not session or not session.currentMapData then return {} end
    if not session.movers or session.moverMapId ~= session.currentMapData.id then
        mover_runtime.initMap(session, session.currentMapData)
    end
    if not session.movers or #session.movers == 0 then return {} end
    local placements = {}
    for _, mover in ipairs(session.movers) do
        local consist = mover.consist or { { offset = 0, doors = true, model = mover.model } }
        for ci, car in ipairs(consist) do
            local carModel = car.model or mover.model
            if car.doors then
                carModel = mover_runtime.resolveModel(mover, carModel)
            end
            if carModel then
                table.insert(placements, {
                    cacheKey = tostring(mover.eventId) .. "_car_" .. ci,
                    model = carModel,
                    x = mover.curX + (car.offset or 0) + 1.5,
                    y = mover.curY + 1.5,
                    mover = mover,
                })
            end
        end
    end
    return placements
end

function mover_runtime.isBlocked(session, targetX, targetY)
    if not session or not session.movers or #session.movers == 0 then return false end
    local tx = targetX - 1
    local ty = targetY - 1

    for _, mover in ipairs(session.movers) do
        local curWp = mover.waypoints[mover.segmentIdx]
        local consist = mover.consist or { { offset = 0, doors = true } }

        -- 1. If player is currently onboard this mover
        if mover.onboard then
            -- Cannot exit while moving or while doors are closing/closed
            if mover.phase ~= "docked" or mover.doorState ~= "open" then
                return true
            end

            -- Inside docked train: allow walking between train cars / along the aisle
            for _, car in ipairs(consist) do
                local carCenter = curWp.x + (car.offset or 0)
                if tx >= carCenter - 1 and tx <= carCenter + 1 and ty == curWp.y then
                    return false
                end
            end

            -- Stepping out onto the platform dock:
            local dockDy = (curWp.dockDir == "S" and 1) or -1
            for _, car in ipairs(consist) do
                if car.doors then
                    local doorX = curWp.x + (car.offset or 0)
                    local doorY = curWp.y
                    if tx == doorX and ty == doorY + dockDy then
                        return false -- Allowed to disembark onto platform!
                    end
                end
            end
            return true -- Blocked by train walls or track trench
        end

        -- 2. If player is on platform attempting to step into a train door
        for wi, wp in ipairs(mover.waypoints) do
            for _, car in ipairs(consist) do
                if car.doors then
                    local doorX = wp.x + (car.offset or 0)
                    local doorY = wp.y
                    if tx == doorX and ty == doorY then
                        -- Player wants to enter this door
                        if mover.segmentIdx == wi and mover.phase == "docked" and mover.doorState == "open" then
                            return false -- Allowed to board!
                        else
                            return true -- Blocked: mover not docked here or doors closed
                        end
                    end
                end
            end
        end
    end

    -- Guard track trench: cannot fall into tracks unless boarding an open docked wagon
    local mat = session.currentMapData and session.currentMapData.materials
    local cellMat = mat and mat[targetY] and mat[targetY][targetX]
    if cellMat == "metro_rails" or cellMat == "metro_rails_ns" then
        return true -- Blocked by the platform drop-off / track trench!
    end

    return false
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
        local consist = mover.consist or { { offset = 0, doors = true } }

        -- Detect player boarding or disembarking
        if not mover.onboard then
            if mover.phase == "docked" and mover.doorState == "open" then
                for _, car in ipairs(consist) do
                    local doorX = curWp.x + (car.offset or 0)
                    local doorY = curWp.y
                    if px == doorX and py == doorY then
                        mover.onboard = true
                        mover.playerOffset = car.offset or 0
                        break
                    end
                end
            end
        else
            -- Onboard: only allow stepping off when docked and doors are fully open
            if mover.phase == "docked" and mover.doorState == "open" then
                local isStillInside = false
                for _, car in ipairs(consist) do
                    local carCenter = curWp.x + (car.offset or 0)
                    if px >= carCenter - 1 and px <= carCenter + 1 and py == curWp.y then
                        isStillInside = true
                        mover.playerOffset = px - curWp.x
                        break
                    end
                end
                if not isStillInside then
                    mover.onboard = false
                    mover.playerOffset = 0
                    session.moverCameraOverride = nil
                end
            end
        end

        -- State Machine
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
            local easeT = t * t * (3 - 2 * t) -- Smooth cubic acceleration and deceleration

            mover.curX = startWp.x + (endWp.x - startWp.x) * easeT
            mover.curY = startWp.y + (endWp.y - startWp.y) * easeT

            if mover.onboard and mover.carryPlayer then
                local targetX = mover.curX + (mover.playerOffset or 0)
                local targetY = mover.curY

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
                -- Reached destination waypoint!
                mover.segmentIdx = mover.nextIdx
                local arrivedWp = mover.waypoints[mover.segmentIdx]
                mover.curX = arrivedWp.x
                mover.curY = arrivedWp.y

                if mover.onboard and mover.carryPlayer then
                    session.playerX = math.floor(arrivedWp.x + (mover.playerOffset or 0) + 0.5) + 1
                    session.playerY = arrivedWp.y + 1
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

return mover_runtime
