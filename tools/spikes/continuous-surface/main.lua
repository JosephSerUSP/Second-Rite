local traversal
local state
local fixture
local testsRun = 0

local function repositoryRoot()
    local source = love.filesystem.getSource():gsub("\\", "/")
    local root = source:match("^(.*)/tools/spikes/continuous%-surface$")
    if not root then
        error("continuous-surface spike must run from its repository path; source=" .. source)
    end
    return root
end

local function assertTrue(value, message)
    testsRun = testsRun + 1
    if not value then error(message or "assertion failed", 0) end
end

local function assertNear(actual, expected, epsilon, message)
    testsRun = testsRun + 1
    epsilon = epsilon or 1e-6
    if math.abs(actual - expected) > epsilon then
        error((message or "values differ") .. string.format(
            ": expected %.9f, got %.9f", expected, actual), 0)
    end
end

local function expectError(fn, needle)
    testsRun = testsRun + 1
    local ok, err = pcall(fn)
    if ok then error("expected error containing '" .. needle .. "'", 0) end
    if not tostring(err):find(needle, 1, true) then
        error("expected error containing '" .. needle .. "', got: " .. tostring(err), 0)
    end
end

local function rectangle(x0, y0, x1, y1)
    return { points = {
        { x0, y0 }, { x1, y0 }, { x1, y1 }, { x0, y1 },
    } }
end

local function openSpec()
    return {
        speed = 3.0,
        maxStep = 0.10,
        groundZ = 0.25,
        regions = { rectangle(0, 0, 30, 30) },
        obstacles = {},
    }
end

local function runTests()
    testsRun = 0

    do
        local s = traversal.new(openSpec(), { x = 2, y = 2 })
        local beforeX, beforeY = s.x, s.y
        local moved = traversal.update(s, 1.0, 1, 1)
        assertNear(moved, 3.0, 1e-6, "keyboard diagonal has unit speed")
        local displacement = math.sqrt((s.x - beforeX) ^ 2 + (s.y - beforeY) ^ 2)
        assertNear(displacement, 3.0, 1e-6, "diagonal displacement is normalized")
        assertNear(s.z, 0.25, 1e-9, "ground Z survives movement")
    end

    do
        local s = traversal.new(openSpec(), { x = 2, y = 2 })
        traversal.update(s, 1.0, 0.5, 0)
        assertNear(s.x, 3.5, 1e-6, "analog half magnitude travels half speed")
    end

    do
        local a = traversal.new(openSpec(), { x = 2, y = 2 })
        local b = traversal.new(openSpec(), { x = 2, y = 2 })
        for _ = 1, 60 do traversal.update(a, 1 / 60, 1, 0) end
        for _ = 1, 10 do traversal.update(b, 0.1, 1, 0) end
        assertNear(a.x, b.x, 1e-6, "open-field movement is frame-rate independent")
        assertNear(a.y, b.y, 1e-6, "open-field Y is frame-rate independent")
    end

    do
        local spec = openSpec()
        spec.obstacles = { rectangle(4.0, 0.5, 4.15, 10.0) }
        local s = traversal.new(spec, { x = 2, y = 5 })
        traversal.moveBy(s, 8, 0)
        assertTrue(s.x < 4.0, "thin obstacle cannot be tunneled through")
        assertTrue(s.x > 2.0, "movement advances until obstacle")
    end

    do
        local spec = {
            speed = 3,
            maxStep = 0.1,
            regions = { rectangle(0, 0, 4, 8) },
        }
        local s = traversal.new(spec, { x = 3.95, y = 2 })
        traversal.update(s, 0.5, 1, 1)
        assertTrue(s.x <= 4.0 + 1e-9, "outer boundary contains X")
        assertTrue(s.y > 2.0, "blocked diagonal slides along legal axis")
    end

    do
        local spec = openSpec()
        spec.obstacles = { rectangle(3, 3, 5, 5) }
        local s = traversal.new(spec, { x = 2, y = 2 })
        assertTrue(traversal.isWalkable(s, 2, 2), "ordinary floor is walkable")
        assertTrue(not traversal.isWalkable(s, 4, 4), "obstacle interior is not walkable")
        assertTrue(not traversal.isWalkable(s, 31, 31), "outside region is not walkable")
    end

    do
        local spec = openSpec()
        local s = traversal.new(spec, { x = 4, y = 7 })
        traversal.update(s, 0.25, -1, 0.25)
        local saved = traversal.serialize(s)
        local restored = traversal.restore(spec, saved)
        assertNear(restored.x, s.x, 1e-9, "serialized X restores")
        assertNear(restored.y, s.y, 1e-9, "serialized Y restores")
        assertNear(restored.z, s.z, 1e-9, "serialized Z restores")
        assertNear(restored.walkDistance, s.walkDistance, 1e-9,
            "serialized traversal distance restores")
    end

    expectError(function()
        traversal.new(openSpec(), { x = 100, y = 100 })
    end, "spawn must be on walkable ground")

    expectError(function()
        traversal.compile({ regions = {} })
    end, "regions must be a non-empty array")

    assertTrue(traversal.containsPolygonPoint(rectangle(0, 0, 2, 2), 1, 1),
        "shared polygon containment accepts interior")
    assertTrue(traversal.containsPolygonPoint(rectangle(0, 0, 2, 2), 0, 1),
        "shared polygon containment includes walk boundary")

    print("CONTINUOUS_SURFACE_SPIKE_OK tests=" .. testsRun)
