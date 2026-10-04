local M={}
function M.run(loader)
    local surface=require('presentation.surface')
    local host=require('engine.scene_host')
    local renderer=require('presentation.renderer')
    local compositor=require('presentation.frame_renderer')
    local lane=require('engine.bounded_lane')
    local exploration=require('engine.exploration')
    require('engine.user_settings').pinForCapture({touchGamepadEnabled=true})
    surface.setProfile(require('presentation.touch_gamepad').configureDeviceSurface(1920,1080))
    local clock=0;love.timer.getTime=function() return clock end
    local game=require('engine.cli_tools').makeHarnessSession(loader)
    renderer.init(game);require('presentation.viewport_3d').init();host.init(nil)
    local ctx={session=game,loader=loader,party=game.party};local frames={}
    for _,pose in ipairs({
        {1001,0,'court-east'},{1001,18,'court-grade'},{1001,27,'passage-house'},
        {1001,36,'court-west-grade'},{1001,46,'court-market-turn'},
        {1002,7,'bakery-frontage'},{1002,10,'market-grade'},{1002,14,'market-quay-turn'},
        {1005,1,'service-climb-foot'},{1006,15,'service-climb-top'},
        {1009,1.5,'churchyard-stair'},{1007,16,'gate-guard'},{28,2.3333,'single-alicia'},
        {29,2.7333,'laura'}}) do
        exploration.loadMap(game,loader.getMapIndex(pose[1]))
        local delta=pose[2]-game.townTraversal.y
        lane.update(game,math.abs(delta)/game.townTraversal.speed,delta<0 and -1 or 1)
        lane.update(game)
        host.goto_scene('map',ctx);host.update(1,ctx);renderer.update(1)
        local w,h=surface.renderSize();local canvas=surface.newRasterCanvas(w,h)
        for i=1,2 do
            clock=clock+.25;love.graphics.setCanvas({canvas,depth=true,stencil=true})
            love.graphics.clear(0,0,0,1,true,true);love.graphics.setColor(1,1,1,1)
            compositor.draw(host,renderer,game,loader,h);love.graphics.setCanvas()
        end
        local state=game.townTraversal;local composition=state.lastPrerenderComposition
        if composition then assert(composition.laneScreenY<=144,'Walking ground falls below the camera floor limit') end
        frames[#frames+1]={label=pose[3],mapId=pose[1],laneY=state.y,groundZ=state.z,
            composition=composition,image=love.data.encode('string','base64',canvas:newImageData():encode('png'))}
        canvas:release()
    end
    print('GROUND FRAMES BEGIN');print(require('engine.data.json').encode(frames));print('GROUND FRAMES END')
end
return M
