local json = require("data.json")

local bundle = {}

local KIND = "thestra-static-model-spike"
local VERSION = 0

local function finite(value, label)
    if type(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then
        error((label or "number") .. " must be finite", 0)
    end
    return value
end

function bundle.validate(decoded)
    if type(decoded) ~= "table" then error("static bundle must be an object", 0) end
    if decoded.kind ~= KIND or decoded.version ~= VERSION then
        error("unsupported static bundle contract", 0)
    end
    local model = decoded.model
    if type(model) ~= "table" or type(model.groups) ~= "table" or #model.groups == 0 then
        error("static bundle model requires material groups", 0)
    end

    local count = 0
    for groupIndex, group in ipairs(model.groups) do
        if type(group) ~= "table" or type(group.material) ~= "string"
                or type(group.vertices) ~= "table" then
            error("static bundle group " .. groupIndex .. " is malformed", 0)
        end
        for vertexIndex, vertex in ipairs(group.vertices) do
            if type(vertex) ~= "table" or #vertex ~= 12 then
                error("static bundle group " .. groupIndex .. " vertex " .. vertexIndex
                    .. " must have 12 floats", 0)
            end
            for component = 1, 12 do
                finite(vertex[component], "static bundle vertex component")
            end
            count = count + 1
        end
    end
    if model.vertexCount ~= count then
        error("static bundle vertexCount disagrees with vertex rows", 0)
    end
    if type(model.bounds) ~= "table" then error("static bundle bounds are missing", 0) end
    for _, key in ipairs({ "minX", "minY", "minZ", "maxX", "maxY", "maxZ" }) do
        finite(model.bounds[key], "static bundle bounds." .. key)
    end
    return decoded
end

-- The bundle is already in Thestra's neutral CPU geometry vocabulary. This
-- consumer intentionally does not call love.graphics or presentation.mesh and
-- does not inspect the original glTF/OBJ source. It returns exactly the model
-- shape engine.geometry.model producers already use.
function bundle.modelFromDecoded(decoded)
    bundle.validate(decoded)
    return decoded.model
end

function bundle.modelFromText(text)
    if type(text) ~= "string" then error("static bundle text must be a string", 0) end
    return bundle.modelFromDecoded(json.decode(text))
end

return bundle
