local M={}
function M.run(loader)
 local json=require('engine.data.json');local surface=require('presentation.surface');local host=require('engine.scene_host');local renderer=require('presentation.renderer');local compositor=require('presentation.frame_renderer');local view=require('presentation.viewport_3d');local lane=require('engine.bounded_lane');local exploration=require('engine.exploration');local markers=require('presentation.transition_markers');local interpreter=require('engine.interpreter')
 require('engine.user_settings').pinForCapture({touchGamepadEnabled=true});surface.setProfile(require('presentation.touch_gamepad').configureDeviceSurface(1920,1080));local clock=0;love.timer.getTime=function() return clock end
 local game=require('engine.cli_tools').makeHarnessSession(loader);renderer.init(game);view.init();host.init(nil);local ctx={session=game,loader=loader,party=game.party};local frames={}
 interpreter.bindPresentation({setTransitionArrowsVisible=markers.setVisible,getTransitionArrowsVisible=markers.isVisible})
 local function position(mapId,anchor)
  exploration.loadMap(game,loader.getMapIndex(mapId),{arrival=anchor});game.townTraversal.y=game.townTraversal.environment.anchors[anchor].position[2];lane.update(game);host.goto_scene('map',ctx);host.update(1,ctx);renderer.update(1)
 end
 local function shoot(label)
  local w,h=surface.renderSize();local canvas=surface.newRasterCanvas(w,h)
  for i=1,2 do clock=clock+.25;love.graphics.setCanvas({canvas,depth=true,stencil=true});love.graphics.clear(0,0,0,1,true,true);love.graphics.setColor(1,1,1,1);compositor.draw(host,renderer,game,loader,h);love.graphics.setCanvas() end
  frames[#frames+1]={label=label,arrowsVisible=markers.isVisible(),image=love.data.encode('string','base64',canvas:newImageData():encode('png'))};canvas:release()
 end
 position(1001,'door-passage-house');shoot('passage-house')
 position(1005,'door-registry');shoot('praca-arrows')
 host.push('options',ctx);host.update(1,ctx);renderer.update(1)
 local scene=host.getCurrentSceneData(ctx);local row
 for i,c in ipairs(scene.config.optionsCommands) do if c.id=='navigation_arrows' then row=i end end
 for i=2,row do host.buttonpressed('DOWN',ctx);host.update(1,ctx);renderer.update(1) end
 shoot('options-arrows-ON');host.buttonpressed('A',ctx);host.update(1,ctx);renderer.update(1);assert(not markers.isVisible());shoot('options-arrows-OFF')
 host.pop(ctx);host.update(1,ctx);renderer.update(1);shoot('praca-no-arrows');assert(lane.promptDoorway(game),'hidden markers retain doorway prompt')
 position(28,'exit_door');shoot('bakery-no-arrows');markers.setVisible(true);shoot('bakery-arrows')
 position(1009,'to-praca');shoot('stair-arrows')
 position(1003,'to-forge');shoot('quay-arrows')
 position(1008,'to-court');shoot('harbour-arrows')
 print('TOWN FRAMES BEGIN');print(json.encode(frames));print('TOWN FRAMES END')
end
return M
