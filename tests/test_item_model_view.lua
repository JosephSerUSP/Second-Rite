-- Unit tests for 3D item model viewer (presentation/item_model_view.lua).

package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("engine.data.loader")
local item_presentation = require("presentation.item_presentation")
local item_model_view = require("presentation.item_model_view")
local retro_mesh_shader = require("presentation.retro_mesh_shader")

print("[TEST] Starting 3D item model viewer tests...")

local passed, failed = 0, 0
local function check(cond, msg)
    if cond then
        passed = passed + 1
        print("  [PASS] " .. msg)
    else
        failed = failed + 1
        print("  [FAIL] " .. msg)
    end
end

loader.init()

-------------------------------------------------- 1. Item & Shop row enrichment --

local hpTonic = loader.getItem(1) -- HP Tonic
local hpRow = item_presentation.enrich({ id = hpTonic.id, name = hpTonic.name }, hpTonic, loader)
check(hpRow.model == "assets/models/items/bottle_family__basis.obj",
    "Item scene: valid model path 'bottle_family__basis.obj' enriched on HP Tonic row")

-- Derived rather than a hard-coded id: fabrication batches keep assigning the
-- next block of items, so naming one here goes stale. See the same reasoning in
-- tests/test_item_model_assignments.lua.
local unmodelled = { id = -1, name = "Synthetic fallback probe" }
local cfRow = item_presentation.enrich({ id = unmodelled.id, name = unmodelled.name }, unmodelled, loader)
check(cfRow.model == "", "Synthetic missing-model row keeps the empty model field contract")

-------------------------------------------------- 2. Fallback resolution tests --

item_model_view.clearCache()

local originalGetTime = love.timer.getTime
local testClock = 10.0
love.timer.getTime = function() return testClock end

-- Selected item with no model ("" or nil) resolves placeholder_question.obj
local fbModel, fbPath, fbUsed = item_model_view.resolveModel("")
check(fbModel ~= nil and fbPath == item_model_view.FALLBACK_PATH and fbUsed == true,
    "Selected item with no model ('') resolves placeholder_question.obj")

local nilModel, nilPath, nilUsed = item_model_view.resolveModel(nil)
check(nilModel ~= nil and nilPath == item_model_view.FALLBACK_PATH and nilUsed == true,
    "Selected item with nil model resolves placeholder_question.obj")

-- Selected item with invalid model path resolves placeholder_question.obj
local invModel, invPath, invUsed = item_model_view.resolveModel("assets/models/items/invalid_nonexistent_item.obj")
check(invModel ~= nil and invPath == item_model_view.FALLBACK_PATH and invUsed == true,
    "Selected item with invalid model path resolves placeholder_question.obj")

-- Caching test: consecutive call for invalid model path returns cached fallback without throwing
local cModel, cPath, cUsed = item_model_view.resolveModel("assets/models/items/invalid_nonexistent_item.obj")
check(cModel == invModel and cPath == invPath and cUsed == true,
    "Invalid model path resolution is cached rather than retried")

-------------------------------------------------- 3. Selection angle reset (Item Identity) --

item_model_view.clearCache()

local sharedObj = "assets/models/items/wind_charm.obj"
local selKey1 = "wind_charm:" .. sharedObj
local selKey2 = "light_amulet:" .. sharedObj

local a0 = item_model_view.getRotationState("window_test", selKey1)
check(math.abs(a0 - 0.0) < 1e-5, "Initial angle for Wind Charm is 0")

local sameTime = item_model_view.getRotationState("window_test", selKey1)
check(math.abs(sameTime - a0) < 1e-5, "Repeated lookup at the same clock time does not advance rotation")

testClock = 11.0
local a1 = item_model_view.getRotationState("window_test", selKey1)
check(math.abs(a1 - 0.4) < 1e-4, "Wind Charm angle follows one second of clock time at 0.4 rad/s (got " .. tostring(a1) .. ")")

local b0 = item_model_view.getRotationState("window_test", selKey2)
check(math.abs(b0 - 0.0) < 1e-5, "Selection change to Light Amulet (same OBJ) resets angle to 0")

