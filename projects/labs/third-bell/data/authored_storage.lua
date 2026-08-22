local json = require("data.json")

local authored_storage = {}
local MANIFEST_PATH = "data/authored_storage_manifest.json"
local VALID_KINDS = {
    document = true,
    ordered_collection = true,
    keyed_registry = true,
    semantic_config = true,
}
local VALID_REPRESENTATIONS = { monolith = true, fragments = true }
local cachedManifest = nil

local function readJson(path)
    local contents = love.filesystem.read(path)
    if not contents then error("Could not read authored JSON file: " .. path) end
    local ok, value = pcall(json.decode, contents)
    if not ok then
        error("Could not decode authored JSON file '" .. path .. "': " .. tostring(value))
    end
    return value
end

local function validateSpec(stem, spec, source)
    source = source or "<authored storage manifest>"
    if type(spec) ~= "table" then
        error("Authored resource '" .. stem .. "' has no storage metadata: " .. source)
    end
    if not VALID_KINDS[spec.kind] then
        error("Authored resource '" .. stem .. "' has unknown kind '" .. tostring(spec.kind) .. "': " .. source)
    end
    if not VALID_REPRESENTATIONS[spec.representation] then
        error("Authored resource '" .. stem .. "' has unknown representation '"
            .. tostring(spec.representation) .. "': " .. source)
    end
    if spec.kind == "document" and spec.representation ~= "monolith" then
        error("Document resource '" .. stem .. "' must use monolith representation: " .. source)
    end
    if spec.kind == "semantic_config" then
        if spec.representation ~= "fragments" or type(spec.modules) ~= "table" or #spec.modules == 0 then
            error("Semantic config resource '" .. stem .. "' must declare non-empty fragment modules: " .. source)
        end
        local seen = {}
        for _, module in ipairs(spec.modules) do
            if type(module) ~= "string" or not module:match("^[A-Za-z0-9_%-]+$") or seen[module] then
                error("Semantic config resource '" .. stem .. "' has invalid or duplicate module '" .. tostring(module) .. "': " .. source)
            end
            seen[module] = true
        end
    end
    return spec
end

function authored_storage.resetManifestCache()
    cachedManifest = nil
end

function authored_storage.manifest()
    if cachedManifest then return cachedManifest end
    local manifest = readJson(MANIFEST_PATH)
    if type(manifest) ~= "table" or type(manifest.resources) ~= "table" then
        error("Authored storage manifest must contain a resources object: " .. MANIFEST_PATH)
    end
    for stem, spec in pairs(manifest.resources) do
        validateSpec(stem, spec, MANIFEST_PATH)
    end
    cachedManifest = manifest
    return manifest
end

function authored_storage.resourceSpec(stem)
    local spec = authored_storage.manifest().resources[stem]
    if not spec then error("Authored resource '" .. stem .. "' is not declared in the storage manifest") end
    return validateSpec(stem, spec)
end

function authored_storage.bulkEditableResources()
    local out = {}
    for stem, spec in pairs(authored_storage.manifest().resources) do
        if spec.bulkEditable == true then table.insert(out, stem) end
    end
    table.sort(out)
    return out
end

local function validateFragmentPath(stem, entry, seen)
    if type(entry) ~= "string" or entry == "" then
        error(stem .. "/index.json entries must be non-empty filenames")
    end
    if entry:find("..", 1, true) or entry:sub(1, 1) == "/"
        or entry:sub(1, 1) == "\\" or entry:find("/", 1, true)
        or entry:find("\\", 1, true) then
        error(stem .. "/index.json contains an unsafe fragment path: " .. entry)
    end
    if not entry:lower():match("%.json$") then
        error(stem .. "/index.json fragment must end in .json: " .. entry)
    end
    local folded = entry:lower()
    if seen[folded] then error(stem .. "/index.json lists the same fragment twice: " .. entry) end
    seen[folded] = true
end

local function fragmentFiles(manifest, stem)
    local files = manifest
    if type(manifest) == "table" and type(manifest.files) == "table" then files = manifest.files end
    if type(files) ~= "table" or #files == 0 then
        error(stem .. "/index.json must be an array or { files = [...] }")
    end
    return files
end

local function orderedFragmentPaths(root, stem)
    local directory = root .. "/" .. stem
    local indexPath = directory .. "/index.json"
    if not love.filesystem.getInfo(indexPath) then
        error("Could not find ordered collection '" .. stem .. "' at " .. indexPath)
    end
    local files = fragmentFiles(readJson(indexPath), stem)
    local seen = {}
    local paths = { indexPath }
    for _, entry in ipairs(files) do
        validateFragmentPath(stem, entry, seen)
        local fragmentPath = directory .. "/" .. entry
        if not love.filesystem.getInfo(fragmentPath) then
            error(stem .. "/index.json references a missing fragment: " .. fragmentPath)
        end
        table.insert(paths, fragmentPath)
    end
    return paths
