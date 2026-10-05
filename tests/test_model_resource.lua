local resource = require("presentation.model_resource")
local obj = require("presentation.obj_model")
local viewer = require("presentation.item_model_view")
local viewport = require("presentation.viewport_3d")
local instance = require("engine.geometry.model_instance")
local json = require("engine.data.json")
local passed = 0
local function check(value, message)
    assert(value, message)
    passed = passed + 1
end
local path = "assets/models/items/lantern.obj"
local legacy = obj.load(path)
resource.clearCache()
local read = love.filesystem.read
love.filesystem.read = function(file, ...)
    assert(not file:match("%.obj$") and not file:match("%.mtl$"), "compiled consumer reparsed source")
    return read(file, ...)
end
local ok, compiled = pcall(resource.load, path)
love.filesystem.read = read
assert(ok, compiled)
check(compiled.modelId == "item.lantern", "registered source resolves to stable Model identity without source reads")
check(compiled.vertexCount == legacy.vertexCount, "import preserves triangle count")
check(resource.load("model:item.lantern") == compiled, "semantic reference and source adapter share one acquired Model")
check(viewer.resolveModel(path) == compiled, "item viewer acquires the same Model as world placement")
local sameUpload = #legacy.groups == #compiled.groups
for groupIndex, group in ipairs(legacy.groups) do
    local imported = compiled.groups[groupIndex]
    if imported then
        for vertexIndex = 1, group.mesh:getVertexCount() do
            local a, b = { group.mesh:getVertex(vertexIndex) }, { imported.mesh:getVertex(vertexIndex) }
            for field = 1, #a do
                if a[field] ~= b[field] then
                    sameUpload = false
                    print(string.format("MODEL UPLOAD DIFFERENCE group=%d vertex=%d field=%d native=%.17g compiled=%.17g",
                        groupIndex, vertexIndex, field, a[field], b[field]))
                end
            end
        end
    end
end
check(sameUpload, "native GPU vertex uploads must preserve positions, normals, UVs and vertex colors")

local function captureItem(useCompiled, w, h, yaw, tilt)
    local old = viewer.resolveModel
    viewer.resolveModel = function() return useCompiled and compiled or legacy end
    local target = require("presentation.surface").newRasterCanvas(w, h)
    love.graphics.push("all")
    love.graphics.setCanvas(target)
    love.graphics.origin()
    love.graphics.setScissor()
    love.graphics.setShader()
    love.graphics.setColor(1,1,1,1)
    love.graphics.clear(0, 0, 0, 0)
    viewer.draw(0, 0, w, h, path, "model-proof", "lantern", yaw, tilt)
    love.graphics.setCanvas()
    love.graphics.pop()
    viewer.resolveModel = old
    local image = target:newImageData()
    return image:getString(), image
end
for _, dimensions in ipairs({ {96,96}, {64,112}, {208,150}, {384,64} }) do
    for _, angle in ipairs({ {0.35,0.17}, {1.92,0.17}, {0.78,1.22}, {0.78,-0.96} }) do
        local nativePixels = captureItem(false, dimensions[1], dimensions[2], angle[1], angle[2])
        local compiledPixels = captureItem(true, dimensions[1], dimensions[2], angle[1], angle[2])
        local visible = nativePixels:find("[^%z]") ~= nil
        check(nativePixels == compiledPixels and visible,
            string.format("item %dx%d yaw=%.2f tilt=%.2f: equal=%s nativeVisible=%s",
                dimensions[1], dimensions[2], angle[1], angle[2],
                tostring(nativePixels == compiledPixels), tostring(visible)))
    end
end

