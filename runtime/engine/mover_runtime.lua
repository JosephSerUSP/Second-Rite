-- Generic authored path-mover runtime.
--
-- A mover is an ordinary Map Event with a declarative mover block. The runtime
-- owns only reusable kinematics, occupancy, boarding and carry state. Route
-- geometry, footprint, boarding ports and presentation-state models are all
-- authored data; this module contains no Project-, vehicle- or material-
-- specific knowledge.
local event_actor = require("engine.event_actor")

local mover_runtime = {}
local VALID_MODES = { loop = true, ping_pong = true, once = true }

local function mapKey(session)
    local mapData = session and session.currentMapData
    local id = mapData and mapData.id or (session and session.currentMapIndex)
    return tostring(id or "__unscoped__")
end

local function eventKey(ev)
    if type(ev) ~= "table" then return nil end
    return ev.instanceId or (ev.id ~= nil and tostring(ev.id)) or nil
end

local function stateBucket(session, create)
    if type(session) ~= "table" then error("mover_runtime: session table required", 3) end
    if not session.moverRuntime and create then session.moverRuntime = {} end
    if not session.moverRuntime then return nil end
    local key = mapKey(session)
    local bucket = session.moverRuntime[key]
    if not bucket and create then bucket = {}; session.moverRuntime[key] = bucket end
    return bucket
end

local function currentEvents(session)
    return (session and session.currentMapData and session.currentMapData.events) or {}
end

local function findEvent(session, key)
    for _, ev in ipairs(currentEvents(session)) do
        if ev.mover and eventKey(ev) == key then return ev end
    end
    return nil
end

local function waypointDwell(spec, wp)
    return tonumber(wp and wp.dwell) or tonumber(spec.dwell) or 4.0
end

local function nextIndex(spec, current, direction)
    local n = #spec.waypoints
    local mode = spec.mode or "ping_pong"
    if mode == "loop" then
        return (current % n) + 1, direction
    elseif mode == "ping_pong" then
        if current >= n then direction = -1 end
        if current <= 1 then direction = 1 end
        return current + direction, direction
    elseif current < n then
        return current + 1, direction
    end
    return nil, direction
end

local function newState(spec)
    local index = math.floor(tonumber(spec.initialWaypoint) or 1)
    if index < 1 or index > #spec.waypoints then index = 1 end
    local direction = 1
    local nxt
    nxt, direction = nextIndex(spec, index, direction)
    local wp = spec.waypoints[index]
    return {
        waypoint = index, nextWaypoint = nxt, direction = direction,
        phase = "docked", doorState = "open", timer = waypointDwell(spec, wp),
        x = wp.x, y = wp.y, onboard = false,
        playerOffsetX = 0, playerOffsetY = 0, transitDuration = nil,
    }
end

local function stateFor(session, ev, create)
    local key = eventKey(ev)
    if not key then error("mover_runtime: mover Event requires stable identity", 3) end
    local bucket = stateBucket(session, create)
    if not bucket then return nil end
    local state = bucket[key]
    if not state and create then state = newState(ev.mover); bucket[key] = state end
    return state
end

local function offsetCell(entry, label)
    if type(entry) ~= "table" then error(label .. " must be a table", 4) end
    local x, y = tonumber(entry.x), tonumber(entry.y)
    if not x or not y or x % 1 ~= 0 or y % 1 ~= 0 then
        error(label .. ".x/.y must be integer offsets", 4)
    end
    return x, y
end