end

local function registryFragmentPaths(root, stem)
    local directory = root .. "/" .. stem
    if not love.filesystem.getInfo(directory) then
        error("Could not find registry '" .. stem .. "' at " .. directory)
    end
    local files = {}
    for _, name in ipairs(love.filesystem.getDirectoryItems(directory)) do
        if name:lower():match("%.json$") then
            if name:lower() == "index.json" then
                error("Registry '" .. stem .. "' must not use a shared index.json")
            end
            table.insert(files, name)
        end
    end
    table.sort(files)
    if #files == 0 then error("Registry '" .. stem .. "' has no JSON fragments: " .. directory) end
    local paths = {}
    for _, name in ipairs(files) do table.insert(paths, directory .. "/" .. name) end
    return paths
end

local function appendOrderedFragment(out, value, path)
    if type(value) ~= "table" then
        error("Ordered collection fragment must contain an object or array: " .. path)
    end
    if value.id ~= nil then
        table.insert(out, value)
        return
    end
    if #value == 0 then
        error("Ordered collection fragment is neither an object with id nor a non-empty array: " .. path)
    end
    for index, entry in ipairs(value) do
        if type(entry) ~= "table" then
            error("Ordered collection fragment array contains a non-object at "
                .. path .. "[" .. tostring(index) .. "]")
        end
        table.insert(out, entry)
    end
end

local function validateOrderedCollection(entries, stem, source)
    if type(entries) ~= "table" or #entries == 0 then
        error("Ordered collection '" .. stem .. "' is not a non-empty array: " .. source)
    end
    local ids = {}
    for index, entry in ipairs(entries) do
        if type(entry) ~= "table" or entry.id == nil then
            error("Ordered collection '" .. stem .. "' entry " .. tostring(index)
                .. " has no id: " .. source)
        end
        local key = tostring(entry.id)
        if ids[key] then
            error("Ordered collection '" .. stem .. "' has duplicate id '" .. key .. "' in " .. source)
        end
        ids[key] = true
    end
    return entries
end

local function validateRegistryRecord(record, stem, source)
    if type(record) ~= "table" then
        error("Registry '" .. stem .. "' record is not an object: " .. source)
    end
    if type(record.id) ~= "string" or record.id == "" then
        error("Registry '" .. stem .. "' record must own a non-empty string id: " .. source)
    end
    return record.id
end

local function validateRegistry(value, stem, source)
    if type(value) ~= "table" then error("Registry '" .. stem .. "' is not an object: " .. source) end
    local out = {}
    local count = 0
    for key, record in pairs(value) do
        if type(key) ~= "string" then
            error("Registry '" .. stem .. "' must be keyed by string ids: " .. source)
        end
        local id = validateRegistryRecord(record, stem, source .. "[" .. key .. "]")
        if key ~= id then
            error("Registry '" .. stem .. "' key '" .. key
                .. "' disagrees with record.id '" .. id .. "': " .. source)
        end
        if out[id] then error("Registry '" .. stem .. "' has duplicate id '" .. id .. "': " .. source) end
        out[id] = record
        count = count + 1
    end
    if count == 0 then error("Registry '" .. stem .. "' is empty: " .. source) end
    return out
end

function authored_storage.validateResource(stem, value, spec, source)
    spec = spec or authored_storage.resourceSpec(stem)
    source = source or ("<write " .. stem .. ">")
    validateSpec(stem, spec)
    if spec.kind == "ordered_collection" then return validateOrderedCollection(value, stem, source) end
    if spec.kind == "keyed_registry" then return validateRegistry(value, stem, source) end
    if spec.kind == "semantic_config" then
        if type(value) ~= "table" or #value > 0 then error("Semantic config '" .. stem .. "' must be an object: " .. source) end
        local expected = {}
        for _, module in ipairs(spec.modules) do expected[module] = true end
        for key, moduleValue in pairs(value) do
            if not expected[key] or type(moduleValue) ~= "table" then
                error("Semantic config '" .. stem .. "' has invalid module '" .. tostring(key) .. "': " .. source)
            end
            expected[key] = nil
        end
        for module in pairs(expected) do error("Semantic config '" .. stem .. "' is missing module '" .. module .. "': " .. source) end
        return value
    end
    if value == nil then error("Document resource '" .. stem .. "' cannot be nil: " .. source) end
    return value
