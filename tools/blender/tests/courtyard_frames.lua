-- Candidate-only native compositor captures; shipping main.lua is never changed.
local module = {}
function module.run(loader)
    local json = require("engine.data.json")
    local exploration = require("engine.exploration")
    local lane = require("engine.bounded_lane")
    local scene_host = require("engine.scene_host")
    local renderer = require("presentation.renderer")
    local frames = require("presentation.frame_renderer")
    local surface = require("presentation.surface")
    local game = require("engine.cli_tools").makeHarnessSession(loader)
    renderer.init(game)
    require("presentation.viewport_3d").init()
    scene_host.init(nil)
    local result = {}
    for _, y in ipairs({0.5,2,5,8,11.5}) do
        exploration.loadMap(game,loader.getMapIndex(32))
        game.townTraversal.y = y
        game.townTraversal.z = lane.groundAt(game,y)
        lane.update(game)
        local ctx = {session=game,loader=loader,party=game.party}
        scene_host.goto_scene("map",ctx)
        scene_host.update(1,ctx)
        renderer.update(1)
        local width,height = surface.renderSize()
        local canvas = love.graphics.newCanvas(width,height)
        for _ = 1,2 do
            love.graphics.setCanvas({canvas,depth=true,stencil=true})
            love.graphics.clear(0,0,0,1,true,true)
            love.graphics.setColor(1,1,1,1)
            frames.draw(scene_host,renderer,game,loader,height)
            love.graphics.setCanvas()
            -- Native labels animate on wall time; settle the first draw before capture.
            if _ == 1 then love.timer.sleep(0.20) end
        end
        local png = canvas:newImageData():encode("png")
        result[#result+1] = {y=y,z=game.townTraversal.z,width=width,height=height,
            image=love.data.encode("string","base64",png)}
        canvas:release()
    end
    print("COURTYARD FRAMES BEGIN")
    print(json.encode(result))
    print("COURTYARD FRAMES END")
end
return module
