-- Resolved consumer facts, below Map/Event/environment authoring semantics.
-- Z-up, map-cell translation, row-major orientation and positive uniform scale.
-- This is not an authored scene graph or an additional gameplay owner.
local instance = {}
local function finite(value)
    return type(value) == "number" and value == value
        and value ~= math.huge and value ~= -math.huge
end

function instance.new(id, modelId, transform, provenance, bakedLighting)
    assert(type(id) == "string" and id ~= "", "Model Instance requires identity")
    assert(type(modelId) == "string" and modelId ~= "", "Model Instance requires Model reference")
    assert(type(transform) == "table", "Model Instance requires transform")
    assert(type(transform.translation) == "table" and #transform.translation == 3, "Model Instance requires XYZ translation")
    assert(type(transform.orientation) == "table" and #transform.orientation == 9, "Model Instance requires row-major orientation")
    for _, value in ipairs(transform.translation) do assert(finite(value), "invalid Model Instance translation") end
    for _, value in ipairs(transform.orientation) do assert(finite(value), "invalid Model Instance orientation") end
    assert(finite(transform.scale) and transform.scale > 0, "Model Instance scale must be positive")
    for a = 0, 2 do
        for b = a, 2 do
            local dot = 0
            for row = 0, 2 do dot = dot + transform.orientation[row * 3 + a + 1] * transform.orientation[row * 3 + b + 1] end
            assert(math.abs(dot - (a == b and 1 or 0)) < 0.00001, "Model Instance orientation must be orthonormal")
        end
    end
    assert(bakedLighting == nil or type(bakedLighting) == "boolean", "Model Instance bakedLighting must be boolean")
    return { id = id, modelId = modelId, transform = transform,
        provenance = provenance, bakedLighting = bakedLighting == true }
end

function instance.direction(value, x, y, z)
    local m = value.transform.orientation
    return m[1]*x + m[2]*y + m[3]*z,
        m[4]*x + m[5]*y + m[6]*z,
        m[7]*x + m[8]*y + m[9]*z
end

function instance.position(value, x, y, z)
    local px, py, pz = instance.direction(value, x, y, z)
    local t, s = value.transform.translation, value.transform.scale
    return t[1] + px*s, t[2] + py*s, t[3] + pz*s
end
return instance
