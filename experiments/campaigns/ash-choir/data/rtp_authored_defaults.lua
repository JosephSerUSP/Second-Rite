local json = require("data.json")

local defaults = {}

local function readJson(path, label)
    local contents = love.filesystem.read(path)
    if not contents then error((label or "authored resource") .. " is missing: " .. path) end
    local ok, value = pcall(json.decode, contents)
    if not ok then error((label or "authored resource") .. " is invalid JSON: " .. path .. ": " .. tostring(value)) end
    return value
end

local function pinnedRevision(system)
    local rtp = system and system.rtp
    if rtp == nil then return nil end
    if type(rtp) ~= "table" or type(rtp.revision) ~= "string" or rtp.revision == "" then
        error("Project system.rtp.revision must be a non-empty string when RTP inheritance is declared")
    end
    local value = rtp.revision
    if value == "." or value == ".." or not value:match("^[A-Za-z0-9][A-Za-z0-9%._%-]*$") then
        error("Project system.rtp.revision is not a safe revision identifier: " .. tostring(value))
    end
    return value
end

local function safeRelative(value)
    if type(value) ~= "string" or value == "" then return false end
    if value:sub(1, 1) == "/" or value:sub(1, 1) == "\\" or value:match("^%a:[/\\]") then return false end
    for segment in value:gmatch("[^/\\]+") do
        if segment == ".." then return false end
    end
    return true
end

local function manifestEnginePath(revision)
    local manifestPath = "rtp/revisions/" .. revision .. "/manifest.json"
    local manifest = readJson(manifestPath, "pinned RTP manifest")
    if type(manifest) ~= "table" or manifest.version ~= 1 or manifest.revision ~= revision then
        error("Pinned RTP revision " .. revision .. " manifest must declare version 1 and matching revision")
    end
    local authored = manifest.authored
    local relative = authored and authored.engineRegistry
    if not safeRelative(relative) then
        error("Pinned RTP revision " .. revision .. " does not declare a safe authored.engineRegistry")
    end
    return "rtp/revisions/" .. revision .. "/" .. relative
end

function defaults.loadEngine(root, system)
    local resolutionPath = root .. "/authored_resolution.json"
    if love.filesystem.getInfo(resolutionPath) then
        local resolution = readJson(resolutionPath, "authored resolution metadata")
        if type(resolution) ~= "table" or resolution.materialized ~= true or type(resolution.resources) ~= "table"
                or resolution.resources.engineRegistry == nil then
            error("authored_resolution.json is not valid materialization metadata")
        end
        return readJson(root .. "/engine.json", "materialized engineRegistry"), resolution.resources.engineRegistry
    end

    local revision = pinnedRevision(system)
    if not revision then
        return readJson(root .. "/engine.json", "Project engineRegistry"), { provider = { kind = "project", id = "project" } }
    end

    local basePath = manifestEnginePath(revision)
    if not love.filesystem.getInfo(basePath) then
        error("Pinned RTP revision " .. revision .. " does not provide inherited engineRegistry baseline: " .. basePath)
    end
    local base = readJson(basePath, "RTP engineRegistry baseline")
    local projectPath = root .. "/engine.json"
    local project = love.filesystem.getInfo(projectPath) and readJson(projectPath, "Project engineRegistry policy") or {}
    for key in pairs(project) do
        if base[key] ~= nil then
            error("engineRegistry ownership collision at top-level key '" .. tostring(key)
                .. "'; RTP baseline and Project policy must be disjoint")
        end
    end
    local out = {}
    for key, value in pairs(base) do out[key] = value end
    for key, value in pairs(project) do out[key] = value end
    return out, { provider = { kind = "composed", id = "engine-registry",
        base = { kind = "rtp", id = "thestra-rtp", revision = revision },
        overlay = { kind = "project", id = "project" } } }
end

return defaults
