local module={}
function module.run(loader)
 local game=require('engine.cli_tools').makeHarnessSession(loader)
 local exploration=require('engine.exploration')
 local lane=require('engine.bounded_lane')
 local interpreter=require('engine.interpreter')
 local json=require('engine.data.json')
 exploration.loadMap(game,loader.getMapIndex(28))
 local spawn=game.townTraversal.y
 local function walkTo(y)
  local steps=0
  while math.abs(game.townTraversal.y-y)>.05 do
   local before=game.townTraversal.y
   lane.update(game,1/60,y>before and 1 or -1)
   assert(game.townTraversal.y~=before,'Movement blocked at '..before)
   steps=steps+1; assert(steps<900,'Movement did not reach target')
  end
  return steps,game.townTraversal.y
 end
 local approachSteps,approachY=walkTo(3)
 local exitSteps,exitY=walkTo(7.0333)
 local event=assert(lane.interact(game),'No exit event after walking')
 assert(event.instanceId=='st-maria-alicias_padaria_3d-exit_door','Wrong exit event')
 interpreter.runImmediate(event.commands,{session=game,loader=loader,party=game.party,eventOwner=event})
 assert(game.currentMapData.id==18,'Exit did not transfer to Market Row')
 local result={mapId=28,spawnY=spawn,approachY=approachY,approachSteps=approachSteps,
  exitY=exitY,exitSteps=exitSteps,exitEvent=event.instanceId,arrivalMapId=game.currentMapData.id,
  arrivalY=game.townTraversal.y,input='bounded_lane.update at 60 Hz',
  transfer='authored commands through interpreter.runImmediate'}
 print('BAKERY WALK BEGIN'); print(json.encode(result)); print('BAKERY WALK END')
end
return module
