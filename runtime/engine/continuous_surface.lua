-- Generic continuous 2D-on-3D traversal semantic.
--
-- This module deliberately owns only locomotion on an authored walk surface.
-- It does not own camera, rendering, Events, physics, pathfinding, encounter
-- scheduling, or Map lifecycle. A host supplies input and keeps the returned
-- state wherever that host's traversal-provider boundary requires.
--
-- The first contract is intentionally small: one or more authored XY walk
-- regions, optional XY obstacle polygons, a constant authored ground Z, and a
-- deterministic movement step. Complex elevation/navmesh/rigid-body behavior
-- belongs to later evidence, not to this primitive.
local continuous_surface = {}

local EPSILON = 1e-9
local DEFAULT_MAX_STEP = 0.10

local function finite(value, label)
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then
        error("continuous surface " .. label .. " must be finite", 0)
    end
    return value
end

local function positive(value, label)
    value = finite(value, label)
    if value <= 0 then
        error("continuous surface " .. label .. " must be > 0", 0)
    end
    return value
end

local function point(raw, label)
    if type(raw) ~= "table" then
        error("continuous surface " .. label .. " must be a point", 0)
    end
    return {
        x = finite(raw.x ~= nil and raw.x or raw[1], label .. ".x"),
        y = finite(raw.y ~= nil and raw.y or raw[2], label .. ".y"),
    }
end

local function samePoint(a, b)
    return math.abs(a.x - b.x) <= EPSILON and math.abs(a.y - b.y) <= EPSILON
end

local function cross(ax, ay, bx, by)
    return ax * by - ay * bx
end

