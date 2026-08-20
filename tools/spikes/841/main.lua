-- Spike harness for the #841 world-presentation and spatial-ownership audit.
--
-- READ-ONLY with respect to the production runtime: it requires real modules
-- (presentation.retro_mesh_shader, presentation.effekseer) off the repository's
-- runtime/ directory and drives them from its own scene. It edits nothing and
-- is wired into no gate.
--
--   lovec tools/spikes/841 <repoRoot> <outDir> <case>
--
-- cases: capability | temporal | projection | cost

-- LOVE puts the game directory in arg[1], so the spike's own three arguments
-- are the LAST three entries rather than the first three.
local n = arg and #arg or 0
local repoRoot = n >= 3 and arg[n - 2] or nil
local outDir = n >= 3 and arg[n - 1] or nil
local case = n >= 3 and arg[n] or nil

if not (repoRoot and outDir and case) then
    io.stderr:write("usage: lovec tools/spikes/841 <repoRoot> <outDir> <case>\n")
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
    writeFile(case .. ".log", table.concat(log, "\n") .. "\n")
    love.event.quit(0)
end

--------------------------------------------------------------------------
-- shared geometry helpers
--------------------------------------------------------------------------

local retro = require("presentation.retro_mesh_shader")

local WORLD_MESH_FORMAT = {
    { "VertexPosition", "float", 2 },
    { "VertexTexCoord", "float", 2 },
    { "VertexColor", "float", 4 },
    { "SurfaceLight", "float", 3 },
    { "FogVisibility", "float", 1 },
    { "WorldHeight", "float", 1 },
}

local W, H = 256, 240

local function solidTexture(r, g, b)
    local data = love.image.newImageData(1, 1)
    data:setPixel(0, 0, r, g, b, 1)
    local img = love.graphics.newImage(data)
    img:setFilter("nearest", "nearest")
    return img
end

local whiteTex, blackTex

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

-- The production uniform set, sent exactly as viewport_3d sends it.
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
    shader:send("fogColor", { 0, 0, 0 })
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
    shader:send("ditherLevels", 0)
    shader:send("roomBakePass", 0)
    shader:send("roomBakeFar", 8)
    shader:send("glowMap", blackTex)
    shader:send("glowStrength", 0)
end

local function makeCamera(opts)
    opts = opts or {}
    local angle = opts.angle or 0
    return {
        projection = "perspective",
        x = opts.x or 0, y = opts.y or 0, z = opts.z or 0.5,
        angle = angle,
        dirX = math.cos(angle), dirY = math.sin(angle),
        rightX = -math.sin(angle), rightY = math.cos(angle),
        pitch = opts.pitch or 0,
        fovHalfX = opts.fovHalfX or 0.75,
        fovHalfY = opts.fovHalfY or 0.421875,
        orthoHalfX = 1, orthoHalfY = 1,
        projectionScaleX = 1, projectionScaleY = 1,
        nearPlane = 0.05, farPlane = 64.0,
        viewportCenterX = opts.viewportCenterX,
        viewportCenterY = opts.viewportCenterY,
        baseViewportWidth = opts.baseViewportWidth,
        baseViewportHeight = opts.baseViewportHeight,
        vertexSnapPixels = opts.vertexSnapPixels or 0,
    }
end

--------------------------------------------------------------------------
-- pixel helpers
--------------------------------------------------------------------------

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

-- Pixels that are neither of the declared source colours: evidence that a
-- coverage-blended value exists somewhere in the image.
local function countBlended(data, colours, tol)
    local w, h = data:getDimensions()
    local n = 0
    for y = 0, h - 1 do
        for x = 0, w - 1 do
            local r, g, b = data:getPixel(x, y)
            local matched = false
            for _, c in ipairs(colours) do
                if math.abs(r - c[1]) <= tol and math.abs(g - c[2]) <= tol
                    and math.abs(b - c[3]) <= tol then
                    matched = true
                    break
                end
            end
            if not matched then n = n + 1 end
        end
    end
    return n, w * h
end

local function countPartialAlpha(data)
    local w, h = data:getDimensions()
    local n = 0
    for y = 0, h - 1 do
        for x = 0, w - 1 do
            local _, _, _, a = data:getPixel(x, y)
            if a > 0.02 and a < 0.98 then n = n + 1 end
        end
    end
    return n
end

local function countOpaque(data)
    local w, h = data:getDimensions()
    local n = 0
    for y = 0, h - 1 do
        for x = 0, w - 1 do
            local _, _, _, a = data:getPixel(x, y)
            if a > 0.5 then n = n + 1 end
        end
    end
    return n
end

local function firstColumnMatching(data, row, predicate)
    for x = 0, data:getWidth() - 1 do
        local r, g, b, a = data:getPixel(x, row)
        if predicate(r, g, b, a) then return x end
    end
    return nil
end

--------------------------------------------------------------------------
-- CASE: capability
--------------------------------------------------------------------------

