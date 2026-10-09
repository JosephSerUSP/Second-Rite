-- Run the actual main host, including its NPC GraphWalker and dialogue sync.
love.errorhandler=function(message)
    print(debug.traceback(tostring(message),2));io.stdout:flush()
    return function() return 1 end
end
assert(love.filesystem.load("player-main.lua"))()
local update = love.update
local elapsed, step = 0, 0
local controller = require("engine.player_controller")
local scenes = require("engine.scene_host")
local view = require("engine.generated.world-view")
love.update = function(dt)
    update(dt)
    elapsed = elapsed + dt
    if step == 0 and elapsed > 0.5 then
        love.keypressed("return"); love.keyreleased("return")
        step = 1
    elseif step == 1 and elapsed > 1.5 then
        assert(activeSession and scenes.getCurrent() == "map", "new game did not reach Map")
        local camera = view.resolveTownCamera(require("engine.data.loader").getScene("map").worldPresentation.camera)
        for _, yaw in ipairs({0, 45, 90, -90, 180}) do
            local c = view.resolveTownCamera({yawDegrees=yaw,pitchDegrees=12,distance=11.5})
            local x,y = controller.worldMovement(c,1,0)
            assert(math.abs(x*c.rightX+y*c.rightY-1)<1e-9)
            x,y = controller.worldMovement(c,0,1)
            assert(math.abs(x*c.dirX+y*c.dirY-1)<1e-9)
        end
        local root = activeSession.continuousTraversal
        local x,y = root.x,root.y
        local ctx={session=activeSession,loader=activeSession.loader,party=activeSession.party}
        controller.press("RIGHT",ctx); controller.update(0.04,ctx);controller.release("RIGHT")
        assert((root.x-x)*camera.rightX+(root.y-y)*camera.rightY>0,"Right did not move screen-right")
        x,y=root.x,root.y
        controller.press("UP",ctx);controller.update(0.04,ctx);controller.release("UP")
        assert((root.x-x)*camera.dirX+(root.y-y)*camera.dirY>0,"Up did not move into the screen")
        root.x,root.y=1.85,1.85
        step=2
    elseif step == 2 and elapsed > 2 then
        love.keypressed("return");love.keyreleased("return")
        step=3
    elseif step == 3 and elapsed > 3 then
        assert(scenes.getCurrent()=="dialogue","NPC did not enter Dialogue")
        local state=scenes.getCurrentState()
        assert(state.v.dialogueText:find("The service annex is blocked",1,true),"NPC text not synchronized")
        assert(scenes.getCurrentSceneData({session=activeSession,loader=activeSession.loader}).config.dock.variant=="dialogue")
        assert(activeSession.loader.engine.dock.variants.dialogue.windows[1],"Dialogue dock has no window definitions")
        love.graphics.captureScreenshot("npc-dialogue-proof.png")
        step=4
    elseif step == 4 and elapsed > 3.5 then
        love.keypressed("return");love.keyreleased("return")
        step=5
    elseif step == 5 and elapsed > 4 then
        if scenes.getCurrent()=="dialogue" then
            love.keypressed("return");love.keyreleased("return")
        end
        step=6
    elseif step == 6 and elapsed > 4.5 then
        assert(scenes.getCurrent()=="map","NPC dialogue did not return to exploration")
        assert(activeSession.arenaEncounter,"Attendant did not start combat")
        assert(activeSession.arenaEncounter.event.id==203,"Wrong combat Event")
        love.graphics.captureScreenshot("npc-combat-proof.png")
        print("PLAYTHROUGH CONTROLS AND NPC TO COMBAT OK")
        local enemy=activeSession.arenaEncounter.root
        require("engine.continuous_surface").moveBy(activeSession.continuousTraversal,
            enemy.x-activeSession.continuousTraversal.x-1.8,enemy.y-activeSession.continuousTraversal.y+1.7)
        step=7
    elseif step == 7 and elapsed > 8 then
        love.keypressed("return");love.keyreleased("return");step=8
    elseif step == 8 and elapsed > 8.3 then
        assert(activeSession.arenaEncounter.mode=="command","real input did not open Command")
        love.keypressed("return");love.keyreleased("return");step=9
    elseif step == 9 and elapsed > 8.6 then
        assert(activeSession.arenaEncounter.mode=="targeting","real input did not open Targeting")
        love.keypressed("return");love.keyreleased("return")
        assert(activeSession.arenaEncounter.mode=="execution" and activeSession.arenaEncounter.actionCount==0,"real input skipped anticipation")
        love.graphics.captureScreenshot("player-anticipation-proof.png");step=10
    elseif step == 10 and elapsed > 8.95 then
        assert(activeSession.arenaEncounter.actionCount==1 and activeSession.arenaEncounter.mode=="execution","real input did not reach contact/recovery")
        love.graphics.captureScreenshot("player-contact-proof.png");step=11
    elseif step == 11 and elapsed > 9.5 then
        assert(activeSession.arenaEncounter.mode=="simulation","real action did not return control")
        print("PLAYTHROUGH PLAYER ACTION LIFECYCLE OK")
        love.event.quit(0)
    end
end
