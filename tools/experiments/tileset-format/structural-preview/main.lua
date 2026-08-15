local retroMeshShader = require("presentation.retro_mesh_shader")

local WIDTH, HEIGHT = 768, 420
local TILE = 64
local meshes = {}
local texture
local shader
local blackGlow
local captured = false
local framesAfterCapture = 0

local WORLD_MESH_FORMAT = {
    { "VertexPosition", "float", 2 },
    { "VertexTexCoord", "float", 2 },
    { "VertexColor", "float", 4 },
    { "SurfaceLight", "float", 3 },
    { "FogVisibility", "float", 1 },
    { "WorldHeight", "float", 1 },
}

local profiles = {
    { id = "square", label = "SQUARE", corner = "square", radius = 0.18, segments = 1 },
    { id = "chamfer", label = "CHAMFER", corner = "chamfer", radius = 0.18, segments = 1 },
    { id = "round", label = "ROUND / 3 SEG", corner = "round", radius = 0.18, segments = 3 },
}

local function cornerPoints(profile)
    local r = profile.radius
    local points = { { x = 0, y = 1 } }
    if profile.corner == "square" then
        points[#points + 1] = { x = 1 - r, y = 1 }
        points[#points + 1] = { x = 1, y = 1 }
        points[#points + 1] = { x = 1, y = 1 - r }
    elseif profile.corner == "chamfer" then
        points[#points + 1] = { x = 1 - r, y = 1 }
        points[#points + 1] = { x = 1, y = 1 - r }
    elseif profile.corner == "round" then
        local cx, cy = 1 - r, 1 - r
        for i = 0, profile.segments do
            local angle = (math.pi * 0.5) * (1 - i / profile.segments)
            points[#points + 1] = {
                x = cx + math.cos(angle) * r,
                y = cy + math.sin(angle) * r,
            }
        end
    else
        error("unknown profile " .. tostring(profile.corner))
    end
    points[#points + 1] = { x = 1, y = 0 }
    return points
end

local function pathDistances(points)
    local distances, total = { 0 }, 0
    for i = 1, #points - 1 do
        local dx, dy = points[i + 1].x - points[i].x, points[i + 1].y - points[i].y
        total = total + math.sqrt(dx * dx + dy * dy)
        distances[i + 1] = total
    end
    return distances, total
end

local function addVertex(vertices, x, y, z, u, v)
    vertices[#vertices + 1] = {
        x, y, u, v,
        1, 1, 1, 1,
        1, 1, 1,
        1,
        z,
    }
end

local function buildProfileMesh(profile, offsetX, offsetY)
    local points = cornerPoints(profile)
    local distances, total = pathDistances(points)
    local iw, ih = texture:getDimensions()
    local tileOriginX, tileOriginY = 0, TILE -- dungeon_001 row 1, column 0
    local atlasU0 = (tileOriginX + 0.5) / iw
    local atlasU1 = (tileOriginX + TILE - 0.5) / iw
    local atlasV0 = (tileOriginY + 0.5) / ih
    local atlasV1 = (tileOriginY + TILE - 0.5) / ih
    local vertices = {}

    local function pathU(index)
        local t = total > 0 and distances[index] / total or 0
        return atlasU0 + (atlasU1 - atlasU0) * t
    end

    for i = 1, #points - 1 do
        local a, b = points[i], points[i + 1]
        local u0, u1 = pathU(i), pathU(i + 1)
        local ax, ay = offsetX + a.x, offsetY + a.y
        local bx, by = offsetX + b.x, offsetY + b.y

        addVertex(vertices, ax, ay, 0, u0, atlasV1)
        addVertex(vertices, bx, by, 0, u1, atlasV1)
        addVertex(vertices, bx, by, 1, u1, atlasV0)

        addVertex(vertices, ax, ay, 0, u0, atlasV1)
        addVertex(vertices, bx, by, 1, u1, atlasV0)
        addVertex(vertices, ax, ay, 1, u0, atlasV0)
    end

    local mesh = love.graphics.newMesh(WORLD_MESH_FORMAT, vertices, "triangles", "static")
    mesh:setTexture(texture)
    return {
        id = profile.id,
        label = profile.label,
        profile = profile,
        points = points,
        mesh = mesh,
        triangles = #vertices / 3,
    }
end

local function sendWorldUniforms()
    local camX, camY, camZ = 3.0, 6.2, 0.58
    local dirX, dirY = 0, -1
    local rightX, rightY = 1, 0
    shader:send("cameraPosition", { camX, camY, camZ })
    shader:send("cameraForward", { dirX, dirY })
    shader:send("cameraRight", { rightX, rightY })
    shader:send("cameraPitch", -0.04)
    shader:send("fovHalfX", 0.75)
    shader:send("fovHalfY", 0.50)
    shader:send("nearPlane", 0.05)
    shader:send("farPlane", 32.0)
    shader:send("baseViewportWidth", WIDTH)
    shader:send("baseViewportHeight", HEIGHT)
    shader:send("targetWidth", WIDTH)
    shader:send("targetHeight", HEIGHT)
    shader:send("compositionOrigin", { 0, 0 })
    shader:send("viewportCenterX", WIDTH * 0.5)
    shader:send("viewportCenterY", HEIGHT * 0.44)
    shader:send("affineTextures", 1.0)
    shader:send("vertexSnapPixels", 1.0)
    shader:send("fogStart", 100.0)
    shader:send("fogDistance", 100.0)
    shader:send("fogSharpness", 1.0)
    shader:send("fogMinFactor", 1.0)
    shader:send("fogBands", 0.0)
    shader:send("fogColor", { 0.08, 0.08, 0.09 })
    shader:send("playerLightColor", { 0, 0, 0 })
    shader:send("playerLightRadius", 0.0)
    shader:send("playerLightFalloff", 1.0)
    shader:send("ditherLevels", 16.0)
    shader:send("roomBakePass", 0.0)
    shader:send("roomBakeFar", 8.0)
    shader:send("glowMap", blackGlow)
    shader:send("glowStrength", 0.0)
end

local function drawTopDownSpecimen(entry, x, y, size)
    local points = entry.points
    love.graphics.setColor(0.2, 0.2, 0.22, 1)
    love.graphics.rectangle("fill", x, y, size, size)
    love.graphics.setColor(0.42, 0.42, 0.46, 1)
    love.graphics.rectangle("line", x, y, size, size)
    local coords = {}
    for _, p in ipairs(points) do
        coords[#coords + 1] = x + p.x * size
        coords[#coords + 1] = y + (1 - p.y) * size
    end
    love.graphics.setLineWidth(3)
    love.graphics.setColor(0.95, 0.95, 0.95, 1)
    love.graphics.line(coords)
    love.graphics.setLineWidth(1)
end

function love.load()
    love.graphics.setDefaultFilter("nearest", "nearest", 1)
    texture = love.graphics.newImage("wall.png")
    texture:setFilter("nearest", "nearest")
    shader = love.graphics.newShader(retroMeshShader.buildWorldShader())

    local black = love.image.newImageData(1, 1)
    black:setPixel(0, 0, 0, 0, 0, 1)
    blackGlow = love.graphics.newImage(black)
    blackGlow:setFilter("nearest", "nearest")

    local placements = {
        { x = 0.45, y = 2.0 },
        { x = 2.45, y = 2.0 },
        { x = 4.45, y = 2.0 },
    }
    for i, profile in ipairs(profiles) do
        meshes[i] = buildProfileMesh(profile, placements[i].x, placements[i].y)
    end

    print("STRUCTURAL_PROFILE_PREVIEW same_atlas_tile=true collision_topology=unchanged")
    for _, entry in ipairs(meshes) do
        print(string.format("PROFILE %s triangles=%d radius=%.2f segments=%d",
            entry.id, entry.triangles, entry.profile.radius, entry.profile.segments))
    end
end

function love.update()
    if captured then
        framesAfterCapture = framesAfterCapture + 1
        if framesAfterCapture >= 6 then love.event.quit(0) end
    end
end

function love.draw()
    love.graphics.clear(0.055, 0.055, 0.065, 1, 1, 0)
    love.graphics.setDepthMode("less", true)
    love.graphics.setShader(shader)
    sendWorldUniforms()
    love.graphics.setColor(1, 1, 1, 1)
    for _, entry in ipairs(meshes) do love.graphics.draw(entry.mesh) end
    love.graphics.setShader()
    love.graphics.setDepthMode()

    love.graphics.setColor(0.95, 0.95, 0.95, 1)
    love.graphics.print("THES TRA / #558 STRUCTURAL PROFILE SPECIMEN", 22, 18)
    love.graphics.setColor(0.68, 0.68, 0.72, 1)
    love.graphics.print("same logical 1x1 wall footprint + same real dungeon atlas tile + real retro mesh shader", 22, 40)

    local cardX = { 70, 292, 514 }
    for i, entry in ipairs(meshes) do
        local x = cardX[i]
        love.graphics.setColor(0.95, 0.95, 0.95, 1)
        love.graphics.print(entry.label, x, 315)
        love.graphics.setColor(0.62, 0.62, 0.66, 1)
        love.graphics.print(string.format("%d tris", entry.triangles), x, 335)
        drawTopDownSpecimen(entry, x + 92, 308, 58)
    end

    love.graphics.setColor(0.66, 0.66, 0.70, 1)
    love.graphics.print("Top-down diagrams show presentation boundary only; collision remains the square logical cell.", 22, 392)

    if not captured then
        love.graphics.captureScreenshot("structural-profiles.png")
        captured = true
    end
end