local function caseCapability()
    say("# LOVE 11.5 colour/depth/MSAA capability probe")
    local maj, min, rev, code = love.getVersion()
    say("love version: %d.%d.%d (%s)", maj, min, rev, tostring(code))
    local rname, rvendor, rdevice, rver = love.graphics.getRendererInfo()
    say("renderer: %s | %s | %s | %s",
        tostring(rname), tostring(rvendor), tostring(rdevice), tostring(rver))
    local formats = love.graphics.getCanvasFormats()
    for _, f in ipairs({ "depth16", "depth24", "depth32f",
        "depth24stencil8", "depth32fstencil8", "stencil8" }) do
        say("canvas format %-18s supported=%s", f, tostring(formats[f] == true))
    end
    say("system limit canvasmsaa: %s", tostring(love.graphics.getSystemLimits().canvasmsaa))

    local shader = love.graphics.newShader(retro.buildWorldShader())

    -- One room: a far back wall, a nearer pillar, and an actor that straddles
    -- the pillar's depth so half of it must be culled by retained depth.
    local back = newQuadMesh({ x = -6, y = 8, z = 0 }, { x = 6, y = 8, z = 0 },
        { x = 6, y = 8, z = 2 }, { x = -6, y = 8, z = 2 }, { 0.25, 0.30, 0.45 })
    local pillar = newQuadMesh({ x = -0.6, y = 3, z = 0 }, { x = 0.6, y = 3, z = 0 },
        { x = 0.6, y = 3, z = 2 }, { x = -0.6, y = 3, z = 2 }, { 0.85, 0.55, 0.20 })
    local actorFar = newQuadMesh({ x = -1.6, y = 3.6, z = 0 }, { x = 1.6, y = 3.6, z = 0 },
        { x = 1.6, y = 3.6, z = 1.2 }, { x = -1.6, y = 3.6, z = 1.2 }, { 0.10, 0.90, 0.35 })

    local cam = makeCamera({ x = 0, y = 0, z = 1.0, angle = math.pi / 2 })

    local function drawWorld(meshes, targetW, targetH)
        love.graphics.setShader(shader)
        sendCamera(shader, cam, targetW or W, targetH or H)
        love.graphics.setColor(1, 1, 1, 1)
        love.graphics.setBlendMode("alpha")
        for _, m in ipairs(meshes) do love.graphics.draw(m) end
        love.graphics.setShader()
    end

    local ENV_COLOURS = { { 0.25, 0.30, 0.45 }, { 0.85, 0.55, 0.20 }, { 0, 0, 0 } }

    ---------------------------------------------------------------- 1
    say("")
    say("## 1. A depth attachment can be created and bound")
    local envColor = love.graphics.newCanvas(W, H)
    local okDepth, depthCanvas = pcall(love.graphics.newCanvas, W, H,
        { format = "depth24stencil8", readable = true })
    say("newCanvas depth24stencil8 readable=true : ok=%s", tostring(okDepth))
    if not okDepth then
        okDepth, depthCanvas = pcall(love.graphics.newCanvas, W, H,
            { format = "depth24stencil8" })
        say("  fallback (readable unset)            : ok=%s", tostring(okDepth))
    end
    assert(okDepth, "no usable depth canvas format: " .. tostring(depthCanvas))

    love.graphics.setCanvas({ envColor, depthstencil = depthCanvas })
    love.graphics.clear(0, 0, 0, 1, true, true)
    love.graphics.setDepthMode("less", true)
    drawWorld({ back, pillar })
    love.graphics.setDepthMode()
    love.graphics.setCanvas()
    savePng(imageDataOf(envColor), "capability-1-environment.png")
    say("environment pass rendered -> capability-1-environment.png")

    ---------------------------------------------------------------- 2
    say("")
    say("## 2. The SAME depth attachment re-bound to a DIFFERENT colour target")
    local actorColor = love.graphics.newCanvas(W, H)
    love.graphics.setCanvas({ actorColor, depthstencil = depthCanvas })
    love.graphics.clear(0, 0, 0, 0, false, false) -- deliberately keep pass 1 depth
    love.graphics.setDepthMode("less", false)     -- test, never write
    drawWorld({ actorFar })
    love.graphics.setDepthMode()
    love.graphics.setCanvas()
    local actorData = savePng(imageDataOf(actorColor), "capability-2-actor-only.png")
    say("actor pixels surviving the RETAINED depth test: %d", countOpaque(actorData))
    say("partial-alpha pixels in that mask            : %d", countPartialAlpha(actorData))

    -- Negative control: the same actor with depth testing disabled.
    local actorNoDepth = love.graphics.newCanvas(W, H)
    love.graphics.setCanvas(actorNoDepth)
    love.graphics.clear(0, 0, 0, 0)
    drawWorld({ actorFar })
    love.graphics.setCanvas()
    local noDepthData = savePng(imageDataOf(actorNoDepth), "capability-2-actor-nodepth.png")
    say("NEGATIVE CONTROL, depth test off             : %d", countOpaque(noDepthData))
    say("(the difference is the pillar's occlusion; equal counts would mean the")
    say(" retained depth attachment was NOT actually consulted)")

    ---------------------------------------------------------------- 3
    say("")
    say("## 3. Composite of environment colour + depth-tested actor")
    local composite = love.graphics.newCanvas(W, H)
    love.graphics.setCanvas(composite)
    love.graphics.clear(0, 0, 0, 1)
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.setBlendMode("alpha", "premultiplied")
    love.graphics.draw(envColor)
    love.graphics.draw(actorColor)
    love.graphics.setBlendMode("alpha")
    love.graphics.setCanvas()
    local compData = savePng(imageDataOf(composite), "capability-3-composite.png")
    local blended, total = countBlended(compData,
        { { 0.25, 0.30, 0.45 }, { 0.85, 0.55, 0.20 }, { 0.10, 0.90, 0.35 }, { 0, 0, 0 } }, 0.02)
    say("non-source-colour pixels in the composite: %d / %d", blended, total)

    ---------------------------------------------------------------- 4
    say("")
    say("## 4. Post-processing the environment COLOUR leaves depth pristine")
    local degrade = love.graphics.newShader([[
        uniform float levels;
        vec4 effect(vec4 c, Image t, vec2 uv, vec2 sc) {
            vec4 texel = Texel(t, uv);
            return vec4(floor(texel.rgb * levels + 0.5) / levels, texel.a) * c;
        }
    ]])
    degrade:send("levels", 4.0)
    local degraded = love.graphics.newCanvas(W, H)
    love.graphics.setCanvas(degraded)
    love.graphics.clear(0, 0, 0, 1)
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.setShader(degrade)
    love.graphics.draw(envColor)
    love.graphics.setShader()
    love.graphics.setCanvas()
    savePng(imageDataOf(degraded), "capability-4-degraded-environment.png")

    local actorColor2 = love.graphics.newCanvas(W, H)
    love.graphics.setCanvas({ actorColor2, depthstencil = depthCanvas })
    love.graphics.clear(0, 0, 0, 0, false, false)
    love.graphics.setDepthMode("less", false)
    drawWorld({ actorFar })
    love.graphics.setDepthMode()
    love.graphics.setCanvas()
    say("actor mask before vs after the colour post-process: %d differing px",
        countDiffering(actorData, imageDataOf(actorColor2)))

    ---------------------------------------------------------------- 5
    say("")
    say("## 5. MSAA")
    local msaaLimit = love.graphics.getSystemLimits().canvasmsaa or 0
    local samples = math.min(4, msaaLimit)
    say("requested msaa samples: %d", samples)
    local okMsaaColor, msaaColor = pcall(love.graphics.newCanvas, W, H, { msaa = samples })
    say("msaa colour canvas (msaa=%d)                : ok=%s %s", samples,
        tostring(okMsaaColor), okMsaaColor and "" or tostring(msaaColor))
    local okMsaaDepth, msaaDepth = pcall(love.graphics.newCanvas, W, H,
        { format = "depth24stencil8", msaa = samples, readable = true })
    say("msaa depth canvas, readable=true            : ok=%s %s",
        tostring(okMsaaDepth), okMsaaDepth and "" or tostring(msaaDepth))
    if not okMsaaDepth then
        okMsaaDepth, msaaDepth = pcall(love.graphics.newCanvas, W, H,
            { format = "depth24stencil8", msaa = samples })
        say("msaa depth canvas, readable unset           : ok=%s %s",
            tostring(okMsaaDepth), okMsaaDepth and "" or tostring(msaaDepth))
    end
    if not okMsaaDepth then
        okMsaaDepth, msaaDepth = pcall(love.graphics.newCanvas, W, H,
            { format = "depth24stencil8", msaa = samples, readable = false })
        say("msaa depth canvas, readable=false           : ok=%s %s",
            tostring(okMsaaDepth), okMsaaDepth and "" or tostring(msaaDepth))
    end

    local okPair, pairErr = false, nil
    if okMsaaColor and okMsaaDepth then
        okPair, pairErr = pcall(function()
            love.graphics.setCanvas({ msaaColor, depthstencil = msaaDepth })
            love.graphics.clear(0, 0, 0, 1, true, true)
            love.graphics.setDepthMode("less", true)
            drawWorld({ back, pillar })
            love.graphics.setDepthMode()
            love.graphics.setCanvas()
        end)
    end
    love.graphics.setCanvas()
    say("bind msaa colour + msaa depth               : ok=%s %s",
        tostring(okPair), okPair and "" or tostring(pairErr))

    local okMismatch = false
    if okMsaaColor then
        okMismatch = pcall(function()
            love.graphics.setCanvas({ msaaColor, depthstencil = depthCanvas })
            love.graphics.setCanvas()
        end)
    end
    love.graphics.setCanvas()
    say("bind msaa colour + NON-msaa depth           : ok=%s", tostring(okMismatch))

    if okPair then
        local resolved = love.graphics.newCanvas(W, H)
        love.graphics.setCanvas(resolved)
        love.graphics.clear(0, 0, 0, 1)
        love.graphics.setColor(1, 1, 1, 1)
        love.graphics.draw(msaaColor)
        love.graphics.setCanvas()
        local resolvedData = savePng(imageDataOf(resolved), "capability-5-msaa-environment.png")
        local msaaBlend = countBlended(resolvedData, ENV_COLOURS, 0.02)
        say("MSAA environment: coverage-blended pixels = %d", msaaBlend)

        local okActorMsaa, actorMsaaCanvas = pcall(love.graphics.newCanvas, W, H, { msaa = samples })
        local drewActor = false
        if okActorMsaa then
            drewActor = pcall(function()
                love.graphics.setCanvas({ actorMsaaCanvas, depthstencil = msaaDepth })
                love.graphics.clear(0, 0, 0, 0, false, false)
                love.graphics.setDepthMode("less", false)
                drawWorld({ actorFar })
                love.graphics.setDepthMode()
                love.graphics.setCanvas()
            end)
        end
        love.graphics.setCanvas()
        say("actor pass against the MSAA depth attachment: ok=%s", tostring(drewActor))
        if drewActor then
            local resolvedActor = love.graphics.newCanvas(W, H)
            love.graphics.setCanvas(resolvedActor)
            love.graphics.clear(0, 0, 0, 0)
            love.graphics.setColor(1, 1, 1, 1)
            love.graphics.draw(actorMsaaCanvas)
            love.graphics.setCanvas()
            local rad = savePng(imageDataOf(resolvedActor), "capability-5-msaa-actor.png")
            say("actor-mask pixels with PARTIAL alpha after resolve: %d",
                countPartialAlpha(rad))
            say("(non-zero => the pass-ownership boundary is coverage-blended,")
            say(" which is exactly what #836 forbids)")
        end
    end

    ---------------------------------------------------------------- 6
    say("")
    say("## 6. Is the depth attachment sampleable as a texture?")
    local okSampleMode = pcall(function() depthCanvas:setDepthSampleMode() end)
    say("depthCanvas:setDepthSampleMode() : ok=%s", tostring(okSampleMode))
    local okShaderRead, shaderReadErr = pcall(function()
        local s = love.graphics.newShader([[
            uniform Image envDepth;
            vec4 effect(vec4 c, Image t, vec2 uv, vec2 sc) {
                return vec4(vec3(Texel(envDepth, uv).r), 1.0);
            }
        ]])
        s:send("envDepth", depthCanvas)
        local probe = love.graphics.newCanvas(W, H)
        love.graphics.setCanvas(probe)
        love.graphics.clear(0, 0, 0, 1)
        love.graphics.setColor(1, 1, 1, 1)
        love.graphics.setShader(s)
        love.graphics.draw(envColor)
        love.graphics.setShader()
        love.graphics.setCanvas()
        savePng(imageDataOf(probe), "capability-6-depth-as-texture.png")
    end)
    love.graphics.setCanvas()
    love.graphics.setShader()
    say("sampling the depth canvas in a shader: ok=%s %s",
        tostring(okShaderRead), okShaderRead and "" or tostring(shaderReadErr))

    ---------------------------------------------------------------- 7
    say("")
    say("## 7. Supersample-then-downsample as the alternative AA location")
    local SS = 3
    local ssColor = love.graphics.newCanvas(W * SS, H * SS)
    local ssDepth = love.graphics.newCanvas(W * SS, H * SS,
        { format = "depth24stencil8", readable = true })
    love.graphics.setCanvas({ ssColor, depthstencil = ssDepth })
    love.graphics.clear(0, 0, 0, 1, true, true)
    love.graphics.setDepthMode("less", true)
    drawWorld({ back, pillar }, W * SS, H * SS)
    love.graphics.setDepthMode()
    love.graphics.setCanvas()

    -- NEGATIVE CONTROL for the downsample itself: drawing the big canvas at
    -- 1/SS with linear filtering POINT-samples one texel per output pixel.
    -- It looks like a downsample and anti-aliases nothing.
    local naive = love.graphics.newCanvas(W, H)
    ssColor:setFilter("linear", "linear")
    love.graphics.setCanvas(naive)
    love.graphics.clear(0, 0, 0, 1)
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.draw(ssColor, 0, 0, 0, 1 / SS, 1 / SS)
    love.graphics.setCanvas()
    local naiveData = savePng(imageDataOf(naive), "capability-7-naive-rescale.png")
    say("naive draw-at-1/%d with linear filter : blended pixels = %d", SS,
        countBlended(naiveData, ENV_COLOURS, 0.02))
    say("(zero => LOVE's linear filter is not a box filter; scaling down does")
    say(" NOT average the SS x SS block, so this is not supersampling at all)")

    local boxShader = love.graphics.newShader([[
        uniform vec2 sourceTexel;
        uniform float taps;
        vec4 effect(vec4 c, Image t, vec2 uv, vec2 sc) {
            vec4 sum = vec4(0.0);
            for (int y = 0; y < 8; y++) {
                if (float(y) >= taps) break;
                for (int x = 0; x < 8; x++) {
                    if (float(x) >= taps) break;
                    sum += Texel(t, uv + vec2(
                        (float(x) + 0.5) * sourceTexel.x,
                        (float(y) + 0.5) * sourceTexel.y));
                }
            }
            return (sum / (taps * taps)) * c;
        }
    ]])
    boxShader:send("sourceTexel", { 1 / (W * SS), 1 / (H * SS) })
    boxShader:send("taps", SS)
    local downs = love.graphics.newCanvas(W, H)
    ssColor:setFilter("nearest", "nearest")
    love.graphics.setCanvas(downs)
    love.graphics.clear(0, 0, 0, 1)
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.setShader(boxShader)
    love.graphics.draw(ssColor, 0, 0, 0, 1 / SS, 1 / SS)
    love.graphics.setShader()
    love.graphics.setCanvas()
    local downData = savePng(imageDataOf(downs), "capability-7-supersampled-environment.png")
    local ssBlend = countBlended(downData, ENV_COLOURS, 0.02)
    say("explicit %dx%d box downsample        : blended pixels = %d", SS, SS, ssBlend)
    say("NOTE: that pass's depth attachment is %dx%d, so it is NOT reusable as",
        W * SS, H * SS)
    say("the native-resolution actor depth without a second native-scale pass.")

    ---------------------------------------------------------------- 8
    say("")
    say("## 8. AA'd environment colour + native-resolution depth mask")
    local nativeDepth = love.graphics.newCanvas(W, H,
        { format = "depth24stencil8", readable = true })
    local scratch = love.graphics.newCanvas(W, H)
    love.graphics.setCanvas({ scratch, depthstencil = nativeDepth })
    love.graphics.clear(0, 0, 0, 1, true, true)
    love.graphics.setDepthMode("less", true)
    drawWorld({ back, pillar })
    love.graphics.setDepthMode()
    love.graphics.setCanvas()

    local actorHard = love.graphics.newCanvas(W, H)
    love.graphics.setCanvas({ actorHard, depthstencil = nativeDepth })
    love.graphics.clear(0, 0, 0, 0, false, false)
    love.graphics.setDepthMode("less", false)
    drawWorld({ actorFar })
    love.graphics.setDepthMode()
    love.graphics.setCanvas()
    local hardData = imageDataOf(actorHard)

    local final = love.graphics.newCanvas(W, H)
    love.graphics.setCanvas(final)
    love.graphics.clear(0, 0, 0, 1)
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.setBlendMode("alpha", "premultiplied")
    love.graphics.draw(downs)
    love.graphics.draw(actorHard)
    love.graphics.setBlendMode("alpha")
    love.graphics.setCanvas()
    savePng(imageDataOf(final), "capability-8-aa-colour-hard-mask.png")
    say("actor-mask pixels with partial alpha: %d (0 => genuinely binary)",
        countPartialAlpha(hardData))
    say("environment colour still carries AA : %d blended pixels", ssBlend)
    say("=> AA location and mask hardness are INDEPENDENT as long as AA lives")
    say("   in the colour path and the mask comes from a native-resolution")
    say("   depth attachment that no resolve ever touches.")

    ---------------------------------------------------------------- 9
    say("")
    say("## 9. A retained depth attachment is READ-ONLY to the actor pass")
    say("   Actors run at 60 Hz against depth held at 15 Hz. If the actor pass")
    say("   writes, frame N's actor depth stays in the snapshot and occludes")
    say("   frame N+1's actor at a position the environment never authorised.")

    -- Two actors at the same depth, laterally overlapping, standing in for
    -- the same actor one held-frame apart.
    -- Placed clear of the pillar (x -0.6..0.6), or the overlap this control
    -- depends on would already be occluded by the environment and the test
    -- would report a false clean bill.
    local actorA = newQuadMesh({ x = 0.9, y = 4.0, z = 0 }, { x = 2.5, y = 4.0, z = 0 },
        { x = 2.5, y = 4.0, z = 1.2 }, { x = 0.9, y = 4.0, z = 1.2 }, { 0.10, 0.90, 0.35 })
    local actorB = newQuadMesh({ x = 2.1, y = 4.0, z = 0 }, { x = 3.7, y = 4.0, z = 0 },
        { x = 3.7, y = 4.0, z = 1.2 }, { x = 2.1, y = 4.0, z = 1.2 }, { 0.10, 0.90, 0.35 })

    local function heldDepth()
        local d = love.graphics.newCanvas(W, H, { format = "depth24stencil8", readable = true })
        local scratch2 = love.graphics.newCanvas(W, H)
        love.graphics.setCanvas({ scratch2, depthstencil = d })
        love.graphics.clear(0, 0, 0, 1, true, true)
        love.graphics.setDepthMode("less", true)
        drawWorld({ back, pillar })
        love.graphics.setDepthMode()
        love.graphics.setCanvas()
        return d
    end

    local function actorFrames(depthWrite)
        local d = heldDepth()
        local target = love.graphics.newCanvas(W, H)
        -- frame N
        love.graphics.setCanvas({ target, depthstencil = d })
        love.graphics.clear(0, 0, 0, 0, false, false)
        love.graphics.setDepthMode("less", depthWrite)
        drawWorld({ actorA })
        love.graphics.setDepthMode()
        love.graphics.setCanvas()
        -- frame N+1, SAME held depth attachment, actor has moved
        local target2 = love.graphics.newCanvas(W, H)
        love.graphics.setCanvas({ target2, depthstencil = d })
        love.graphics.clear(0, 0, 0, 0, false, false)
        love.graphics.setDepthMode("less", false)
        drawWorld({ actorB })
        love.graphics.setDepthMode()
        love.graphics.setCanvas()
        return imageDataOf(target2)
    end

    local readOnly = savePng(actorFrames(false), "capability-9-actor-depth-readonly.png")
    local contaminated = savePng(actorFrames(true), "capability-9-actor-depth-written.png")
    local a = countOpaque(readOnly)
    local b = countOpaque(contaminated)
    say("frame N+1 actor pixels, actor pass depthwrite=false : %d", a)
    say("frame N+1 actor pixels, actor pass depthwrite=true  : %d  (%d lost)",
        b, a - b)
    say("=> a writing actor pass silently carves its previous silhouette into")
    say("   the held snapshot. `setDepthMode(\"less\", false)` is not an")
    say("   optimisation, it is a correctness requirement of the held frame.")

    finish()