testClock = 12.0
local a2 = item_model_view.getRotationState("window_test", selKey1)
check(math.abs(a2 - 0.0) < 1e-5, "Returning to Wind Charm resets angle to 0 rather than inheriting Light Amulet's angle")

item_model_view.resetRotationStates()
local resetAngle = item_model_view.getRotationState("window_test", selKey1)
check(math.abs(resetAngle - 0.0) < 1e-5, "Resetting rotation states restarts the selection clock")

love.timer.getTime = originalGetTime

-------------------------------------------------- 4. Tilt-fit calculation tests --

local tilt = item_model_view.ITEM_PRESENTATION_TILT
local cosT = math.abs(math.cos(tilt))
local sinT = math.abs(math.sin(tilt))

-- Tall bottle bounds
local bottleBounds = { minX = -1, maxX = 1, minY = -1, maxY = 1, minZ = -5, maxZ = 5 }
local bCenter, bHalfW, bHalfH = item_model_view.calculateFit(bottleBounds, 100, 100, 0.81, tilt)
local bTiltedX = 1 * cosT + 5 * sinT
local bTiltedY = 1
local bTiltedZ = 1 * sinT + 5 * cosT
local bHorizRad = math.sqrt(bTiltedX * bTiltedX + bTiltedY * bTiltedY)
local bVertRad = bTiltedZ
check(bHalfH >= bVertRad / 0.81 - 1e-4 and bHalfW >= bHorizRad / 0.81 - 1e-4,
    "Tall bottle fit includes local-Y tilt in extents")

-- Long horizontal sword bounds
local swordBounds = { minX = -6, maxX = 6, minY = -0.5, maxY = 0.5, minZ = -0.5, maxZ = 0.5 }
local _, sHalfW, sHalfH = item_model_view.calculateFit(swordBounds, 100, 100, 0.81, tilt)
local sTiltedX = 6 * cosT + 0.5 * sinT
local sTiltedY = 0.5
local sHorizRad = math.sqrt(sTiltedX * sTiltedX + sTiltedY * sTiltedY)
check(math.abs(sHalfH - sHorizRad / 0.81) < 1e-4,
    "Long horizontal sword fits tilted rotation-safe horizontal radius")

-- Flat charm bounds
local charmBounds = { minX = -2, maxX = 2, minY = -0.1, maxY = 0.1, minZ = -2, maxZ = 2 }
local _, cHalfW, cHalfH = item_model_view.calculateFit(charmBounds, 100, 100, 0.81, tilt)
check(cHalfH > 0 and cHalfW > 0, "Flat charm bounds fit safely with tilt")

-- Zero-sized bounds
local zeroBounds = { minX = 0, maxX = 0, minY = 0, maxY = 0, minZ = 0, maxZ = 0 }
local _, zHalfW, zHalfH = item_model_view.calculateFit(zeroBounds, 100, 100, 0.81, tilt)
check(zHalfH > 0 and zHalfW > 0, "Zero-sized bounds calculate safely without division by zero")

-- Aspect ratio fitting (square, wide, narrow)
local _, wAspectW, wAspectH = item_model_view.calculateFit(swordBounds, 200, 100, 0.81, tilt) -- aspect 2.0
check(math.abs(wAspectW - sHorizRad / 0.81) < 1e-4, "Wide viewport (aspect 2.0) fits tilted horizontal radius")

local _, nAspectW, nAspectH = item_model_view.calculateFit(swordBounds, 100, 200, 0.81, tilt) -- aspect 0.5
check(math.abs(nAspectH - (sHorizRad / 0.5) / 0.81) < 1e-4, "Narrow viewport (aspect 0.5) fits tilted horizontal radius across height")

local validator = require("engine.validator_core")

-------------------------------------------------- 5. Real validator tests --

local function validateWithItems(itemsList)
    local mockLoader = {}
    for k, v in pairs(loader) do mockLoader[k] = v end
    mockLoader.items = itemsList
    return pcall(validator.run, mockLoader)
end

-- Valid model
local okValid, errValid = validateWithItems({ { id = "valid_item", model = "assets/models/items/silver_blade.obj" } })
check(okValid == true, "Real validator: valid item model path passes validation")