end

local function rejectLegacyMonolith(root, stem)
    local monolith = root .. "/" .. stem .. ".json"
    if love.filesystem.getInfo(monolith) then
        error("Authored resource '" .. stem .. "' has both fragment storage and legacy monolith: " .. monolith)
    end
end

local function semanticModulePaths(root, stem, spec)
    local directory = root .. "/" .. stem
    if not love.filesystem.getInfo(directory) then error("Could not find semantic config directory: " .. directory) end
    local expected, paths = {}, {}
    for _, module in ipairs(spec.modules) do
        local name = module .. ".json"
        local modulePath = directory .. "/" .. name
        if not love.filesystem.getInfo(modulePath) then error("Semantic config '" .. stem .. "' is missing module: " .. modulePath) end
        expected[name] = true
        table.insert(paths, modulePath)
    end
    for _, name in ipairs(love.filesystem.getDirectoryItems(directory)) do
        if name:lower():match("%.json$") and not expected[name] then error("Semantic config '" .. stem .. "' has undeclared module: " .. directory .. "/" .. name) end
    end
    return paths
end

function authored_storage.authoritativeFiles(root, stem, spec)
    spec = spec or authored_storage.resourceSpec(stem)
    validateSpec(stem, spec)
    if spec.representation == "monolith" then
        local monolith = root .. "/" .. stem .. ".json"
        if not love.filesystem.getInfo(monolith) then error("Could not find authored document: " .. monolith) end
        return { monolith }, "monolith"
    end
    rejectLegacyMonolith(root, stem)
    if spec.kind == "ordered_collection" then return orderedFragmentPaths(root, stem), "fragments" end
    if spec.kind == "keyed_registry" then return registryFragmentPaths(root, stem), "fragments" end
    if spec.kind == "semantic_config" then return semanticModulePaths(root, stem, spec), "fragments" end
    error("Document resource '" .. stem .. "' cannot use fragmented storage")
end

function authored_storage.loadResource(root, stem, spec)
    spec = spec or authored_storage.resourceSpec(stem)
    validateSpec(stem, spec)
    if spec.representation == "monolith" then
        local source = root .. "/" .. stem .. ".json"
        local value = authored_storage.validateResource(stem, readJson(source), spec, source)
        return value, "monolith"
    end
    rejectLegacyMonolith(root, stem)
    if spec.kind == "ordered_collection" then
        local paths = orderedFragmentPaths(root, stem)
        local out = {}
        for index = 2, #paths do appendOrderedFragment(out, readJson(paths[index]), paths[index]) end
        return validateOrderedCollection(out, stem, paths[1]), "fragments"
    end
    if spec.kind == "keyed_registry" then
        local out = {}
        for _, fragmentPath in ipairs(registryFragmentPaths(root, stem)) do
            local record = readJson(fragmentPath)
            local id = validateRegistryRecord(record, stem, fragmentPath)
            if out[id] then error("Registry '" .. stem .. "' has duplicate id '" .. id .. "': " .. fragmentPath) end
            out[id] = record
        end
        return out, "fragments"
    end
    if spec.kind == "semantic_config" then
        local out = {}
        for _, module in ipairs(spec.modules) do out[module] = readJson(root .. "/" .. stem .. "/" .. module .. ".json") end
        return authored_storage.validateResource(stem, out, spec, root .. "/" .. stem), "fragments"
    end
    error("Document resource '" .. stem .. "' cannot use fragmented storage")
end

function authored_storage.loadOrderedCollection(root, stem, spec)
    spec = spec or authored_storage.resourceSpec(stem)
    if spec.kind ~= "ordered_collection" then error("Authored resource '" .. stem .. "' is not an ordered collection") end
    return authored_storage.loadResource(root, stem, spec)
end

function authored_storage.loadRegistry(root, stem, spec)
    spec = spec or authored_storage.resourceSpec(stem)
    if spec.kind ~= "keyed_registry" then error("Authored resource '" .. stem .. "' is not a keyed registry") end
    return authored_storage.loadResource(root, stem, spec)
end

function authored_storage.loadSemanticConfig(root, stem, spec)
    spec = spec or authored_storage.resourceSpec(stem)
    if spec.kind ~= "semantic_config" then error("Authored resource '" .. stem .. "' is not semantic config") end
    return authored_storage.loadResource(root, stem, spec)
end

local function hexBytes(value)
    return (tostring(value):gsub(".", function(char) return string.format("%02x", string.byte(char)) end))
end

