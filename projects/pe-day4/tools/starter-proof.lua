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
local function confirm() love.keypressed("return");love.keyreleased("return") end
local function stop()
    for _,button in ipairs({"LEFT","RIGHT","UP","DOWN"}) do controller.release(button) end
end
local function walkTo(x,y,ctx)
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
local function frame(label)
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
    elseif step==9 and elapsed-checkpoint>.3 then
        if walkTo(-2.6,1.3,ctx) then confirm();checkpoint=elapsed;step=10 end
    elseif step==10 and elapsed-checkpoint>.6 then
        assert(scenes.getCurrent()=="dialogue" and scenes.getCurrentState().v.dialogueText:find("Starter boundary",1,true),"basement boundary is not explicit")
        print("HOSPITAL STARTER INPUT TRANSFER AND SAVE OK")
        io.stdout:flush();love.event.quit(0)
    end
    assert(elapsed<60,"Hospital starter proof timed out at "..step)
end