-- Optional model field (missing model key)
local okNoModel, errNoModel = validateWithItems({ { id = "no_model_item" } })
check(okNoModel == true, "Real validator: item without model field passes validation")

-- Missing file
local okMissing, errMissing = validateWithItems({ { id = "missing_model_item", model = "assets/models/items/definitely_missing.obj" } })
check(okMissing == false and tostring(errMissing):find("resolves to no asset"),
    "Real validator: missing model asset yields 'resolves to no asset' problem")

-- Empty string
local okEmpty, errEmpty = validateWithItems({ { id = "empty_model_item", model = "" } })
check(okEmpty == false and tostring(errEmpty):find("must be a non-empty asset path", 1, true) ~= nil,
    "Real validator: empty model path string yields 'must be a non-empty asset path' problem")

-- Wrong type (number, boolean)
local okNum, errNum = validateWithItems({ { id = "numeric_model_item", model = 42 } })
check(okNum == false and tostring(errNum):find("must be a non-empty asset path", 1, true) ~= nil,
    "Real validator: numeric model path yields 'must be a non-empty asset path' problem without crashing")

local okBool, errBool = validateWithItems({ { id = "bool_model_item", model = true } })
check(okBool == false and tostring(errBool):find("must be a non-empty asset path", 1, true) ~= nil,
    "Real validator: boolean model path yields 'must be a non-empty asset path' problem without crashing")

-------------------------------------------------- 6. Graphics state protection & offset scissor regression test --

if love.graphics and love.graphics.isCreated() then
    love.graphics.setColor(0.8, 0.4, 0.2, 0.5)
    love.graphics.setScissor(150, 40, 80, 100)

    local screenCanvas = love.graphics.newCanvas(300, 300)
    love.graphics.setCanvas(screenCanvas)
    love.graphics.clear(0, 0, 0, 0)

    item_model_view.draw(150, 40, 80, 100, "assets/models/items/silver_blade.obj", "scissor_test_window", "scissor_test_item", 0)

    love.graphics.setCanvas()

    local r, g, b, a = love.graphics.getColor()
    local sx, sy, sw, sh = love.graphics.getScissor()

    check(math.abs(r - 0.8) < 1e-4 and math.abs(g - 0.4) < 1e-4 and math.abs(b - 0.2) < 1e-4 and math.abs(a - 0.5) < 1e-4,
        "Caller graphics color is restored after item_model_view.draw")
    check(sx == 150 and sy == 40 and sw == 80 and sh == 100,
        "Caller offset scissor is restored after item_model_view.draw")

    local imgData = screenCanvas:newImageData()
    local nonZeroAlpha = 0
    for py = 40, 139 do
        for px = 150, 229 do
            local _, _, _, alpha = imgData:getPixel(px, py)
            if alpha > 0 then nonZeroAlpha = nonZeroAlpha + 1 end
        end
    end
    check(nonZeroAlpha > 0, "Offset scissor regression test: model renders into offscreen canvas and composite pixels appear in destination region (" .. nonZeroAlpha .. " px)")
end

-------------------------------------------------- 6b. Material overlay passes --

-- The shader cannot compute specular, reflection or refraction (SPEC 1.25), so
-- material identity beyond a flat colour comes from layering sampled images
-- with fixed blend operations. Nothing in the repository's own MTL files
-- declares a pass yet, so without these the whole path would sit at count 0
-- and every test would pass while doing nothing.

local obj_model = require("presentation.obj_model")

-- The registry and the code must agree, or the editor offers a blend the
-- parser rejects. Prose cannot enforce that; this can.
local engineData = loader.engine or (loader.getEngine and loader.getEngine())
local registryBlends = {}
for _, entry in ipairs((engineData.geometry or {}).materialBlendOps or {}) do
    registryBlends[entry.id] = true
end
local blendsAgree = true
for name in pairs(retro_mesh_shader.BLEND_OPS) do
    if not registryBlends[name] then blendsAgree = false end
end
for name in pairs(registryBlends) do
    if not retro_mesh_shader.BLEND_OPS[name] then blendsAgree = false end
