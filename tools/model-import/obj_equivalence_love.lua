local function fail(message)
    error("OBJ equivalence: " .. tostring(message), 0)
end

local function near(actual, expected, label)
    if type(actual) ~= "number" or math.abs(actual - expected) > 1e-6 then
        fail((label or "number") .. " expected " .. tostring(expected)
            .. ", got " .. tostring(actual))
    end
end

local function rowNear(actual, expected, label)
    if type(actual) ~= "table" or #actual ~= #expected then
        fail((label or "row") .. " length mismatch")
    end
    for index = 1, #expected do
        near(actual[index], expected[index], (label or "row") .. "[" .. index .. "]")
    end
end

local EXPECTED_VERTICES = {
    { 0, 0, 0, 0, 0, 0, -1, 0, 1, 1, 1, 1 },
    { 1, 0, 0, 1, 0, 0, -1, 0, 1, 1, 1, 1 },
    { 0, 0, 1, 0, 1, 0, -1, 0, 1, 1, 1, 1 },
}

local EXPECTED_BOUNDS = {
    minX = 0, minY = 0, minZ = 0,
    maxX = 1, maxY = 0, maxZ = 1,
}

local function run()
    local obj_model = require("presentation.obj_model")
    local path = "tools/model-import/fixtures/static-equivalence.obj"
    local source = love.filesystem.read(path)
    if not source then fail("fixture missing: " .. path) end

    local parsed = obj_model.parse(source, path)
    if parsed.vertexCount ~= 3 then fail("expected vertexCount 3, got " .. tostring(parsed.vertexCount)) end
    if #parsed.groups ~= 1 then fail("expected one material group, got " .. tostring(#parsed.groups)) end
    local group = parsed.groups[1]
    if group.material ~= "body" then fail("expected material 'body', got '" .. tostring(group.material) .. "'") end
    if #group.vertices ~= #EXPECTED_VERTICES then fail("unexpected normalized vertex count") end
    for index = 1, #EXPECTED_VERTICES do
        rowNear(group.vertices[index], EXPECTED_VERTICES[index], "vertex " .. index)
    end
    for key, expected in pairs(EXPECTED_BOUNDS) do
        near(parsed.bounds[key], expected, "bounds." .. key)
    end

    print("OBJ_GLTF_EQUIVALENCE_OBJ_SIDE_OK")
end

function love.load()
    local ok, err = xpcall(run, debug.traceback)
    if ok then
        love.event.quit(0)
        return
    end
    print("OBJ_GLTF_EQUIVALENCE_OBJ_SIDE_FAILED")
    print(err)
    love.event.quit(1)
end
