-- Persistent and release-time store for compiled geometry (#161).
--
-- The geometry compiler is deterministic and expensive. The in-memory cache in
-- geometry/init.lua removes repeat compilation inside one process; this module
-- gives the same neutral compiler output two longer-lived homes:
--
--   assets/generated/geometry/   release prebakes staged by the exporter
--   geocache/                    per-machine development/runtime cache
--
-- Release prebakes are checked first. They are derived build artifacts, never
-- authored source truth: a manifest validates compiler format plus content
-- digests for every declared source before a prebake is accepted. Any missing,
-- stale, malformed, or incompatible artifact is an ordinary cache miss and the
-- deterministic compiler remains the fallback.
--
-- What is stored is the model as engine.geometry.model's Builder:build()
-- returns it -- geometry only. Materials, textures and GPU meshes are NOT
-- stored. presentation.mesh.finalize attaches those afterwards through
-- engine.geometry's injected materialization seam.
local compiled_store = {}
local buildProfiler = require("engine.map_build_profiler")

-- Bump when the binary encoding changes. Entries with a different version are
-- rejected rather than migrated: the compiler is the source of truth.
local FORMAT_VERSION = 2
local MANIFEST_VERSION = 1
local MAGIC = "SRGEO"
local CACHE_DIR = "geocache"
local PREBAKE_DIR = "assets/generated/geometry"
local PREBAKE_MANIFEST = PREBAKE_DIR .. "/manifest.json"

compiled_store.FORMAT_VERSION = FORMAT_VERSION
compiled_store.MANIFEST_VERSION = MANIFEST_VERSION
compiled_store.PREBAKE_DIR = PREBAKE_DIR
compiled_store.PREBAKE_MANIFEST = PREBAKE_MANIFEST

-- LÖVE runs LuaJIT (Lua 5.1), which has no string.pack/string.unpack -- those
-- arrived in 5.3. love.data provides the same format strings.
local FIELDS = 12
local VERTEX_FORMAT = "<" .. string.rep("d", FIELDS)

-- float64, not float32. Doubles round-trip a Lua number exactly, so a model
-- restored from disk is bit-identical to a freshly compiled one and golden
-- screenshots cannot shift depending on whether a cache/prebake was warm.
local function available()
    return (love and love.filesystem and love.data) and true or false
end

local function digest(value)
    return love.data.encode("string", "hex", love.data.hash("md5", value))
end

function compiled_store.artifactName(key)
    if not available() or type(key) ~= "string" then return nil end
    return digest(key) .. ".geo"
end

function compiled_store.cachePath(key)
    local name = compiled_store.artifactName(key)
    return name and (CACHE_DIR .. "/" .. name) or nil
end

function compiled_store.prebakePath(key)
    local name = compiled_store.artifactName(key)
    return name and (PREBAKE_DIR .. "/" .. name) or nil
end

function compiled_store.fileDigest(path)
    if not available() or type(path) ~= "string" then return nil end
    local contents = love.filesystem.read(path)
    if not contents then return nil end
    return digest(contents)
end

local function safeRelativePath(path)
    if type(path) ~= "string" or path == "" then return false end
    if path:match("^[A-Za-z]:") or path:sub(1, 1) == "/" or path:sub(1, 1) == "\\" then
        return false
    end
    for part in path:gmatch("[^/\\]+") do
        if part == ".." then return false end
    end
    return true
end

-- FORMAT_VERSION 2 embeds the full deterministic cache identity in the blob.
-- The file name is merely a compact lookup hash; accepting a file whose body
-- declares a different identity would make accidental/malicious renames able
-- to bypass compiler/quality/source selection.
function compiled_store.encode(model, identity)
    if type(identity) ~= "string" or identity == "" then
        error("compiled geometry encode requires a non-empty identity", 0)
    end
    local out = {}
    out[#out + 1] = MAGIC
    out[#out + 1] = love.data.pack("string", "<I4", FORMAT_VERSION)
    out[#out + 1] = love.data.pack("string", "<s4", identity)
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

function compiled_store.decode(blob, expectedIdentity)
    if type(blob) ~= "string" or #blob < #MAGIC + 4 then return nil, "truncated header" end
    if blob:sub(1, #MAGIC) ~= MAGIC then return nil, "bad magic" end
    local pos = #MAGIC + 1
    local version
    version, pos = love.data.unpack("<I4", blob, pos)
    if version ~= FORMAT_VERSION then return nil, "format version mismatch" end
    local identity
    identity, pos = love.data.unpack("<s4", blob, pos)
    if expectedIdentity and identity ~= expectedIdentity then
        return nil, "identity mismatch"
    end
    local minX, minY, minZ, maxX, maxY, maxZ
    minX, minY, minZ, maxX, maxY, maxZ, pos = love.data.unpack("<dddddd", blob, pos)
    local groupCount
    groupCount, pos = love.data.unpack("<I4", blob, pos)
    local groups, total = {}, 0
    for groupIndex = 1, groupCount do
        local material, count
        material, pos = love.data.unpack("<s4", blob, pos)
        count, pos = love.data.unpack("<I4", blob, pos)
        local vertices = {}
        for vertexIndex = 1, count do
            local a, b2, c, d, e, f, g2, h, i, j, k, l
            a, b2, c, d, e, f, g2, h, i, j, k, l, pos =
                love.data.unpack(VERTEX_FORMAT, blob, pos)
            vertices[vertexIndex] = { a, b2, c, d, e, f, g2, h, i, j, k, l }
        end
        total = total + count
        groups[groupIndex] = { material = material, vertices = vertices }
    end
    return {
        groups = groups, vertexCount = total,
        bounds = { minX = minX, minY = minY, minZ = minZ,
            maxX = maxX, maxY = maxY, maxZ = maxZ },
    }, identity
end

local manifestState = nil
local warnedManifest = false

local function compilerVersionFromKey(key)
    local value = key:match("^atlas:v(%d+):") or key:match("^v(%d+)|")
    return value and tonumber(value) or nil
end

-- Export provenance is deliberately conservative: one changed declared source
-- invalidates the whole release prebake set. This may recompile more than the
-- theoretical minimum in a modified staging tree, but it can never select a
-- stale mesh. Release packages are immutable, so the verification is cached for
-- the process after the first successful/failed check.
function compiled_store.validateManifest(manifest, requestedKey)
    if type(manifest) ~= "table" then return false, "manifest is not an object" end
    if manifest.version ~= MANIFEST_VERSION then return false, "manifest version mismatch" end
    if manifest.formatVersion ~= FORMAT_VERSION then return false, "binary format version mismatch" end
    local requestedCompiler = requestedKey and compilerVersionFromKey(requestedKey) or nil
    if requestedCompiler and tonumber(manifest.compilerVersion) ~= requestedCompiler then
        return false, "compiler version mismatch"
    end
    if type(manifest.sourceFiles) ~= "table" then return false, "sourceFiles missing" end
    for _, source in ipairs(manifest.sourceFiles) do
        if type(source) ~= "table" or not safeRelativePath(source.path)
                or type(source.digest) ~= "string" or source.digest == "" then
            return false, "invalid source provenance entry"
        end
        local actual = compiled_store.fileDigest(source.path)
        if not actual then return false, "source missing: " .. tostring(source.path) end
        if actual ~= source.digest then return false, "source changed: " .. tostring(source.path) end
    end
    if type(manifest.entries) ~= "table" then return false, "entries missing" end
    return true
end

local function loadManifest(requestedKey)
    if manifestState ~= nil then
        if not manifestState.valid then return nil, manifestState.reason end
        local requestedCompiler = compilerVersionFromKey(requestedKey)
        if requestedCompiler and manifestState.compilerVersion ~= requestedCompiler then
            return nil, "compiler version mismatch"
        end
        return manifestState.manifest
    end
    if not love.filesystem.getInfo(PREBAKE_MANIFEST) then
        manifestState = { valid = false, reason = "manifest absent" }
        return nil, manifestState.reason
    end
    local text = love.filesystem.read(PREBAKE_MANIFEST)
    if not text then
        manifestState = { valid = false, reason = "manifest unreadable" }
        return nil, manifestState.reason
    end
    local ok, manifest = pcall(require("engine.data.json").decode, text)
    if not ok then
        manifestState = { valid = false, reason = "manifest JSON malformed" }
        return nil, manifestState.reason
    end
    local valid, reason = compiled_store.validateManifest(manifest, requestedKey)
    if not valid then
        manifestState = { valid = false, reason = reason }
        if reason ~= "manifest absent" and not warnedManifest then
            warnedManifest = true
            print("[geometry] release prebakes ignored: " .. tostring(reason))
        end
        return nil, reason
    end
    local entriesByFile = {}
    for _, entry in ipairs(manifest.entries) do
        if type(entry) ~= "table" or type(entry.file) ~= "string"
                or type(entry.key) ~= "string" or not safeRelativePath(entry.file)
                or entry.file:find("[/\\]") then
            manifestState = { valid = false, reason = "invalid prebake manifest entry" }
            return nil, manifestState.reason
        end
        entriesByFile[entry.file] = entry
    end
    manifestState = {
        valid = true,
        manifest = manifest,
        entriesByFile = entriesByFile,
        compilerVersion = tonumber(manifest.compilerVersion),
    }
    return manifest
end

-- Test/tooling seam: source trees can change inside one test process, while a
-- shipped archive cannot. Resetting forces provenance to be re-read.
function compiled_store.resetPrebakeManifestCache()
    manifestState = nil
    warnedManifest = false
end

function compiled_store.loadPrebake(key)
    if not available() then return nil end
    local manifest = loadManifest(key)
    if not manifest or not manifestState or not manifestState.valid then return nil end
    local name = compiled_store.artifactName(key)
    local entry = manifestState.entriesByFile[name]
    if not entry or entry.key ~= key then return nil end
    local path = PREBAKE_DIR .. "/" .. name
    if not love.filesystem.getInfo(path) then return nil end

    local finish = buildProfiler.span("geometry.prebake.deserialize", "cpu")
    local blob = love.filesystem.read(path)
    local ok, model, reason
    if blob then ok, model, reason = pcall(compiled_store.decode, blob, key) end
    finish()
    if not blob or not ok or type(model) ~= "table" or #model.groups == 0 then
        if not warnedManifest then
            warnedManifest = true
            print("[geometry] release prebake ignored for " .. tostring(name)
                .. ": " .. tostring(ok and reason or model or "unreadable artifact"))
        end
        return nil
    end
    return model
end

local function loadCache(key)
    local path = compiled_store.cachePath(key)
    if not path or not love.filesystem.getInfo(path) then return nil end
    local blob = love.filesystem.read(path)
    if not blob then return nil end
    local ok, model = pcall(compiled_store.decode, blob, key)
    if not ok or type(model) ~= "table" or #model.groups == 0 then
        -- Save-directory data is disposable; remove corrupt entries so they are
        -- not re-read every launch. Source-tree prebakes are never mutated.
        pcall(love.filesystem.remove, path)
        return nil
    end
    return model
end

-- Release prebake first, then the development/per-machine persistent cache.
-- Every failure degrades to a cache miss: the deterministic compiler remains
-- the safe fallback for Test Play and for an incompatible release artifact.
function compiled_store.load(key)
    if not available() then return nil end
    local prebaked = compiled_store.loadPrebake(key)
    if prebaked then return prebaked, "prebake" end
    local cached = loadCache(key)
    if cached then return cached, "cache" end
    return nil
end

function compiled_store.save(key, model)
    if not available() then return false end
    if type(key) ~= "string" or key == "" then return false end
    if not model or not model.groups or #model.groups == 0 then return false end
    if not love.filesystem.getInfo(CACHE_DIR) then
        if not love.filesystem.createDirectory(CACHE_DIR) then return false end
    end
    local ok, blob = pcall(compiled_store.encode, model, key)
    if not ok then return false end
    return love.filesystem.write(compiled_store.cachePath(key), blob) and true or false
end

function compiled_store.clear()
    if not available() then return false end
    if not love.filesystem.getInfo(CACHE_DIR) then return true end
    for _, name in ipairs(love.filesystem.getDirectoryItems(CACHE_DIR)) do
        love.filesystem.remove(CACHE_DIR .. "/" .. name)
    end
    return true
end

return compiled_store