local function polygonArea(points)
    local twice = 0
    for i = 1, #points do
        local a = points[i]
        local b = points[(i % #points) + 1]
        twice = twice + (a.x * b.y - b.x * a.y)
    end
    return twice * 0.5
end

local function normalizePolygon(raw, label)
    if type(raw) ~= "table" then
        error("continuous surface " .. label .. " must be an object", 0)
    end
    local authored = raw.points or raw
    if type(authored) ~= "table" or #authored < 3 then
        error("continuous surface " .. label .. " must contain at least 3 points", 0)
    end

    local points = {}
    for i, rawPoint in ipairs(authored) do
        points[i] = point(rawPoint, label .. ".points[" .. i .. "]")
        if i > 1 and samePoint(points[i - 1], points[i]) then
            error("continuous surface " .. label .. " has duplicate adjacent points", 0)
        end
    end
    if samePoint(points[1], points[#points]) then
        table.remove(points)
    end
    if #points < 3 or math.abs(polygonArea(points)) <= EPSILON then
        error("continuous surface " .. label .. " must enclose non-zero area", 0)
    end
    return { points = points }
end

local function pointOnSegment(px, py, a, b)
    local abx, aby = b.x - a.x, b.y - a.y
    local apx, apy = px - a.x, py - a.y
    if math.abs(cross(abx, aby, apx, apy)) > EPSILON then return false end
    local dot = apx * abx + apy * aby
    if dot < -EPSILON then return false end
    local len2 = abx * abx + aby * aby
    return dot <= len2 + EPSILON
end

-- Boundary-inclusive point-in-polygon. Walk-region edges are valid ground;
-- obstacle edges are invalid because the caller negates this result.
local function pointInPolygon(px, py, polygon)
    local points = polygon.points
    local inside = false
    local j = #points
    for i = 1, #points do
        local a, b = points[j], points[i]
        if pointOnSegment(px, py, a, b) then return true end
        local crosses = ((b.y > py) ~= (a.y > py))
        if crosses then
            local xAtY = (a.x - b.x) * (py - b.y) / (a.y - b.y) + b.x
            if px < xAtY then inside = not inside end
        end
        j = i
    end
    return inside
end

local function orientation(a, b, c)
    return cross(b.x - a.x, b.y - a.y, c.x - a.x, c.y - a.y)
end

local function segmentsIntersect(a, b, c, d)
    local o1 = orientation(a, b, c)
    local o2 = orientation(a, b, d)
    local o3 = orientation(c, d, a)
    local o4 = orientation(c, d, b)

    if ((o1 > EPSILON and o2 < -EPSILON) or (o1 < -EPSILON and o2 > EPSILON))
            and ((o3 > EPSILON and o4 < -EPSILON) or (o3 < -EPSILON and o4 > EPSILON)) then
        return true
    end
    if math.abs(o1) <= EPSILON and pointOnSegment(c.x, c.y, a, b) then return true end
    if math.abs(o2) <= EPSILON and pointOnSegment(d.x, d.y, a, b) then return true end
    if math.abs(o3) <= EPSILON and pointOnSegment(a.x, a.y, c, d) then return true end
    if math.abs(o4) <= EPSILON and pointOnSegment(b.x, b.y, c, d) then return true end
    return false
end

local function segmentHitsPolygon(x0, y0, x1, y1, polygon)
    if pointInPolygon(x0, y0, polygon) or pointInPolygon(x1, y1, polygon) then
        return true
    end
    local a = { x = x0, y = y0 }
    local b = { x = x1, y = y1 }
    local points = polygon.points
    for i = 1, #points do
        local c = points[i]
        local d = points[(i % #points) + 1]
        if segmentsIntersect(a, b, c, d) then return true end
    end
    return false
end

local function compile(spec)
    if type(spec) ~= "table" then
        error("continuous surface spec must be an object", 0)
    end
    local authoredRegions = spec.regions
    if type(authoredRegions) ~= "table" or #authoredRegions == 0 then
        error("continuous surface regions must be a non-empty array", 0)
    end

    local compiled = {
        speed = positive(spec.speed or 3.0, "speed"),
        maxStep = positive(spec.maxStep or DEFAULT_MAX_STEP, "maxStep"),
        groundZ = finite(spec.groundZ or 0, "groundZ"),
        regions = {},
        obstacles = {},
    }
    for i, raw in ipairs(authoredRegions) do
        compiled.regions[i] = normalizePolygon(raw, "regions[" .. i .. "]")
    end
    if spec.obstacles ~= nil and type(spec.obstacles) ~= "table" then
        error("continuous surface obstacles must be an array", 0)
    end
    for i, raw in ipairs(spec.obstacles or {}) do
        compiled.obstacles[i] = normalizePolygon(raw, "obstacles[" .. i .. "]")
    end
    return compiled
end

local function walkable(compiled, x, y)
    local onGround = false
    for _, region in ipairs(compiled.regions) do
        if pointInPolygon(x, y, region) then
            onGround = true
            break
        end
    end
    if not onGround then return false end
    for _, obstacle in ipairs(compiled.obstacles) do
        if pointInPolygon(x, y, obstacle) then return false end
    end
    return true
end

local function segmentWalkable(compiled, x0, y0, x1, y1)
    if not walkable(compiled, x1, y1) then return false end

    -- Obstacles get an exact segment/edge test so a thin authored wall cannot
    -- be tunneled through simply because both movement endpoints are outside it.
    for _, obstacle in ipairs(compiled.obstacles) do
        if segmentHitsPolygon(x0, y0, x1, y1, obstacle) then return false end
    end

    -- Walk regions are a union. The movement loop already caps each segment to
    -- maxStep; midpoint coverage catches a short excursion outside a concave
    -- boundary without pretending this small semantic is a general navmesh.
    local mx, my = (x0 + x1) * 0.5, (y0 + y1) * 0.5
    return walkable(compiled, mx, my)
end

local function normalizeInput(x, y)
    x, y = tonumber(x) or 0, tonumber(y) or 0
    local len = math.sqrt(x * x + y * y)
    if len <= EPSILON then return 0, 0, 0 end
    -- Preserve analog magnitude below one, but cap diagonals / oversized input
    -- so keyboard diagonals do not move sqrt(2) times faster.
    if len > 1 then
        x, y, len = x / len, y / len, 1
    end
    return x, y, len
end

local function tryMicroStep(state, dx, dy)
    local compiled = state._compiled
    local x0, y0 = state.x, state.y
    local x1, y1 = x0 + dx, y0 + dy
    if segmentWalkable(compiled, x0, y0, x1, y1) then
        state.x, state.y = x1, y1
        return math.sqrt(dx * dx + dy * dy)
    end

    -- Collision response is intentionally modest: try the dominant axis first
    -- and use the other axis only if it is the only legal slide. This gives a
    -- useful wall-slide without turning the traversal primitive into physics.
    local candidates = {
        { dx = dx, dy = 0, amount = math.abs(dx), order = 1 },
        { dx = 0, dy = dy, amount = math.abs(dy), order = 2 },
    }
    table.sort(candidates, function(a, b)
        if math.abs(a.amount - b.amount) <= EPSILON then return a.order < b.order end
        return a.amount > b.amount
    end)
    for _, candidate in ipairs(candidates) do
        if candidate.amount > EPSILON then
            local cx, cy = x0 + candidate.dx, y0 + candidate.dy
            if segmentWalkable(compiled, x0, y0, cx, cy) then
                state.x, state.y = cx, cy
                return candidate.amount
            end
        end
    end
    return 0
end

function continuous_surface.compile(spec)
    return compile(spec)
end

function continuous_surface.new(spec, spawn)
    local compiled = compile(spec)
    spawn = spawn or {}
    local x = finite(spawn.x ~= nil and spawn.x or spawn[1], "spawn.x")
    local y = finite(spawn.y ~= nil and spawn.y or spawn[2], "spawn.y")
    if not walkable(compiled, x, y) then
        error("continuous surface spawn must be on walkable ground", 0)
    end
    local z = spawn.z ~= nil and finite(spawn.z, "spawn.z") or compiled.groundZ
    return {
        provider = "continuous_surface",
        x = x,
        y = y,
        z = z,
        facingX = 0,
        facingY = 1,
        moving = false,
        walkDistance = 0,
        _compiled = compiled,
    }
end

function continuous_surface.isWalkable(state, x, y)
    if type(state) ~= "table" or state.provider ~= "continuous_surface" or not state._compiled then
        return false
    end
    x = finite(x, "query.x")
    y = finite(y, "query.y")
    return walkable(state._compiled, x, y)
end

-- Move by an authored world-space delta, with collision resolution. Returns the
-- actual distance travelled. This is useful to deterministic harnesses and to a
-- future host that already owns its own input integration.
function continuous_surface.moveBy(state, dx, dy)
    if type(state) ~= "table" or state.provider ~= "continuous_surface" or not state._compiled then
        error("continuous surface moveBy requires a live state", 0)
    end
    dx = finite(dx, "move.dx")
    dy = finite(dy, "move.dy")
    local distance = math.sqrt(dx * dx + dy * dy)
    if distance <= EPSILON then
        state.moving = false
        return 0
    end

    local steps = math.max(1, math.ceil(distance / state._compiled.maxStep))
    local sx, sy = dx / steps, dy / steps
    local moved = 0
    for _ = 1, steps do
        moved = moved + tryMicroStep(state, sx, sy)
    end
    state.moving = moved > EPSILON
    state.walkDistance = (state.walkDistance or 0) + moved
    return moved
end

-- Frame-rate-independent host-facing update. Input is an XY vector in authored
-- world coordinates. Analog magnitude <= 1 is preserved; magnitude > 1 is
-- normalized. Returns actual distance travelled this update.
function continuous_surface.update(state, dt, inputX, inputY)
    if type(state) ~= "table" or state.provider ~= "continuous_surface" or not state._compiled then
        error("continuous surface update requires a live state", 0)
    end
    dt = finite(dt or 0, "dt")
    if dt < 0 then error("continuous surface dt must be >= 0", 0) end

    local nx, ny, magnitude = normalizeInput(inputX, inputY)
    if magnitude <= EPSILON or dt <= EPSILON then
        state.moving = false
        return 0
    end
    state.facingX, state.facingY = nx, ny
    local scale = state._compiled.speed * dt * magnitude
    return continuous_surface.moveBy(state, nx * scale, ny * scale)
end

function continuous_surface.serialize(state)
    if type(state) ~= "table" or state.provider ~= "continuous_surface" then
        error("continuous surface serialize requires a live state", 0)
    end
    return {
        provider = "continuous_surface",
        x = state.x,
        y = state.y,
        z = state.z,
        facingX = state.facingX,
        facingY = state.facingY,
        walkDistance = state.walkDistance or 0,
    }
end

function continuous_surface.restore(spec, saved)
    if type(saved) ~= "table" or saved.provider ~= "continuous_surface" then
        error("continuous surface restore requires continuous_surface state", 0)
    end
    local state = continuous_surface.new(spec, {
        x = saved.x,
        y = saved.y,
        z = saved.z,
    })
    local fx = tonumber(saved.facingX)
    local fy = tonumber(saved.facingY)
    if fx and fy then
        local nx, ny, magnitude = normalizeInput(fx, fy)
        if magnitude > EPSILON then state.facingX, state.facingY = nx, ny end
    end
    state.walkDistance = math.max(0, tonumber(saved.walkDistance) or 0)
    return state
end

-- Exposed for deterministic tooling/Studio adapters without duplicating the
-- semantic point-in-polygon rule in another host.
function continuous_surface.containsPolygonPoint(rawPolygon, x, y)
    local polygon = normalizePolygon(rawPolygon, "polygon")
    return pointInPolygon(finite(x, "point.x"), finite(y, "point.y"), polygon)
end

return continuous_surface
