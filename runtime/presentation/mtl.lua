-- Shared source-material adapter. Compilation and direct OBJ acquisition use
-- this one grammar; compiled consumers never parse MTL.
local retro_mesh_shader = require("presentation.retro_mesh_shader")

-- Validates and appends one overlay pass. Every token is checked against the
-- shader's own tables, so an authored typo fails at load rather than rendering
-- nothing -- the failure mode that matters most for something invisible.
local function addPass(material, uvSource, blend, strength, path)
    local blendId = retro_mesh_shader.BLEND_OPS[blend]
    if not blendId then
        local names = {}
        for name in pairs(retro_mesh_shader.BLEND_OPS) do names[#names + 1] = name end
        table.sort(names)
        error("MTL pass blend '" .. tostring(blend) .. "' is unknown; expected one of "
            .. table.concat(names, ", "), 0)
    end
    local uvId = retro_mesh_shader.UV_SOURCES[uvSource]
    if not uvId then
        local names = {}
        for name in pairs(retro_mesh_shader.UV_SOURCES) do names[#names + 1] = name end
        table.sort(names)
        error("MTL pass uv source '" .. tostring(uvSource) .. "' is unknown; expected one of "
            .. table.concat(names, ", "), 0)
    end
    local amount = tonumber(strength)
    if not amount or amount < 0 then
        error("MTL pass strength must be a non-negative number, got '" .. tostring(strength) .. "'", 0)
    end
    if path == nil or path == "" then
        error("MTL pass needs a texture path", 0)
    end

    material.passes = material.passes or {}
    if #material.passes >= retro_mesh_shader.MAX_PASSES then
        error("MTL material declares more than " .. retro_mesh_shader.MAX_PASSES
            .. " overlay passes; the shader has no slot for the extras", 0)
    end
    material.passes[#material.passes + 1] = {
        texture = path,
        blend = blend,
        blendId = blendId,
        uvSource = uvSource,
        uvSourceId = uvId,
        strength = amount,
    }
end

local function parseMtl(text)
    local materials, current = {}, nil
    for raw in (text .. "\n"):gmatch("([^\r\n]*)[\r\n]+") do
        local line = raw:gsub("#.*$", ""):match("^%s*(.-)%s*$")
        local op, rest = line:match("^(%S+)%s*(.*)$")
        if op == "newmtl" then
            if rest == "" then error("MTL newmtl needs a name", 0) end
            current = { color = { 1, 1, 1, 1 } }
            materials[rest] = current
        elseif op == "Kd" and current then
            local r, g, b = rest:match("^(%S+)%s+(%S+)%s+(%S+)$")
            if not r then error("MTL Kd needs three numbers", 0) end
            current.color = { assert(tonumber(r)), assert(tonumber(g)), assert(tonumber(b)), 1 }
        elseif op == "map_Kd" and current then
            if rest == "" then error("MTL map_Kd needs a path", 0) end
            current.texture = rest
        elseif op == "refl" and current then
            -- Sphere-mapped reflection: the standard MTL statement, not a
            -- private extension. The shader cannot compute a specular term
            -- (SPEC 1.25), so a highlight is *sampled* from a small sheen
            -- image indexed by the screen-space normal -- the same trick
            -- PS1/N64-era hardware used for chrome and gemstones.
            --
            -- It is sugar for `pass sphere add 1.0 <path>`: the sheen is one
            -- configuration of the general overlay mechanism, not a parallel
            -- feature with its own code path.
            local reflType, path = rest:match("^%-type%s+(%S+)%s+(.+)$")
            if not reflType then
                error("MTL refl needs '-type <kind> <path>'", 0)
            end
            if reflType ~= "sphere" then
                -- Cube maps would need a sampler the retro shader does not
                -- have; failing here beats silently rendering no reflection.
                error("MTL refl type '" .. reflType .. "' is unsupported; only 'sphere'", 0)
            end
            addPass(current, "sphere", "add", "1.0", path)
        elseif op == "pass" and current then
            -- `pass <uvSource> <blend> <strength> <path>` -- an overlay layer
            -- composited onto the base colour in declaration order. MTL has no
            -- standard vocabulary for blend layers, so this one is ours; it is
            -- documented in SPEC 1.25 and every token is validated.
            local uvSource, blend, strength, path =
                rest:match("^(%S+)%s+(%S+)%s+(%S+)%s+(.+)$")
            if not uvSource then
                error("MTL pass needs '<uvSource> <blend> <strength> <path>'", 0)
            end
            addPass(current, uvSource, blend, strength, path)
        end
    end
    return materials
end


return { parse = parseMtl }
