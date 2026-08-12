-- Typed resolution and validation for authored runtime resource references (#353).
--
-- This module deliberately does NOT walk arbitrary strings looking for path-like
-- values. A caller has to name the resource contract it is validating. That
-- distinction keeps semantic/non-filesystem authoring forms (geometry source
-- ids, generated runtime surfaces, formula strings, etc.) out of filesystem
-- validation while giving G1 one authority for the filesystem forms that
-- several authored categories share.
--
-- Sprite resolution delegates to presentation.small_battlers.resolveFile: that
-- function is already the runtime authority for sprite keys, case variants and
-- [key=value] filename tokens, so validation must not reproduce that lookup.
local small_battlers = require("presentation.small_battlers")

local resource_reference = {}

-- Stable sentinel used by callers/tests that need to distinguish an embedded
-- source from a filesystem path. Runtime tilesets accept textureImage in place
-- of texture; that is not a dangling file reference and must remain legal.
resource_reference.EMBEDDED = { kind = "embedded" }

local function nonEmptyString(value)
    return type(value) == "string" and value ~= ""
end

local function directFile(path)
    if not nonEmptyString(path) then return nil end
    return love.filesystem.getInfo(path) and path or nil
end

local function panoramaPath(value)
    if not nonEmptyString(value) then return nil end
    local clean = tostring(value):gsub("^assets/panorama/", ""):gsub("%.png$", "")
    if clean == "" then return nil end
    return "assets/panorama/" .. clean .. ".png"
end

resource_reference.panoramaPath = panoramaPath

local function imageId(value, context)
    if not nonEmptyString(value) then return nil end
    local directory = context and context.directory
    if not nonEmptyString(directory) then
        error("image_id resource references require context.directory", 0)
    end
    local slug = value:gsub("[^%w]+", "_"):gsub("^_+", ""):gsub("_+$", "")
    local candidates = {
        directory .. "/" .. value .. ".png",
        directory .. "/" .. slug .. ".png",
        directory .. "/" .. value:lower() .. ".png",
        directory .. "/" .. value:sub(1, 1):upper() .. value:sub(2):lower() .. ".png",
    }
    for _, path in ipairs(candidates) do
        if love.filesystem.getInfo(path) then return path end
    end
    return nil
end

local RESOLVERS = {
    -- Direct authored paths: models, image pictures, backdrops, height/glow
    -- maps, Effekseer effects, and similar resources whose runtime loader uses
    -- the authored path verbatim.
    file = function(value)
        return directFile(value)
    end,

    -- Event/small-battler sprites support logical keys as well as direct paths.
    sprite = function(value)
        if not nonEmptyString(value) then return nil end
        local direct = directFile(value)
        if direct then return direct end
        local resolved = small_battlers.resolveFile(value)
        return resolved and resolved.path or nil
    end,

    -- Fog/sky panoramas use the viewport's authored shorthand: either
    -- `fog_001`, `fog_001.png`, or `assets/panorama/fog_001.png` names the same
    -- filesystem resource.
    panorama = function(value)
        local path = panoramaPath(value)
        return path and directFile(path) or nil
    end,

    -- ENTER_LOCATION stores a filename relative to assets/locationArt while
    -- SHOW_IMAGE_PICTURE/backdrops store full paths and therefore use `file`.
    location_art = function(value)
        if not nonEmptyString(value) then return nil end
        return directFile("assets/locationArt/" .. value)
    end,

    -- Actor portrait/big-battler ids use a directory plus the existing filename
    -- convention. The validator supplies the directory; the id itself is not a
    -- path and must not be validated as one.
    image_id = imageId,

    -- A tileset texture can be a filesystem image OR an already-created image
    -- object. The latter is a legitimate embedded/generated form used by the
    -- renderer and is intentionally not subjected to getInfo().
    tileset_texture = function(_, context)
        local definition = context and context.definition or nil
        local id = context and context.id or nil
        if type(definition) ~= "table" then
            error("tileset_texture resource references require context.definition", 0)
        end
        if definition.textureImage ~= nil then
            return resource_reference.EMBEDDED
        end
        local path = definition.texture
            or (id ~= nil and ("assets/tilesets/" .. tostring(id) .. ".png") or nil)
        return directFile(path)
    end,
}

function resource_reference.resolve(kind, value, context)
    local resolver = RESOLVERS[kind]
    if not resolver then
        error("unknown resource reference kind '" .. tostring(kind) .. "'", 0)
    end
    return resolver(value, context)
end

function resource_reference.required(kind, value, context)
    local resolved = resource_reference.resolve(kind, value, context)
    return resolved ~= nil, resolved
end

-- Optional authoring means omission (or explicit false for presentation
-- suppression) is legal. An authored empty string is NOT omission: callers may
-- layer their own shape error on top, and resolution correctly returns false.
function resource_reference.optional(kind, value, context)
    if value == nil or value == false then return true, nil end
    local resolved = resource_reference.resolve(kind, value, context)
    return resolved ~= nil, resolved
end

-- Map events, event pages and common events share one presentation vocabulary:
-- model and sprite may be omitted, or explicitly suppressed with false. Their
-- filesystem semantics must therefore be identical no matter which owner the
-- renderer inherited the field from.
function resource_reference.validatePresentation(pres, ownerDesc, report)
    if pres.model ~= nil and pres.model ~= false then
        report(type(pres.model) == "string" and pres.model ~= "",
            ownerDesc .. ".model must be a non-empty string or false")
        if type(pres.model) == "string" and pres.model ~= "" then
            report(pres.model:sub(-4) == ".obj",
                ownerDesc .. ".model '" .. pres.model .. "' must be a .obj file")
            report(resource_reference.required("file", pres.model),
                ownerDesc .. ".model is missing (" .. pres.model .. ")")
        end
    end

    if pres.sprite ~= nil and pres.sprite ~= false then
        report(type(pres.sprite) == "string" and pres.sprite ~= "",
            ownerDesc .. ".sprite must be a non-empty string/key or false")
        if type(pres.sprite) == "string" and pres.sprite ~= "" then
            report(resource_reference.required("sprite", pres.sprite),
                ownerDesc .. ".sprite resolves to no asset ('" .. pres.sprite .. "')")
        end
    end
end

local function validateFogPanoramas(fog, ownerDesc, report)
    if type(fog) ~= "table" or type(fog.panorama) ~= "table" then return end
    for i, layer in ipairs(fog.panorama) do
        local desc = ownerDesc .. ".panorama[" .. i .. "]"
        if type(layer) == "table" and nonEmptyString(layer.image) then
            report(resource_reference.required("panorama", layer.image),
                desc .. ".image resolves to no panorama asset ('" .. layer.image .. "')")
        end
    end
end

-- Commands are walked by opcode, never by path-looking strings. These are the
-- two command forms whose runtime loaders have a direct filesystem contract.
-- Nested command collections are generic authored blocks, so recurse through
-- tables but only interpret a value as an asset after its command id says so.
local function validateCommandResources(node, ownerDesc, report, seen)
    if type(node) ~= "table" then return end
    seen = seen or {}
    if seen[node] then return end
    seen[node] = true

    if node.cmd == "ENTER_LOCATION" and node.image ~= nil then
        report(resource_reference.required("location_art", node.image),
            ownerDesc .. " ENTER_LOCATION references missing location art '"
                .. tostring(node.image) .. "'")
    elseif node.cmd == "SHOW_IMAGE_PICTURE" and node.path ~= nil then
        report(resource_reference.required("file", node.path),
            ownerDesc .. " SHOW_IMAGE_PICTURE references missing image '"
                .. tostring(node.path) .. "'")
    end

    for _, value in pairs(node) do
        if type(value) == "table" then
            validateCommandResources(value, ownerDesc, report, seen)
        end
    end
end

-- Resource-reference phase of canonical G1. Shape/schema validation remains in
-- validator_rules; this pass owns only typed filesystem resolution and delegates
-- each nontrivial lookup to the same resolver the runtime uses. It deliberately
-- does not inspect geometry/runtimeSurface strings: those are semantic sources,
-- not file references, and keep their existing geometry/compiler validation.
function resource_reference.validateAuthored(loader)
    local problems = {}
    local function report(ok, message)
        if not ok then problems[#problems + 1] = message end
        return ok
    end

    for _, map in ipairs(loader.maps or {}) do
        local mapDesc = "map '" .. tostring(map.name or map.title or map.id) .. "'"
        for _, ev in ipairs(map.events or {}) do
            local evDesc = mapDesc .. " event (" .. tostring(ev.x) .. "," .. tostring(ev.y) .. ")"
            resource_reference.validatePresentation(ev, evDesc, report)
            validateCommandResources(ev.commands, evDesc, report)
            for pi, page in ipairs(ev.pages or {}) do
                local pageDesc = evDesc .. " page " .. pi
                resource_reference.validatePresentation(page, pageDesc, report)
                validateCommandResources(page.commands, pageDesc, report)
            end
        end
        if map.fog and map.fog.preset == nil then
            validateFogPanoramas(map.fog, mapDesc .. " fog", report)
        end
    end

    for ceId, ce in pairs(loader.commonEvents or {}) do
        local desc = "common event '" .. tostring(ceId) .. "'"
        resource_reference.validatePresentation(ce, desc, report)
        validateCommandResources(ce.commands, desc, report)
    end

    for _, preset in ipairs((loader.engine and loader.engine.fogPresets) or {}) do
        validateFogPanoramas(preset,
            "fog preset '" .. tostring(preset.id or "?") .. "'", report)
    end

    -- Keep actor image conventions on the same resolver contract as event
    -- sprites. validator_rules still owns the required-field shape checks.
    for _, actor in ipairs(loader.units or {}) do
        local who = "actor '" .. tostring(actor.name or actor.id) .. "'"
        if nonEmptyString(actor.smallBattler) then
            report(resource_reference.required("sprite", actor.smallBattler),
                who .. " smallBattler '" .. actor.smallBattler .. "' resolves to no file")
        end
        for _, asset in ipairs({
            { field = "portrait", directory = "assets/portraits" },
            { field = "bigBattler", directory = "assets/bigBattlers" },
        }) do
            local id = actor[asset.field]
            if nonEmptyString(id) then
                report(resource_reference.required("image_id", id,
                        { directory = asset.directory }),
                    who .. " " .. asset.field .. " '" .. id
                        .. "' resolves to no image in " .. asset.directory)
            end
        end
    end

    if #problems > 0 then
        error(table.concat(problems, "\n"), 0)
    end
end

return resource_reference