end
check(blendsAgree and next(registryBlends) ~= nil,
    "engine.json materialBlendOps matches the shader's own blend table")

local registryUvs = {}
for _, entry in ipairs((engineData.geometry or {}).materialUvSources or {}) do
    registryUvs[entry.id] = true
end
local uvsAgree = true
for name in pairs(retro_mesh_shader.UV_SOURCES) do
    if not registryUvs[name] then uvsAgree = false end
end
for name in pairs(registryUvs) do
    if not retro_mesh_shader.UV_SOURCES[name] then uvsAgree = false end
end
check(uvsAgree and next(registryUvs) ~= nil,
    "engine.json materialUvSources matches the shader's own uv-source table")

local passMtl = "newmtl grimy\nKd 0.8 0.7 0.2\npass uv multiply 0.5 assets/models/items/grime.png\n"
local parsedPass = obj_model.parseMtl(passMtl)
check(parsedPass.grimy and parsedPass.grimy.passes and #parsedPass.grimy.passes == 1
        and parsedPass.grimy.passes[1].blend == "multiply"
        and parsedPass.grimy.passes[1].uvSource == "uv"
        and math.abs(parsedPass.grimy.passes[1].strength - 0.5) < 1e-6
        and parsedPass.grimy.passes[1].texture == "assets/models/items/grime.png",
    "MTL 'pass' declares an overlay with uv source, blend, strength and texture")

-- refl must remain the standard statement AND stop being a parallel code path.
local reflMtl = "newmtl polished\nrefl -type sphere assets/models/items/sheen.png\n"
local parsedRefl = obj_model.parseMtl(reflMtl)
check(parsedRefl.polished and parsedRefl.polished.passes
        and #parsedRefl.polished.passes == 1
        and parsedRefl.polished.passes[1].blend == "add"
        and parsedRefl.polished.passes[1].uvSource == "sphere"
        and parsedRefl.polished.passes[1].texture == "assets/models/items/sheen.png",
    "MTL refl is sugar for an additive sphere-mapped pass, not a second mechanism")

local okType = pcall(obj_model.parseMtl, "newmtl m\nrefl -type cube nope.png\n")
check(okType == false, "MTL refl with an unsupported type fails loudly")
local okBare = pcall(obj_model.parseMtl, "newmtl m\nrefl nope.png\n")
check(okBare == false, "MTL refl without a -type is rejected")

local okBlend, errBlend = pcall(obj_model.parseMtl, "newmtl m\npass uv glow 1.0 x.png\n")
check(okBlend == false and tostring(errBlend):find("unknown", 1, true) ~= nil,
    "An unknown pass blend fails at load rather than rendering nothing")
local okUv = pcall(obj_model.parseMtl, "newmtl m\npass cube add 1.0 x.png\n")
check(okUv == false, "An unknown pass uv source fails at load")
local okStrength = pcall(obj_model.parseMtl, "newmtl m\npass uv add lots x.png\n")
check(okStrength == false, "A non-numeric pass strength fails at load")

-- The slot bound is stated, so exceeding it must be an error and not a silent
-- truncation: a dropped pass is invisible, which is the worst outcome.
local tooMany = "newmtl m\n"
for _ = 1, retro_mesh_shader.MAX_PASSES + 1 do
    tooMany = tooMany .. "pass uv add 1.0 x.png\n"
end
local okMany, errMany = pcall(obj_model.parseMtl, tooMany)
check(okMany == false and tostring(errMany):find("no slot", 1, true) ~= nil,
    "Declaring more passes than the shader has slots fails rather than dropping them")

