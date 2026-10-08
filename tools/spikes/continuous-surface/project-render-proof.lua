-- Native Project proof: run as main.lua in a canonical gauntlet stage.
-- Rejects missing environment pixels and bounded-lane reads on continuous Maps.
local function run()
    local loader = require("engine.data.loader")
    local exploration = require("engine.exploration")
    local host = require("engine.traversal_host")
    local view = require("presentation.viewport_3d")
    local door = require("presentation.door_transition")
    local surface = require("presentation.surface")
    local world = require("presentation.continuous_surface_world")
    local bundle = require("presentation.map_renderable_bundle")
    local json = require("engine.data.json")
    loader.init()
    require("engine.user_settings").pinForCapture()
    surface.setProfile("wide")
    view.init()
    local camera = loader.getScene("map").worldPresentation.camera
    local captures = {}
    local originalTime = love.timer.getTime
    love.timer.getTime = function() return 1.25 end
    local function capture(game, label)
        local width, height = surface.renderSize()
        local canvas = love.graphics.newCanvas(width, height)
        for i = 1, 2 do
            love.graphics.setCanvas({canvas, depth = true, stencil = true})
            love.graphics.clear(0, 0, 0, 1, true, true)
            love.graphics.setColor(1, 1, 1, 1)
            world.draw(game, {camera = camera})
            love.graphics.setCanvas()
        end
        local image = canvas:newImageData()
        local visible = 0
        for y=0,height-1 do for x=0,width-1 do
            local r,g,b = image:getPixel(x,y)
            if math.max(r,g,b) > 0.02 then visible = visible + 1 end
        end end
        assert(visible > width * height * 0.1, "empty world capture " .. label .. " pixels=" .. visible)
        captures[#captures+1] = {label = label, image = love.data.encode("string","base64",image:encode("png")),
            visiblePixels = visible, stats = view.getLastFrameStats(), actor = host.serialize(game)}
        image:release(); canvas:release()
    end
    loader.system.dungeon = loader.system.dungeon or {}
    loader.system.dungeon.psxRendering = loader.system.dungeon.psxRendering or {}
    for _, scale in ipairs({1,2}) do
        loader.system.dungeon.psxRendering.environmentSupersample = scale
        for mapId=1,2 do
            local game = require("engine.cli_tools").makeHarnessSession(loader)
            exploration.loadMap(game, loader.getMapIndex(mapId))

            do
                local previous = getmetatable(game).__index
                setmetatable(game, {__index = function(self, key)
                    assert(key ~= "townTraversal", "continuous renderer read townTraversal")
                    if type(previous) == "function" then return previous(self,key) end
                    return previous[key]
                end})
            end
            local result = assert(bundle.collect(game, "authoring", {includeCollision=true}))
            local renderFound, collisionFound = false, false
            for _, item in ipairs(result.surfaces) do
                renderFound = renderFound or item.source.kind == "environment" and item.source.surface == "render"
                collisionFound = collisionFound or item.source.kind == "environment" and item.source.surface == "collision"
            end
            assert(renderFound and collisionFound, "collector lost environment or collision")
            local prefix = "room-" .. mapId .. "-ss" .. scale
            capture(game,prefix .. "-idle")
            host.update(game,0.15,{left=true})
            capture(game,prefix .. "-walking")
            local raw = host.serialize(game)
            assert(door.begin(function() end,{actorDirection="away"}))
            door.update(0.12)
            capture(game,prefix .. "-door")
            local after = host.serialize(game)
            assert(raw.x == after.x and raw.y == after.y, "presentation changed gameplay pose")
            while door.isActive() do door.update(1) end
        end
    end
    -- An actor/grid remnant must not satisfy native environment proof.
    do
        local game = require("engine.cli_tools").makeHarnessSession(loader)
        exploration.loadMap(game, loader.getMapIndex(1))
        local originalView = host.presentationView
        host.presentationView = function(session)
            local raw = originalView(session)
            raw.environment = nil
            return raw
        end
        local accepted, failure = pcall(capture, game, "missing-environment-control")
        host.presentationView = originalView
        assert(not accepted and tostring(failure):find("empty world capture",1,true),
            "actor-only negative control was accepted")
    end
    love.timer.getTime = originalTime
    print("NATIVE PROOF BEGIN")
    print(json.encode({captures=captures}))
    print("NATIVE PROOF END")
    io.stdout:flush(); os.exit(0)
end
function love.load()
    local ok,err=pcall(run)
    if not ok then print(err); io.stdout:flush(); os.exit(1) end
end