end

local function makeFixture()
    return {
        speed = 3.2,
        maxStep = 0.08,
        groundZ = 0,
        -- One concave authored room: lobby to the left, a narrower service
        -- corridor rising on the right. This is deliberately not a grid.
        regions = {
            { points = {
                { 0, 0 }, { 14, 0 }, { 14, 5 }, { 10, 5 },
                { 10, 11 }, { 0, 11 },
            } },
        },
        obstacles = {
            rectangle(3.2, 2.0, 5.2, 7.8),
            rectangle(7.0, 1.2, 8.0, 4.7),
            rectangle(1.0, 9.0, 6.5, 9.6),
        },
    }
end

function love.load(args)
    local root = repositoryRoot()
    package.path = root .. "/runtime/?.lua;" .. root .. "/runtime/?/init.lua;" .. package.path
    traversal = require("engine.continuous_surface")

    runTests()
    for _, value in ipairs(args or {}) do
        if value == "--test-only" then
            love.event.quit(0)
            return
        end
    end

    fixture = makeFixture()
    state = traversal.new(fixture, { x = 1.5, y = 1.5 })
end

function love.keypressed(key)
    if key == "escape" then love.event.quit() end
    if key == "r" then state = traversal.new(fixture, { x = 1.5, y = 1.5 }) end
end

function love.update(dt)
    if not state then return end
    local x, y = 0, 0
    if love.keyboard.isDown("left") or love.keyboard.isDown("a") then x = x - 1 end
    if love.keyboard.isDown("right") or love.keyboard.isDown("d") then x = x + 1 end
    if love.keyboard.isDown("up") or love.keyboard.isDown("w") then y = y - 1 end
    if love.keyboard.isDown("down") or love.keyboard.isDown("s") then y = y + 1 end
    traversal.update(state, dt, x, y)
end

local function transformPoint(p, ox, oy, scale)
    return ox + p.x * scale, oy + p.y * scale
end

local function polygonVertices(poly, ox, oy, scale)
    local vertices = {}
    for _, p in ipairs(poly.points or poly) do
        local x = p.x ~= nil and p.x or p[1]
        local y = p.y ~= nil and p.y or p[2]
        vertices[#vertices + 1] = ox + x * scale
        vertices[#vertices + 1] = oy + y * scale
    end
    return vertices
end

function love.draw()
    if not state then return end
    local ox, oy, scale = 90, 80, 42

    love.graphics.print("continuous_surface semantic spike", 22, 18)
    love.graphics.print("WASD / arrows move diagonally; R resets; Esc quits", 22, 38)
    love.graphics.print(string.format("position  X %.3f   Y %.3f   Z %.3f", state.x, state.y, state.z), 22, 58)

    for _, region in ipairs(fixture.regions) do
        local vertices = polygonVertices(region, ox, oy, scale)
        love.graphics.polygon("fill", vertices)
        love.graphics.polygon("line", vertices)
    end

    for _, obstacle in ipairs(fixture.obstacles) do
        local vertices = polygonVertices(obstacle, ox, oy, scale)
        love.graphics.polygon("fill", vertices)
        love.graphics.polygon("line", vertices)
    end

    local px, py = ox + state.x * scale, oy + state.y * scale
    love.graphics.circle("fill", px, py, 8)
    love.graphics.line(px, py,
        px + state.facingX * 22,
        py + state.facingY * 22)

    love.graphics.print("The geometry is authored polygon data; camera/rendering are intentionally absent from the semantic.",
        22, love.graphics.getHeight() - 30)
end
