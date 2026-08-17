local json = require("engine.data.json")

local bundle = {}

local KIND = "thestra-model-bundle"
local VERSION = 1

local function finite(value, label)
    if type(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then
        error((label or "number") .. " must be finite", 0)
    end
    return value
end

function bundle.validate(decoded)
    if type(decoded) ~= "table" then error("Model Bundle must be an object", 0) end
    if decoded.kind ~= KIND or decoded.version ~= VERSION then
        error("unsupported Model Bundle contract", 0)
    end
    if type(decoded.modelId) ~= "string" or decoded.modelId == "" then
        error("Model Bundle requires modelId", 0)
    end
    local geometry = decoded.geometry
    if type(geometry) ~= "table" or type(geometry.groups) ~= "table" or #geometry.groups == 0 then
        error("Model Bundle geometry requires groups", 0)
    end
    local declaredSlots = {}
    for _, slot in ipairs(decoded.materialSlots or {}) do
        if type(slot) ~= "table" or type(slot.id) ~= "string" or slot.id == "" then
            error("Model Bundle materialSlots require ids", 0)
        end
        declaredSlots[slot.id] = true
    end

    local count = 0
    for groupIndex, group in ipairs(geometry.groups) do
        if type(group) ~= "table" or type(group.materialSlot) ~= "string"
                or not declaredSlots[group.materialSlot] or type(group.vertices) ~= "table" then
            error("Model Bundle group " .. groupIndex .. " is malformed", 0)
        end
        for vertexIndex, vertex in ipairs(group.vertices) do
            if type(vertex) ~= "table" or #vertex ~= 12 then
                error("Model Bundle group " .. groupIndex .. " vertex " .. vertexIndex
                    .. " must have 12 floats", 0)
            end
            for component = 1, 12 do
                finite(vertex[component], "Model Bundle vertex component")
            end
            count = count + 1
        end
    end
    if geometry.vertexCount ~= count then error("Model Bundle vertexCount disagrees with vertex rows", 0) end
    if type(geometry.bounds) ~= "table" then error("Model Bundle bounds are missing", 0) end
    for _, key in ipairs({ "minX", "minY", "minZ", "maxX", "maxY", "maxZ" }) do
        finite(geometry.bounds[key], "Model Bundle bounds." .. key)
    end
    return decoded
end

-- Convert the compiled bundle into the exact renderer-neutral CPU shape already
-- consumed by engine.geometry.model / presentation.mesh. Material slots retain
-- semantic identity; Surface/material realization belongs downstream.
function bundle.modelFromDecoded(decoded)
    bundle.validate(decoded)
    local groups = {}
    for index, source in ipairs(decoded.geometry.groups) do
        groups[index] = {
            material = source.materialSlot,
            vertices = source.vertices,
        }
    end
    return {
        groups = groups,
        vertexCount = decoded.geometry.vertexCount,
        bounds = decoded.geometry.bounds,
        modelId = decoded.modelId,
        materialSlots = decoded.materialSlots,
    }
end

function bundle.modelFromText(text)
    if type(text) ~= "string" then error("Model Bundle text must be a string", 0) end
    return bundle.modelFromDecoded(json.decode(text))
end

function bundle.load(path)
    local text = love.filesystem.read(path)
    if not text then error("Could not read Model Bundle: " .. tostring(path), 0) end
    return bundle.modelFromText(text)
end

return bundle
