local json = require("data.json")

-- EXPERIMENT for #632: one loader-facing membrane that uses normal authored
-- source storage in direct development, but becomes a trivial monolith reader
-- inside a resolved runtime stage. The materialized player therefore does not
-- need the fragment/index/RTP authoring-storage implementation at all.

local MARKER_PATH = "data/authored_runtime_snapshot.json"

local function readJson(path, label)
    local contents = love.filesystem.read(path)
    if not contents then error((label or "runtime authored resource") .. " is missing: " .. path) end
    local ok, value = pcall(json.decode, contents)
    if not ok then error((label or "runtime authored resource") .. " is invalid JSON: " .. path .. ": " .. tostring(value)) end
    return value
end

local marker = nil
if love.filesystem.getInfo(MARKER_PATH) then
    marker = readJson(MARKER_PATH, "authored runtime snapshot marker")
    if type(marker) ~= "table" or marker.version ~= 1 or marker.materialized ~= true
            or type(marker.resources) ~= "table" then
        error("authored_runtime_snapshot.json must declare version 1, materialized=true, and resources")
    end
end

if not marker then
    return require("data.authored_storage_resolved")
end

local runtime = {}

local function entry(stem)
    local value = marker.resources[stem]
    if type(value) ~= "table" or value.runtimePath ~= "data/" .. stem .. ".json" then
        error("authored runtime snapshot does not declare resource '" .. tostring(stem) .. "'")
    end
    return value
end

local function load(root, stem)
    entry(stem)
    return readJson(root .. "/" .. stem .. ".json", "materialized authored resource '" .. stem .. "'")
end

function runtime.resourceSpec(stem)
    local value = entry(stem)
    return {
        kind = "runtime_snapshot",
        representation = "monolith",
        sourceRepresentation = value.sourceRepresentation,
    }
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
