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

    failFast("test_baked_environment_package", failed, passed)
end

M.run()

return M