end

--------------------------------------------------------------------------
-- CASE: temporal
--------------------------------------------------------------------------

local function caseTemporal()
    say("# Held environment frame vs 60 Hz actors")
    say("Environment cadence: every 4th frame => 15 FPS against 60 FPS actors.")

    local shader = love.graphics.newShader(retro.buildWorldShader())

    local back = newQuadMesh({ x = -8, y = 10, z = 0 }, { x = 8, y = 10, z = 0 },
        { x = 8, y = 10, z = 2.5 }, { x = -8, y = 10, z = 2.5 }, { 0.22, 0.26, 0.40 })
    local pillar = newQuadMesh({ x = -0.5, y = 4, z = 0 }, { x = 0.5, y = 4, z = 0 },
        { x = 0.5, y = 4, z = 2.5 }, { x = -0.5, y = 4, z = 2.5 }, { 0.85, 0.55, 0.20 })

    local actorCache = {}
    local function actorAt(t)
        local key = string.format("%.5f", t)
        if not actorCache[key] then
            -- BEHIND the pillar (pillar sits at y = 4): the actor is partly
            -- occluded while it crosses, which is what makes stale depth and
            -- stale camera observable at all.
            local x = -3 + 6 * t
            actorCache[key] = newQuadMesh(
                { x = x - 0.35, y = 4.6, z = 0 }, { x = x + 0.35, y = 4.6, z = 0 },
                { x = x + 0.35, y = 4.6, z = 1.6 }, { x = x - 0.35, y = 4.6, z = 1.6 },
                { 0.10, 0.90, 0.35 })
        end
        return actorCache[key]
    end

    local function drawMeshes(cam, meshes)
        love.graphics.setShader(shader)
        sendCamera(shader, cam, W, H)
        love.graphics.setColor(1, 1, 1, 1)
        for _, m in ipairs(meshes) do love.graphics.draw(m) end
        love.graphics.setShader()
    end

    local envColor = love.graphics.newCanvas(W, H)
    local envDepth = love.graphics.newCanvas(W, H,
        { format = "depth24stencil8", readable = true })
    local actorCanvas = love.graphics.newCanvas(W, H)
    local composite = love.graphics.newCanvas(W, H)

    local function renderEnvironment(cam)
        love.graphics.setCanvas({ envColor, depthstencil = envDepth })
        love.graphics.clear(0, 0, 0, 1, true, true)
        love.graphics.setDepthMode("less", true)
        drawMeshes(cam, { back, pillar })
        love.graphics.setDepthMode()
        love.graphics.setCanvas()
    end

    local function renderActor(cam, t)
        love.graphics.setCanvas({ actorCanvas, depthstencil = envDepth })
        love.graphics.clear(0, 0, 0, 0, false, false)
        love.graphics.setDepthMode("less", false)
        drawMeshes(cam, { actorAt(t) })
        love.graphics.setDepthMode()
        love.graphics.setCanvas()
    end

    local function compose()
        love.graphics.setCanvas(composite)
        love.graphics.clear(0, 0, 0, 1)
        love.graphics.setColor(1, 1, 1, 1)
        love.graphics.setBlendMode("alpha", "premultiplied")
        love.graphics.draw(envColor)
        love.graphics.draw(actorCanvas)
        love.graphics.setBlendMode("alpha")
        love.graphics.setCanvas()
        return imageDataOf(composite)
    end

    local function staticCameraAt()
        return makeCamera({ x = 0, y = 0, z = 1.2, angle = math.pi / 2 })
    end
    local function movingCameraAt(frame)
        return makeCamera({
            x = -0.9 + 0.05 * frame,
            y = 0,
            z = 1.2,
            angle = math.pi / 2 - 0.012 * frame,
        })
    end

    local FRAMES = 12
    local ENV_EVERY = 4
    local KEEP = { [3] = true, [7] = true, [11] = true }

    -- One variant of the presentation.
    --   held                : environment redrawn only every ENV_EVERY frames
    --   actorUsesHeldCamera : the actor pass reuses the camera snapshot that
    --                         produced the held colour+depth, instead of the
    --                         live 60 Hz camera
    --   depthEveryFrame     : depth refreshed at 60 Hz underneath a held
    --                         colour image -- the non-atomic failure #836
    --                         explicitly forbids
    local function run(label, cameraAt, opts)
        opts = opts or {}
        local snapshot = nil
        local frames, actorMasks, visible = {}, {}, {}
        local heldColour = love.graphics.newCanvas(W, H)
        for frame = 0, FRAMES - 1 do
            local live = cameraAt(frame)
            local refreshColour = (not opts.held) or frame % ENV_EVERY == 0
            local refreshDepth = refreshColour or opts.depthEveryFrame == true
            if refreshDepth then
                renderEnvironment(live)
                if not opts.depthEveryFrame then snapshot = live end
            end
            if refreshColour then
                snapshot = snapshot or live
                if opts.depthEveryFrame then snapshot = live end
                love.graphics.setCanvas(heldColour)
                love.graphics.clear(0, 0, 0, 1)
                love.graphics.setColor(1, 1, 1, 1)
                love.graphics.setBlendMode("alpha", "premultiplied")
                love.graphics.draw(envColor)
                love.graphics.setBlendMode("alpha")
                love.graphics.setCanvas()
            end
            local actorCam = (opts.held and opts.actorUsesHeldCamera) and snapshot or live
            renderActor(actorCam, frame / (FRAMES - 1))
            actorMasks[frame] = imageDataOf(actorCanvas)
            visible[frame] = countOpaque(actorMasks[frame])

            love.graphics.setCanvas(composite)
            love.graphics.clear(0, 0, 0, 1)
            love.graphics.setColor(1, 1, 1, 1)
            love.graphics.setBlendMode("alpha", "premultiplied")
            love.graphics.draw(heldColour)
            love.graphics.draw(actorCanvas)
            love.graphics.setBlendMode("alpha")
            love.graphics.setCanvas()
            frames[frame] = imageDataOf(composite)
            if KEEP[frame] then
                savePng(frames[frame], string.format("temporal-%s-f%02d.png", label, frame))
            end
        end
        return { composite = frames, actor = actorMasks, visible = visible }
    end

    local function compare(label, a, b, field)
        local worst, worstFrame, total = 0, -1, 0
        for frame = 0, FRAMES - 1 do
            local n = countDiffering(a[field][frame], b[field][frame])
            total = total + n
            if n > worst then worst, worstFrame = n, frame end
        end
        say("%-56s worst %6d px (frame %2d)  total %7d", label, worst, worstFrame, total)
        return worst
    end

    local function visibleRow(r)
        local out = {}
        for frame = 0, FRAMES - 1 do out[#out + 1] = tostring(r.visible[frame]) end
        return table.concat(out, " ")
    end

    say("")
    say("## Static camera")
    local sRef = run("static-ref", staticCameraAt, {})
    local sHeldSnap = run("static-heldcam", staticCameraAt, { held = true, actorUsesHeldCamera = true })
    local sHeldLive = run("static-livecam", staticCameraAt, { held = true, actorUsesHeldCamera = false })
    compare("static | actors on held camera vs 60 Hz reference", sHeldSnap, sRef, "composite")
    compare("static | actors on live camera vs 60 Hz reference", sHeldLive, sRef, "composite")
    compare("static | ACTOR LAYER, held vs live camera        ", sHeldSnap, sHeldLive, "actor")
    say("static | actor pixels visible per frame (reference): %s", visibleRow(sRef))
    say("=> with a static camera the held and live cameras are the same camera,")
    say("   so temporal asymmetry is free. This is the case #836 is safe in.")

    say("")
    say("## Moving camera (dolly + yaw every frame)")
    local mRef = run("moving-ref", movingCameraAt, {})
    local mHeldSnap = run("moving-heldcam", movingCameraAt, { held = true, actorUsesHeldCamera = true })
    local mHeldLive = run("moving-livecam", movingCameraAt, { held = true, actorUsesHeldCamera = false })
    local mDesync = run("moving-desync", movingCameraAt,
        { held = true, actorUsesHeldCamera = false, depthEveryFrame = true })

    say("")
    say("### Whole-frame difference from a 60 Hz reference")
    say("(dominated by the held BACKGROUND being stale, which is the intended")
    say(" look, so this number is context, not the defect measurement)")
    compare("moving | actors on held camera vs 60 Hz reference", mHeldSnap, mRef, "composite")
    compare("moving | actors on live camera vs 60 Hz reference", mHeldLive, mRef, "composite")

    say("")
    say("### Actor-layer registration against the DISPLAYED environment")
    say("(the self-consistent frame is `actors on the held camera`; anything")
    say(" else is the actor sliding against its own occluders)")
    local reg = compare("moving | ACTOR LAYER, live camera vs held camera  ",
        mHeldLive, mHeldSnap, "actor")
    local desyncReg = compare("moving | ACTOR LAYER, 60 Hz depth under 15 Hz colour",
        mDesync, mHeldSnap, "actor")
    say("moving | actor pixels visible per frame, held camera : %s", visibleRow(mHeldSnap))
    say("moving | actor pixels visible per frame, live camera : %s", visibleRow(mHeldLive))
    say("moving | actor pixels visible per frame, 60 Hz depth : %s", visibleRow(mDesync))

    say("")
    say("### Negative control")
    say("The static rows above are 0 for every variant, so the metric cannot")
    say("manufacture an error where none exists. The moving rows are %d and %d",
        reg, desyncReg)
    say("px, so it does detect exactly the two failures #836 must resolve:")
    say("  * actors projected with a camera the displayed image never used;")
    say("  * depth advancing underneath a held colour image.")

    finish()
end

--------------------------------------------------------------------------
-- CASE: projection
--------------------------------------------------------------------------

local function caseProjection()
    say("# Projection-window panning against the existing camera contract")

    ----------------------------------------------------------------
    say("")
    say("## A. Numerical oracle: NDC-centre offset vs asymmetric frustum")

    local fovHalfX = 0.75
    local targetWidth, baseWidth = 426, 256
    local nearRef = 1.0
    local halfExtent = fovHalfX * targetWidth / baseWidth

    local function shaderNdcX(horizontal, depth, viewportCenterX)
        local viewportCenter = (2 * viewportCenterX / targetWidth) - 1
        return viewportCenter + horizontal / (fovHalfX * depth) * (baseWidth / targetWidth)
    end
    -- glFrustum(l, r, b, t, n, f), eye looking down -Z so w_clip = depth:
    --   x_ndc = (2n/(r-l)) * h/depth - (r+l)/(r-l)
    local function frustumNdcX(horizontal, depth, l, r, n)
        return (2 * n / (r - l)) * horizontal / depth - (r + l) / (r - l)
    end
    -- Solve the frustum extents that reproduce the shader exactly:
    --   2n/(r-l) = k/f          (k = baseWidth/targetWidth, f = fovHalfX)
    --   -(r+l)/(r-l) = c        (c = the shader's NDC centre offset)
    local function extentsFor(centre, n)
        local k = baseWidth / targetWidth
        local c = (2 * centre / targetWidth) - 1
        local width = 2 * n * fovHalfX / k
        return -width * (1 + c) * 0.5, width * (1 - c) * 0.5
    end

    local worstDelta = 0
    for _, shiftPixels in ipairs({ -80, -25, 0, 25, 80 }) do
        local centre = targetWidth * 0.5 + shiftPixels
        local l, r = extentsFor(centre, nearRef)
        for _, depth in ipairs({ 0.5, 1, 2, 4, 8, 16, 32 }) do
            for _, horizontal in ipairs({ -3, -1, 0, 1, 3 }) do
                worstDelta = math.max(worstDelta, math.abs(
                    shaderNdcX(horizontal, depth, centre)
                    - frustumNdcX(horizontal, depth, l, r, nearRef)))
            end
        end
    end
    say("max |shader NDC.x - asymmetric-frustum NDC.x| over the sweep: %.3e", worstDelta)
    say("frustum extents at n=1 for window offsets -80/0/+80 px:")
    for _, shiftPixels in ipairs({ -80, 0, 80 }) do
        local l, r = extentsFor(targetWidth * 0.5 + shiftPixels, nearRef)
        say("  offset %+4d px -> l = %+8.5f  r = %+8.5f  (width %.5f)",
            shiftPixels, l, r, r - l)
    end
    say("=> the existing `viewportCenterX` uniform IS an off-axis frustum shift:")
    say("   the extents translate, the frustum width is invariant.")

    say("")
    local shiftPixels = 40
    local worstSpread = 0
    for _, horizontal in ipairs({ -3, -1, 0, 1, 3 }) do
        local lo, hi = math.huge, -math.huge
        for _, depth in ipairs({ 0.5, 1, 2, 4, 8, 16, 32 }) do
            local d = (shaderNdcX(horizontal, depth, targetWidth * 0.5 + shiftPixels)
                - shaderNdcX(horizontal, depth, targetWidth * 0.5)) * targetWidth * 0.5
            lo, hi = math.min(lo, d), math.max(hi, d)
        end
        worstSpread = math.max(worstSpread, hi - lo)
    end
    say("pixel displacement spread across depths for a %d px window pan: %.3e px",
        shiftPixels, worstSpread)
    say("=> exactly depth-independent, which a camera dolly is not.")

    ----------------------------------------------------------------
    say("")
    say("## B. Effekseer world projection consumes the same offset")
    local okEfk, effekseer = pcall(require, "presentation.effekseer")
    if not okEfk then
        say("could not load presentation.effekseer: %s", tostring(effekseer))
    else
        local function mul(v, m)
            local o = {}
            for c = 1, 4 do
                o[c] = v[1] * m[c] + v[2] * m[4 + c] + v[3] * m[8 + c] + v[4] * m[12 + c]
            end
            return o
        end
        local function efkNdcX(centre, horizontal, depth)
            local camera = {
                projection = "perspective",
                x = 0, y = 0, z = 0.5,
                dirX = 0, dirY = 1, rightX = -1, rightY = 0, pitch = 0,
                fovHalfX = fovHalfX, fovHalfY = 0.421875,
                nearPlane = 0.05, farPlane = 64,
                projectionScaleX = 1, projectionScaleY = 1,
                targetWidth = targetWidth, targetHeight = 240,
                compositionWidth = baseWidth, compositionHeight = 144,
                viewportCenterX = centre, viewportCenterY = 70,
            }
            local view, proj = effekseer.worldCameraMatrices(camera)
            -- camera.rightX = -1 means world +X is screen -X, so a screen-space
            -- `horizontal` of h sits at world x = -h.
            local wx, wy, wz = -horizontal, depth, 0.5
            local eye = mul({ wx, wz, wy, 1 }, view)
            local clip = mul(eye, proj)
            return clip[1] / clip[4]
        end
        local worst = 0
        for _, shift in ipairs({ -60, 0, 60 }) do
            local centre = targetWidth * 0.5 + shift
            for _, depth in ipairs({ 1, 4, 16 }) do
                for _, horizontal in ipairs({ -2, 0, 2 }) do
                    worst = math.max(worst, math.abs(
                        efkNdcX(centre, horizontal, depth)
                        - shaderNdcX(horizontal, depth, centre)))
                end
            end
        end
        say("max |Effekseer NDC.x - world-shader NDC.x| over the sweep: %.3e", worst)
        say("=> world-space effects already track `viewportCenterX`.")
    end
    ----------------------------------------------------------------
    say("")
    say("## C/D. Rendered sweep: fixed transform + moving window vs camera follow")

    local shader = love.graphics.newShader(retro.buildWorldShader())
    local meshes = {}
    -- A long street of posts, so extremity distortion under a fixed optical
    -- centre is legible in the captures.
    for i = -10, 10 do
        local shade = (i % 2 == 0) and 0.80 or 0.45
        meshes[#meshes + 1] = newQuadMesh(
            { x = i * 1.5 - 0.15, y = 6, z = 0 }, { x = i * 1.5 + 0.15, y = 6, z = 0 },
            { x = i * 1.5 + 0.15, y = 6, z = 2.2 }, { x = i * 1.5 - 0.15, y = 6, z = 2.2 },
            { shade, shade * 0.6, 0.25 })
    end
    -- Two narrow, uniquely coloured markers on the SAME world axis but at very
    -- different depths. Their relative screen separation is the parallax
    -- signature that distinguishes a window pan from a camera move.
    local NEAR_MARKER = { 0.10, 0.85, 0.95 }
    local FAR_MARKER = { 0.95, 0.15, 0.65 }
    meshes[#meshes + 1] = newQuadMesh(
        { x = -0.12, y = 3, z = 0 }, { x = 0.12, y = 3, z = 0 },
        { x = 0.12, y = 3, z = 1.8 }, { x = -0.12, y = 3, z = 1.8 }, NEAR_MARKER)
    -- Laterally offset so the near marker never occludes it.
    meshes[#meshes + 1] = newQuadMesh(
        { x = 2.60, y = 12, z = 0 }, { x = 3.40, y = 12, z = 0 },
        { x = 3.40, y = 12, z = 3.2 }, { x = 2.60, y = 12, z = 3.2 }, FAR_MARKER)

    local depthBuf = love.graphics.newCanvas(W, H,
        { format = "depth24stencil8", readable = true })
    local colourBuf = love.graphics.newCanvas(W, H)

    local function render(cam, name)
        love.graphics.setCanvas({ colourBuf, depthstencil = depthBuf })
        love.graphics.clear(0, 0, 0, 1, true, true)
        love.graphics.setDepthMode("less", true)
        love.graphics.setShader(shader)
        sendCamera(shader, cam, W, H)
        love.graphics.setColor(1, 1, 1, 1)
        for _, m in ipairs(meshes) do love.graphics.draw(m) end
        love.graphics.setShader()
        love.graphics.setDepthMode()
        love.graphics.setCanvas()
        local data = imageDataOf(colourBuf)
        if name then savePng(data, name) end
        return data
    end

    -- Mean column of every pixel matching a marker colour.
    local function centroidColumn(data, colour)
        local sum, count = 0, 0
        for y = 0, H - 1 do
            for x = 0, W - 1 do
                local r, g, b = data:getPixel(x, y)
                if math.abs(r - colour[1]) < 0.03 and math.abs(g - colour[2]) < 0.03
                    and math.abs(b - colour[3]) < 0.03 then
                    sum, count = sum + x, count + 1
                end
            end
        end
        if count == 0 then return nil end
        return sum / count
    end

    local panNear, panFar, followNear, followFar = {}, {}, {}, {}
    local panFrames = {}
    for i, shift in ipairs({ -96, -48, 0, 48, 96 }) do
        local data = render(makeCamera({
            x = 0, y = 0, z = 1.1, angle = math.pi / 2,
            viewportCenterX = W * 0.5 + shift,
            baseViewportWidth = W, baseViewportHeight = H,
        }), string.format("projection-window-%d.png", i))
        panFrames[i] = data
        panNear[i] = centroidColumn(data, NEAR_MARKER)
        panFar[i] = centroidColumn(data, FAR_MARKER)
    end
    -- A camera strafe chosen to move the NEAR marker by the same screen
    -- distance, so the two experiments are directly comparable.
    for i, dx in ipairs({ -1.5, -0.75, 0, 0.75, 1.5 }) do
        local data = render(makeCamera({
            x = dx, y = 0, z = 1.1, angle = math.pi / 2,
            baseViewportWidth = W, baseViewportHeight = H,
        }), string.format("projection-follow-%d.png", i))
        followNear[i] = centroidColumn(data, NEAR_MARKER)
        followFar[i] = centroidColumn(data, FAR_MARKER)
    end
    say("wrote projection-window-1..5.png and projection-follow-1..5.png")

    local function row(t)
        local out = {}
        for i = 1, 5 do
            out[i] = t[i] and string.format("%7.2f", t[i]) or "    n/a"
        end
        return table.concat(out, " ")
    end
    say("                          %s", "  -2      -1       0      +1      +2")
    say("window pan    near marker col : %s", row(panNear))
    say("window pan    far  marker col : %s", row(panFar))
    say("camera follow near marker col : %s", row(followNear))
    say("camera follow far  marker col : %s", row(followFar))
    local function separation(near, far)
        local out = {}
        for i = 1, 5 do
            out[i] = (near[i] and far[i]) and string.format("%7.2f", near[i] - far[i]) or "    n/a"
        end
        return table.concat(out, " ")
    end
    say("window pan    near-far parallax: %s", separation(panNear, panFar))
    say("camera follow near-far parallax: %s", separation(followNear, followFar))
    say("=> a window pan translates every depth by the SAME pixel count, so the")
    say("   near-far separation is invariant. A camera strafe changes it.")
    say("   That invariant separation is what makes actor/environment/depth")
    say("   alignment automatic under #837.")

    ----------------------------------------------------------------
    say("")
    say("## E. Is a whole-pixel window pan a rigid image translation?")
    -- If the window pan is a pure projection-plane offset, panning by an
    -- integer pixel count must reproduce the same image translated. Anything
    -- else means some consumer is resampling or quantising independently.
    local function shiftedDiff(a, b, dx)
        local n = 0
        for y = 0, H - 1 do
            for x = math.max(0, -dx), math.min(W - 1, W - 1 - dx) do
                local r1, g1, b1 = a:getPixel(x, y)
                local r2, g2, b2 = b:getPixel(x + dx, y)
                if r1 ~= r2 or g1 ~= g2 or b1 ~= b2 then n = n + 1 end
            end
        end
        return n
    end
    local baseNoSnap = render(makeCamera({
        x = 0, y = 0, z = 1.1, angle = math.pi / 2,
        viewportCenterX = W * 0.5,
        baseViewportWidth = W, baseViewportHeight = H, vertexSnapPixels = 0,
    }), nil)
    for _, dx in ipairs({ 1, 4, 16 }) do
        local panned = render(makeCamera({
            x = 0, y = 0, z = 1.1, angle = math.pi / 2,
            viewportCenterX = W * 0.5 + dx,
            baseViewportWidth = W, baseViewportHeight = H, vertexSnapPixels = 0,
        }), nil)
        say("  vertexSnapPixels=0, window +%2d px, compared as a %2d px image shift: %d px differ",
            dx, dx, shiftedDiff(baseNoSnap, panned, dx))
    end

    local baseSnap = render(makeCamera({
        x = 0, y = 0, z = 1.1, angle = math.pi / 2,
        viewportCenterX = W * 0.5,
        baseViewportWidth = W, baseViewportHeight = H, vertexSnapPixels = 1,
    }), nil)
    for _, dx in ipairs({ 1, 4, 16 }) do
        local panned = render(makeCamera({
            x = 0, y = 0, z = 1.1, angle = math.pi / 2,
            viewportCenterX = W * 0.5 + dx,
            baseViewportWidth = W, baseViewportHeight = H, vertexSnapPixels = 1,
        }), nil)
        say("  vertexSnapPixels=1, window +%2d px, compared as a %2d px image shift: %d px differ",
            dx, dx, shiftedDiff(baseSnap, panned, dx))
    end

    say("")
    say("### Sub-pixel window steps")
    local prev, changed = nil, 0
    for step = 0, 8 do
        local data = render(makeCamera({
            x = 0, y = 0, z = 1.1, angle = math.pi / 2,
            viewportCenterX = W * 0.5 + step * 0.25,
            baseViewportWidth = W, baseViewportHeight = H,
            vertexSnapPixels = 1,
        }), nil)
        if prev then
            local n = countDiffering(prev, data)
            if n > 0 then changed = changed + 1 end
            say("  window at +%.2f px, vertexSnapPixels=1 -> %d px changed",
                step * 0.25, n)
        end
        prev = data
    end
    say("sub-pixel window steps producing ANY change: %d of 8", changed)
    say("(vertexSnapPixels anchors its grid at the composition origin, so an")
    say(" INTEGER-pixel window pan preserves every vertex's sub-pixel phase and")
    say(" translates rigidly. A sub-pixel pan does not: each vertex crosses its")
    say(" own rounding boundary at a different phase, so the scene shears.")
    say(" A #837 window pan must therefore advance in whole pixels while")
    say(" vertexSnapPixels is non-zero.)")


    ----------------------------------------------------------------
    say("")
    say("## F. #836 x #837: a held environment holds its projection window too")
    local envColour = love.graphics.newCanvas(W, H)
    local envDepth = love.graphics.newCanvas(W, H,
        { format = "depth24stencil8", readable = true })
    local actorMesh = newQuadMesh(
        { x = -0.4, y = 4.2, z = 0 }, { x = 0.4, y = 4.2, z = 0 },
        { x = 0.4, y = 4.2, z = 1.5 }, { x = -0.4, y = 4.2, z = 1.5 },
        { 0.10, 0.90, 0.35 })

    local function windowCam(shift)
        return makeCamera({
            x = 0, y = 0, z = 1.1, angle = math.pi / 2,
            viewportCenterX = W * 0.5 + shift,
            baseViewportWidth = W, baseViewportHeight = H,
        })
    end

    local function renderPair(envShift, actorShift, name)
        love.graphics.setCanvas({ envColour, depthstencil = envDepth })
        love.graphics.clear(0, 0, 0, 1, true, true)
        love.graphics.setDepthMode("less", true)
        love.graphics.setShader(shader)
        sendCamera(shader, windowCam(envShift), W, H)
        love.graphics.setColor(1, 1, 1, 1)
        for _, m in ipairs(meshes) do love.graphics.draw(m) end
        love.graphics.setShader()
        love.graphics.setDepthMode()
        love.graphics.setCanvas()

        local actorCanvas = love.graphics.newCanvas(W, H)
        love.graphics.setCanvas({ actorCanvas, depthstencil = envDepth })
        love.graphics.clear(0, 0, 0, 0, false, false)
        love.graphics.setDepthMode("less", false)
        love.graphics.setShader(shader)
        sendCamera(shader, windowCam(actorShift), W, H)
        love.graphics.setColor(1, 1, 1, 1)
        love.graphics.draw(actorMesh)
        love.graphics.setShader()
        love.graphics.setDepthMode()
        love.graphics.setCanvas()

        local out = love.graphics.newCanvas(W, H)
        love.graphics.setCanvas(out)
        love.graphics.clear(0, 0, 0, 1)
        love.graphics.setColor(1, 1, 1, 1)
        love.graphics.setBlendMode("alpha", "premultiplied")
        love.graphics.draw(envColour)
        love.graphics.draw(actorCanvas)
        love.graphics.setBlendMode("alpha")
        love.graphics.setCanvas()
        local data = imageDataOf(out)
        if name then savePng(data, name) end
        return data
    end

    local aligned = renderPair(0, 0, "combined-aligned.png")
    say("aligned (env window == actor window) written")
    for _, lag in ipairs({ 1, 2, 4, 8, 16 }) do
        local drifted = renderPair(0, lag,
            lag == 8 and "combined-window-lag-8px.png" or nil)
        say("  actor window %2d px ahead of held environment window -> %6d px differ",
            lag, countDiffering(aligned, drifted))
    end
    say("=> a held environment frame necessarily holds the projection window")
    say("   that produced it. Panning the window at 60 Hz over a 15 Hz")
    say("   environment image displaces every actor against its own occluders.")

    finish()
end

--------------------------------------------------------------------------

--------------------------------------------------------------------------
-- CASE: cost -- what the extra passes actually cost on this machine
--------------------------------------------------------------------------

local function caseCost()
    say("# Cost of the extra render targets #836 would add")
    local rname, rvendor, rdevice = love.graphics.getRendererInfo()
    say("renderer: %s | %s | %s", tostring(rname), tostring(rvendor), tostring(rdevice))

    local shader = love.graphics.newShader(retro.buildWorldShader())

    -- A deliberately geometry-heavy room, so the measurement is not dominated
    -- by fixed overhead: 400 wall quads plus 40 actor quads.
    local envMeshes, actorMeshes = {}, {}
    for i = 1, 400 do
        local a = i * 0.31
        local x = math.cos(a) * (2 + (i % 9))
        local y = 3 + (i % 23) * 0.7
        envMeshes[#envMeshes + 1] = newQuadMesh(
            { x = x - 0.3, y = y, z = 0 }, { x = x + 0.3, y = y, z = 0 },
            { x = x + 0.3, y = y, z = 2 }, { x = x - 0.3, y = y, z = 2 },
            { 0.3 + (i % 5) * 0.1, 0.35, 0.5 })
    end
    for i = 1, 40 do
        local x = -4 + i * 0.2
        actorMeshes[#actorMeshes + 1] = newQuadMesh(
            { x = x - 0.1, y = 2.5, z = 0 }, { x = x + 0.1, y = 2.5, z = 0 },
            { x = x + 0.1, y = 2.5, z = 1.5 }, { x = x - 0.1, y = 2.5, z = 1.5 },
            { 0.1, 0.9, 0.35 })
    end

    local cam = makeCamera({ x = 0, y = 0, z = 1.0, angle = math.pi / 2 })

    local function drawSet(meshes, tw, th)
        love.graphics.setShader(shader)
        sendCamera(shader, cam, tw, th)
        love.graphics.setColor(1, 1, 1, 1)
        for _, m in ipairs(meshes) do love.graphics.draw(m) end
        love.graphics.setShader()
    end

    local ITER = 120
    local sync = love.graphics.newCanvas(1, 1)
    -- A readback is the only portable way to make the CPU wait for submitted
    -- GPU work, so every measurement is bracketed by one. Each configuration
    -- is measured three times and the MINIMUM is reported: an isolated slow
    -- round is scheduler noise, and a first round is cold pipeline state.
    local function flush()
        love.graphics.setCanvas(sync)
        love.graphics.setCanvas()
        sync:newImageData()
    end
    local function timeIt(label, fn)
        for _ = 1, 20 do fn() end
        flush()
        local best = math.huge
        for _ = 1, 3 do
            local t0 = love.timer.getTime()
            for _ = 1, ITER do fn() end
            flush()
            best = math.min(best, (love.timer.getTime() - t0) * 1000 / ITER)
        end
        say("%-56s %7.3f ms/iteration", label, best)
        return best
    end

    local function suite(profileName, tw, th)
        say("")
        say("## %s surface (%dx%d)", profileName, tw, th)
        local colour = love.graphics.newCanvas(tw, th)
        local depth = love.graphics.newCanvas(tw, th,
            { format = "depth24stencil8", readable = true })
        local actorColour = love.graphics.newCanvas(tw, th)
        local out = love.graphics.newCanvas(tw, th)

        local single = timeIt("current shape: one pass, one colour+depth target", function()
            love.graphics.setCanvas({ colour, depthstencil = depth })
            love.graphics.clear(0, 0, 0, 1, true, true)
            love.graphics.setDepthMode("less", true)
            drawSet(envMeshes, tw, th)
            drawSet(actorMeshes, tw, th)
            love.graphics.setDepthMode()
            love.graphics.setCanvas()
        end)

        local envOnly = timeIt("environment pass only", function()
            love.graphics.setCanvas({ colour, depthstencil = depth })
            love.graphics.clear(0, 0, 0, 1, true, true)
            love.graphics.setDepthMode("less", true)
            drawSet(envMeshes, tw, th)
            love.graphics.setDepthMode()
            love.graphics.setCanvas()
        end)

        local actorOnly = timeIt("actor pass only, against retained depth", function()
            love.graphics.setCanvas({ actorColour, depthstencil = depth })
            love.graphics.clear(0, 0, 0, 0, false, false)
            love.graphics.setDepthMode("less", false)
            drawSet(actorMeshes, tw, th)
            love.graphics.setDepthMode()
            love.graphics.setCanvas()
        end)

        local composite = timeIt("composite (two full-surface blits)", function()
            love.graphics.setCanvas(out)
            love.graphics.clear(0, 0, 0, 1)
            love.graphics.setColor(1, 1, 1, 1)
            love.graphics.setBlendMode("alpha", "premultiplied")
            love.graphics.draw(colour)
            love.graphics.draw(actorColour)
            love.graphics.setBlendMode("alpha")
            love.graphics.setCanvas()
        end)

        local degrade = love.graphics.newShader([[
            uniform float levels;
            uniform vec2 chroma;
            vec4 effect(vec4 c, Image t, vec2 uv, vec2 sc) {
                vec4 texel = Texel(t, uv + vec2(mod(sc.x, 2.0) * chroma.x, 0.0));
                vec3 q = floor(texel.rgb * levels + 0.5) / levels;
                return vec4(q, texel.a) * c;
            }
        ]])
        degrade:send("levels", 6.0)
        degrade:send("chroma", { 0.0006, 0.0 })
        local post = timeIt("colour degradation post-process", function()
            love.graphics.setCanvas(out)
            love.graphics.clear(0, 0, 0, 1)
            love.graphics.setColor(1, 1, 1, 1)
            love.graphics.setShader(degrade)
            love.graphics.draw(colour)
            love.graphics.setShader()
            love.graphics.setCanvas()
        end)

        local SS = 3
        local ssColour = love.graphics.newCanvas(tw * SS, th * SS)
        local ssDepth = love.graphics.newCanvas(tw * SS, th * SS,
            { format = "depth24stencil8", readable = true })
        local ssEnv = timeIt(string.format("environment pass at %dx supersample", SS), function()
            love.graphics.setCanvas({ ssColour, depthstencil = ssDepth })
            love.graphics.clear(0, 0, 0, 1, true, true)
            love.graphics.setDepthMode("less", true)
            drawSet(envMeshes, tw * SS, th * SS)
            love.graphics.setDepthMode()
            love.graphics.setCanvas()
        end)

        local msaaSamples = math.min(4, love.graphics.getSystemLimits().canvasmsaa or 0)
        local msaaEnv = nil
        local okC, msaaColour = pcall(love.graphics.newCanvas, tw, th, { msaa = msaaSamples })
        local okD, msaaDepth = pcall(love.graphics.newCanvas, tw, th,
            { format = "depth24stencil8", msaa = msaaSamples })
        if okC and okD then
            msaaEnv = timeIt(string.format("environment pass with %dx MSAA", msaaSamples), function()
                love.graphics.setCanvas({ msaaColour, depthstencil = msaaDepth })
                love.graphics.clear(0, 0, 0, 1, true, true)
                love.graphics.setDepthMode("less", true)
                drawSet(envMeshes, tw, th)
                love.graphics.setDepthMode()
                love.graphics.setCanvas()
            end)
        end

        local bytes = function(w, h) return w * h * 4 end
        say("")
        say("render-target memory, native pair    : %.2f MB",
            (bytes(tw, th) * 3 + bytes(tw, th)) / 1048576)
        say("  (environment colour + actor colour + composite + depth24stencil8)")
        say("render-target memory, %dx supersample : %.2f MB extra", SS,
            (bytes(tw * SS, th * SS) * 2) / 1048576)

        say("")
        say("### Frame budgets at 60 Hz actors")
        for _, cadence in ipairs({ 60, 30, 15 }) do
            local perFrame = actorOnly + composite + envOnly * (cadence / 60)
            say("  environment at %2d FPS, native colour   : %6.3f ms/frame (single-pass baseline %6.3f)",
                cadence, perFrame, single)
        end
        for _, cadence in ipairs({ 60, 30, 15 }) do
            local perFrame = actorOnly + composite + post + (ssEnv) * (cadence / 60)
            say("  environment at %2d FPS, %dx supersample  : %6.3f ms/frame",
                cadence, SS, perFrame)
        end
        if msaaEnv then
            for _, cadence in ipairs({ 60, 30, 15 }) do
                local perFrame = actorOnly + composite + post + msaaEnv * (cadence / 60)
                say("  environment at %2d FPS, %dx MSAA        : %6.3f ms/frame",
                    cadence, msaaSamples, perFrame)
            end
        end
    end

    suite("classic", 256, 240)
    suite("wide", 426, 240)

    say("")
    say("NOTE: this measures the PASS SHAPE on a synthetic 440-quad room, not")
    say("Second Gate content. Compare against `lovec <gateRoot> profile-3d`,")
    say("whose whole-frame cost on the real maps is CPU geometry preparation")
    say("dominated, not fill dominated.")

    finish()
end

--------------------------------------------------------------------------

function love.load()
    whiteTex = solidTexture(1, 1, 1)
    blackTex = solidTexture(0, 0, 0)
    if case == "capability" then
        caseCapability()
    elseif case == "temporal" then
        caseTemporal()
    elseif case == "projection" then
        caseProjection()
    elseif case == "cost" then
        caseCost()
    else
        io.stderr:write("unknown case: " .. tostring(case) .. "\n")
        os.exit(2)
    end
end

function love.draw() end
