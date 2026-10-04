local M = {}
function M.run(loader)
    local json=require('engine.data.json')
    local surface=require('presentation.surface')
    local host=require('engine.scene_host')
    local renderer=require('presentation.renderer')
    local compositor=require('presentation.frame_renderer')
    local view=require('presentation.viewport_3d')
    local lane=require('engine.bounded_lane')
    local transition=require('presentation.door_transition')
    local exploration=require('engine.exploration')
    require('engine.user_settings').pinForCapture({touchGamepadEnabled=true})
    surface.setProfile(require('presentation.touch_gamepad').configureDeviceSurface(1920,1080))
    local clock=0
    love.timer.getTime=function() return clock end
    local game=require('engine.cli_tools').makeHarnessSession(loader)
    renderer.init(game);view.init();host.init(nil)
    local ctx={session=game,loader=loader,party=game.party}
    local frames={}
    local function position(mapId,anchor,offset)
        exploration.loadMap(game,loader.getMapIndex(mapId),{arrival=anchor})
        game.townTraversal.y=game.townTraversal.environment.anchors[anchor].position[2]+(offset or 0)
        lane.update(game)
        host.goto_scene('map',ctx);host.update(1,ctx);renderer.update(1)
    end
    local function shoot(label)
        local w,h=surface.renderSize()
        local canvas=surface.newRasterCanvas(w,h)
        for i=1,2 do
            clock=clock+.25
            love.graphics.setCanvas({canvas,depth=true,stencil=true})
            love.graphics.clear(0,0,0,1,true,true);love.graphics.setColor(1,1,1,1)
            compositor.draw(host,renderer,game,loader,h)
            love.graphics.setCanvas()
        end
        frames[#frames+1]={label=label,image=love.data.encode('string','base64',canvas:newImageData():encode('png'))}
        canvas:release()
    end
    position(1002,'door-bakery');shoot('bakery-UP')
    transition.begin(function()
        position(28,'exit_door')
        transition.setArrivalDirection('toward')
    end,{approach=false,actorDirection='away'})
    transition.update(.20);shoot('bakery-entry-depth-step')
    transition.update(.04);transition.update(.58);transition.update(.16);transition.update(.68)
    shoot('bakery-DOWN')
    transition.begin(function()
        position(1002,'door-bakery')
        transition.setArrivalDirection('away')
    end,{approach=false,actorDirection='toward'})
    transition.update(.20);shoot('bakery-exit-depth-step')
    transition.update(.04);transition.update(.58);transition.update(.16)
    transition.update(.30);shoot('bakery-return-arrival')
    transition.update(.38)
    while transition.isActive() do transition.update(1) end
    position(1003,'to-forge',2);shoot('quay-LEFT-preview')
    position(1009,'to-praca');shoot('stair-DOWN-return')
    print('DIRECTION FRAMES BEGIN');print(json.encode(frames));print('DIRECTION FRAMES END')
end
return M
