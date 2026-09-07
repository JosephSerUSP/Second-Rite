-- Tests for the Blender-authored baked-environment package spike.
--
-- Proves that the exported package (environment.obj, environment.mtl,
-- environment.png, collision.obj, environment.json) can be loaded and validated
-- purely at runtime without any Blender dependency.
local M = {}

local failFast = require("tests.fail_fast")
local repository = require("tests.repository_root")
local json = require("engine.data.json")
local obj_model = require("presentation.obj_model")

local passed, failed = 0, 0

local function check(condition, message)
    if condition then
        passed = passed + 1
    else
        failed = failed + 1
        print("FAIL: " .. tostring(message))
    end
end

local function readFile(relPath)
    local fullPath = repository.path(relPath)
    local f, err = io.open(fullPath, "rb")
    if not f then
        error("cannot open file " .. fullPath .. ": " .. tostring(err), 0)
    end
    local content = f:read("*a")
    f:close()
    return content
end

function M.run()
    local packageDir = "exports/environments/town_slice_spike"

    -- 1. Read and parse manifest
    local manifestJson = readFile(packageDir .. "/environment.json")
    local manifest = json.decode(manifestJson)

    check(manifest ~= nil, "environment.json decoded successfully")
    check(manifest.contractVersion == 1, "contractVersion is 1")
    check(manifest.renderMesh == "environment.obj", "renderMesh is environment.obj")
    check(manifest.materialLibrary == "environment.mtl", "materialLibrary is environment.mtl")
    check(manifest.textureAtlas == "environment.png", "textureAtlas is environment.png")
    check(manifest.collisionMesh == "collision.obj", "collisionMesh is collision.obj")

    -- 2. Validate stats
    local stats = manifest.stats
    check(stats ~= nil, "manifest contains stats")
    check(stats.triangleCount > 0, "triangleCount > 0")
    check(stats.vertexCount > 0, "vertexCount > 0")
    check(stats.materialGroupCount == 1, "materialGroupCount == 1 (single draw call)")
    check(stats.textureDimensions[1] > 0 and stats.textureDimensions[2] > 0, "texture dimensions valid")

    -- 3. Parse render mesh OBJ
    local objText = readFile(packageDir .. "/" .. manifest.renderMesh)
    local parsedModel = obj_model.parse(objText, manifest.renderMesh)

    check(parsedModel ~= nil, "obj_model parsed environment.obj")
    check(#parsedModel.groups == 1, "exactly one material group in render model")
    check(parsedModel.vertexCount > 0, "parsedModel vertexCount > 0")
    check(parsedModel.mtllib == manifest.materialLibrary, "mtllib matches manifest")

    -- 4. Parse material library MTL
    local mtlText = readFile(packageDir .. "/" .. manifest.materialLibrary)
    local materials = obj_model.parseMtl(mtlText)

    check(materials ~= nil, "obj_model parsed material library")
    check(materials["EnvironmentBakedAtlas"] ~= nil, "EnvironmentBakedAtlas material declared")
    check(materials["EnvironmentBakedAtlas"].texture == manifest.textureAtlas, "map_Kd points to environment.png")

    -- 5. Validate Spatial Anchors
    local anchors = manifest.anchors
    check(anchors ~= nil, "anchors table present in manifest")
    local requiredAnchors = { "spawn_player", "npc_elder", "torch_mount", "shop_counter" }
    for _, anchorId in ipairs(requiredAnchors) do
        local anchor = anchors[anchorId]
        check(anchor ~= nil, "anchor '" .. anchorId .. "' exists")
        if anchor then
            check(#anchor.position == 3, anchorId .. " position is 3D vector")
            check(#anchor.forward == 3, anchorId .. " forward is 3D vector")
            check(anchor.id == anchorId, anchorId .. " id matches key")
        end
    end

    -- 6. Foreground occluder check in render mesh
    -- Foreground pillar was authored near x=-1.8, y=1.0 in Z-up world coords.
    -- In normalized Z-up coordinates from obj_model, verify vertices near x=-1.8 exist.
    local foundPillarVertex = false
    local group = parsedModel.groups[1]
    if group and group.vertices then
        for _, v in ipairs(group.vertices) do
            local vx, vy, vz = v[1], v[2], v[3]
            if math.abs(vx - (-1.8)) < 0.5 and math.abs(vy - 1.0) < 0.5 then
                foundPillarVertex = true
                break
            end
        end
    end
    check(foundPillarVertex, "foreground occluder pillar geometry preserved in render mesh")

    -- 7. Parse Collision mesh OBJ
    local colObjText = readFile(packageDir .. "/" .. manifest.collisionMesh)
    local parsedCol = obj_model.parse(colObjText, manifest.collisionMesh)
    check(parsedCol ~= nil, "collision OBJ parsed successfully")
    check(parsedCol.vertexCount > 0, "collision mesh has vertices")
    check(parsedCol.mtllib == nil, "collision mesh has no material library dependencies")

    -- 8. Runtime environment_package loader optional collision contract (#1065)
    local environment_package = require("engine.environment_package")
    local pubPkg = environment_package.load("assets/environments/st_maria_town/pub/environment.json")
    check(pubPkg ~= nil, "loaded shipping pub package")
    check(pubPkg.collisionMesh ~= nil, "pub package has collisionMesh")

    local originalRead = love.filesystem.read
    local mockManifest = json.decode(manifestJson)
    mockManifest.collisionMesh = nil
    local mockJson = json.encode(mockManifest)

    love.filesystem.read = function(p)
        if p == "test/no_collision_env.json" then return mockJson end
        return originalRead(p)
    end

    local okNoCol, noColPkg = pcall(environment_package.load, "test/no_collision_env.json")
    check(okNoCol, "environment package without collisionMesh loads without error")
    if okNoCol then
        check(noColPkg.collisionMesh == nil, "noColPkg.collisionMesh is nil")
    end

    mockManifest.collisionMesh = json.null
    mockJson = json.encode(mockManifest)
    local okNullCol, nullColPkg = pcall(environment_package.load, "test/no_collision_env.json")
    check(okNullCol, "environment package with json.null collisionMesh loads without error")
    if okNullCol then
        check(nullColPkg.collisionMesh == nil, "nullColPkg.collisionMesh is nil")
    end

    mockManifest.collisionMesh = ""
    mockJson = json.encode(mockManifest)
    local okEmptyCol = pcall(environment_package.load, "test/no_collision_env.json")
    check(not okEmptyCol, "environment package with empty collisionMesh string fails loudly")

    mockManifest.collisionMesh = 42
    mockJson = json.encode(mockManifest)
    local okBadType = pcall(environment_package.load, "test/no_collision_env.json")
    check(not okBadType, "environment package with non-string collisionMesh fails loudly")

    -- 9. Runtime environment_package loader bakedLighting property (#1037)
    check(pubPkg.bakedLighting == false, "pre-rendered pub package defaults to bakedLighting == false")

    local aliciaPkg = environment_package.load("assets/environments/st_maria_town/alicias_padaria_3d/environment.json")
    check(aliciaPkg ~= nil, "loaded alicias_padaria_3d environment package")
    check(aliciaPkg.bakedLighting == true, "live-mesh alicias_padaria_3d defaults to bakedLighting == true")

    mockManifest.collisionMesh = nil
    mockManifest.bakedLighting = false
    mockJson = json.encode(mockManifest)
    local falseBakedPkg = environment_package.load("test/no_collision_env.json")
    check(falseBakedPkg.bakedLighting == false, "explicit bakedLighting: false is preserved")

    mockManifest.bakedLighting = true
    mockJson = json.encode(mockManifest)
    local trueBakedPkg = environment_package.load("test/no_collision_env.json")
    check(trueBakedPkg.bakedLighting == true, "explicit bakedLighting: true is preserved")

    love.filesystem.read = originalRead

    -- 10. viewport_3d getFogConfig respects baked town environments (#1037)
    local viewport_3d = require("presentation.viewport_3d")
    check(type(viewport_3d.getFogConfig) == "function", "viewport_3d.getFogConfig is exposed")
    check(type(viewport_3d.isLiveBakedTown) == "function", "viewport_3d.isLiveBakedTown is exposed")

    -- Case A: Dungeon / non-town session (townTraversal == nil)
    local dungeonSession = {}
    local dFogDef, dHasFog = viewport_3d.getFogConfig(dungeonSession, {})
    check(not dHasFog, "map without fog returns hasFog == false")
    check(math.abs(dFogDef.minFactor - 0.12) < 0.001, "dungeon default minFactor is 0.12 (fog attenuation active)")

    local dFogExplicit = viewport_3d.getFogConfig(dungeonSession, { fog = { minFactor = 0.5 } })
    check(math.abs(dFogExplicit.minFactor - 0.5) < 0.001, "dungeon honors explicit minFactor 0.5")

    -- Case B: Live-mesh baked town environment session
    local liveTownSession = {
        townTraversal = {
            environment = aliciaPkg,
        },
    }
    check(viewport_3d.isLiveBakedTown(liveTownSession), "liveTownSession identified as live baked town")

    local liveFogDef, liveHasFog = viewport_3d.getFogConfig(liveTownSession, {})
    check(not liveHasFog, "live town map without fog returns hasFog == false")
    check(math.abs(liveFogDef.minFactor - 1.0) < 0.001, "live baked town map without fog defaults to minFactor == 1.0 (no attenuation)")

    local liveFogNoMin = viewport_3d.getFogConfig(liveTownSession, { fog = { color = { 0, 0, 0 }, distance = 10 } })
    check(math.abs(liveFogNoMin.minFactor - 1.0) < 0.001, "live baked town map with fog but no minFactor defaults to minFactor == 1.0")

    local liveFogExplicit = viewport_3d.getFogConfig(liveTownSession, { fog = { minFactor = 0.65 } })
    check(math.abs(liveFogExplicit.minFactor - 0.65) < 0.001, "live baked town honors explicit author minFactor 0.65")

    -- Case C: Pre-rendered town environment session
    local preRenderTownSession = {
        townTraversal = {
            environment = pubPkg,
        },
    }
    check(not viewport_3d.isLiveBakedTown(preRenderTownSession), "preRenderTownSession is not live baked mesh")
    local preFogDef = viewport_3d.getFogConfig(preRenderTownSession, {})
    check(math.abs(preFogDef.minFactor - 0.12) < 0.001, "pre-rendered town environment defaults to minFactor == 0.12")

    failFast("test_baked_environment_package", failed, passed)
end

M.run()

return M
