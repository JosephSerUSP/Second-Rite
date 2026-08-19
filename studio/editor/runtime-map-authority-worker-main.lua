-- Persistent revision-scoped Map authority for Thestra Studio (#739).
--
-- This keeps #754's proven LÖVE worker lifecycle deliberately intact: initialize
-- the ordinary runtime data loader from love.load(), emit READY, then service a
-- single serial stdin protocol until QUIT. The only extension is a typed route
-- selecting one of two existing runtime-owned Map bridges. Map Inspection is
-- lazy-required on its first request so its dependency initialization belongs
-- to the request clock, not the process-startup clock.
if io.stdout and io.stdout.setvbuf then io.stdout:setvbuf("no") end

local loader = require("engine.data.loader")
local cliTools = require("engine.cli_tools")
local renderableBridge = require("presentation.editor_renderable_bridge")
local inspectionBridge = nil

local REQUEST = "RENDERABLE WORKER REQUEST"
local DONE = "RENDERABLE WORKER REQUEST DONE"
local ERROR = "RENDERABLE WORKER ERROR"

local function protocolError(requestId, value)
    local message = tostring(value or "runtime Map authority worker failed")
        :gsub("[%c]", " ")
    if #message > 8192 then message = message:sub(1, 8192) end
    print(ERROR .. "\t" .. tostring(requestId or 0) .. "\t" .. message)
end

local function finish(requestId)
    print(DONE .. "\t" .. tostring(requestId or 0))
end

local function parseRoute(route)
    local kind, mapId = tostring(route or ""):match("^([%a]+):(.+)$")
    if (kind ~= "renderable" and kind ~= "inspection") or not mapId or mapId == "" then
        error("unknown Map authority route: " .. tostring(route), 0)
    end
    return kind, mapId
end

local function runInspection(requestPath, mapId)
    if not inspectionBridge then
        inspectionBridge = require("presentation.editor_map_inspection_bridge")
    end
    inspectionBridge.run(requestPath, mapId, loader)
end

function love.load()
    loader.init()
    print("RENDERABLE WORKER READY")

    while true do
        local line = io.read("*l")
        if line == nil or line == "QUIT" then break end

        local requestId, route, requestPath = line:match(
            "^" .. REQUEST .. "\t(%d+)\t([^\t\r\n]+)\t([^\t\r\n]+)$"
        )
        if not requestId or not route or not requestPath then
            local recoverId = line:match("^" .. REQUEST .. "\t(%d+)") or "0"
            protocolError(recoverId, "invalid request line")
            finish(recoverId)
        else
            local ok, err = pcall(function()
                local kind, mapId = parseRoute(route)
                if kind == "renderable" then
                    renderableBridge.run(requestPath, mapId, loader, cliTools)
                else
                    runInspection(requestPath, mapId)
                end
            end)
            if not ok then protocolError(requestId, err) end
            finish(requestId)
        end
    end

    if love.event and love.event.quit then love.event.quit(0) end
    os.exit(0)
end
