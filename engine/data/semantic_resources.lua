-- Semantic resource provider for direct source development.
--
-- Ordinary source runs resolve author-friendly fragment/index/registry forms.
-- Same-root Test Play / transient preview can point data.loader at a disposable
-- compiled data root containing runtime_data_manifest.json; in that mode this
-- module reads semantic monoliths directly and never loads authored storage.
-- Fully staged/exported players still replace this file with the even smaller
-- compiled-only provider.
local json = require("engine.data.json")

local resources = {}
local ORDERED_COLLECTIONS = {
    units = true,
    maps = true,
    scenes = true,
}
local COMPILED = {
    units = true,
    maps = true,
    flows = true,
    scenes = true,
    tilesets = true,
}
local authored_storage = nil

local function sourceStorage()
    if not authored_storage then
        authored_storage = require("engine.data.authored_storage_resolved")
    end
    return authored_storage
end

local function readJson(path, label)
    local contents = love.filesystem.read(path)
    if not contents then error((label or "semantic resource") .. " is missing: " .. path) end
    local ok, value = pcall(json.decode, contents)
    if not ok then error((label or "semantic resource") .. " is invalid JSON: " .. path .. ": " .. tostring(value)) end
    return value
end

local function compiledRoot(root)
    return love.filesystem.getInfo(root .. "/runtime_data_manifest.json") ~= nil
end

-- `_test` is a repository/validator-only Flow module. It remains declared in
-- the source storage manifest so the root Second Gate checkout can exercise the
-- deep regression fixture, while sparse/external Projects are not required to
-- author it. Runtime compilation owns the same explicit projection.
local function projectFlowSpec(root)
    local storage = sourceStorage()
    local spec = storage.resourceSpec("flows")
    if love.filesystem.getInfo(root .. "/flows/_test.json") then return spec end

    local projectSpec = {}
    for key, value in pairs(spec) do projectSpec[key] = value end
    projectSpec.modules = {}
    for _, module in ipairs(spec.modules or {}) do
        if module ~= "_test" then table.insert(projectSpec.modules, module) end
    end
    return projectSpec
end

function resources.load(root, stem)
    if compiledRoot(root) then
        if not COMPILED[stem] then
            error("No compiled semantic resource adapter for '" .. tostring(stem) .. "'")
        end
        return readJson(root .. "/" .. stem .. ".json",
            "compiled semantic resource '" .. tostring(stem) .. "'")
    end

    local storage = sourceStorage()
    if ORDERED_COLLECTIONS[stem] then
        local value = storage.loadOrderedCollection(root, stem)
        return value
    end
    if stem == "flows" then
        local value = storage.loadSemanticConfig(root, stem, projectFlowSpec(root))
        return value
    end
    if stem == "tilesets" then
        local value = storage.loadRegistry(root, stem)
        return value
    end
    error("No source semantic-resource adapter for '" .. tostring(stem) .. "'")
end

return resources