if love.graphics and love.graphics.isCreated() then
    -- Section 6 deliberately leaves its scissor set to prove the viewer
    -- restores it. This block draws at the origin, which that scissor clips
    -- away entirely, so clear it first.
    love.graphics.setScissor()

    local function midGreyImage()
        local data = love.image.newImageData(4, 4)
        data:mapPixel(function() return 0.5, 0.5, 0.5, 1 end)
        local image = love.graphics.newImage(data)
        image:setFilter("nearest", "nearest")
        return image
    end

    -- Render the same model with no passes, then with one pass per blend op.
    -- Identical geometry, identical light, identical everything else.
    local function renderWith(passes)
        item_model_view.clearCache()
        local model = obj_model.load("assets/models/items/silver_blade.obj")
        for _, group in ipairs(model.groups or {}) do
            group.passes = passes
        end
        local canvas = love.graphics.newCanvas(120, 120)
        love.graphics.setCanvas(canvas)
        love.graphics.clear(0, 0, 0, 0)
        item_model_view.draw(0, 0, 120, 120, "assets/models/items/silver_blade.obj",
            "pass_window", "pass_item", 0)
        love.graphics.setCanvas()
        return canvas:newImageData()
    end

    local function summarize(data)
        local covered, luminance = 0, 0
        for py = 0, 119 do
            for px = 0, 119 do
                local r, g, b, a = data:getPixel(px, py)
                if a > 0 then
                    covered = covered + 1
                    luminance = luminance + r + g + b
                end
            end
        end
        return covered, luminance
    end

    local plainCovered, plainLuminance = summarize(renderWith(nil))
    -- Coverage is asserted separately from difference: two blank renders are
    -- also identical, and would read as passes that did nothing. That is
    -- exactly what a leftover scissor once caused here.
    check(plainCovered > 0,
        "The comparison actually rendered the model (" .. plainCovered .. " px covered)")

    local function passOf(blend)
        return { {
            texture = midGreyImage(),
            blend = blend,
            blendId = retro_mesh_shader.BLEND_OPS[blend],
            uvSource = "uv",
            uvSourceId = retro_mesh_shader.UV_SOURCES.uv,
            strength = 1.0,
        } }
    end

    local _, addLuminance = summarize(renderWith(passOf("add")))
    local _, subLuminance = summarize(renderWith(passOf("subtract")))
    local _, mulLuminance = summarize(renderWith(passOf("multiply")))
    local _, screenLuminance = summarize(renderWith(passOf("screen")))

    check(addLuminance > plainLuminance,
        "add brightens the base (" .. math.floor(addLuminance) .. " vs " .. math.floor(plainLuminance) .. ")")
    check(subLuminance < plainLuminance,
        "subtract darkens the base (" .. math.floor(subLuminance) .. " vs " .. math.floor(plainLuminance) .. ")")
    check(mulLuminance < plainLuminance,
        "multiply darkens the base (" .. math.floor(mulLuminance) .. " vs " .. math.floor(plainLuminance) .. ")")
    check(screenLuminance > plainLuminance,
        "screen brightens the base (" .. math.floor(screenLuminance) .. " vs " .. math.floor(plainLuminance) .. ")")
    -- Distinct operations must not merely differ from the default; they must
    -- differ from each other, or a wrong enum mapping passes every check above.
    check(math.abs(subLuminance - mulLuminance) > 1e-3,
        "subtract and multiply are genuinely different operations")
    check(math.abs(addLuminance - screenLuminance) > 1e-3,
        "add and screen are genuinely different operations")

    -- Strength 0 must be exactly the unmodified base, so an authored pass can
    -- be neutralized without removing it.
    local zeroPass = passOf("add")
    zeroPass[1].strength = 0.0
    local _, zeroLuminance = summarize(renderWith(zeroPass))
    check(math.abs(zeroLuminance - plainLuminance) < 1e-3,
        "A pass at strength 0 leaves the base exactly unchanged")

    item_model_view.clearCache()
end


-------------------------------------------------- 7. Shared clip-space coordinate contract --

local clipSpaceShader = retro_mesh_shader.clipSpaceSource()
local worldShader = retro_mesh_shader.buildWorldShader()
local itemShader = retro_mesh_shader.buildItemShader()

check(clipSpaceShader:find("screenYToCanonicalClipY", 1, true) ~= nil
        and clipSpaceShader:find("canonicalClipYToScreenY", 1, true) ~= nil,
    "Shared 3D shader explicitly converts between Y-down screen pixels and canonical Y-up clip space")
check(clipSpaceShader:find("float love11ClipY(float canonicalClipY)", 1, true) ~= nil
        and clipSpaceShader:find("return -canonicalClipY;", 1, true) ~= nil,
    "LÖVE 11.5 Y inversion is isolated as a named legacy runtime handoff")
