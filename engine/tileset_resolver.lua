-- Immutable sparse tileset deltas for per-map/per-floor presentation.
-- Pool arrays merge by id; ordinary arrays (atlas coordinates, colors) replace.
local resolver = {}

local cache = setmetatable({}, { __mode = "k" })
local POOLS = { "features", "doors", "fixturePrefabs" }
local BASE_POOLS = { "walls", "floors", "ceilings", "wallTops", "skies" }

local function isArray(value)
    return type(value) == "table" and #value > 0
end

local function copy(value)
    if type(value) ~= "table" then return value end
    local out = {}
    for k, v in pairs(value) do out[k] = copy(v) end
    return out
end

local function mergeObject(base, delta)
    if type(delta) ~= "table" then return delta end
    if isArray(delta) then return copy(delta) end
    local out = type(base) == "table" and copy(base) or {}
    for key, value in pairs(delta) do
        if key ~= "remove" then
            if type(value) == "table" and not isArray(value) then
                out[key] = mergeObject(out[key], value)
            else
                out[key] = copy(value)
            end
        end
    end
    return out
end

local function mergePool(base, delta)
    local out, index = copy(base or {}), {}
    for i, entry in ipairs(out) do index[entry.id] = i end
    for _, patch in ipairs(delta or {}) do
        local at = index[patch.id]
        if patch.remove == true then
            if at then
                table.remove(out, at)
                index = {}
                for i, entry in ipairs(out) do index[entry.id] = i end
            end
        elseif at then
            out[at] = mergeObject(out[at], patch)
        else
            out[#out + 1] = mergeObject(nil, patch)
            index[patch.id] = #out
        end
    end
    return out
end

function resolver.resolveSurface(loader, surfaceRef, tilesetDef)
    if not surfaceRef then return nil end
    if type(surfaceRef) == "table" then return copy(surfaceRef) end
    if type(surfaceRef) ~= "string" then return nil end

    if tilesetDef and type(tilesetDef.surfaces) == "table" and tilesetDef.surfaces[surfaceRef] then
        local found = copy(tilesetDef.surfaces[surfaceRef])
        if type(found) == "table" and not found.id then found.id = surfaceRef end
        return found
    end

    if loader and type(loader.getSurface) == "function" then
        local found = loader.getSurface(surfaceRef)
        if found then return copy(found) end
    end

    return { id = surfaceRef }
end

function resolver.resolveVariantSurface(variant, tilesetDef, loader)
    if type(variant) ~= "table" then return nil end
    if variant.surface then
        return resolver.resolveSurface(loader, variant.surface, tilesetDef)
    end
    return nil
end

local function getZoneAt(mapData, x, y)
    if not mapData or x == nil or y == nil then return nil end
    if mapData.zoneGrid and type(mapData.zoneGrid) == "table" then
        local row = nil
        if mapData.zoneGrid[0] ~= nil then
            row = mapData.zoneGrid[y]
        else
            row = mapData.zoneGrid[y + 1] or mapData.zoneGrid[y]
        end
        if type(row) == "table" then
            local z = nil
            if row[0] ~= nil then
                z = row[x]
            else
                z = row[x + 1] or row[x]
            end
            if z and z ~= "" then return z end
        end
    end
    if mapData.zones and type(mapData.zones) == "table" then
        if #mapData.zones > 0 then
            for _, zone in ipairs(mapData.zones) do
                if zone.cells then
                    for _, cell in ipairs(zone.cells) do
                        if cell.x == x and cell.y == y then
                            return zone.id or zone.name
                        end
                    end
                end
            end
        end
    end
    return nil
end

local function getZoneDef(mapData, zoneId)
    if not mapData or not mapData.zones or not zoneId then return nil end
    if type(mapData.zones) == "table" then
        if mapData.zones[zoneId] then return mapData.zones[zoneId] end
        for _, zone in ipairs(mapData.zones) do
            if zone.id == zoneId or zone.name == zoneId then
                return zone
            end
        end
    end
    return nil
end

function resolver.resolveWallFacePalette(mapData, wallX, wallY, facingX, facingY, loader)
    if not mapData then return nil end
    local zoneId = getZoneAt(mapData, facingX, facingY)
    local zoneDef = getZoneDef(mapData, zoneId)

    if zoneDef then
        local paletteId = zoneDef.palette or zoneDef.tileset
        if paletteId and loader and loader.getTileset then
            local palette = loader.getTileset(paletteId)
            if palette then
                return {
                    zone = zoneId,
                    paletteId = paletteId,
                    palette = palette,
                    wallCell = { wallX, wallY },
                    facingCell = { facingX, facingY },
                }
            end
        end
    end

    local defaultPalette, defaultId = resolver.resolve(loader, mapData)
    return {
        zone = zoneId,
        paletteId = defaultId,
        palette = defaultPalette,
        wallCell = { wallX, wallY },
        facingCell = { facingX, facingY },
    }
end

function resolver.resolve(loader, mapData)
    local id = (mapData and mapData.tileset) or "dungeon_default"
    local base = loader and loader.getTileset and loader.getTileset(id)
    if not base then return nil, id end
    local delta = mapData and mapData.tilesetOverride
    if type(delta) ~= "table" or next(delta) == nil then return base, id end

    local cached = cache[mapData]
    if cached and cached.base == base and cached.delta == delta then
        return cached.value, cached.key
    end

    local value = mergeObject(base, delta)
    for _, pool in ipairs(POOLS) do
        if delta[pool] ~= nil then value[pool] = mergePool(base[pool], delta[pool]) end
    end
    if delta.surfaces ~= nil then
        value.surfaces = mergeObject(base.surfaces or {}, delta.surfaces)
    end
    if delta.base ~= nil then
        value.base = mergeObject(base.base or {}, delta.base)
        for _, pool in ipairs(BASE_POOLS) do
            if delta.base[pool] ~= nil then
                value.base[pool] = mergePool(base.base and base.base[pool], delta.base[pool])
            end
        end
    end
    value.id = base.id or id
    local key = id .. "@map:" .. tostring(mapData)
    cache[mapData] = { base = base, delta = delta, value = value, key = key }
    return value, key
end

function resolver.invalidate(mapData)
    if mapData then cache[mapData] = nil end
end

return resolver
