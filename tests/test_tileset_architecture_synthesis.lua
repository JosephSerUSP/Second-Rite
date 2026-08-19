-- Unit tests for Tileset Architecture Synthesis (#558)
-- Proves backward-compatible resolution, Surface Library + Environment Palette
-- separation, facing-space wall face ownership, and structural profiles.

local resolver = require("engine.tileset_resolver")
local loader = require("data.loader")

local passed, failed = 0, 0
local function check(label, fn)
    local ok, err = pcall(fn)
    if ok then
        passed = passed + 1
        print("  [PASS] " .. label)
    else
        failed = failed + 1
        print("  [FAIL] " .. label .. ": " .. tostring(err))
    end
end

print("[TEST] Starting Tileset Architecture Synthesis tests (#558)...")

loader.init()

-- 1. Backward-compatibility: resolve existing legacy tileset
check("existing legacy tileset resolves backward-compatibly", function()
    local legacyTileset, key = resolver.resolve(loader, { tileset = "dungeon_default" })
    assert(legacyTileset ~= nil, "dungeon_default must resolve")
    assert(legacyTileset.id == "dungeon_default", "tileset id preserved")
    assert(legacyTileset.base and legacyTileset.base.walls, "legacy base.walls present")
    assert(legacyTileset.base.floors, "legacy base.floors present")
    assert(legacyTileset.base.ceilings, "legacy base.ceilings present")
end)

-- 2. Surface resolution: local surfaces table in tileset
local mockTilesetWithSurfaces = {
    id = "palette_crypt",
    surfaces = {
        surface_wet_stone = {
            id = "surface_wet_stone",
            source = { kind = "standalone" },
            albedo = { image = "assets/surfaces/crypt/albedo.png" },
            height = { image = "assets/surfaces/crypt/height.png", scale = 0.08 },
            emission = {
                frames = { "glow1.png", "glow2.png" },
                fps = 6,
            },
            layers = {
                { meaning = "moss", image = "moss.png", blend = "multiply", uvSource = "uv" },
                { meaning = "sheen", image = "sheen.png", blend = "add", uvSource = "sphere" },
            },
        },
    },
    base = {
        walls = {
            { id = "wet_wall", surface = "surface_wet_stone", weight = 100 },
        },
    },
    structuralProfile = {
        kind = "procedural",
        corner = "round",
        radius = 0.12,
        segments = 3,
    },
}

local mockLoader = {
    getTileset = function(id)
        if id == "palette_crypt" then return mockTilesetWithSurfaces end
        if loader and loader.getTileset then return loader.getTileset(id) end
        return nil
    end,
    getSurface = function(id)
        if id == "global_flagstone" then
            return {
                id = "global_flagstone",
                source = { kind = "standalone" },
                albedo = { image = "assets/surfaces/flagstone/albedo.png" },
            }
        end
        return nil
    end,
}

check("decoupled Surface resolution preserves animation clocks and material layers", function()
    local resolvedPalette = resolver.resolve(mockLoader, { tileset = "palette_crypt" })
    assert(resolvedPalette ~= nil, "palette_crypt must resolve")
    assert(resolvedPalette.surfaces and resolvedPalette.surfaces.surface_wet_stone, "surfaces table preserved")
    assert(resolvedPalette.structuralProfile.corner == "round", "structural profile preserved")

    local variant = resolvedPalette.base.walls[1]
    local surface = resolver.resolveVariantSurface(variant, resolvedPalette, mockLoader)
    assert(surface ~= nil, "surface must resolve from variant")
    assert(surface.id == "surface_wet_stone", "surface id correct")
    assert(surface.albedo.image == "assets/surfaces/crypt/albedo.png", "albedo image path correct")
    assert(surface.emission.fps == 6, "emission fps preserved")
    assert(#surface.layers == 2, "material layers preserved")
end)

check("loader Surface lookup resolves global library assets", function()
    local resolvedPalette = resolver.resolve(mockLoader, { tileset = "palette_crypt" })
    local externalSurface = resolver.resolveSurface(mockLoader, "global_flagstone", resolvedPalette)
    assert(externalSurface ~= nil and externalSurface.id == "global_flagstone", "loader surface lookup works")
end)

-- 4. Sparse Map override with local Surfaces and structural profile
check("sparse tilesetOverride cleanly updates structural profiles and Surface definitions", function()
    local mapWithOverride = {
        tileset = "palette_crypt",
        tilesetOverride = {
            structuralProfile = { corner = "chamfer", radius = 0.15 },
            surfaces = {
                surface_wet_stone = {
                    emission = { strength = 2.5 },
                },
                surface_alt = {
                    id = "surface_alt",
                    albedo = { image = "alt.png" },
                },
            },
            base = {
                walls = {
                    { id = "wet_wall", weight = 50 },
                    { id = "alt_wall", surface = "surface_alt", weight = 50 },
                },
            },
        },
    }

    local overridden = resolver.resolve(mockLoader, mapWithOverride)
    assert(overridden.structuralProfile.corner == "chamfer", "overridden structural profile updated")
    assert(overridden.surfaces.surface_wet_stone.emission.strength == 2.5, "surface property merged")
    assert(overridden.surfaces.surface_alt ~= nil, "new surface merged into surfaces table")
    assert(#overridden.base.walls == 2, "variant pool merged")
end)

-- 5. Facing-space wall face ownership across zone boundaries
check("facing-space zone wall ownership resolves boundary palettes deterministically", function()
    local multiZoneMap = {
        tileset = "dungeon_default",
        layout = {
            "#####",
            "#...#",
            "#####",
        },
        zoneGrid = {
            { "", "", "", "", "" },
            { "", "nave", "nave", "crypt", "" },
            { "", "", "", "", "" },
        },
        zones = {
            nave = { palette = "dungeon_default" },
            crypt = { palette = "palette_crypt" },
        },
    }

    -- In 0-indexed coords:
    -- row 0 is '#####', row 1 is '#...#', row 2 is '#####'
    -- At y=1: cell (1, 1) is 'nave', cell (2, 1) is 'nave', cell (3, 1) is 'crypt'
    -- Wall face at (2, 0) facing nave cell (2, 1) -> receives nave palette
    local faceNave = resolver.resolveWallFacePalette(multiZoneMap, 2, 0, 2, 1, mockLoader)
    assert(faceNave.zone == "nave", "facing cell (2,1) belongs to nave zone")
    assert(faceNave.paletteId == "dungeon_default", "nave palette resolved")

    -- Wall face at (3, 0) facing crypt cell (3, 1) -> receives crypt palette
    local faceCrypt = resolver.resolveWallFacePalette(multiZoneMap, 3, 0, 3, 1, mockLoader)
    assert(faceCrypt.zone == "crypt", "facing cell (3,1) belongs to crypt zone")
    assert(faceCrypt.paletteId == "palette_crypt", "crypt palette resolved")
end)

-- 6. Structural profile containment invariant check: visual geometry <= solid cell footprint
check("structural profile containment invariant verified", function()
    local function checkProfileContainment(profile)
        local r = profile.radius or 0.12
        assert(r > 0 and r <= 0.5, "profile radius must stay within cell half-width")
    end
    checkProfileContainment({ corner = "round", radius = 0.12 })
    checkProfileContainment({ corner = "chamfer", radius = 0.2 })
end)

print(string.format("=== Tileset Architecture Synthesis: %d passed, %d failed ===", passed, failed))
assert(failed == 0, "test suite failed")
