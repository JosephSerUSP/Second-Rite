if io and io.stdout and io.stdout.setvbuf then io.stdout:setvbuf("no") end

-- #754 benchmark-only entry point. The Node harness copies this file over the
-- disposable staged runtime's main.lua; production main.lua is never changed.
-- It initializes the real loader once, then accepts transient renderable request
-- paths over stdin and delegates every request to the existing presentation
-- bridge authority. No geometry, map, or transport semantics live here.
local loader = require("engine.data.loader")
local cliTools = require("engine.cli_tools")
local bridge = require("presentation.editor_renderable_bridge")

local function flush()
    if io and io.stdout and io.stdout.flush then io.stdout:flush() end
end

function love.load()
    loader.init()
    print("RENDERABLE SERVER READY")
    flush()

    while true do
        local line = io.read("*l")
        if not line or line == "QUIT" then break end
        local mapId, requestPath = line:match("^([^\t]+)\t(.+)$")
        if not mapId or not requestPath then
            print("RENDERABLE SERVER ERROR\tinvalid request line")
            print("RENDERABLE SERVER REQUEST DONE")
            flush()
        else
            local ok, err = pcall(bridge.run, requestPath, mapId, loader, cliTools)
            if not ok then
                print("RENDERABLE SERVER ERROR\t" .. tostring(err))
            end
            print("RENDERABLE SERVER REQUEST DONE")
            flush()
        end
    end

    love.event.quit(0)
    os.exit(0)
end
