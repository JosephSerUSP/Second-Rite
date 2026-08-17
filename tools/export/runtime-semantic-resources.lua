-- Candidate A+ runtime provider.
--
-- This file is copied over engine/data/semantic_resources.lua only after Project/RTP
-- resolution and source->runtime compilation. It deliberately knows nothing
-- about authored fragments, registries, semantic-config modules, explicit-empty
-- markers, or the authored storage manifest: a staged player consumes ordinary
-- semantic JSON resources.
local json = require("engine.data.json")

local resources = {}
local COMPILED = {
    units = true,
    maps = true,
    flows = true,
    scenes = true,
    tilesets = true,
}

local function readJson(path, label)
    local contents = love.filesystem.read(path)
    if not contents then error((label or "compiled semantic resource") .. " is missing: " .. path) end
    local ok, value = pcall(json.decode, contents)
    if not ok then
        error((label or "compiled semantic resource") .. " is invalid JSON: " .. path .. ": " .. tostring(value))
    end
    return value
end

function resources.load(root, stem)
    if not COMPILED[stem] then
        error("Unknown compiled semantic resource '" .. tostring(stem) .. "'")
    end
    return readJson(root .. "/" .. stem .. ".json",
        "compiled semantic resource '" .. tostring(stem) .. "'")
end

return resources
