local lane = require('engine.bounded_lane')
local transition = require('presentation.door_transition')
local town_prompt = require('presentation.town_prompt')
local failed, passed = 0, 0
local function check(value, message)
    if value then passed=passed+1 else failed=failed+1; print('CHECK FAILED: '..message) end
end
local game = {currentMapData={events={}}, townTraversal={provider='bounded_lane',x=0,y=5,minY=0,maxY=10,
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
    'town prompt removes navigation prose carried by the direction glyph')
check(town_prompt.compactLabel({name='Down to the Port'})=='Port',
    'town prompt removes vertical navigation prose')
check(town_prompt.compactLabel({name="Laura's Smithy (3D)"})=="Laura's Smithy",
    'town prompt hides authoring/debug suffixes')
check(town_prompt.compactLabel({name='Out to the Quay',label='Harbour'})=='Harbour',
    'authored compact labels override presentation compaction')
local renderedName, renderedDirection = town_prompt.parseRenderedDoorLabel('Out to the Cortico  - LEFT')
check(renderedName=='Out to the Cortico' and renderedDirection=='LEFT',
    'renderer doorway sentence resolves into destination and direction projection')
check(town_prompt.parseRenderedDoorLabel('Talk to Agnes')==nil,
    'ordinary NPC prompts are not mistaken for directed door prompts')
check(town_prompt.parseRenderedDoorLabel('Door - DIAGONAL')==nil,
    'unsupported direction words are not projected as valid controls')
game.townTraversal.y=0
check(lane.edgeDoorway(game,-1)==nil,'pushing a bound cannot hijack its depth doorway')
check(not lane.isEdgeDoorway(game,foreground),'a foreground door on a bound remains a DOWN interaction')
game.townTraversal.y=8
check(lane.promptDoorway(game)==street,'the next street is previewed before reaching the boundary')
check(lane.interact(game,'RIGHT')==nil,'a preview does not widen the activation radius')

-- The scoped adapter must change both measurement and drawing semantics only
-- for the bounded-lane frame, then put the shared UI API back exactly as found.
local ui=require('presentation.ui')
local originalMeasure=ui.measureText
local rawWidth=originalMeasure('next street  - RIGHT')
local compactWidth
town_prompt.withCompactDoorUi(game,function()
    compactWidth=ui.measureText('next street  - RIGHT')
end)
check(compactWidth and compactWidth<rawWidth,'direction glyph projection shrinks the actual prompt footprint')
check(ui.measureText==originalMeasure,'town prompt projection restores the shared UI measurement seam')

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

-- Bounded-lane walking is continuous and therefore does not arrive through
-- the map scene's directional hooks. A field menu is a modal mode *inside*
-- that scene, so the provider must still surrender held directions while the
-- modal owns input. This is the regression behind walking through St. Maria
-- with the menu open.
game.townTraversal.speed=3.4
game.townTraversal.groundZ=0
game.townTraversal.groundProfile=nil
game.townTraversal.tracking={center=5,pixelsPerWorld=1,minOffsetX=0,maxOffsetX=0}
game.townTraversal.camera={}
game.townTraversal.y=5
host.init('map',{})
local mapState=host.getCurrentState()
mapState.v.mode=1
lane.update(game,.5,1)
check(math.abs(game.townTraversal.y-5)<.001,
    'a modal field menu owns held directions and freezes bounded-lane walking')
mapState.v.mode=0
lane.update(game,.5,1)
check(math.abs(game.townTraversal.y-6.7)<.001,
    'closing the field menu returns held directions to bounded-lane walking')
host.init(nil,{})

-- Recruitment choices are player-facing offers, never forced prompts. Keep B
-- wired at every CHOICE layer (including challenge-before-recruit branches),
-- so new units authored by Studio cannot silently reintroduce the historical
-- Decline/Leave row that looked cancellable but ignored B.
local dataLoader=require('engine.data.loader')
dataLoader.init()
local recruitChoiceCount=0
local function auditRecruitChoices(cmds, unitId)
    for _,cmd in ipairs(cmds or {}) do
        if cmd.cmd=='CHOICE' then
            recruitChoiceCount=recruitChoiceCount+1
            local optionCount=#(cmd.options or {})
            check(type(cmd.cancelOption)=='number'
                    and cmd.cancelOption==math.floor(cmd.cancelOption)
                    and cmd.cancelOption>=1 and cmd.cancelOption<=optionCount,
                'recruitment CHOICE for '..tostring(unitId)..' needs a valid cancelOption')
            for _,opt in ipairs(cmd.options or {}) do
                auditRecruitChoices(opt.commands,unitId)
            end
        end
        auditRecruitChoices(cmd.commands,unitId)
        auditRecruitChoices(cmd.onVictory,unitId)
        auditRecruitChoices(cmd.onDefeat,unitId)
        auditRecruitChoices(cmd['then'],unitId)
        auditRecruitChoices(cmd['else'],unitId)
        auditRecruitChoices(cmd.elseCommands,unitId)
    end
end
for _,unit in ipairs(dataLoader.units or {}) do
    if type(unit.recruitEvent)=='table' and #unit.recruitEvent>0 then
        auditRecruitChoices(unit.recruitEvent,unit.id)
    end
end
check(recruitChoiceCount>0,'the recruitment cancel audit exercised at least one CHOICE')

require('tests.fail_fast')('test_town_threshold_direction',failed,passed)