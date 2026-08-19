-- Persistent Studio Map-renderable authority host (#754).
--
-- This is intentionally not a general RPC daemon. It initializes the ordinary
-- runtime loader once, then accepts exactly one serial command shape for the
-- existing editor_renderable_bridge. Every request is a transient file inside
-- the disposable staged Project and is tagged with an explicit request id so
-- stdout noise or a stale frame cannot be mistaken for another request.
if io.stdout and io.stdout.setvbuf then io.stdout:setvbuf("no") end

local loader = require("engine.data.loader")
local cliTools = require("engine.cli_tools")
local bridge = require("presentation.editor_renderable_bridge")

local REQUEST = "RENDERABLE WORKER REQUEST"
local DONE = "RENDERABLE WORKER REQUEST DONE"
local ERROR = "RENDERABLE WORKER ERROR"

local function protocolError(requestId, value)
    local message = tostring(value or "runtime renderable worker failed")
        :gsub("[%c]", " ")
    if #message > 8192 then message = message:sub(1, 8192) end
    print(ERROR .. "\t" .. tostring(requestId or 0) .. "\t" .. message)
end

local function finish(requestId)
    print(DONE .. "\t" .. tostring(requestId or 0))
end

function love.load()
    loader.init()
    print("RENDERABLE WORKER READY")

    while true do
        local line = io.read("*l")
        if line == nil or line == "QUIT" then break end

        local requestId, mapId, requestPath = line:match(
            "^" .. REQUEST .. "\t(%d+)\t([^\t\r\n]+)\t([^\t\r\n]+)$"
        )
        if not requestId or not mapId or not requestPath then
            local recoverId = line:match("^" .. REQUEST .. "\t(%d+)") or "0"
            protocolError(recoverId, "invalid request line")
            finish(recoverId)
        else
            local ok, err = pcall(bridge.run, requestPath, mapId, loader, cliTools)
            if not ok then protocolError(requestId, err) end
            finish(requestId)
        end
    end

    if love.event and love.event.quit then love.event.quit(0) end
    os.exit(0)
end
