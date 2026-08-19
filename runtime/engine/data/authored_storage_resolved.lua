local json = require("engine.data.json")
local physical = require("engine.data.authored_storage")

-- #392: resolved authored-storage semantics for Project loading. The physical
-- storage module intentionally keeps its historical strictness; this wrapper
-- adds one explicit representation needed by genuinely blank Projects:
--
--     <stem>/index.json = { "files": [] }
--
-- means the fragmented collection/registry is deliberately empty. Missing
-- storage is still an error, and every non-empty catalog delegates byte-for-
-- byte to the existing physical implementation.
local resolved = setmetatable({}, { __index = physical })

local function readJson(path)
    local contents = love.filesystem.read(path)
    if not contents then return nil end
    local ok, value = pcall(json.decode, contents)
    if not ok then
        error("Could not decode authored empty-catalog marker '" .. path .. "': " .. tostring(value))
    end
    return value
end

local function explicitEmptyIndex(root, stem)
    local path = root .. "/" .. stem .. "/index.json"
    if not love.filesystem.getInfo(path) then return false end
    local manifest = readJson(path)
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