function mover_runtime.validateSpec(spec)
    if type(spec) ~= "table" then error("mover must be a table", 2) end
    if spec.type ~= "path" then error("mover.type must be 'path'", 2) end
    if type(spec.waypoints) ~= "table" or #spec.waypoints < 2 then
        error("path mover requires at least two waypoints", 2)
    end
    for i, wp in ipairs(spec.waypoints) do
        if type(wp) ~= "table" or type(wp.x) ~= "number" or type(wp.y) ~= "number" then
            error("mover.waypoints[" .. i .. "] requires numeric x/y", 2)
        end
        if wp.dwell ~= nil and (type(wp.dwell) ~= "number" or wp.dwell < 0) then
            error("mover.waypoints[" .. i .. "].dwell must be >= 0", 2)
        end
    end
    if spec.speed ~= nil and (type(spec.speed) ~= "number" or spec.speed <= 0) then
        error("mover.speed must be > 0", 2)
    end
    if spec.dwell ~= nil and (type(spec.dwell) ~= "number" or spec.dwell < 0) then
        error("mover.dwell must be >= 0", 2)
    end
    if spec.mode ~= nil and not VALID_MODES[spec.mode] then
        error("mover.mode must be loop, ping_pong or once", 2)
    end
    if spec.initialWaypoint ~= nil then
        local index = tonumber(spec.initialWaypoint)
        if not index or index % 1 ~= 0 or index < 1 or index > #spec.waypoints then
            error("mover.initialWaypoint is outside waypoint range", 2)
        end
    end
    if spec.carryPlayer ~= nil and type(spec.carryPlayer) ~= "boolean" then
        error("mover.carryPlayer must be boolean", 2)
    end

    local footprint = spec.footprint or { { x = 0, y = 0 } }
    if type(footprint) ~= "table" or #footprint == 0 then
        error("mover.footprint must contain at least one cell", 2)
    end
    local footprintSet = {}
    for i, cell in ipairs(footprint) do
        local x, y = offsetCell(cell, "mover.footprint[" .. i .. "]")
        footprintSet[x .. "," .. y] = true
    end
    for i, port in ipairs(spec.ports or {}) do
        if type(port) ~= "table" then error("mover.ports[" .. i .. "] must be a table", 2) end
        local ix, iy = offsetCell(port.inside, "mover.ports[" .. i .. "].inside")
        offsetCell(port.outside, "mover.ports[" .. i .. "].outside")
        if not footprintSet[ix .. "," .. iy] then
            error("mover.ports[" .. i .. "].inside must lie in mover.footprint", 2)
        end
    end
    if spec.carryPlayer == true and #(spec.ports or {}) == 0 then
        error("carryPlayer mover requires at least one authored port", 2)
    end
    if spec.door ~= nil then
        if type(spec.door) ~= "table" then error("mover.door must be a table", 2) end
        for _, key in ipairs({ "closeSeconds", "openSeconds" }) do
            if spec.door[key] ~= nil and (type(spec.door[key]) ~= "number" or spec.door[key] < 0) then
                error("mover.door." .. key .. " must be >= 0", 2)
            end
        end
    end
    if spec.visual ~= nil then
        if type(spec.visual) ~= "table" then error("mover.visual must be a table", 2) end
        if spec.visual.models ~= nil then
            if type(spec.visual.models) ~= "table" then error("mover.visual.models must be a table", 2) end
            for state, path in pairs(spec.visual.models) do
                if type(state) ~= "string" or type(path) ~= "string" or path == "" then
                    error("mover.visual.models entries must be non-empty string paths", 2)
                end
            end
        end
    end
    return true
end

local function projectState(session, ev, state)
    event_actor.setRoot(session, ev, state.x, state.y)
end

local function footprint(spec)
    return spec.footprint or { { x = 0, y = 0 } }
end

local function containsAt(spec, baseX, baseY, x, y)
    for _, cell in ipairs(footprint(spec)) do
        if baseX + cell.x == x and baseY + cell.y == y then return true end
    end
    return false
end

local function reservedAt(spec, x, y)
    for _, wp in ipairs(spec.waypoints) do
        if containsAt(spec, wp.x, wp.y, x, y) then return true end
    end
    return false
end

local function portTransition(spec, baseX, baseY, fromX, fromY, toX, toY)
    for _, port in ipairs(spec.ports or {}) do
        local ix, iy = baseX + port.inside.x, baseY + port.inside.y
        local ox, oy = baseX + port.outside.x, baseY + port.outside.y
        if fromX == ox and fromY == oy and toX == ix and toY == iy then return "board" end
        if fromX == ix and fromY == iy and toX == ox and toY == oy then return "exit" end
    end
    return nil
