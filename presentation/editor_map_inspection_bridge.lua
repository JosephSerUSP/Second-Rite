-- Read-only semantic Map inspection bridge for Thestra Studio.
-- The request is transient authored data. The engine resolves it through
-- exploration.loadMap in an isolated session and returns semantic facts only;
-- it never writes project data or the player's runtime instance.
local bridge = {}

local function readRequest(path)
    local json = require("data.json")
    local text, err = love.filesystem.read(path)
    if not text then error("map inspection request could not be read: " .. tostring(err), 0) end
    local decoded = json.decode(text)
    if type(decoded) ~= "table" or type(decoded.map) ~= "table" then
        error("map inspection request needs a map snapshot", 0)
    end
    return decoded
end

function bridge.run(requestPath, mapId, loader)
    local json = require("data.json")
    local payload
    local ok, err = pcall(function()
        local request = readRequest(requestPath)
        local requestedId = request.map.id
        if requestedId == nil then requestedId = mapId end
        if tostring(requestedId) ~= tostring(mapId) then
            error("map inspection request id does not match preview-map-inspection id", 0)
        end
        payload = require("engine.map_inspection").resolve(
            loader, mapId, request.map, tonumber(request.seed))
    end)
    if not ok then payload = { error = tostring(err) } end

    print("MAP INSPECTION BEGIN")
    print(json.encode(payload))
    print("MAP INSPECTION END")
end

return bridge
