-- One acquisition seam for compiled semantic Models and explicitly unmigrated
-- OBJ sources. Registered source paths resolve once to stable Model identity.
local json = require("engine.data.json")
local bundle = require("presentation.model_bundle")
local mesh = require("presentation.mesh")
local resource = {}
local manifest, cache = nil, {}

local function registry()
    if manifest ~= nil then return manifest end
    local text = love.filesystem.read("assets/generated/models/manifest.json")
    manifest = text and json.decode(text) or { version = 1, models = {}, sourcePaths = {} }
    assert(manifest.version == 1 and type(manifest.models) == "table"
        and type(manifest.sourcePaths) == "table", "invalid Model manifest")
    return manifest
end

function resource.modelId(reference)
    if type(reference) ~= "string" then return nil end
    return reference:match("^model:(.+)$") or registry().sourcePaths[reference]
end

function resource.load(reference)
    local id = resource.modelId(reference)
    if not id then return require("presentation.obj_model").load(reference) end
    if cache[id] then return cache[id] end
    local path = registry().models[id]
    assert(path, "unknown compiled Model '" .. id .. "'")
    local model = bundle.load(path)
    assert(model.modelId == id, "Model manifest identity disagrees with bundle")
    local materials = {}
    for _, slot in ipairs(model.materialSlots) do
        assert(slot.appearance, "Model '" .. id .. "' slot '" .. slot.id .. "' has no compiled appearance binding")
        materials[slot.id] = slot.appearance
    end
    mesh.finalize(model, materials, "")
    model.path = path
    cache[id] = model
    return model
end

function resource.clearCache() manifest, cache = nil, {} end
return resource