local event = viewport.resolveModelInstance({ modelScale = 2 }, "event:proof", compiled.modelId, 3, 4, 1, "x", nil, nil, { kind = "event", id = 7 })
local px, py, pz = instance.position(event, 1, 2, 3)
check(px == 5 and py == 8 and pz == 7, "resolved instance preserves world scale and Z translation")
local wall = viewport.resolveModelInstance({}, "fixture:proof", compiled.modelId, 3, 4, 0, nil, 0, -1, { kind = "cell" })
px, py, pz = instance.position(wall, 1, 2, 3)
check(px == 5 and py == 3 and pz == 3, "wall fixture resolves into the same instance transform")
local environment = viewport.resolveModelInstance({ bakedLighting = false }, "root:proof", compiled.modelId, 0, 0, 0, "x", nil, nil, { kind = "environment" })
check(not environment.bakedLighting, "environment provenance does not imply baked lighting")
local baked = viewport.resolveModelInstance({ bakedLighting = true }, "ordinary:proof", compiled.modelId, 0, 0, 0, "x")
check(baked.bakedLighting, "ordinary Model can explicitly consume baked appearance")

local loader = require("engine.data.loader")
local session = require("engine.session").GameSession.new(loader)
session:initializeStartingParty()
require("engine.exploration").loadMap(session, 30)
session.currentMapData = json.decode(json.encode(session.currentMapData))
session.mapGrid = { {"#","#","#","#","#"}, {"#",".",".",".","#"}, {"#",".",".",".","#"}, {"#",".",".",".","#"}, {"#","#","#","#","#"} }
session.playerX, session.playerY, session.playerDir = 3, 4, "N"
session.currentMapData.events = { { id = 98765, x = 1, y = 1, model = path } }
viewport.init()
local function captureWorld(model)
    local load = resource.load
    resource.load = function(reference) return reference == path and model or load(reference) end
    viewport.invalidateStructure(session)
    local canvas = require("presentation.surface").newRasterCanvas(256, 240)
    love.graphics.push("all")
    love.graphics.setCanvas({ canvas, depth = true, stencil = true })
    love.graphics.origin()
    love.graphics.setScissor()
    love.graphics.setShader()
    love.graphics.setColor(1,1,1,1)
    love.graphics.clear(0, 0, 0, 0, 0, 1)
    viewport.draw(session)
    love.graphics.setCanvas()
    love.graphics.pop()
    resource.load = load
    local image = canvas:newImageData()
    return image:getString(), image
end
local worldLegacy = captureWorld(legacy)
local worldCompiled, worldImage = captureWorld(compiled)
check(worldLegacy == worldCompiled, "real world renderer preserves compiled Model pixels")
session.currentMapData.events = {}
check(captureWorld(compiled) ~= worldCompiled, "world fixture visibly exercises the lantern, not an empty view")
session.currentMapData.events = { { id = 98765, x = 1, y = 1, model = path } }
local world = assert(require("presentation.map_renderable_bundle").collect(session))
local found = false
for _, surface in ipairs(world.surfaces) do
    if surface.source.kind == "event" and surface.source.id == 98765 then
        found = surface.modelInstance.modelId == "item.lantern" and surface.materialSlot ~= nil
    end
end
check(found, "Studio transport preserves Model identity, material slot and resolved instance provenance")
local proofRoot = os.getenv("THESTRA_MODEL_PROOF_OUTPUT")
if proofRoot and proofRoot ~= "" then
    local function write(name, text)
        local file = assert(io.open(proofRoot .. "/" .. name, "wb"))
        file:write(text); file:close()
    end
    local facts = {}
    for _, value in ipairs({event, wall, environment, baked}) do
        local x,y,z = instance.position(value, 1,2,3)
        facts[#facts+1] = {instance = value, point = {1,2,3}, world = {x,y,z}}
    end
    write("instances.json", json.encode(facts))
    write("bundle.json", assert(love.filesystem.read(compiled.path)))
    write("world.png", worldImage:encode("png"):getString())
    local _, itemImage = captureItem(true, 208,150,0.35,0.17)
    write("item.png", itemImage:encode("png"):getString())
end
print("=== test_model_resource: " .. passed .. " passed ===")
