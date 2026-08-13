local json = require("data.json")

local config = {}

-- Engine-wide capacity defaults. system.json may override them, but they are
-- structural limits rather than ordinary optional presentation settings, so a
-- config reload must never make them disappear when authored data omits an
-- override.
local LIMIT_DEFAULTS = {
    MAX_PARTY_SIZE = 4,
    MAX_RESERVE_SIZE = 4,
    MAX_STORAGE_SIZE = 99,
}

local function applyLimitDefaults()
    for key, value in pairs(LIMIT_DEFAULTS) do
        if config[key] == nil then config[key] = value end
    end
end

function config.load()
    -- A runnable Project has one authored data authority: data/system.json.
    -- External Projects reach the runtime through #358's staged Project root;
    -- same-root development reads the same path directly.
    local path = "data/system.json"
    if love.filesystem.getInfo(path) then
        local contents = love.filesystem.read(path)
        if contents then
            local data = json.decode(contents)
            if data then
                -- Clear existing keys except load function
                for k, _ in pairs(config) do
                    if k ~= "load" then
                        config[k] = nil
                    end
                end

                -- Populate with new data
                for k, v in pairs(data) do
                    if k ~= "load" then
                        config[k] = v
                    end
                end
            end
        end
    end

    -- Restore missing structural limits on every load while still honoring an
    -- authored system.json override when one exists.
    applyLimitDefaults()
end

config.load()

return config