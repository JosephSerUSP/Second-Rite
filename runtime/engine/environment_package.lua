-- Runtime reader for a baked spatial package.  The package owns geometry,
-- bounds and anchors; gameplay meaning remains in Project/Event data.
local json = require("engine.data.json")

local environment_package = {}

local function requiredString(value, label)
    if type(value) ~= "string" or value == "" then
        error("environment package " .. label .. " must be a non-empty string", 0)
    end
    return value
end

local function readJson(path)
    local text = love.filesystem.read(path)
    if not text then error("environment package missing: " .. path, 0) end
    local ok, value = pcall(json.decode, text)
    if not ok or type(value) ~= "table" then
        error("environment package is not valid JSON: " .. path, 0)
    end
    return value
end

function environment_package.load(path)
    path = requiredString(path, "path")
    local manifest = readJson(path)
    if manifest.contractVersion ~= 1 then
        error("unsupported environment package contract: " .. tostring(manifest.contractVersion), 0)
    end
    local base = path:match("^(.*)/[^/]+$") or ""
    local function asset(name, label)
        local file = requiredString(manifest[name], label)
        return base == "" and file or (base .. "/" .. file)
    end
    if type(manifest.bounds) ~= "table" or #manifest.bounds ~= 6 then
        error("environment package bounds must be [minX,minY,minZ,maxX,maxY,maxZ]", 0)
    end
    if type(manifest.anchors) ~= "table" then
        error("environment package anchors must be an object", 0)
    end
    return {
        manifestPath = path,
        manifest = manifest,
        renderMesh = asset("renderMesh", "renderMesh"),
        materialLibrary = asset("materialLibrary", "materialLibrary"),
        textureAtlas = asset("textureAtlas", "textureAtlas"),
        collisionMesh = asset("collisionMesh", "collisionMesh"),
        bounds = manifest.bounds,
        anchors = manifest.anchors,
    }
end

function environment_package.anchor(package, id)
    local anchor = package and package.anchors and package.anchors[id]
    if type(anchor) ~= "table" or type(anchor.position) ~= "table" then
        error("environment package has no anchor '" .. tostring(id) .. "'", 0)
    end
    return anchor
end

return environment_package
