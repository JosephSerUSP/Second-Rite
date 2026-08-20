-- #841 isolated LÖVE 11.5 framebuffer / temporal-projection audit.
-- Not production renderer code; no Project data is consumed or mutated.

local W, H = 256, 240
local ENV_DIVISOR = 4 -- 60 Hz presentation -> 15 Hz held environment
local msaa = 0
local mode = 1 -- 1 static, 2 moving held optical state (correct), 3 current over stale (negative)
local view = 1 -- 1 final, 2 held environment
local postAA = false
local actorWritesDepth = false
local t, frame, generation = 0, 0, 0
local envColor, envDepth, finalColor
local worldShader, aaShader
local envMeshes, actorMesh
local held = { camera = 0, projection = 0 }
local capability = {}

local format = {
    { "VertexPosition", "float", 3 },
    { "VertexColor", "float", 4 },
}

local function log(s) print("[#841 audit] " .. tostring(s)) end

local function canvas(formatName, samples)
    return love.graphics.newCanvas(W, H, {
        format = formatName,
        msaa = samples or 0,
        readable = true,
    })
end

local function depthFormat()
    local f = love.graphics.getCanvasFormats(true)
    for _, name in ipairs({ "depth24stencil8", "depth24", "depth16", "depth32f" }) do
        if f[name] then return name end
    end
    return "depth24"
end

local function tryBind(color, depth)
    local ok, err = pcall(function()
        love.graphics.setCanvas({ color, depthstencil = depth })
        love.graphics.setCanvas()
    end)
    return ok, ok and "ok" or tostring(err)
end

local function rebuild(samples)
    msaa = samples or 0
    local df = depthFormat()
    local ok, result = pcall(function()
        return {
            envColor = canvas("rgba8", msaa),
            envDepth = canvas(df, msaa),
            finalColor = canvas("rgba8", msaa),
        }
    end)
    if not ok and msaa ~= 0 then
        log("MSAA target creation failed; falling back to 0: " .. tostring(result))
        return rebuild(0)
    elseif not ok then
        error(result)
    end
    envColor, envDepth, finalColor = result.envColor, result.envDepth, result.finalColor
    local pairOK, pairMsg = tryBind(envColor, envDepth)
    local rebindOK, rebindMsg = tryBind(finalColor, envDepth)
    local single = canvas("rgba8", 0)
    local mismatchOK, mismatchMsg = tryBind(single, envDepth)
    if single.release then single:release() end
    capability = {
        depthFormat = df,
        requested = msaa,
        color = envColor:getMSAA(),
        depth = envDepth:getMSAA(),
        final = finalColor:getMSAA(),
        pairOK = pairOK,
        rebindOK = rebindOK,
        mismatchOK = mismatchOK,
    }
    log(string.format("MSAA req=%d actual color/depth/final=%d/%d/%d depth=%s",
        msaa, capability.color, capability.depth, capability.final, df))
    log("environment color+depth bind: " .. tostring(pairOK) .. " (" .. pairMsg .. ")")
    log("retained depth rebind: " .. tostring(rebindOK) .. " (" .. rebindMsg .. ")")
    log("single-sample color + tested depth: " .. tostring(mismatchOK) .. " (" .. mismatchMsg .. ")")
    generation = 0
end

local function quad(x0, y0, x1, y1, z, color)
    local r,g,b,a = color[1],color[2],color[3],color[4] or 1
    local v = {
        {x0,y0,z,r,g,b,a},{x1,y0,z,r,g,b,a},{x1,y1,z,r,g,b,a},
        {x0,y0,z,r,g,b,a},{x1,y1,z,r,g,b,a},{x0,y1,z,r,g,b,a},
    }
    return love.graphics.newMesh(format, v, "triangles", "static")
end

local function buildGeometry()
    -- Screen/clip-space geometry is deliberate: this probe isolates attachment,
    -- cadence and optical-state ownership rather than reimplementing viewport_3d.
    envMeshes = {
        quad(-1,-1,1,1,0.85,{0.12,0.15,0.20,1}),
        quad(-0.95,-0.82,0.95,-0.62,0.55,{0.27,0.31,0.35,1}), -- floor band
        quad(-0.18,-0.62,0.12,0.72,0.20,{0.70,0.58,0.38,1}), -- foreground occluder
        quad(0.48,-0.62,0.75,0.35,0.42,{0.31,0.49,0.38,1}), -- structural prop
    }
    actorMesh = quad(-0.10,-0.56,0.10,0.18,0.34,{0.92,0.28,0.24,1})
end

local vertex = [[
#ifdef VERTEX
uniform float xShift;
uniform float projectionShift;
vec4 position(mat4 transform_projection, vec4 vertex_position) {
    return vec4(VertexPosition.x + xShift + projectionShift,
                VertexPosition.y, VertexPosition.z, 1.0);
}
#endif
]]

local pixel = [[
#ifdef PIXEL
vec4 effect(vec4 color, Image tex, vec2 uv, vec2 px) { return color; }
#endif
]]

