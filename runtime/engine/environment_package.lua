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

local function requiredSha256(value, label)
    if type(value) ~= "string" or #value ~= 64 or not value:match("^[%x]+$") then
        error("environment package " .. label .. " must be a 64-character SHA-256 hex string", 0)
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
        local joined = (base == "" or file:sub(1, 1) == "/") and file or (base .. "/" .. file)
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
    local floorMesh = nil
    if manifest.floorMesh ~= nil and manifest.floorMesh ~= json.null then
        floorMesh = asset("floorMesh", "floorMesh")
        local provenance = manifest.provenance
        local floor = provenance and provenance.floor
        if type(floor) ~= "table" then
            error("environment package provenance.floor is required when floorMesh is present", 0)
        end
        requiredString(floor.sourceObject, "provenance.floor.sourceObject")
        if type(floor.gridSpacingWorld) ~= "number" or floor.gridSpacingWorld <= 0 then
            error("environment package provenance.floor.gridSpacingWorld must be positive", 0)
        end
        if type(floor.texturePeriodWorld) ~= "number" or floor.texturePeriodWorld <= 0 then
            error("environment package provenance.floor.texturePeriodWorld must be positive", 0)
        end
        if type(floor.vertexCount) ~= "number" or floor.vertexCount < 4
                or floor.vertexCount ~= math.floor(floor.vertexCount) then
            error("environment package provenance.floor.vertexCount must be an integer >= 4", 0)
        end
        if type(floor.faceCount) ~= "number" or floor.faceCount < 1
                or floor.faceCount ~= math.floor(floor.faceCount) then
            error("environment package provenance.floor.faceCount must be a positive integer", 0)
        end
        requiredString(floor.textureSource, "provenance.floor.textureSource")
        if type(floor.sha256) ~= "table" then
            error("environment package provenance.floor.sha256 must be an object", 0)
        end
        for _, file in ipairs({ "floor.obj", "floor.mtl", "floor.png" }) do
            requiredSha256(floor.sha256[file], "provenance.floor.sha256." .. file)
        end
    end
    local backgroundLayers = {}
    if manifest.backgroundLayers ~= nil then
        if type(manifest.backgroundLayers) ~= "table" then
            error("environment package backgroundLayers must be an array", 0)
        end
        local seen = {}
        for index, layer in ipairs(manifest.backgroundLayers) do
            if type(layer) ~= "table" then
                error("environment package backgroundLayers[" .. index .. "] must be an object", 0)
            end
            local id = requiredString(layer.id, "backgroundLayers[" .. index .. "].id")
            if seen[id] then
                error("environment package background layer id is duplicated: " .. id, 0)
            end
            seen[id] = true
            local renderMesh = requiredString(layer.renderMesh,
                "backgroundLayers[" .. index .. "].renderMesh")
            local materialLibrary = requiredString(layer.materialLibrary,
                "backgroundLayers[" .. index .. "].materialLibrary")
            local provenance = layer.provenance
            if type(provenance) ~= "table" then
                error("environment package backgroundLayers[" .. index .. "].provenance is required", 0)
            end
            requiredString(provenance.sourceBlend,
                "backgroundLayers[" .. index .. "].provenance.sourceBlend")
            requiredString(provenance.sourceRepresentation,
                "backgroundLayers[" .. index .. "].provenance.sourceRepresentation")
            if provenance.cameraSpace ~= false then
                error("environment package backgroundLayers[" .. index
                    .. "].provenance.cameraSpace must be false", 0)
            end
            if provenance.reactsToPitch ~= true then
                error("environment package backgroundLayers[" .. index
                    .. "].provenance.reactsToPitch must be true", 0)
            end
            if type(provenance.sha256) ~= "table" then
                error("environment package backgroundLayers[" .. index
                    .. "].provenance.sha256 must be an object", 0)
            end
            requiredSha256(provenance.sha256["renderMesh"],
                "backgroundLayers[" .. index .. "].provenance.sha256.renderMesh")
            requiredSha256(provenance.sha256["materialLibrary"],
                "backgroundLayers[" .. index .. "].provenance.sha256.materialLibrary")
            requiredSha256(provenance.sha256["texture"],
                "backgroundLayers[" .. index .. "].provenance.sha256.texture")
            backgroundLayers[#backgroundLayers + 1] = {
                id = id,
                renderMesh = resolve(renderMesh),
                materialLibrary = resolve(materialLibrary),
                provenance = provenance,
            }
        end
    end
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
        floorMesh = floorMesh,
        backgroundLayers = backgroundLayers,
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
