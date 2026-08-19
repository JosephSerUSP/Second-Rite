-- Runtime adapter for deterministic, renderer-neutral vertex shading.
--
-- The executable semantic authority is shared/semantics/vertex-shading.ts and
-- is mechanically compiled to engine/generated/vertex-shading.lua. This file
-- retains only the Lua-facing return shape and runtime authored-data validation
-- hook; it does not carry a second shading algorithm.
local semantics = require("engine.generated.vertex-shading")
local vertex_shading = {}

vertex_shading.hash01 = semantics.hash01
vertex_shading.valueNoise = semantics.valueNoise
vertex_shading.fractalNoise = semantics.fractalNoise
vertex_shading.validate = semantics.validate
vertex_shading.compile = semantics.compile
vertex_shading.grid = semantics.grid

function vertex_shading.assertValid(layers, where)
    local problems = semantics.validate(layers, where)
    if #problems > 0 then error(table.concat(problems, "\n"), 0) end
    return true
end

-- TypeScript/JavaScript naturally returns an RGB tuple. Keep the historical
-- Lua API's three return values at this host boundary so runtime consumers do
-- not need to know how the shared implementation is authored.
function vertex_shading.sampleCompiled(compiled, x, y)
    local rgb = semantics.sampleCompiled(compiled, x, y)
    return rgb[1], rgb[2], rgb[3]
end

function vertex_shading.sample(layers, x, y)
    local rgb = semantics.sample(layers, x, y)
    return rgb[1], rgb[2], rgb[3]
end

local function assertPinned(actual, expected, label)
    if math.abs(actual - expected) > 1e-12 then
        error("vertex shading numerical contract drifted at " .. label
            .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual), 0)
    end
end

function vertex_shading.validateAuthored(loader)
    -- These pins remain runtime truth checks, but the implementation they pin is
    -- now the same mechanically authored source that Studio executes locally.
    assertPinned(vertex_shading.hash01(0, 0, 0), 0.9616300366300367, "hash 0,0,0")
    assertPinned(vertex_shading.hash01(1, 2, 1729), 0.18543956043956045, "hash 1,2,1729")
    assertPinned(vertex_shading.hash01(-1, 0, 23), 0.6313644688644688, "hash -1,0,23")
    assertPinned(vertex_shading.valueNoise(0.5, 0.5, 1729), 0.42679334554334547, "value noise .5,.5")
    assertPinned(vertex_shading.fractalNoise(0.5, 0.5, 1729), 0.4540415838459217, "fractal .5,.5")
    assertPinned(vertex_shading.fractalNoise(1.25, 2.75, 1729), 0.45447714242048237, "fractal 1.25,2.75")
    assertPinned(vertex_shading.fractalNoise(-0.25, 0.5, 23), 0.3765472024340493, "fractal -.25,.5")

    local problems = {}
    for index, map in ipairs((loader and loader.maps) or {}) do
        local label = map.name or map.title or map.id or index
        local found = vertex_shading.validate(map.vertexShadingLayers,
            "map '" .. tostring(label) .. "' vertexShadingLayers")
        for _, problem in ipairs(found) do problems[#problems + 1] = problem end
    end
    if #problems > 0 then
        error("vertex shading validation failed:\n" .. table.concat(problems, "\n"), 0)
    end
    return true
end

return vertex_shading
