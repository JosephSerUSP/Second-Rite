local json = require("data.json")

-- #392: resolved authored-storage semantics for Project loading. In ordinary
-- source development this wraps the physical fragment/monolith implementation
-- and adds the explicit-empty catalog representation.
--
-- EXPERIMENT #632 adds one second *resolved* input shape for staged/exported
-- games: tools/export may emit authored_runtime_snapshot.json plus plain
-- <stem>.json monoliths after all Project/RTP authoring resolution has happened.
-- When that marker exists this module never requires data.authored_storage at
-- all, proving that source storage representation can stop at the stage
-- boundary while loader.lua keeps its existing API.

local RUNTIME_MARKER_PATH = "data/authored_runtime_snapshot.json"

local function readJson(path, label, optional)
    local contents = love.filesystem.read(path)
    if not contents then
        if optional then return nil end
        error((label or "authored resource") .. " is missing: " .. path)
    end
    local ok, value = pcall(json.decode, contents)
    if not ok then
        error((label or "authored resource") .. " is invalid JSON: " .. path .. ": " .. tostring(value))
    end
    return value
end

local runtimeMarker = nil
if love.filesystem.getInfo(RUNTIME_MARKER_PATH) then
    runtimeMarker = readJson(RUNTIME_MARKER_PATH, "authored runtime snapshot marker")
    if type(runtimeMarker) ~= "table" or runtimeMarker.version ~= 1
            or runtimeMarker.materialized ~= true or type(runtimeMarker.resources) ~= "table" then
        error("authored_runtime_snapshot.json must declare version 1, materialized=true, and resources")
    end
end

if runtimeMarker then
    local runtime = {}

    local function entry(stem)
        local value = runtimeMarker.resources[stem]
        if type(value) ~= "table" or value.runtimePath ~= "data/" .. stem .. ".json" then
            error("authored runtime snapshot does not declare resource '" .. tostring(stem) .. "'")
        end
        return value
    end

    local function load(root, stem)
        entry(stem)
        return readJson(root .. "/" .. stem .. ".json",
            "materialized authored resource '" .. tostring(stem) .. "'")
    end

    function runtime.resourceSpec(stem)
        local value = entry(stem)
        return {
            kind = "runtime_snapshot",
            representation = "monolith",
            sourceRepresentation = value.sourceRepresentation,
        }
    end

    function runtime.loadResource(root, stem)
        return load(root, stem), "runtime_snapshot"
    end

    function runtime.loadOrderedCollection(root, stem)
        return load(root, stem), "runtime_snapshot"
    end

    function runtime.loadRegistry(root, stem)
        return load(root, stem), "runtime_snapshot"
    end

    function runtime.loadSemanticConfig(root, stem)
        return load(root, stem), "runtime_snapshot"
    end

    function runtime.explicitEmptyIndex()
        return false
    end

    return runtime
end

local physical = require("data.authored_storage")
local resolved = setmetatable({}, { __index = physical })

local function explicitEmptyIndex(root, stem)
    local path = root .. "/" .. stem .. "/index.json"
    if not love.filesystem.getInfo(path) then return false end
    local manifest = readJson(path, "authored empty-catalog marker")
    local files = manifest
    if type(manifest) == "table" and type(manifest.files) == "table" then files = manifest.files end
    if type(files) ~= "table" then return false end
    return next(files) == nil
end

function resolved.loadOrderedCollection(root, stem)
    if explicitEmptyIndex(root, stem) then return {}, "fragments" end
    return physical.loadOrderedCollection(root, stem)
end

function resolved.loadRegistry(root, stem)
    if explicitEmptyIndex(root, stem) then return {}, "fragments" end
    return physical.loadRegistry(root, stem)
end

resolved.explicitEmptyIndex = explicitEmptyIndex

return resolved