end

function mover_runtime.activateMap(session)
    if not session or not session.currentMapData then return end
    local bucket = stateBucket(session, true)
    local live = {}
    for _, ev in ipairs(currentEvents(session)) do
        if ev.mover then
            mover_runtime.validateSpec(ev.mover)
            local key = eventKey(ev)
            if not key then error("mover Event requires instanceId or id", 2) end
            live[key] = true
            local state = stateFor(session, ev, true)
            projectState(session, ev, state)
            if state.onboard and ev.mover.carryPlayer == true then
                session.playerX = math.floor(state.x + (state.playerOffsetX or 0) + 0.5) + 1
                session.playerY = math.floor(state.y + (state.playerOffsetY or 0) + 0.5) + 1
            end
        end
    end
    for key in pairs(bucket) do if not live[key] then bucket[key] = nil end end
end

local function activeOnboard(session)
    local bucket = stateBucket(session, false)
    if not bucket then return nil end
    for key, state in pairs(bucket) do
        if state.onboard then
            local ev = findEvent(session, key)
            if ev then return ev, state end
        end
    end
    return nil
end

function mover_runtime.stepPolicy(session, targetX, targetY)
    if not session or not session.currentMapData then return nil end
    mover_runtime.activateMap(session)
    local fromX, fromY = (session.playerX or 1) - 1, (session.playerY or 1) - 1
    local toX, toY = targetX - 1, targetY - 1
    local onboardEv, onboardState = activeOnboard(session)
    if onboardEv then
        local spec = onboardEv.mover
        if onboardState.phase ~= "docked" or onboardState.doorState ~= "open" then return "block" end
        if containsAt(spec, onboardState.x, onboardState.y, toX, toY) then return "allow" end
        if portTransition(spec, onboardState.x, onboardState.y, fromX, fromY, toX, toY) == "exit" then return "allow" end
        return "block"
    end
    local reserved = false
    for _, ev in ipairs(currentEvents(session)) do
        if ev.mover then
            local spec, state = ev.mover, stateFor(session, ev, true)
            if state.phase == "docked" and state.doorState == "open"
                    and portTransition(spec, state.x, state.y, fromX, fromY, toX, toY) == "board" then
                return "allow"
            end
            if reservedAt(spec, toX, toY) then reserved = true end
        end
    end
    return reserved and "block" or nil
end

function mover_runtime.afterPlayerStep(session)
    if not session or not session.currentMapData then return end
    local px, py = (session.playerX or 1) - 1, (session.playerY or 1) - 1
    local onboardEv, onboardState = activeOnboard(session)
    if onboardEv then
        if containsAt(onboardEv.mover, onboardState.x, onboardState.y, px, py) then
            onboardState.playerOffsetX = px - onboardState.x
            onboardState.playerOffsetY = py - onboardState.y
        else
            onboardState.onboard = false
            onboardState.playerOffsetX, onboardState.playerOffsetY = 0, 0
        end
        return
    end
    for _, ev in ipairs(currentEvents(session)) do
        if ev.mover then
            local state = stateFor(session, ev, true)
            if state.phase == "docked" and state.doorState == "open"
                    and containsAt(ev.mover, state.x, state.y, px, py) then
                state.onboard = true
                state.playerOffsetX, state.playerOffsetY = px - state.x, py - state.y
                return
            end
        end
    end
end

local function startLeg(spec, state)
    local nxt, direction = nextIndex(spec, state.waypoint, state.direction or 1)
    state.direction, state.nextWaypoint = direction, nxt
    if not nxt then state.phase, state.timer = "docked", 999999999; return false end
    local a, b = spec.waypoints[state.waypoint], spec.waypoints[nxt]
    local dx, dy = b.x - a.x, b.y - a.y
    state.transitDuration = math.max(0.05, math.sqrt(dx * dx + dy * dy) / (tonumber(spec.speed) or 3.0))
    state.timer, state.phase, state.doorState = state.transitDuration, "moving", "closed"
    return true
