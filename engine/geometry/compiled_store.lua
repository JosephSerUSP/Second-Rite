-- Persistent store for compiled geometry (#161).
--
-- The geometry compiler is deterministic and expensive: on map 8 a cold build
-- spends ~550 ms in QEM decimation for four unique surfaces, and map 12 spends
-- ~1440 ms for eight. The in-memory cache in geometry/init.lua removes that for
-- the rest of the process, but every launch pays it again from scratch.
--
-- This writes the compiler's OUTPUT beside the save files, so the cost is paid
-- once per machine per (source, quality, compiler version) rather than once per
-- launch. It is the runtime half of the issue's prebake direction, and it
-- deliberately uses the same on-disk shape a build-time prebake would ship, so
-- that step becomes "ship these files" rather than "design a format".
--
-- What is stored is the model as engine.geometry.model's Builder:build()
-- returns it -- geometry only. Materials, textures and GPU meshes are NOT
-- stored: presentation.mesh.finalize attaches those afterwards through
-- engine.geometry's injected materialization seam. This is what keeps prebake
-- and headless inspection independent of an active graphics device.
local compiled_store = {}

-- Bump when the encoding changes. Entries with a different version are ignored
-- rather than migrated: the compiler is the source of truth, so a stale entry
-- costs one recompile, and migration code would be a second thing to keep
-- correct for no benefit.
local FORMAT_VERSION = 1
local MAGIC = "SRGEO"
local DIR = "geocache"

-- LÖVE runs LuaJIT (Lua 5.1), which has no string.pack/string.unpack -- those
-- arrived in 5.3. love.data provides the same format strings.
local FIELDS = 12
local VERTEX_FORMAT = "<" .. string.rep("d", FIELDS)

-- float64, not float32. Doubles round-trip a Lua number exactly, so a model
-- restored from disk is bit-identical to a freshly compiled one and the golden
-- screenshots cannot shift depending on whether the store was warm. float32
-- would halve the file and silently perturb geometry -- the one failure mode
-- that would be both invisible here and visible in G5.
local function available()
    return (love and love.filesystem and love.data) and true or false
end

local function pathFor(key)
    local hashed = love.data.encode("string", "hex", love.data.hash("md5", key))
    return DIR .. "/" .. hashed .. ".geo"
end

function compiled_store.encode(model)
    local out = {}
    out[#out + 1] = MAGIC
    out[#out + 1] = love.data.pack("string", "<I4", FORMAT_VERSION)
    local b = model.bounds or {}
    out[#out + 1] = love.data.pack("string", "<dddddd",
        b.minX or 0, b.minY or 0, b.minZ or 0,
        b.maxX or 0, b.maxY or 0, b.maxZ or 0)
    out[#out + 1] = love.data.pack("string", "<I4", #model.groups)
    for _, group in ipairs(model.groups) do
        out[#out + 1] = love.data.pack("string", "<s4", tostring(group.material or ""))
        out[#out + 1] = love.data.pack("string", "<I4", #group.vertices)
        local chunk = {}
        for i, v in ipairs(group.vertices) do
            chunk[i] = love.data.pack("string", VERTEX_FORMAT,
                v[1] or 0, v[2] or 0, v[3] or 0, v[4] or 0,
                v[5] or 0, v[6] or 0, v[7] or 0, v[8] or 0,
                v[9] or 1, v[10] or 1, v[11] or 1, v[12] or 1)
        end
        out[#out + 1] = table.concat(chunk)
    end
    return table.concat(out)
end

function compiled_store.decode(blob)
    if type(blob) ~= "string" or #blob < #MAGIC + 4 then return nil end
    if blob:sub(1, #MAGIC) ~= MAGIC then return nil end
    local pos = #MAGIC + 1
    local version
    version, pos = love.data.unpack("<I4", blob, pos)
    if version ~= FORMAT_VERSION then return nil end
    local minX, minY, minZ, maxX, maxY, maxZ
    minX, minY, minZ, maxX, maxY, maxZ, pos = love.data.unpack("<dddddd", blob, pos)
    local groupCount
    groupCount, pos = love.data.unpack("<I4", blob, pos)
    local groups, total = {}, 0
    for g = 1, groupCount do
        local material, count
        material, pos = love.data.unpack("<s4", blob, pos)
        count, pos = love.data.unpack("<I4", blob, pos)
        local vertices = {}
        for v = 1, count do
            local a, b2, c, d, e, f, g2, h, i, j, k, l
            a, b2, c, d, e, f, g2, h, i, j, k, l, pos =
                love.data.unpack(VERTEX_FORMAT, blob, pos)
            vertices[v] = { a, b2, c, d, e, f, g2, h, i, j, k, l }
        end
        total = total + count
        groups[g] = { material = material, vertices = vertices }
    end
    return {
        groups = groups, vertexCount = total,
        bounds = { minX = minX, minY = minY, minZ = minZ,
            maxX = maxX, maxY = maxY, maxZ = maxZ },
    }
end

-- Every failure path degrades to "cache miss" rather than raising: the compiler
-- can always produce the answer, so a corrupt or unreadable entry must never be
-- able to stop the game starting.
function compiled_store.load(key)
    if not available() then return nil end
    local path = pathFor(key)
    if not love.filesystem.getInfo(path) then return nil end
    local blob = love.filesystem.read(path)
    if not blob then return nil end
    local ok, model = pcall(compiled_store.decode, blob)
    if not ok or type(model) ~= "table" or #model.groups == 0 then
        -- Drop it, so a corrupt entry is not re-read on every launch.
        pcall(love.filesystem.remove, path)
        return nil
    end
    return model
end

function compiled_store.save(key, model)
    if not available() then return false end
    if not model or not model.groups or #model.groups == 0 then return false end
    if not love.filesystem.getInfo(DIR) then
        if not love.filesystem.createDirectory(DIR) then return false end
    end
    local ok, blob = pcall(compiled_store.encode, model)
    if not ok then return false end
    return love.filesystem.write(pathFor(key), blob) and true or false
end

-- Test/tooling seam. Not wired to a CLI: entries are keyed by compiler version
-- and quality, so a stale one is unreachable rather than wrong.
function compiled_store.clear()
    if not available() then return false end
    if not love.filesystem.getInfo(DIR) then return true end
    for _, name in ipairs(love.filesystem.getDirectoryItems(DIR)) do
        love.filesystem.remove(DIR .. "/" .. name)
    end
    return true
end

return compiled_store