local function safeFragmentCandidate(id, reserved)
    id = tostring(id)
    reserved = reserved or {}
    local folded = {}
    for _, name in ipairs(reserved) do folded[name:lower()] = true end
    local candidate = nil
    if id:match("^[A-Za-z0-9%._%-]+$") and id ~= "." and id ~= ".." and id:lower() ~= "index" then
        candidate = id .. ".json"
    end
    if candidate and not folded[candidate:lower()] then return candidate end
    local slug = id:lower():gsub("[^a-z0-9]+", "-"):gsub("^%-+", ""):gsub("%-+$", "")
    if slug == "" then slug = "record" end
    candidate = slug .. "--" .. hexBytes(id) .. ".json"
    if folded[candidate:lower()] then error("Fragment filename collision for id '" .. id .. "': " .. candidate) end
    return candidate
end

local function defaultAdapter()
    local source = love.filesystem.getSource()
    return {
        writeJson = function(path, value)
            local encoded = json.encode(value)
            local absolute = source .. "/" .. path
            local file, err = io.open(absolute, "w")
            if not file then error("Could not write authored project file '" .. absolute .. "': " .. tostring(err)) end
            file:write(encoded)
            file:close()
            love.filesystem.write(path, encoded)
        end,
        remove = function(path)
            os.remove(source .. "/" .. path)
            if love.filesystem.remove then love.filesystem.remove(path) end
        end,
    }
end

local function directoryJsonNames(directory)
    local names = {}
    if not love.filesystem.getInfo(directory) then return names end
    for _, name in ipairs(love.filesystem.getDirectoryItems(directory)) do
        if name:lower():match("%.json$") then table.insert(names, name) end
    end
    table.sort(names)
    return names
end

function authored_storage.writeResource(root, stem, value, adapter, spec)
    spec = spec or authored_storage.resourceSpec(stem)
    local validated = authored_storage.validateResource(stem, value, spec)
    adapter = adapter or defaultAdapter()

    if spec.representation == "monolith" then
        adapter.writeJson(root .. "/" .. stem .. ".json", validated)
        return "monolith"
    end

    rejectLegacyMonolith(root, stem)
    local directory = root .. "/" .. stem
    if not love.filesystem.getInfo(directory) then
        error("Fragment directory does not exist: " .. directory)
    end

    local keep = {}
    if spec.kind == "ordered_collection" then
        local reserved = {}
        local planned = {}
        for _, entry in ipairs(validated) do
            local name = safeFragmentCandidate(entry.id, reserved)
            table.insert(reserved, name)
            table.insert(planned, { name = name, value = entry })
            keep[name:lower()] = true
        end
        for _, fragment in ipairs(planned) do
            adapter.writeJson(directory .. "/" .. fragment.name, fragment.value)
        end
        local files = {}
        for _, fragment in ipairs(planned) do table.insert(files, fragment.name) end
        adapter.writeJson(directory .. "/index.json", { files = files })
        keep["index.json"] = true
    elseif spec.kind == "keyed_registry" then
        local sourceById = {}
        local existingNames = directoryJsonNames(directory)
        for _, name in ipairs(existingNames) do
            if name:lower() == "index.json" then
                error("Registry '" .. stem .. "' must not use a shared index.json")
            end
            local record = readJson(directory .. "/" .. name)
            sourceById[validateRegistryRecord(record, stem, directory .. "/" .. name)] = name
        end
        local ids = {}
        for id in pairs(validated) do table.insert(ids, id) end
        table.sort(ids)
        local reserved = {}
        for _, name in ipairs(existingNames) do table.insert(reserved, name) end
        for _, id in ipairs(ids) do
            local name = sourceById[id]
            if not name then
                name = safeFragmentCandidate(id, reserved)
                table.insert(reserved, name)
            end
            keep[name:lower()] = true
            adapter.writeJson(directory .. "/" .. name, validated[id])
        end
    elseif spec.kind == "semantic_config" then
        for _, module in ipairs(spec.modules) do
            keep[(module .. ".json"):lower()] = true
            adapter.writeJson(directory .. "/" .. module .. ".json", validated[module])
        end
    else
        error("Document resource '" .. stem .. "' cannot use fragmented storage")
    end

    for _, name in ipairs(directoryJsonNames(directory)) do
        if not keep[name:lower()] then adapter.remove(directory .. "/" .. name) end
    end
    return "fragments"
end

function authored_storage.snapshotResource(root, stem, destinationPath, adapter, spec)
    local value = authored_storage.loadResource(root, stem, spec)
    adapter = adapter or defaultAdapter()
    adapter.writeJson(destinationPath, value)
    return destinationPath
end

return authored_storage