check(worldShader:find("uniform vec2 playerLightPosition;", 1, true) ~= nil
        and worldShader:find("length(VertexPosition.xy - playerLightPosition)", 1, true) ~= nil
        and worldShader:find("length(relative.xy)", 1, true) == nil,
    "Player light owns an explicit world anchor instead of assuming camera equals player")

check(worldShader:find("float viewportCenterClipY = screenYToCanonicalClipY(viewportCenterY, targetHeight);", 1, true) ~= nil
        and worldShader:find("float ndcY;", 1, true) ~= nil
        and worldShader:find("ndcY = viewportCenterClipY", 1, true) ~= nil
        and worldShader:find("+ vertical / orthoHalfY", 1, true) ~= nil
        and worldShader:find("+ vertical / (fovHalfY * safeDepth)", 1, true) ~= nil,
    "World orthographic and perspective projection both construct canonical Y-up NDC before runtime handoff")
-- Vertex snapping is the one place the renderer leaves canonical Y-up clip
-- space on purpose. It used to be written out inline in both shaders, so both
-- copies had to be checked and either could drift; it is now a single shared
-- function, and the contract is correspondingly stronger: the round trip is
-- declared once, and neither shader may re-implement it.
check(clipSpaceShader:find("vec2 snapToPixelGrid(", 1, true) ~= nil
        and clipSpaceShader:find("canonicalClipYToScreenY(ndc.y, targetSize.y)", 1, true) ~= nil
        and clipSpaceShader:find("screenYToCanonicalClipY(pixelY, targetSize.y)", 1, true) ~= nil,
    "Vertex snapping crosses explicitly into Y-down pixel space and back, in one shared place")
check(worldShader:find("snapToPixelGrid(", 1, true) ~= nil
        and worldShader:find("vertexSnapPixels, compositionOrigin", 1, true) ~= nil,
    "World snapping calls the shared grid anchored at its composition origin")
check(worldShader:find("love11ClipY(ndcY) * safeDepth", 1, true) ~= nil
        and worldShader:find("float viewportTop =", 1, true) == nil,
    "World shader applies the legacy LÖVE 11 conversion only at final clip-space output")
check(itemShader:find("float ndcY = rotZ / halfHeight;", 1, true) ~= nil
        and itemShader:find("float ndcY = -rotZ / halfHeight;", 1, true) == nil,
    "Item-model projection uses the same canonical Y-up NDC convention")
check(itemShader:find("snapToPixelGrid(", 1, true) ~= nil
        and itemShader:find("vertexSnapPixels, vec2(0.0)", 1, true) ~= nil
        and itemShader:find("love11ClipY(ndcY)", 1, true) ~= nil,
    "Item-model snapping calls the shared grid at origin zero, and still ends on the LÖVE 11 handoff")

-- The anti-duplication invariant itself, since prose has already failed here
-- once: neither shader body may carry its own copy of the snapping or dither
-- math. Both blocks were verbatim duplicates differing only by an origin term.
-- Strip both shared blocks: each shader embeds them verbatim, so what remains
-- is only the code that shader wrote for itself.
local function shaderBody(source)
    local body = source
    for _, shared in ipairs({ clipSpaceShader, retro_mesh_shader.sharedSource() }) do
        body = body:gsub(shared:gsub("%p", "%%%0"), "")
    end
    return body
end
for name, source in pairs({ world = worldShader, item = itemShader }) do
    local body = shaderBody(source)
    check(body:find("floor((pixelX", 1, true) == nil
            and body:find("floor(pixelX /", 1, true) == nil,
        name .. " shader does not re-implement pixel snapping inline")
    check(body:find("orderedDither(", 1, true) == nil,
        name .. " shader dithers through the shared quantizer, not its own copy")
end
check(retro_mesh_shader.sharedSource():find("vec3 quantizeWithDither(", 1, true) ~= nil,
    "Ordered-dither quantization is declared once in the shared source")

print("Item model view tests completed: " .. passed .. " passed, " .. failed .. " failed")
if failed > 0 then error("item_model_view tests failed", 0) end
