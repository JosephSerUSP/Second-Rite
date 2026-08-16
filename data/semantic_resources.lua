-- Source-side semantic resource provider.
--
-- data.loader owns semantic resources, not their authored physical layout. In
-- the repository/source Project this adapter resolves the author-friendly
-- fragment/index/registry forms. The runtime-data compiler replaces this file
-- in staged players with a tiny monolith-only provider, so source storage
-- vocabulary stops at the compile boundary instead of leaking into the player.
local authored_storage = require("data.authored_storage_resolved")

local resources = {}
local ORDERED_COLLECTIONS = {
    units = true,
    maps = true,
    scenes = true,
}

-- `_test` is a repository/validator-only Flow module. It remains declared in
-- the source storage manifest so the root Second Gate checkout can exercise the
-- deep regression fixture, while sparse/external Projects are not required to
-- author it. Runtime compilation owns the same explicit projection.
local function projectFlowSpec(root)
    local spec = authored_storage.resourceSpec("flows")
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
    if ORDERED_COLLECTIONS[stem] then
        local value = authored_storage.loadOrderedCollection(root, stem)
        return value
    end
    if stem == "flows" then
        local value = authored_storage.loadSemanticConfig(root, stem, projectFlowSpec(root))
        return value
    end
    if stem == "tilesets" then
        local value = authored_storage.loadRegistry(root, stem)
        return value
    end
    error("No source semantic-resource adapter for '" .. tostring(stem) .. "'")
end

return resources