local aa = [[
extern vec2 texelSize;
extern float enabled;
vec4 effect(vec4 color, Image tex, vec2 uv, vec2 px) {
    vec4 c = Texel(tex, uv);
    if (enabled < 0.5) return c * color;
    vec4 x = Texel(tex, uv + vec2(texelSize.x, 0.0));
    vec4 y = Texel(tex, uv + vec2(0.0, texelSize.y));
    return (c * 0.60 + x * 0.20 + y * 0.20) * color;
}
]]

local function opticalNow()
    if mode == 1 then return 0, 0 end
    return math.sin(t * 0.8) * 0.18, math.sin(t * 0.55) * 0.14
end

local function drawMeshes(meshes, camera, projection)
    worldShader:send("xShift", -camera)
    worldShader:send("projectionShift", projection)
    love.graphics.setShader(worldShader)
    for _, mesh in ipairs(meshes) do love.graphics.draw(mesh) end
    love.graphics.setShader()
end

local function refreshEnvironment()
    local camera, projection = opticalNow()
    held.camera, held.projection = camera, projection
    generation = generation + 1
    love.graphics.setCanvas({ envColor, depthstencil = envDepth })
    love.graphics.clear({0.02,0.025,0.04,1}, false, 1)
    love.graphics.setDepthMode("less", true)
    drawMeshes(envMeshes, held.camera, held.projection)
    love.graphics.setDepthMode()
    love.graphics.setCanvas()
end

local function actorOptical()
    if mode == 3 then return opticalNow() end -- deliberately wrong current optical state
    return held.camera, held.projection
end

local function composite()
    if not capability.rebindOK then return end
    love.graphics.setCanvas({ finalColor, depthstencil = envDepth })
    -- Preserve retained depth: clear color only.
    love.graphics.clear({0,0,0,1}, false, false)
    love.graphics.setDepthMode()
    aaShader:send("enabled", postAA and 1 or 0)
    aaShader:send("texelSize", {1/W,1/H})
    love.graphics.setShader(aaShader)
    love.graphics.setColor(1,1,1,1)
    love.graphics.draw(envColor)
    love.graphics.setShader()

    local camera, projection = actorOptical()
    local actorMotion = math.sin(t * 2.2) * 0.42
    worldShader:send("xShift", actorMotion - camera)
    worldShader:send("projectionShift", projection)
    love.graphics.setDepthMode("less", actorWritesDepth)
    love.graphics.setShader(worldShader)
    love.graphics.draw(actorMesh)
    love.graphics.setShader()
    love.graphics.setDepthMode()
    love.graphics.setCanvas()
end

local function reset()
    t, frame, generation = 0, 0, 0
    held.camera, held.projection = 0, 0
end

function love.load()
    worldShader = love.graphics.newShader(vertex .. pixel)
    aaShader = love.graphics.newShader(aa)
    buildGeometry()
    local major, minor, revision, codename = love.getVersion()
    local rn, rv, vendor, device = love.graphics.getRendererInfo()
    log(string.format("LÖVE %d.%d.%d %s", major, minor, revision, codename or ""))
    log("renderer: " .. table.concat({tostring(rn),tostring(rv),tostring(vendor),tostring(device)}, " | "))
    rebuild(0)
    reset()
end

function love.update(dt)
    t = t + dt
    frame = frame + 1
end

function love.draw()
    if generation == 0 or frame % ENV_DIVISOR == 0 then refreshEnvironment() end
    composite()
    love.graphics.setColor(1,1,1,1)
    local source = (view == 2) and envColor or finalColor
    love.graphics.draw(source, 0, 0, 0, love.graphics.getWidth()/W, love.graphics.getHeight()/H)
    love.graphics.setColor(0,0,0,0.78)
    love.graphics.rectangle("fill", 0, 0, love.graphics.getWidth(), 48)
    love.graphics.setColor(1,1,1,1)
    local modeName = ({"static", "moving + HELD optical state (correct)", "CURRENT over stale depth (negative)"})[mode]
    love.graphics.print(string.format("#841 | %s | env generation %d | AA %s | actor depth write %s",
        modeName, generation, tostring(postAA), tostring(actorWritesDepth)), 6, 5)
    love.graphics.print(string.format("MSAA req/actual %d/%d | retained-depth rebind %s | view %s",
        capability.requested or 0, capability.depth or 0, tostring(capability.rebindOK), view == 1 and "final" or "environment"), 6, 21)
    love.graphics.print("1/2/3 mode  A color-AA  D depth-write negative  M MSAA  V view  S capture  R reset", 6, 36)
end

function love.keypressed(key)
    if key == "escape" then love.event.quit(); return end
    if key == "1" or key == "2" or key == "3" then mode = tonumber(key); reset(); return end
    if key == "a" then postAA = not postAA
    elseif key == "d" then actorWritesDepth = not actorWritesDepth; reset()
    elseif key == "v" then view = view % 2 + 1
    elseif key == "m" then
        local values, idx = {0,2,4,8}, 1
        for i,v in ipairs(values) do if v == msaa then idx = i break end end
        rebuild(values[idx % #values + 1]); reset()
    elseif key == "r" then reset()
    elseif key == "s" then
        love.graphics.captureScreenshot(string.format("issue841-mode%d-aa%s-depthwrite%s.png",
            mode, tostring(postAA), tostring(actorWritesDepth)))
    end
end