end

local function carryPlayer(session, spec, state)
    if not state.onboard or spec.carryPlayer ~= true then return end
    local x, y = state.x + (state.playerOffsetX or 0), state.y + (state.playerOffsetY or 0)
    session.playerX, session.playerY = math.floor(x + 0.5) + 1, math.floor(y + 0.5) + 1
end

function mover_runtime.update(session, dt)
    if not session or not session.currentMapData then return end
    if type(dt) ~= "number" or dt < 0 then error("mover_runtime.update: dt must be >= 0", 2) end
    mover_runtime.activateMap(session)
    for _, ev in ipairs(currentEvents(session)) do
        local spec = ev.mover
        if spec then
            local state = stateFor(session, ev, true)
            local wp = spec.waypoints[state.waypoint]
            local closeSeconds = (spec.door and tonumber(spec.door.closeSeconds)) or 0
            local openSeconds = (spec.door and tonumber(spec.door.openSeconds)) or 0
            if state.phase == "docked" then
                state.x, state.y, state.doorState = wp.x, wp.y, "open"
                state.timer = (state.timer or waypointDwell(spec, wp)) - dt
                if state.timer <= 0 then
                    if closeSeconds > 0 then
                        state.phase, state.doorState, state.timer = "closing", "closing", closeSeconds
                    else startLeg(spec, state) end
                end
            elseif state.phase == "closing" then
                state.x, state.y, state.timer = wp.x, wp.y, state.timer - dt
                if state.timer <= 0 then startLeg(spec, state) end
            elseif state.phase == "moving" then
                local target, duration = spec.waypoints[state.nextWaypoint], state.transitDuration or 0.05
                state.timer = state.timer - dt
                local t = 1 - math.max(0, math.min(1, state.timer / duration))
                local smooth = t * t * (3 - 2 * t)
                state.x = wp.x + (target.x - wp.x) * smooth
                state.y = wp.y + (target.y - wp.y) * smooth
                if state.timer <= 0 then
                    state.waypoint = state.nextWaypoint
                    wp = spec.waypoints[state.waypoint]
                    state.x, state.y = wp.x, wp.y
                    if openSeconds > 0 then
                        state.phase, state.doorState, state.timer = "opening", "opening", openSeconds
                    else
                        state.phase, state.doorState, state.timer = "docked", "open", waypointDwell(spec, wp)
                    end
                end
            elseif state.phase == "opening" then
                state.x, state.y, state.timer = wp.x, wp.y, state.timer - dt
                if state.timer <= 0 then
                    state.phase, state.doorState, state.timer = "docked", "open", waypointDwell(spec, wp)
                end
            else error("mover_runtime: unknown phase " .. tostring(state.phase), 2) end
            projectState(session, ev, state)
            carryPlayer(session, spec, state)
        end
    end
end

function mover_runtime.playerWorldRoot(session)
    local ev, state = activeOnboard(session)
    if not ev or ev.mover.carryPlayer ~= true then return nil end
    return state.x + (state.playerOffsetX or 0) + 1.5, state.y + (state.playerOffsetY or 0) + 1.5
end

function mover_runtime.presentationModel(session, ev, fallback)
    if not ev or not ev.mover then return fallback end
    local models = ev.mover.visual and ev.mover.visual.models
    if type(models) ~= "table" then return fallback end
    local state = stateFor(session, ev, false)
    local phase, door = state and state.phase or "docked", state and state.doorState or "open"
    if phase == "moving" then return models.moving or models.closed or fallback end
    if door == "closing" then return models.closing or models.closed or fallback end
    if door == "opening" then return models.opening or models.open or fallback end
    return models.open or fallback
end

function mover_runtime.stateForEvent(session, ev)
    return stateFor(session, ev, false)
end

return mover_runtime
