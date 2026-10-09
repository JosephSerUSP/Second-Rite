-- Actual player host: no position, flag, HP or inventory injection after start.
love.errorhandler=function(message)
    print(debug.traceback(tostring(message),2));io.stdout:flush()
    return function() return 1 end
end
assert(love.filesystem.load("player-main.lua"))()
local update=love.update
local controller=require("engine.player_controller")
local scenes=require("engine.scene_host")
local variables=require("engine.game_variables")
local elapsed,step,checkpoint=0,0,0
local points={{-3.3,0},{-3.3,-2.15},{2.7,-2.15}}
local waypoint=1
local confirm, walkTo, frame
local plan, actionIndex, phase, selected = {}, 1, 'approach', 1
local function add(kind, fields) fields.kind=kind;plan[#plan+1]=fields end
local function travel(label, destination, locked) add('door',{label=label,destination=destination,locked=locked}) end
local function use(label, item, flag) add('station',{label=label,item=item,flag=flag}) end
local function save(label) add('save',{label=label}) end
add('canceldoor',{label='Cancel route selection',destination=4})
travel('1F Elevators',4,true) -- power-off elevator cannot return
travel('Basement main corridor',5)
travel('Basement autopsy room',5,true)
travel('Basement blue-card corridor',10)
travel('Basement fusebox area',10,true)
travel('Basement main corridor',5)
travel('Basement storage room',6)
use('Take fuse 1','fuse_1')
use('Take fuse 1','fuse_1') -- returning/repeating never duplicates pickup
travel('Basement main corridor',5)
travel('Basement morgue',7)
use('Take autopsy key','autopsy_key')
travel('Basement main corridor',5)
travel('Basement autopsy room',8)
travel('Basement inner autopsy room',9)
use('Take blue cardkey','blue_cardkey')
use('Take fuse 2','fuse_2')
save('pre-power')
travel('Basement autopsy room',8)
travel('Basement main corridor',5)
travel('Basement blue-card corridor',10)
travel('Basement fusebox area',11)
use('Toggle power',nil,nil) -- missing repair/fuses must refuse
travel('Basement office',12)
use('Take fuse 3','fuse_3')
travel('Basement fusebox area',11)
use('Install fuse 1',nil,'fuse_1_installed')
use('Install fuse 2',nil,'fuse_2_installed')
use('Toggle power',nil,nil) -- missing third installation still refuses
use('Install fuse 3',nil,'fuse_3_installed')
use('Toggle power',nil,nil) -- all fuses installed but wires still broken
use('Repair wires',nil,'wires_repaired')
use('Toggle power',nil,'powerState')
save('restored-power')
travel('Basement elevator landing',4)
travel('Basement main corridor',5)
travel('Basement storage room',6)
use('Take fuse 1','fuse_1') -- pickup remains spent after powered save/load
travel('Basement main corridor',5)
travel('Basement elevator landing',4)
travel('1F Elevators',3)
travel('Basement elevator landing',4) -- powered reverse route, never replay crash
travel('1F Elevators',3)
travel('Ward route / unit boundary',3,true)
local function verifyAction(action)
    if action.destination then assert(activeSession.currentMapData.id==action.destination,'basement route destination mismatch: '..action.label) end
    if action.item then assert(activeSession.inventory[action.item]==1,'pickup missing/duplicated: '..action.item) end
    if action.flag then
        local value=variables.get(activeSession,action.flag)
        assert(value==(action.flag=='powerState' and 'on' or true),'world state missing: '..action.flag)
    end
    if action.label=='Toggle power' and not action.flag then assert(variables.get(activeSession,'powerState')=='off','power restored without all repairs/installations') end
end
local function drivePlan(ctx)
    local action=plan[actionIndex]
    if not action then
        assert(variables.get(activeSession,'ward_route_open')==true,'powered return did not open ward route')
        assert(variables.get(activeSession,'powerState')=='on','crash replay reset power')
        print('HOSPITAL BASEMENT INPUT LOOP AND SAVE OK');io.stdout:flush();love.event.quit(0);return
    end
    if action.kind=='save' then
        local before=activeSession.currentMapData.id
        love.keypressed('f5');love.keyreleased('f5');love.keypressed('f6');love.keyreleased('f6')
        assert(activeSession.currentMapData.id==before,'checkpoint map lost')
        assert(activeSession.inventory.fuse_1==1 and activeSession.inventory.fuse_2==1 and activeSession.inventory.blue_cardkey==1,'checkpoint inventory lost')
        assert(variables.get(activeSession,'collected_take_fuse_1')==true,'pickup marker lost')
        assert(variables.get(activeSession,'powerState')==(action.label=='pre-power' and 'off' or 'on'),'checkpoint power lost')
        if action.label=='restored-power' then
            for _,flag in ipairs({'wires_repaired','fuse_1_installed','fuse_2_installed','fuse_3_installed'}) do assert(variables.get(activeSession,flag)==true,'installation lost at save') end
            frame('powered')
        end
        actionIndex=actionIndex+1;return
    end
    if phase=='approach' then
        local service=activeSession.currentMapData.traversal.environmentPackage:find('service_annex',1,true)
        local x,y=action.kind=='station' and .25 or (service and -2.6 or 2.7),action.kind=='station' and 1.1 or (service and 1.3 or -2.15)
        if walkTo(x,y,ctx) then confirm();checkpoint=elapsed;phase='menu' end
    elseif phase=='menu' and elapsed-checkpoint>.25 then
        if scenes.getCurrent()=='dialogue' and scenes.getCurrentState().v.dialogueMode=='choice' then
            if action.kind=='canceldoor' then
                love.keypressed('escape');love.keyreleased('escape');checkpoint=elapsed;phase='settle';return
            end
            local state=scenes.getCurrentState().v
            local found
            for i,option in ipairs(state.dialogueOptions) do if option==action.label then found=i end end
            assert(found,'authored action absent: '..action.label)
            if state.dialogueCursorIdx~=found then love.keypressed('down');love.keyreleased('down');checkpoint=elapsed
            else confirm();checkpoint=elapsed;phase='settle' end
        else checkpoint=elapsed;phase='settle' end
    elseif phase=='settle' and elapsed-checkpoint>.3 then
        verifyAction(action)
        print("HOSPITAL ACTION OK "..actionIndex.." "..action.label);io.stdout:flush()
        if scenes.getCurrent()=='dialogue' then confirm();checkpoint=elapsed;phase='close'
        else actionIndex=actionIndex+1;phase='approach' end
    elseif phase=='close' and elapsed-checkpoint>.25 then
        if scenes.getCurrent()=='dialogue' then confirm();checkpoint=elapsed
        else actionIndex=actionIndex+1;phase='approach' end
    end
end
function confirm() love.keypressed("return");love.keyreleased("return") end
local function stop()
    for _,button in ipairs({"LEFT","RIGHT","UP","DOWN"}) do controller.release(button) end
end
function walkTo(x,y,ctx)
    local root=activeSession.continuousTraversal
    local dx,dy=x-root.x,y-root.y
    stop()
    if dx*dx+dy*dy<.12*.12 then return true end
    local camera=require("engine.generated.world-view").resolveTownCamera(activeSession.loader.getScene("map").worldPresentation.camera)
    local horizontal=dx*camera.rightX+dy*camera.rightY
    local vertical=dx*camera.dirX+dy*camera.dirY
    local button
    if math.abs(horizontal)>math.abs(vertical) then button=horizontal>0 and "RIGHT" or "LEFT"
    else button=vertical>0 and "UP" or "DOWN" end
    controller.press(button,ctx)
    return false
end
function frame(label)
    love.graphics.captureScreenshot(function(img)
        print("HOSPITAL FRAME "..label.." "..love.data.encode("string","base64",img:encode("png")))
        img:release()
    end)
end
love.update=function(dt)
    update(dt);elapsed=elapsed+dt
    local ctx=activeSession and {session=activeSession,loader=activeSession.loader,party=activeSession.party}
    if step==0 and elapsed>.5 then confirm();step=1
    elseif step==1 and scenes.getCurrent()=="map" then
        assert(activeSession.currentMapData.id==1,"snapshot entry mismatch")
        local actor=activeSession.party[1]
        assert(actor.level==18 and actor.equipment[1].id=="m9_2" and actor.equipment[2].id=="n_jacket","snapshot level/equipment not loaded")
        assert(activeSession.inventory.handgun_ammo==30 and activeSession.inventory.mayoke==1,"snapshot inventory not loaded")
        assert(variables.get(activeSession,"bonusPoints")==0,"snapshot BP missing")
        assert(not variables.get(activeSession,"elevator_crashed"),"Hospital starts pre-completed")
        frame("entrance");print("HOSPITAL SNAPSHOT IDENTITIES OK - PROTOTYPE STATS")
        step=2
    elseif step==2 then
        local target=points[waypoint]
        if walkTo(target[1],target[2],ctx) then
            waypoint=waypoint+1
            if waypoint>#points then confirm();checkpoint=elapsed;step=3 end
        end
    elseif step==3 and elapsed-checkpoint>.6 then
        assert(activeSession.currentMapData.id==2,"visible entrance door failed")
        if walkTo(-2.6,1.3,ctx) then confirm();checkpoint=elapsed;step=4 end
    elseif step==4 and elapsed-checkpoint>.6 then
        assert(activeSession.currentMapData.id==3,"lobby route failed")
        confirm();checkpoint=elapsed;step=5
    elseif step==5 and elapsed-checkpoint>.6 then
        assert(scenes.getCurrent()=="dialogue" and scenes.getCurrentState().v.dialogueMode=="choice","elevator choices absent")
        love.keypressed("down");love.keyreleased("down");checkpoint=elapsed;step=6
    elseif step==6 and elapsed-checkpoint>.3 then
        assert(scenes.getCurrentState().v.dialogueCursorIdx==2,"elevator destination did not change")
        confirm();checkpoint=elapsed;step=7
    elseif step==7 and elapsed-checkpoint>.6 then
        assert(activeSession.currentMapData.id==4,"elevator did not reach basement")
        assert(variables.get(activeSession,"elevator_crashed")==true and variables.get(activeSession,"powerState")=="off","crash/power state not authored")
        assert(not activeSession.arenaEncounter,"starter unexpectedly enters combat")
        love.keypressed("f5");love.keyreleased("f5")
        love.keypressed("f6");love.keyreleased("f6")
        assert(activeSession.currentMapData.id==4 and variables.get(activeSession,"powerState")=="off","basement save/load failed")
        assert(activeSession.inventory.handgun_ammo==30 and activeSession.party[1].equipment[1].id=="m9_2","snapshot inventory/equipment did not round-trip")
        checkpoint=elapsed;step=8
    elseif step==8 and elapsed-checkpoint>.6 then
        frame("basement");checkpoint=elapsed;step=9
    elseif step==9 then drivePlan(ctx)
    end
    assert(elapsed<180,"Hospital starter proof timed out at "..step.." action "..actionIndex.." phase "..phase)
end
