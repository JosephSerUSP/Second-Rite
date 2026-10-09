-- Run the actual main host, including its NPC GraphWalker and dialogue sync.
love.errorhandler=function(message)
    print(debug.traceback(tostring(message),2));io.stdout:flush()
    return function() return 1 end
end
assert(love.filesystem.load("player-main.lua"))()
local update = love.update
local elapsed, step = 0, 0
local lastConfirm, checkpoint
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
        assert(state.v.dialogueText:find("The service door is the blue door",1,true),"NPC text not synchronized")
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
        assert(scenes.getCurrent()=="map" and activeSession.currentMapData.id==1,"attendant teleported player")
        assert(not activeSession.arenaEncounter,"attendant started combat")
        activeSession.continuousTraversal.x,activeSession.continuousTraversal.y=3.35,-2.15
        love.keypressed("return");love.keyreleased("return");step=7
    elseif step == 7 and elapsed > 5.2 then
        assert(activeSession.currentMapData.id==2 and not activeSession.arenaEncounter,"door did not enter peaceful annex")
        local a=activeSession.continuousTraversal.environment.anchors.arrival_from_archive.position
        assert(math.abs(activeSession.continuousTraversal.x-a[1])<1e-5 and math.abs(activeSession.continuousTraversal.y-a[2])<1e-5,"door arrival drift")
        activeSession.continuousTraversal.x,activeSession.continuousTraversal.y=1.6,-2.2
        love.keypressed("return");love.keyreleased("return");step=8
    elseif step == 8 and elapsed > 5.8 then
        assert(scenes.getCurrent()=="dialogue","Sentinel inspection did not show dialogue")
        assert(scenes.getCurrentState().v.dialogueText:find("The Sentinel is dormant",1,true),"wrong investigation text")
        love.graphics.captureScreenshot("sentinel-inspection-proof.png")
        love.keypressed("return");love.keyreleased("return");step=9
    elseif step == 9 and elapsed > 6.3 then
        if scenes.getCurrent()=="dialogue" then love.keypressed("return");love.keyreleased("return") end
        if activeSession.arenaEncounter then
            assert(activeSession.arenaEncounter.event.id==203,"wrong encounter")
            assert(require("engine.game_variables").get(activeSession,"sentinelInspected")==true)
            love.graphics.captureScreenshot("npc-combat-proof.png")
            print("PLAYTHROUGH DOOR AND INVESTIGATION TO COMBAT OK")
            step=10
        end
    elseif step == 10 then
        local encounter=activeSession.arenaEncounter
        if encounter then
            if elapsed-(lastConfirm or 0)>.3 and (encounter.at>=1 or encounter.mode=="command" or encounter.mode=="targeting") then
                lastConfirm=elapsed
                local old=encounter.mode
                love.keypressed("return");love.keyreleased("return")
                if old=="targeting" and encounter.mode=="execution" then
                    assert(encounter.action and encounter.action.index==1,"confirmation skipped anticipation")
                    love.graphics.captureScreenshot("player-anticipation-proof.png")
                end
            end
        else
            assert(require("engine.game_variables").get(activeSession,"sentinelDefeated")==true,"natural player combat did not win")
            assert(activeSession.arenaResult.actionCount>=4,"combat bypassed actual actions")
            love.graphics.captureScreenshot("chapter-victory-proof.png")
            print("PLAYTHROUGH PLAYER ACTION LIFECYCLE AND VICTORY OK")
            activeSession.continuousTraversal.x,activeSession.continuousTraversal.y=-3.35,1.85
            love.keypressed("return");love.keyreleased("return");checkpoint=elapsed;step=11
        end
    elseif step == 11 and elapsed-checkpoint>.6 then
        assert(activeSession.currentMapData.id==1,"victory return door failed")
        love.keypressed("f5");love.keyreleased("f5")
        love.keypressed("f6");love.keyreleased("f6")
        assert(require("engine.game_variables").get(activeSession,"sentinelDefeated")==true,"victory flag did not reload")
        assert(not require("engine.game_variables").get(activeSession,"chapterComplete"),"chapter completed before report")
        activeSession.continuousTraversal.x,activeSession.continuousTraversal.y=1.85,1.85
        checkpoint=elapsed;step=12
    elseif step == 12 and elapsed-checkpoint>.5 then
        love.keypressed("return");love.keyreleased("return");checkpoint=elapsed;step=13
    elseif step == 13 and elapsed-checkpoint>.6 then
        assert(scenes.getCurrent()=="dialogue","report did not show dialogue")
        assert(scenes.getCurrentState().v.dialogueText:find("Assignment complete",1,true),"completion dialogue missing")
        love.graphics.captureScreenshot("chapter-report-proof.png")
        love.keypressed("return");love.keyreleased("return");checkpoint=elapsed;step=14
    elseif step == 14 and elapsed-checkpoint>.6 then
        if scenes.getCurrent()=="dialogue" then love.keypressed("return");love.keyreleased("return")
        else
            assert(require("engine.game_variables").get(activeSession,"chapterComplete")==true,"report did not complete chapter")
            love.keypressed("f5");love.keyreleased("f5")
            love.keypressed("f6");love.keyreleased("f6")
            assert(require("engine.game_variables").get(activeSession,"chapterComplete")==true,"completion did not reload")
            assert(not activeSession.arenaEncounter,"load restarted combat")
            love.graphics.captureScreenshot("chapter-complete-proof.png")
            print("PLAYTHROUGH CHAPTER REPORT AND SAVE LOAD OK")
            love.event.quit(0)
        end
    end
    assert(elapsed<65,"chapter playthrough timed out at step "..step)
end
