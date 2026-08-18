if io and io.stdout and io.stdout.setvbuf then io.stdout:setvbuf("no") end

-- Studio-only persistent renderable worker entry point.
--
-- The Node host installs this over main.lua only inside a disposable compiled
-- Project stage. Runtime semantics remain entirely in the ordinary loader,
-- cli_tools, and presentation.editor_renderable_bridge modules. This file owns
-- only a tiny serial framing protocol so one already-initialized LÖVE process
-- can answer repeated transient Map snapshots.
local loader = require("engine.data.loader")
local cliTools = require("engine.cli_tools")
local bridge = require("presentation.editor_renderable_bridge")

local function flush()
    if io and io.stdout and io.stdout.flush then io.stdout:flush() end
end

local function reply(line)
    print(line)
    flush()
end

function love.load()
    loader.init()
    reply("RENDERABLE WORKER READY")

    while true do
        local line = io.read("*l")
        if not line or line == "QUIT" then break end

        local mapId, requestPath = line:match("^([^\t]+)\t(.+)$")
        if not mapId or not requestPath then
            reply("RENDERABLE WORKER ERROR\tinvalid request line")
            reply("RENDERABLE WORKER REQUEST DONE")
        else
            local ok, err = pcall(bridge.run, requestPath, mapId, loader, cliTools)
            if not ok then
                reply("RENDERABLE WORKER ERROR\t" .. tostring(err))
            end
            reply("RENDERABLE WORKER REQUEST DONE")
        end
    end

    love.event.quit(0)
    os.exit(0)
end
