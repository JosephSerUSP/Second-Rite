local function fail(message)
    error("shared bundle LÖVE probe: " .. tostring(message), 0)
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

local function run()
    local consumer = require("tools.model-import.static_bundle_love")
    local path = "tools/model-import/fixtures/static-equivalence.bundle.json"
    local text = love.filesystem.read(path)
    if not text then fail("fixture missing: " .. path) end
    local model = consumer.modelFromText(text)

    if model.vertexCount ~= 3 then fail("expected vertexCount 3") end
    if #model.groups ~= 1 then fail("expected one group") end
    if model.groups[1].material ~= "body" then fail("expected body material identity") end
    for index = 1, #EXPECTED_VERTICES do
        rowNear(model.groups[1].vertices[index], EXPECTED_VERTICES[index], "vertex " .. index)
    end
    near(model.bounds.minX, 0, "minX")
    near(model.bounds.minY, 0, "minY")
    near(model.bounds.minZ, 0, "minZ")
    near(model.bounds.maxX, 1, "maxX")
    near(model.bounds.maxY, 0, "maxY")
    near(model.bounds.maxZ, 1, "maxZ")

    print("SHARED_STATIC_BUNDLE_LOVE_SIDE_OK")
end

function love.load()
    local ok, err = xpcall(run, debug.traceback)
    if ok then
        love.event.quit(0)
        return
    end
    print("SHARED_STATIC_BUNDLE_LOVE_SIDE_FAILED")
    print(err)
    love.event.quit(1)
end
