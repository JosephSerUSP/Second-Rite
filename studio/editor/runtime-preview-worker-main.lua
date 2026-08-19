-- Persistent Studio PREVIEW authority host (#794 follow-up).
--
-- Sibling of runtime-renderable-worker-main.lua, sharing its protocol and its
-- Node-side lifecycle. That worker serves Map renderables; this one serves the
-- preview commands Studio used to pay a cold LÖVE boot for on every request:
-- scene, window, font, fog and animation previews, each 3-9 s measured.
--
-- These are NOT candidates for shared executable semantics. Every one of them
-- renders pixels through love.graphics -- a canvas, the real font stack, the
-- gradient shader, Effekseer -- and returns a base64 PNG. They are exactly the
-- runtime-bound class #754 says persistence IS warranted for, as opposed to
-- declarative surfaces like sprite metadata, which moved to shared semantics
-- instead and no longer reach a subprocess at all.
--
-- Each command prints the same envelope its cold `lovec . <command>` run
-- printed, so the Node parsers are unchanged and cold remains a usable
-- fallback and reference.
if io.stdout and io.stdout.setvbuf then io.stdout:setvbuf("no") end

local json = require("engine.data.json")
local loader = require("engine.data.loader")
local cliTools = require("engine.cli_tools")
local presentation_surface = require("presentation.surface")

-- This file REPLACES main.lua in the staged Project, so main.lua's module-level
-- requires do not run. Several of them are side-effecting: `engine.scenes.battle`
-- registers scene behaviour, and the presentation modules populate the
-- registries `scene_host.draw` consults.
--
-- Skipping them does not fail loudly. It quietly changes answers: a scene
-- preview came back `frameKind = "declarative"` instead of `"windows"` because
-- nothing had registered the window renderers, with a byte-identical image to
-- hide it. The cold-vs-warm parity gate is what caught that, and is what will
-- catch this list drifting away from main.lua's.
local scene_host = require("engine.scene_host")
require("engine.session")
require("engine.exploration")
require("engine.battle")
require("engine.director")
require("engine.traits")
require("engine.effects")
require("engine.interpreter")
require("engine.flow")
require("engine.quest")
require("engine.savegame")
require("engine.scenes.battle")
require("presentation.renderer")
require("presentation.viewport_3d")
require("presentation.sprite_sheet")
require("presentation.frame_renderer")
require("presentation.door_transition")
local _ = scene_host

local REQUEST = "RENDERABLE WORKER REQUEST"
local DONE = "RENDERABLE WORKER REQUEST DONE"
local ERROR = "RENDERABLE WORKER ERROR"

local function protocolError(requestId, value)
    local message = tostring(value or "runtime preview worker failed"):gsub("[%c]", " ")
    if #message > 8192 then message = message:sub(1, 8192) end
    print(ERROR .. "\t" .. tostring(requestId or 0) .. "\t" .. message)
end

local function finish(requestId)
    print(DONE .. "\t" .. tostring(requestId or 0))
end

local function readRequest(requestPath)
    local contents = love.filesystem.read(requestPath)
    if not contents then error("preview request file could not be read: " .. tostring(requestPath), 0) end
    local decoded = json.decode(contents)
    if type(decoded) ~= "table" then error("preview request must be an object", 0) end
    return decoded
end

-- Composition size is re-read per request rather than captured once, because a
-- Project may change its presentation surface between two requests that this
-- process happens to serve.
local function compositionSize()
    return presentation_surface.compositionSize()
end

local dispatch = {}

function dispatch.preview_scene(request)
    local w, h = compositionSize()
    cliTools.runPreviewScene(request.sceneId, loader, w, h)
end

function dispatch.preview_window(request)
    local w, h = compositionSize()
    cliTools.runPreviewWindow(request.windowId, request.mockSpec, loader, w, h)
end

function dispatch.preview_font(request)
    cliTools.runPreviewFont(request.name, tonumber(request.size))
end

function dispatch.preview_fog(request)
    cliTools.runPreviewFog(request.spec, request.mapId, loader)
end

function dispatch.preview_anim(request)
    cliTools.runPreviewAnim(request.animId, request.animJson, request.spritePath, loader)
end

function love.load()
    loader.init()
    print("RENDERABLE WORKER READY")

    while true do
        local line = io.read("*l")
        if line == nil or line == "QUIT" then break end

        local requestId, command, requestPath = line:match(
            "^" .. REQUEST .. "\t(%d+)\t([^\t\r\n]+)\t([^\t\r\n]+)$"
        )
        if not requestId or not command or not requestPath then
            local recoverId = line:match("^" .. REQUEST .. "\t(%d+)") or "0"
            protocolError(recoverId, "invalid request line")
            finish(recoverId)
        else
            local handler = dispatch[(command:gsub("%-", "_"))]
            if not handler then
                protocolError(requestId, "unknown preview command: " .. tostring(command))
            else
                local ok, err = pcall(function()
                    local request = readRequest(requestPath)
                    handler(request)
                end)
                if not ok then protocolError(requestId, err) end
            end
            finish(requestId)
        end
    end

    if love.event and love.event.quit then love.event.quit(0) end
    os.exit(0)
end
