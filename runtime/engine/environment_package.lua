-- Runtime reader for a baked spatial package. The package owns spatial facts
-- (geometry, bounds, anchors and optional walk/collision semantics); gameplay
-- meaning and locomotion tuning remain in Project/Event data.
local json = require("engine.data.json")

local environment_package = {}

-- Project asset references share one logical-path resolver. LOVE does not
-- collapse parent segments in either package manifests or OBJ materials.
function environment_package.resolveAssetPath(base, file)
    local joined = (base == "" or file:sub(1, 1) == "/" or file:match("^assets/"))
        and file or (base .. "/" .. file)
    local parts = {}
    for segment in joined:gmatch("[^/]+") do
        if segment == ".." then
            if #parts == 0 then
                error("environment package path escapes the project: " .. joined, 0)
            end
            parts[#parts] = nil
        elseif segment ~= "." then
            parts[#parts + 1] = segment
        end
    end
    return table.concat(parts, "/")
end

local function requiredString(value, label)
    if type(value) ~= "string" or value == "" then
        error("environment package " .. label .. " must be a non-empty string", 0)
    end
    return value
end

local function finiteNumber(value, label)
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then
        error("environment package " .. label .. " must be finite", 0)
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

-- A walk surface is deliberately a package spatial fact, not a traversal
-- provider. Blender/source tooling may compile the same room for different
-- games, while each Project remains free to choose speed, input and interaction
-- policy. V1 is intentionally planar: ordered XY polygon loops plus one ground Z.
local function normalizeWalkSurface(raw)
    if raw == nil or raw == json.null then return nil end
    if type(raw) ~= "table" then
        error("environment package walkSurface must be an object", 0)
    end
    if type(raw.regions) ~= "table" or #raw.regions == 0 then
        error("environment package walkSurface.regions must be a non-empty array", 0)
    end

    local function polygon(value, label)
        if type(value) ~= "table" then
            error("environment package " .. label .. " must be an object", 0)
        end
        local points = value.points or value
        if type(points) ~= "table" or #points < 3 then
            error("environment package " .. label .. " must contain at least 3 points", 0)
        end
        local normalized = { points = {} }
        for index, point in ipairs(points) do
            if type(point) ~= "table" then
                error("environment package " .. label .. ".points[" .. index .. "] must be a point", 0)
            end
            normalized.points[index] = {
                finiteNumber(point.x ~= nil and point.x or point[1],
                    label .. ".points[" .. index .. "].x"),
                finiteNumber(point.y ~= nil and point.y or point[2],
                    label .. ".points[" .. index .. "].y"),
            }
        end
        return normalized
    end

    if raw.obstacles ~= nil and raw.obstacles ~= json.null and type(raw.obstacles) ~= "table" then
        error("environment package walkSurface.obstacles must be an array", 0)
    end
    local result = {
        groundZ = finiteNumber(raw.groundZ or 0, "walkSurface.groundZ"),
        regions = {},
        obstacles = {},
    }
    for index, region in ipairs(raw.regions) do
        result.regions[index] = polygon(region, "walkSurface.regions[" .. index .. "]")
    end
    for index, obstacle in ipairs(raw.obstacles or {}) do
        result.obstacles[index] = polygon(obstacle, "walkSurface.obstacles[" .. index .. "]")
    end
    return result
end

function environment_package.load(path)
    path = requiredString(path, "path")
    local manifest = readJson(path)
    if manifest.contractVersion ~= 1 then
        error("unsupported environment package contract: " .. tostring(manifest.contractVersion), 0)
    end
    if manifest.provenance ~= nil then
        if type(manifest.provenance) ~= "table" then
            error("environment package provenance must be an object", 0)
        end
        local transform = manifest.provenance.plateSourceViewTransform
        if transform ~= nil and transform ~= "AgX" and transform ~= "Standard"
                and transform ~= "NotRecorded" then
            error("environment package provenance plateSourceViewTransform "
                .. "must be AgX, Standard, or NotRecorded", 0)
        end
    end
    local base = path:match("^(.*)/[^/]+$") or ""
    -- LOVE's filesystem does not collapse "..", so a manifest that points at a
    -- sibling directory resolves to a path that does not exist. Normalise here
    -- rather than forbidding relative references in authored packages.
    local function resolve(file)
        return environment_package.resolveAssetPath(base, file)
    end
    local function asset(name, label)
        return resolve(requiredString(manifest[name], label))
    end
    local preRendered = nil
    if manifest.preRendered ~= nil then
        local spec = manifest.preRendered
        if type(spec) ~= "table" or spec.mode ~= "layered_2d" then
            error("environment package preRendered mode must be layered_2d", 0)
        end
        local function assetList(value, label)
            if type(value) ~= "table" or #value == 0 then
                error("environment package preRendered " .. label .. " must be a non-empty array", 0)
            end
            local result = {}
            for index, file in ipairs(value) do
                file = requiredString(file, label .. "[" .. index .. "]")
                result[index] = resolve(file)
            end
            return result
        end
        if type(spec.slicePositions) ~= "table"
                or #spec.slicePositions < 1
                or #spec.slicePositions ~= #(spec.backgrounds or {})
                or #spec.slicePositions ~= #(spec.foregrounds or {})
                or #spec.slicePositions ~= #(spec.scenes or {}) then
            error("environment package preRendered slice arrays must have equal non-zero length", 0)
        end
        if type(spec.imageSize) ~= "table" or #spec.imageSize ~= 2
                or tonumber(spec.imageSize[1]) <= 0 or tonumber(spec.imageSize[2]) <= 0 then
            error("environment package preRendered imageSize must be positive [width,height]", 0)
        end
        if type(spec.playerProjection) ~= "table" then
            error("environment package preRendered playerProjection is required", 0)
        end
        local projection = spec.playerProjection
        for _, field in ipairs({ "width", "height", "pixelsPerRuntimeY" }) do
            if type(projection[field]) ~= "number" or projection[field] <= 0 then
                error("environment package preRendered playerProjection." .. field
                    .. " must be positive", 0)
            end
        end
        if type(projection.screenY) ~= "number" then
            error("environment package preRendered playerProjection.screenY must be numeric", 0)
        end
        if spec.cameraMode ~= nil and spec.cameraMode ~= "static" and spec.cameraMode ~= "panning" then
            error("environment package preRendered cameraMode must be static or panning", 0)
        end
        preRendered = {
            mode = spec.mode,
            cameraMode = spec.cameraMode or "panning",
            backgrounds = assetList(spec.backgrounds, "backgrounds"),
            foregrounds = assetList(spec.foregrounds, "foregrounds"),
            scenes = assetList(spec.scenes, "scenes"),
            slicePositions = spec.slicePositions,
            imageSize = { tonumber(spec.imageSize[1]), tonumber(spec.imageSize[2]) },
            lane = spec.lane,
            playerProjection = spec.playerProjection,
        }
    end
    if type(manifest.bounds) ~= "table" or #manifest.bounds ~= 6 then
        error("environment package bounds must be [minX,minY,minZ,maxX,maxY,maxZ]", 0)
    end
    if type(manifest.anchors) ~= "table" then
        error("environment package anchors must be an object", 0)
    end
    local collisionMesh = nil
    if manifest.collisionMesh ~= nil and manifest.collisionMesh ~= json.null then
        collisionMesh = asset("collisionMesh", "collisionMesh")
    end
    local walkSurface = normalizeWalkSurface(manifest.walkSurface)
    local bakedLighting = manifest.bakedLighting
    if bakedLighting == nil then
        bakedLighting = (preRendered == nil)
    else
        bakedLighting = (bakedLighting == true)
    end
    return {
        manifestPath = path,
        manifest = manifest,
        renderMesh = asset("renderMesh", "renderMesh"),
        materialLibrary = asset("materialLibrary", "materialLibrary"),
        textureAtlas = asset("textureAtlas", "textureAtlas"),
        collisionMesh = collisionMesh,
        walkSurface = walkSurface,
        bounds = manifest.bounds,
        anchors = manifest.anchors,
        preRendered = preRendered,
        bakedLighting = bakedLighting,
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
