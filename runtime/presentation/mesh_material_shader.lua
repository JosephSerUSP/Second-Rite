-- Shared material overlay bindings for mesh viewports.
local retro_mesh_shader=require("presentation.retro_mesh_shader")
local blackPassTexture = nil

-- The "no overlay here" sampler, mirroring the world renderer's black glow
-- texture. Bound into every unused pass slot so no sampler uniform is ever
-- left unset, and paired with a pass count that stops the shader sampling it
-- at all rather than relying on the black texel.
local function getBlackPassTexture()
    if blackPassTexture then return blackPassTexture end
    local imageData = love.image.newImageData(1, 1)
    imageData:setPixel(0, 0, 0, 0, 0, 1)
    blackPassTexture = love.graphics.newImage(imageData)
    blackPassTexture:setFilter("nearest", "nearest")
    return blackPassTexture
end

-- Every slot is written on every group, always. Sending only the slots a group
-- happens to use is how one decorated group would leak its overlays onto every
-- later group in the model -- the failure the world renderer's paired glow send
-- exists to prevent, generalized to N slots.
local function setPassUniforms(shader, passes)
    if not shader then return end
    local count = math.min(passes and #passes or 0, retro_mesh_shader.MAX_PASSES)
    shader:send("passCount", count)
    for slot = 0, retro_mesh_shader.MAX_PASSES - 1 do
        local pass = passes and passes[slot + 1]
        local suffix = tostring(slot)
        shader:send("passMap" .. suffix, (pass and pass.texture) or getBlackPassTexture())
        shader:send("passBlend" .. suffix, pass and pass.blendId or 0)
        shader:send("passStrength" .. suffix, pass and pass.strength or 0)
        shader:send("passUvSource" .. suffix, pass and pass.uvSourceId or 0)
    end
end


return {set=setPassUniforms, reset=function() blackPassTexture=nil end}
