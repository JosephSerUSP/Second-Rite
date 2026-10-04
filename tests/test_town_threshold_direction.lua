local lane = require('engine.bounded_lane')
local transition = require('presentation.door_transition')
local town_prompt = require('presentation.town_prompt')
local failed, passed = 0, 0
local function check(value, message)
    if value then passed=passed+1 else failed=failed+1; print('CHECK FAILED: '..message) end
end
local game = {currentMapData={events={}}, townTraversal={x=0,y=5,minY=0,maxY=10,
    doorways={},environment={anchors={}}}}
local function door(id,y,direction)
    local d={anchor=id,eventInstanceId=id,radius=.65}
    game.currentMapData.events[#game.currentMapData.events+1]={instanceId=id,direction=direction,name=id}
    game.townTraversal.doorways[#game.townTraversal.doorways+1]=d
    game.townTraversal.environment.anchors[id]={position={0,y,0}}
    return d
end
local inward=door('enter',5,'away')
local outward=door('leave',5,'toward')
local street=door('next street',10,'right')
local foreground=door('foreground door',0,'toward')
check(lane.interact(game,'UP').instanceId=='enter','UP selects only the inward entrance')
check(lane.interact(game,'DOWN').instanceId=='leave','DOWN selects only the foreground exit at the same point')
check(lane.interact(game,'LEFT')==nil,'a sideways press cannot open a depth door')
check(lane.doorwayButton(game,street)=='RIGHT','marker and input share the authored axis')
check(town_prompt.compactLabel({name='Out to the Cortico'})=='Cortico',
    'town prompt removes navigation prose carried by the direction icon')
check(town_prompt.compactLabel({name='Down to the Port'})=='Port',
    'town prompt removes vertical navigation prose')
check(town_prompt.compactLabel({name="Laura's Smithy (3D)"})=="Laura's Smithy",
    'town prompt hides authoring/debug suffixes')
check(town_prompt.compactLabel({name='Out to the Quay',label='Harbour'})=='Harbour',
    'authored compact labels override presentation compaction')
local icon = town_prompt.directionIcon('RIGHT')
check(type(icon)=='table' and icon.direction=='RIGHT',
    'resolved gameplay direction projects to an icon source without changing semantics')
local badDirection = pcall(town_prompt.directionIcon,'DIAGONAL')
check(not badDirection,'unknown prompt directions fail loudly')
game.townTraversal.y=0
check(lane.edgeDoorway(game,-1)==nil,'pushing a bound cannot hijack its depth doorway')
check(not lane.isEdgeDoorway(game,foreground),'a foreground door on a bound remains a DOWN interaction')
game.townTraversal.y=8
check(lane.promptDoorway(game)==street,'the next street is previewed before reaching the boundary')
check(lane.interact(game,'RIGHT')==nil,'a preview does not widen the activation radius')

local transfers=0
check(transition.begin(function() transfers=transfers+1; transition.setArrivalDirection('toward') end,
    {approach=false,actorDirection='away'}),'depth walk starts')
transition.update(.12)
local pose=transition.actorPose()
check(pose and pose.x>0 and pose.frame>0,'UP animates feet and recedes into depth')
check(transition.approachProgress()==0,'the town camera remains still during the player walk')
check(game.townTraversal.x==0 and game.townTraversal.y==8,'the animated pose does not mutate gameplay position')
transition.update(.12)
transition.update(.58)
check(transfers==1 and transition.overlayAlpha()==1,'the transfer fires once under full cover')
transition.update(.16)
pose=transition.actorPose()
check(pose and pose.x<0,'arrival at a DOWN exit starts toward the camera')
transition.update(.34)
local near=transition.actorPose()
check(near and math.abs(near.x)<math.abs(pose.x),'arrival walks from the threshold to the lane')
transition.update(.34)
check(not transition.isActive(),'the arrival settles')
transition.begin(function() transfers=transfers+1 end,{approach=false,actorDirection='toward'})
transition.update(.12)
pose=transition.actorPose()
check(pose and pose.x<0,'DOWN animates toward the camera')
for i=1,10 do transition.update(1) end
check(transfers==2,'leaving also transfers exactly once')
local controller=require('engine.player_controller')
local host=require('engine.scene_host')
local originalDispatch=host.buttonpressed
local presses=0
host.buttonpressed=function() presses=presses+1;return true end
controller.reset()
controller.press('DOWN',{})
controller.consumeUntilRelease('DOWN')
controller.update(3,{}, {initial=.3,interval=.06})
controller.refireFirstHeld({})
check(presses==1,'holding a depth direction across a transfer cannot bounce back')
check(controller.isHeld('DOWN'),'consuming a press preserves physical held state')
controller.release('DOWN');controller.press('DOWN',{})
check(presses==2,'releasing and pressing deliberately can use the return path')
controller.reset();host.buttonpressed=originalDispatch
require('tests.fail_fast')('test_town_threshold_direction',failed,passed)
