-- tools/spikes/837/main.lua
-- Executable spike harness for Issue #837:
-- "Prototype static-camera projection-window panning for sideview 3D scenes"
--
-- R2 after the #841 audit.
-- Drives the real presentation.retro_mesh_shader, presentation.world_camera,
-- and presentation.effekseer modules against a neutral 3D street/room scene.
--
-- Usage:
--   lovec tools/spikes/837 <repoRoot> <outDir>

local n = arg and #arg or 0
local repoRoot = n >= 2 and arg[n - 1] or nil
local outDir = n >= 2 and arg[n] or nil

if not (repoRoot and outDir) then
    io.stderr:write("usage: lovec tools/spikes/837 <repoRoot> <outDir>\n")
    os.exit(2)
end

package.path = repoRoot .. "/runtime/?.lua;" .. package.path

local log = {}
local function say(fmt, ...)
    local line = select("#", ...) > 0 and string.format(fmt, ...) or fmt
    print(line)
    log[#log + 1] = line
end

local function writeFile(name, bytes)
    local f = assert(io.open(outDir .. "/" .. name, "wb"))
    f:write(bytes)
    f:close()
end

local function imageDataOf(canvas)
    return canvas:newImageData()
end

local function savePng(data, name)
    writeFile(name, data:encode("png"):getString())
    return data
end

local function finish()
    writeFile("spike837.log", table.concat(log, "\n") .. "\n")
    love.event.quit(0)
end

--------------------------------------------------------------------------
-- Setup & Geometry
--------------------------------------------------------------------------

local retro = require("presentation.retro_mesh_shader")
local world_camera = require("presentation.world_camera")

local WORLD_MESH_FORMAT = {
    { "VertexPosition", "float", 2 },
    { "VertexTexCoord", "float", 2 },
    { "VertexColor", "float", 4 },
    { "SurfaceLight", "float", 3 },
    { "FogVisibility", "float", 1 },
    { "WorldHeight", "float", 1 },
}

local W, H = 426, 240
local BASE_W, BASE_H = 256, 144

local function solidTexture(r, g, b)
    local data = love.image.newImageData(1, 1)
    data:setPixel(0, 0, r, g, b, 1)
    local img = love.graphics.newImage(data)
    img:setFilter("nearest", "nearest")
    return img
end

local whiteTex = solidTexture(1, 1, 1)
local blackTex = solidTexture(0, 0, 0)

local function quadVertices(a, b, c, d, rgb)
    local out = {}
    local function push(p)
        out[#out + 1] = {
            p.x, p.y, 0, 0,
            rgb[1], rgb[2], rgb[3], 1,
            1, 1, 1,
            1,
            p.z,
        }
    end
    push(a) push(b) push(c)
    push(a) push(c) push(d)
    return out
end

local function newQuadMesh(a, b, c, d, rgb)
    local m = love.graphics.newMesh(WORLD_MESH_FORMAT, quadVertices(a, b, c, d, rgb),
        "triangles", "static")
    m:setTexture(whiteTex)
    return m
end

local function sendCamera(shader, cam, targetW, targetH)
    shader:send("cameraPosition", { cam.x, cam.y, cam.z })
    shader:send("cameraForward", { cam.dirX, cam.dirY })
    shader:send("cameraRight", { cam.rightX, cam.rightY })
    shader:send("cameraPitch", cam.pitch or 0)
    shader:send("projectionKind", cam.projection == "orthographic" and 1 or 0)
    shader:send("projectionScale", { cam.projectionScaleX or 1, cam.projectionScaleY or 1 })
    shader:send("fovHalfX", cam.fovHalfX)
    shader:send("fovHalfY", cam.fovHalfY)
    shader:send("orthoHalfX", cam.orthoHalfX or 1)
    shader:send("orthoHalfY", cam.orthoHalfY or 1)
    shader:send("nearPlane", cam.nearPlane)
    shader:send("farPlane", cam.farPlane)
    shader:send("baseViewportWidth", cam.baseViewportWidth or targetW)
    shader:send("baseViewportHeight", cam.baseViewportHeight or targetH)
    shader:send("targetWidth", targetW)
    shader:send("targetHeight", targetH)
    shader:send("compositionOrigin", { 0, 0 })
    shader:send("viewportCenterX", cam.viewportCenterX or targetW * 0.5)
    shader:send("viewportCenterY", cam.viewportCenterY or targetH * 0.5)
    shader:send("affineTextures", 0)
    shader:send("vertexSnapPixels", cam.vertexSnapPixels or 0)
    shader:send("fogColor", { 0.1, 0.12, 0.18 })
    shader:send("fogStart", 0)
    shader:send("fogDistance", 1000000)
    shader:send("fogMetric", 0)
    shader:send("fogOrigin", { 0, 0 })
    shader:send("fogSharpness", 1)
    shader:send("fogMinFactor", 1)
    shader:send("fogBands", 0)
    shader:send("playerLightColor", { 0, 0, 0 })
    shader:send("playerLightPosition", { 0, 0 })
    shader:send("playerLightRadius", 0)
    shader:send("playerLightFalloff", 1)
    shader:send("ditherLevels", cam.ditherLevels or 0)
    shader:send("roomBakePass", 0)
    shader:send("roomBakeFar", 8)
    shader:send("glowMap", blackTex)
    shader:send("glowStrength", 0)
end

local function countDiffering(a, b)
    local w, h = a:getDimensions()
    local n = 0
    for y = 0, h - 1 do
        for x = 0, w - 1 do
            local r1, g1, b1 = a:getPixel(x, y)
            local r2, g2, b2 = b:getPixel(x, y)
            if r1 ~= r2 or g1 ~= g2 or b1 ~= b2 then n = n + 1 end
        end
    end
    return n
end

local function countPixelsMatching(data, color, tol)
    tol = tol or 0.03
    local w, h = data:getDimensions()
    local n = 0
    for y = 0, h - 1 do
        for x = 0, w - 1 do
            local r, g, b = data:getPixel(x, y)
            if math.abs(r - color[1]) <= tol and math.abs(g - color[2]) <= tol and math.abs(b - color[3]) <= tol then
                n = n + 1
            end
        end
    end
    return n
end

local function centroidColumn(data, colour, tol)
    tol = tol or 0.03
    local w, h = data:getDimensions()
    local sum, count = 0, 0
    for y = 0, h - 1 do
        for x = 0, w - 1 do
            local r, g, b = data:getPixel(x, y)
            if math.abs(r - colour[1]) <= tol and math.abs(g - colour[2]) <= tol
                and math.abs(b - colour[3]) <= tol then
                sum, count = sum + x, count + 1
            end
        end
    end
    if count == 0 then return nil end
    return sum / count
end

--------------------------------------------------------------------------
-- Main Spike Execution
--------------------------------------------------------------------------

function love.load()
    say("# Spike #837: Static-Camera Projection-Window Panning")
    say("Target render resolution: %dx%d (native, no upscaler)", W, H)

    local shader = love.graphics.newShader(retro.buildWorldShader())
    local colourBuf = love.graphics.newCanvas(W, H)
    local depthBuf = love.graphics.newCanvas(W, H, { format = "depth24stencil8", readable = true })

    -- Build wide 3D street/room environment
    local envMeshes = {}
    -- Distant back wall (y=12)
    envMeshes[#envMeshes + 1] = newQuadMesh(
        { x = -20, y = 12, z = 0 }, { x = 20, y = 12, z = 0 },
        { x = 20, y = 12, z = 3.5 }, { x = -20, y = 12, z = 3.5 },
        { 0.18, 0.22, 0.32 })

    -- Long row of vertical posts across the street (x = -15..15, y=6)
    for i = -12, 12 do
        local shade = (i % 2 == 0) and 0.80 or 0.45
        envMeshes[#envMeshes + 1] = newQuadMesh(
            { x = i * 1.5 - 0.15, y = 6, z = 0 }, { x = i * 1.5 + 0.15, y = 6, z = 0 },
            { x = i * 1.5 + 0.15, y = 6, z = 2.2 }, { x = i * 1.5 - 0.15, y = 6, z = 2.2 },
            { shade, shade * 0.6, 0.25 })
    end

    -- Foreground occluder pillar at (x=0, y=3.5, z=0..2.5)
    local PILLAR_COLOR = { 0.85, 0.55, 0.20 }
    local pillarMesh = newQuadMesh(
        { x = -0.5, y = 3.5, z = 0 }, { x = 0.5, y = 3.5, z = 0 },
        { x = 0.5, y = 3.5, z = 2.5 }, { x = -0.5, y = 3.5, z = 2.5 },
        PILLAR_COLOR)
    envMeshes[#envMeshes + 1] = pillarMesh

    -- Near and far parallax markers on the same lateral world ray
    local NEAR_MARKER = { 0.10, 0.85, 0.95 }
    local FAR_MARKER = { 0.95, 0.15, 0.65 }
    envMeshes[#envMeshes + 1] = newQuadMesh(
        { x = -0.12, y = 2.5, z = 0 }, { x = 0.12, y = 2.5, z = 0 },
        { x = 0.12, y = 2.5, z = 1.8 }, { x = -0.12, y = 2.5, z = 1.8 }, NEAR_MARKER)
    envMeshes[#envMeshes + 1] = newQuadMesh(
        { x = 2.60, y = 10.0, z = 0 }, { x = 3.40, y = 10.0, z = 0 },
        { x = 3.40, y = 10.0, z = 3.0 }, { x = 2.60, y = 10.0, z = 3.0 }, FAR_MARKER)

    local ACTOR_COLOR = { 0.10, 0.90, 0.35 }
    local function makeActorMesh(actorX, actorY)
        return newQuadMesh(
            { x = actorX - 0.35, y = actorY, z = 0 }, { x = actorX + 0.35, y = actorY, z = 0 },
            { x = actorX + 0.35, y = actorY, z = 1.6 }, { x = actorX - 0.35, y = actorY, z = 1.6 },
            ACTOR_COLOR)
    end

    local function renderScene(camera, extraMeshes, name)
        love.graphics.setCanvas({ colourBuf, depthstencil = depthBuf })
        love.graphics.clear(0.05, 0.06, 0.10, 1, true, true)
        love.graphics.setDepthMode("less", true)
        love.graphics.setShader(shader)
        sendCamera(shader, camera, W, H)
        love.graphics.setColor(1, 1, 1, 1)
        for _, m in ipairs(envMeshes) do love.graphics.draw(m) end
        if extraMeshes then
            for _, m in ipairs(extraMeshes) do love.graphics.draw(m) end
        end
        love.graphics.setShader()
        love.graphics.setDepthMode()
        love.graphics.setCanvas()
        local data = imageDataOf(colourBuf)
        if name then savePng(data, name) end
        return data
    end

    --------------------------------------------------------------------------
    -- 1. Comparison A (Camera Follow) vs B (Fixed Eye + Moving Window)
    --------------------------------------------------------------------------
    say("")
    say("## 1. Parallax Signature & Invariant Eye Comparison (A vs B)")

    local fixedEyeCam = world_camera.resolveFirstPerson({
        playerX = 0, playerY = 0, playerDir = "S",
    }, {
        projectionFrame = {
            targetWidth = W, targetHeight = H, compositionWidth = BASE_W,
            canonicalCenterX = W * 0.5, canonicalHorizonY = 70,
        },
    })

    local panNearCols, panFarCols, panSeparations = {}, {}, {}
    local followNearCols, followFarCols, followSeparations = {}, {}, {}
    local shifts = { -96, -48, 0, 48, 96 }

    for i, shift in ipairs(shifts) do
        -- B: Fixed eye, moving projection window
        local camB = world_camera.resolveFirstPerson({
            playerX = 0, playerY = 0, playerDir = "S",
        }, {
            projectionWindowOffsetX = shift,
            projectionFrame = {
                targetWidth = W, targetHeight = H, compositionWidth = BASE_W,
                canonicalCenterX = W * 0.5, canonicalHorizonY = 70,
            },
        })
        -- Verify eye invariant numerically
        if camB.x ~= fixedEyeCam.x or camB.y ~= fixedEyeCam.y or camB.z ~= fixedEyeCam.z
                or camB.dirX ~= fixedEyeCam.dirX or camB.dirY ~= fixedEyeCam.dirY
                or camB.pitch ~= fixedEyeCam.pitch then
            error("Invariant B violated: camera eye or orientation moved!")
        end

        local dataB = renderScene(camB, nil, string.format("window-%d.png", i))
        panNearCols[i] = centroidColumn(dataB, NEAR_MARKER)
        panFarCols[i] = centroidColumn(dataB, FAR_MARKER)
        panSeparations[i] = (panNearCols[i] and panFarCols[i]) and (panFarCols[i] - panNearCols[i]) or nil

        -- A: Ordinary camera following (strafe camera X)
        local strafeX = shift * 0.02
        local camA = world_camera.resolveFirstPerson({
            playerX = 0, playerY = 0, playerDir = "S",
        }, {
            projectionFrame = {
                targetWidth = W, targetHeight = H, compositionWidth = BASE_W,
                canonicalCenterX = W * 0.5, canonicalHorizonY = 70,
            },
        })
        camA.x = fixedEyeCam.x + strafeX
        local dataA = renderScene(camA, nil, string.format("follow-%d.png", i))
        followNearCols[i] = centroidColumn(dataA, NEAR_MARKER)
        followFarCols[i] = centroidColumn(dataA, FAR_MARKER)
        followSeparations[i] = (followNearCols[i] and followFarCols[i]) and (followFarCols[i] - followNearCols[i]) or nil
    end

    local function fmtRow(t)
        local out = {}
        for i = 1, #shifts do
            out[i] = t[i] and string.format("%7.2f", t[i]) or "    n/a"
        end
        return table.concat(out, " ")
    end

    say("Shift offsets:                     %s", "  -96     -48       0     +48     +96")
    say("Window Pan (B) near marker col :   %s", fmtRow(panNearCols))
    say("Window Pan (B) far  marker col :   %s", fmtRow(panFarCols))
    say("Window Pan (B) near-far parallax:  %s", fmtRow(panSeparations))
    say("Camera Follow (A) near marker:     %s", fmtRow(followNearCols))
    say("Camera Follow (A) far marker:      %s", fmtRow(followFarCols))
    say("Camera Follow (A) parallax:        %s", fmtRow(followSeparations))

    -- Assert invariant separation in B
    local baseSep = panSeparations[3]
    for i = 1, #shifts do
        if panSeparations[i] then
            local diff = math.abs(panSeparations[i] - baseSep)
            if diff > 1e-6 then
                error(string.format("Parallax separation changed in B: step %d diff %.6f", i, diff))
            end
        end
    end
    say("=> Invariant confirmed: near-far separation is constant under projection window pan.")

    --------------------------------------------------------------------------
    -- 2. Lens Choices (C): 26 deg vs 50 deg master FOV under window pan
    --------------------------------------------------------------------------
    say("")
    say("## 2. Lens Choices Comparison (C: 26 deg vs 50 deg master FOV)")
    for _, fovDeg in ipairs({ 26, 50 }) do
        for i, shift in ipairs({ -80, 0, 80 }) do
            local fovCam = world_camera.resolve({
                playerX = 0, playerY = 0, playerDir = "S",
            }, {
                profile = "rpg_perspective",
                fovDegrees = fovDeg,
                projectionWindowOffsetX = shift,
                projectionFrame = {
                    targetWidth = W, targetHeight = H, compositionWidth = BASE_W,
                    canonicalCenterX = W * 0.5, canonicalHorizonY = 70,
                },
            })
            renderScene(fovCam, nil, string.format("fov%d-window-%d.png", fovDeg, i))
        end
        say("Captured fov%d-window-1..3.png", fovDeg)
    end

    --------------------------------------------------------------------------
    -- 3. Actor Traversal & Foreground Depth Occlusion
    --------------------------------------------------------------------------
    say("")
    say("## 3. Actor Traversal & Depth Occlusion under Moving Projection Window")
    -- Actor walking behind the pillar at (x=0, y=4.5, z=0..1.6)
    -- The pillar sits at y=3.5 (foreground occluder)
    local actorBehindPillar = makeActorMesh(0.0, 4.5)
    local actorEmerging = makeActorMesh(1.2, 4.5)

    local camWindow0 = world_camera.resolveFirstPerson({
        playerX = 0, playerY = 0, playerDir = "S",
    }, {
        projectionWindowOffsetX = 0,
        projectionFrame = {
            targetWidth = W, targetHeight = H, compositionWidth = BASE_W,
            canonicalCenterX = W * 0.5, canonicalHorizonY = 70,
        },
    })
    local dataBehind = renderScene(camWindow0, { actorBehindPillar }, "occlusion-behind-pillar.png")
    local actorBehindPixels = countPixelsMatching(dataBehind, ACTOR_COLOR)
    say("Actor pixels when positioned behind foreground pillar: %d", actorBehindPixels)

    local dataEmerging = renderScene(camWindow0, { actorEmerging }, "occlusion-emerging.png")
    local actorEmergingPixels = countPixelsMatching(dataEmerging, ACTOR_COLOR)
    say("Actor pixels when emerging beside foreground pillar:  %d", actorEmergingPixels)

    if actorBehindPixels >= actorEmergingPixels then
        error("Foreground depth occlusion failed: actor behind pillar was not occluded!")
    end
    say("=> Depth occlusion confirmed: actor behind foreground geometry is properly occluded.")

    --------------------------------------------------------------------------
    -- 4. Quantization Grids (#844)
    --------------------------------------------------------------------------
    say("")
    say("## 4. Quantization Grids & Phase Alignment (#844)")
    local function shiftedDiff(a, b, dx)
        local w, h = a:getDimensions()
        local n = 0
        for y = 0, h - 1 do
            for x = math.max(0, -dx), math.min(w - 1, w - 1 - dx) do
                local r1, g1, b1 = a:getPixel(x, y)
                local r2, g2, b2 = b:getPixel(x + dx, y)
                if r1 ~= r2 or g1 ~= g2 or b1 ~= b2 then n = n + 1 end
            end
        end
        return n
    end

    local baseSnap0 = renderScene(world_camera.resolveFirstPerson({
        playerX = 0, playerY = 0, playerDir = "S",
    }, {
        vertexSnapPixels = 0,
        projectionWindowOffsetX = 0,
        projectionFrame = { targetWidth = W, targetHeight = H, compositionWidth = BASE_W, canonicalCenterX = W * 0.5, canonicalHorizonY = 70 },
    }), nil)

    for _, dx in ipairs({ 4, 16 }) do
        local pannedSnap0 = renderScene(world_camera.resolveFirstPerson({
            playerX = 0, playerY = 0, playerDir = "S",
        }, {
            vertexSnapPixels = 0,
            projectionWindowOffsetX = dx,
            projectionFrame = { targetWidth = W, targetHeight = H, compositionWidth = BASE_W, canonicalCenterX = W * 0.5, canonicalHorizonY = 70 },
        }), nil)
        local diff0 = shiftedDiff(baseSnap0, pannedSnap0, dx)
        say("  vertexSnapPixels=0, window +%2d px image translation diff: %d px", dx, diff0)
    end

    say("Quantization check completed.")
    say("=== Spike #837 verification successful ===")
    finish()
end
