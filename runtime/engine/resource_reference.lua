-- Typed resolution and validation for authored runtime resource references (#353).
--
-- This module deliberately does NOT walk arbitrary strings looking for path-like
-- values. A caller has to name the resource contract it is validating. That
-- distinction keeps semantic/non-filesystem authoring forms (geometry source
-- ids, generated runtime surfaces, formula strings, etc.) out of filesystem
-- validation while giving G1 one authority for resource forms that several
-- authored categories share.
--
-- Existing G1 rules already validate many concrete asset-owning fields. This
-- module does not re-walk those owners. It supplies their shared resolution
-- vocabulary and a small canonical phase for resource holes the existing pass
-- did not cover (notably common-event presentation sprites and fog panoramas).
--
-- Sprite resolution delegates to presentation.sprite_sheet.resolveFile: that
-- function is the runtime authority for sprite keys, case variants and
-- [key=value] filename tokens, so validation must not reproduce that lookup.
local sprite_sheet = require("presentation.sprite_sheet")

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
        local resolved = sprite_sheet.resolveFile(value)
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
    -- convention. The id itself is not a path and must not be validated as one.
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
-- renderer inherited the field from. Existing G1 checks already cover map/page
-- sprites and common-event models; applying the vocabulary to common events
-- closes the owner gap without inventing a CommonEvent.sprite-only rule.
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
        -- validator_rules owns panorama shape. Only resolve a valid-looking
        -- authored image here, so malformed values remain one deterministic
        -- shape error instead of being reinterpreted as file paths.
        if type(layer) == "table" and nonEmptyString(layer.image) then
            report(resource_reference.required("panorama", layer.image),
                desc .. ".image resolves to no panorama asset ('" .. layer.image .. "')")
        end
    end
end

-- Resource-reference phase of canonical G1. validator_rules remains the owner
-- of schema/gameplay checks and of asset fields it already validates. This pass
-- intentionally covers only known resolution gaps, through typed contracts.
-- It does not inspect geometry/runtimeSurface strings: those are semantic
-- sources, not filesystem references, and retain their geometry/compiler rules.
function resource_reference.validateAuthored(loader)
    local problems = {}
    local function report(ok, message)
        if not ok then problems[#problems + 1] = message end
        return ok
    end

    -- Common-event presentation is inherited by map events just like map/page
    -- presentation, but the old asset sweep omitted this owner. Validate the
    -- whole shared presentation vocabulary instead of a sprite-only exception.
    for ceId, ce in pairs(loader.commonEvents or {}) do
        resource_reference.validatePresentation(ce,
            "common event '" .. tostring(ceId) .. "'", report)
    end

    -- Fog shape was already validated, but panorama existence was not. Resolve
    -- both inline map fog and registered presets using the renderer's shorthand.
    for _, map in ipairs(loader.maps or {}) do
        if type(map.fog) == "table" and map.fog.preset == nil then
            validateFogPanoramas(map.fog,
                "map '" .. tostring(map.name or map.title or map.id) .. "' fog", report)
        end
    end
    for _, preset in ipairs((loader.engine and loader.engine.fogPresets) or {}) do
        validateFogPanoramas(preset,
            "fog preset '" .. tostring(preset.id or "?") .. "'", report)
    end

    if #problems > 0 then
        error(table.concat(problems, "\n"), 0)
    end
end

return resource_reference
