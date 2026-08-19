-- Persistent revision-scoped Map authority for Thestra Studio.
--
-- One staged LÖVE generation answers both compact renderable and semantic Map
-- inspection requests. Each request still goes through the existing runtime
-- bridge module that owns that fact; this file only multiplexes the protocol.
-- The Node owner serializes requests, supplies request IDs and kills/rebuilds
-- this process on revision invalidation, timeout or protocol failure.

local loader = require("engine.loader")
local cliTools = require("engine.cli_tools")
local renderableBridge = require("presentation.editor_renderable_bridge")
local inspectionBridge = require("presentation.editor_map_inspection_bridge")

loader.init()

local REQUEST_MARKER = "RENDERABLE WORKER REQUEST"
local DONE_MARKER = "RENDERABLE WORKER REQUEST DONE"
local ERROR_MARKER = "RENDERABLE WORKER ERROR"

local function flush()
    if io and io.stdout and io.stdout.flush then io.stdout:flush() end
end

local function sanitizeError(err)
    return tostring(err):gsub("[\r\n\t]", " ")
end

local function parseRoute(route)
    local kind, mapId = tostring(route or ""):match("^([%a]+):(.+)$")
    if (kind ~= "renderable" and kind ~= "inspection") or not mapId or mapId == "" then
        error("unknown Map authority route: " .. tostring(route), 0)
    end
    return kind, mapId
end

print("RENDERABLE WORKER READY")
flush()

function love.update()
    while true do
        local line = io.read("*l")
        if not line then
            love.event.quit(0)
            return
        end
        if line == "QUIT" then
            love.event.quit(0)
            return
        end

        local requestId, route, requestPath = line:match(
            "^" .. REQUEST_MARKER .. "\t([0-9]+)\t([^\t]+)\t([^\t]+)$"
        )
        if not requestId then
            print(ERROR_MARKER .. "\t0\tmalformed request line")
            flush()
        else
            local ok, err = pcall(function()
                local kind, mapId = parseRoute(route)
                if kind == "renderable" then
                    renderableBridge.run(requestPath, mapId, loader, cliTools)
                else
                    inspectionBridge.run(requestPath, mapId, loader)
                end
            end)
            if not ok then
                print(ERROR_MARKER .. "\t" .. requestId .. "\t" .. sanitizeError(err))
            end
            print(DONE_MARKER .. "\t" .. requestId)
            flush()
        end
    end
end
