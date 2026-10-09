local function run()
    local loader=require("engine.data.loader");loader.init()
    require("tests.test_action_timeline")
    local presentationTime=1.25
    love.timer.getTime=function() return presentationTime end
    local host=require("engine.arena_host")
    local interpreter=require("engine.interpreter")
    local exploration=require("engine.exploration")
    local scene=require("engine.scene_host")
    local controller=require("engine.player_controller")
    local json=require("engine.data.json")
    require("engine.user_settings").pinForCapture()
    local surface=require("presentation.surface");surface.setProfile("wide")
    local game=require("engine.cli_tools").makeHarnessSession(loader)
    exploration.loadMap(game,loader.getMapIndex(2))
    require("presentation.renderer").init(game)
    require("presentation.viewport_3d").init()
    require("presentation.scene_compositor")
    scene.init(nil);scene.push("map",{session=game,loader=loader,party=game.party})
    local ctx={session=game,loader=loader,party=game.party}
    local event
    for _,ev in ipairs(game.currentMapData.events) do if ev.id==203 then event=ev end end
    local original=json.encode(event)
    local encounterCommands=json.decode(assert(love.filesystem.read("data/commonEvents.json")))["1"].commands
    local invalid={};for key,value in pairs(encounterCommands[1]) do invalid[key]=value end
    invalid.range=0
    assert(not pcall(host.validate,invalid,loader,game.currentMapData),"invalid range accepted")
    invalid.range=encounterCommands[1].range;invalid.enemyUnitId="missing"
    assert(not pcall(host.validate,invalid,loader,game.currentMapData),"missing enemy accepted")
    local captures={}
    local skillCost=require("engine.skill_cost")
    local originalSpend=skillCost.spend
    local costCalls=0
    skillCost.spend=function(...) costCalls=costCalls+1;return originalSpend(...) end
    local function capture(label)
        local width,height=surface.renderSize()
        local canvas=love.graphics.newCanvas(width,height)
        love.graphics.setCanvas({canvas,depth=true,stencil=true});love.graphics.clear(0,0,0,1,true,true)
        scene.draw(ctx)
        presentationTime=presentationTime+0.2
        require("presentation.scene_compositor").update(0.2)
        scene.draw(ctx)
        love.graphics.setCanvas()
        local image=canvas:newImageData()
        captures[#captures+1]={label=label,image=love.data.encode("string","base64",image:encode("png")),
            facts=require("engine.game_variables").get(game,"arena"),root=require("engine.traversal_host").serialize(game)}
        image:release();canvas:release()
    end
    local function tick(dt) controller.update(dt,ctx) end
    local function confirm() scene.buttonpressed("A",ctx) end
    local function cancel() scene.buttonpressed("B",ctx) end
    interpreter.runImmediate(encounterCommands,{session=game,loader=loader,event=event})
    local formulaSpec={};for key,value in pairs(encounterCommands[1]) do formulaSpec[key]=value end
    formulaSpec.range="2 + 0.6"
    local resolved=host.resolveSpec(formulaSpec,function(value)
        local result,err=require("engine.formula").eval(value,{});assert(not err,err);return result
    end)
    assert(resolved.range==2.6,"arena tuning bypassed shared formula semantics")
    formulaSpec.range="2 +"
    assert(not pcall(host.validateSpec,formulaSpec,loader,true),"malformed tuning formula accepted")
    local state=assert(game.arenaEncounter)
    capture("01-entry")
    local x=state.root.x;tick(1);assert(state.root.x~=x or state.root.y~=event.worldPosition[2],"enemy did not move")
    capture("02-motion")
    tick(2.1);assert(state.telegraph,"no telegraph");capture("03-telegraph")
    confirm();assert(state.mode=="command");capture("04-command")
    local elapsed,at,remaining,enemyX,playerX=state.elapsed,state.at,state.telegraph.remaining,state.root.x,game.continuousTraversal.x
    controller.press("RIGHT",ctx);tick(0.75);controller.release("RIGHT")
    assert(state.elapsed==elapsed and state.at==at and state.telegraph.remaining==remaining and state.root.x==enemyX and game.continuousTraversal.x==playerX,"pause advanced simulation")
    assert(not pcall(require("engine.savegame").serialize,game,loader,"map"),"active save accepted")
    assert(not pcall(exploration.loadMap,game,loader.getMapIndex(1)),"active Map transfer accepted")
    local saved,reason=require("engine.savegame").save(game,loader,"map","arena-proof-blocked")
    assert(not saved and reason:find("active arena"),"save request was not rejected explicitly")
    local actor=require("presentation.animated_actor")
    local appearance=require("presentation.viewport_3d").resolveEventPresentation(event,game)
    local beforePose=actor.resolveEvent(game,event,appearance,1)
    local afterPose=actor.resolveEvent(game,event,appearance,9)
    assert(json.encode(beforePose.groups)==json.encode(afterPose.groups),"paused locomotion advanced animation")
    confirm();assert(state.mode=="targeting");capture("05-targeting")
    cancel();assert(state.mode=="command");cancel();assert(state.mode=="simulation" and state.actionCount==0,"cancel spent action")
    -- Move through the shared walk/collision semantic to a distant valid point.
    local semantic=require("engine.continuous_surface")
    semantic.moveBy(game.continuousTraversal,-3-game.continuousTraversal.x,1.3-game.continuousTraversal.y)
    local lockX,lockY=state.telegraph.x,state.telegraph.y
    local playerHp=state.player.hp
    tick(state.spec.windupSeconds)
    assert(state.telegraph.x==lockX and state.telegraph.y==lockY,"windup retargeted after dodge")
    tick(state.spec.strikeSeconds/2);capture("03b-enemy-strike")
    tick(state.spec.strikeSeconds/2)
    assert(state.impact and state.impact.miss and state.player.hp==playerHp,"dodged lunge delivered damage")
    assert(require("engine.action_timeline").phase(state.enemyAction).id=="recovery","enemy has no recovery window")
    capture("03c-enemy-recovery")
    tick(state.spec.enemyRecoverySeconds)
    assert(not state.enemyAction,"enemy recovery did not finish")
    state.at=1;confirm();confirm();local hp=state.enemy.hp;confirm()
    assert(state.message=="out_of_range" and state.enemy.hp==hp and state.actionCount==0,"range rejection mutated battle")
    capture("06-range-rejected");cancel();cancel()
    semantic.moveBy(game.continuousTraversal,state.root.x-game.continuousTraversal.x-1.8,state.root.y-game.continuousTraversal.y+0.5)
    state.at=1;confirm();confirm();confirm()
    assert(state.mode=="execution" and state.actionCount==0 and state.enemy.hp==hp and costCalls==0,"confirmation resolved before contact")
    local root=game.continuousTraversal
    local x0,y0,enemyClock=root.x,root.y,state.enemyClock
    confirm();cancel();controller.press("RIGHT",ctx);tick(state.spec.playerWindupSeconds/2);controller.release("RIGHT")
    assert(root.x==x0 and root.y==y0 and state.enemyClock==enemyClock,"commitment leaked movement or enemy time")
    assert(state.actionCount==0 and state.enemy.hp==hp,"anticipation delivered early")
    capture("07a-anticipation")
    tick(state.spec.playerWindupSeconds/2)
    assert(state.actionCount==1 and state.enemy.hp<hp and state.mode=="execution","contact did not resolve once")
    capture("07-contact")
    local committedHp=state.enemy.hp
    confirm();cancel();tick(state.spec.playerRecoverySeconds/2)
    assert(state.enemy.hp==committedHp and costCalls==1 and state.mode=="execution","recovery replayed or canceled contact")
    local actions=0;for _,ev in ipairs(state.events) do if ev.type=="action" then actions=actions+1 end end
    assert(actions==1 and costCalls==1,"action or cost execution duplicated")
    local damageCount=0
    for _,ev in ipairs(state.events) do
        if ev.target==state.enemy and ev.resolved and ev.resolved.hp~=nil then
            damageCount=damageCount+1;assert(ev.resolved.hp==state.enemy.hp,"damage fact missing committed HP")
        end
    end
    assert(damageCount==1,"damage applied or published more than once")
    capture("07-hit")
    tick(state.spec.playerRecoverySeconds/2)
    assert(state.mode=="simulation","recovery did not release control")
    -- Continue legitimate actions to victory; no direct HP mutation for this path.
    while game.arenaEncounter do
        if state.mode=="simulation" then
            state.at=1;confirm();confirm();confirm()
            tick(state.spec.playerWindupSeconds)
            if state.pendingResult then
                assert(game.arenaEncounter and require("engine.world_event_actor").snapshot(game,event),"lethal contact cleaned up before aftermath")
                capture("07b-lethal-contact")
            end
            tick(state.spec.playerRecoverySeconds)
        elseif state.mode=="aftermath" then
            local count=state.actionCount
            confirm();cancel();tick(state.spec.terminalSeconds/2)
            assert(game.arenaEncounter and state.actionCount==count,"aftermath accepted input or ended early")
            capture("07c-aftermath")
            tick(state.spec.terminalSeconds/2)
        else error("unexpected victory mode "..state.mode) end
        assert(state.actionCount<30,"victory did not terminate")
    end
    assert(game.arenaResult.result=="victory" and not state.telegraph)
    assert(not require("engine.world_event_actor").snapshot(game,event),"world binding leaked")
    assert(require("engine.game_variables").get(game,"sentinelDefeated")==true,"outcome commands missing")
    capture("08-victory")
    controller.press("LEFT",ctx);tick(0.2);controller.release("LEFT");capture("09-exploration-resumed")
    assert(pcall(require("engine.savegame").serialize,game,loader,"map"),"post-terminal save rejected")
    -- Negative terminal control: enemy attacks reach defeat and authored recovery.
    require("engine.game_variables").set(game,"sentinelDefeated",false)
    interpreter.runImmediate(encounterCommands,{session=game,loader=loader,event=event})
    state=game.arenaEncounter
    semantic.moveBy(game.continuousTraversal,state.root.x-game.continuousTraversal.x,state.root.y-game.continuousTraversal.y+0.4)
    local steps=0
    while game.arenaEncounter do
        tick(0.1);steps=steps+1
        assert(steps<3000 and state.enemyActionCount<40,"defeat did not terminate")
    end
    assert(game.arenaResult.result=="defeat" and game.party[1].hp>0,"loss cleanup/recovery missing")
    capture("10-defeat-recovered")
    skillCost.spend=originalSpend
    assert(json.encode(event)==original,"mutated authored Event")
    print("ARENA PROOF OK")
    print("ARENA PROOF BEGIN");print(json.encode({captures=captures}));print("ARENA PROOF END")
end
function love.load()
    local ok,err=xpcall(run,debug.traceback)
    if not ok then print(err) end
    if io and io.stdout then io.stdout:flush() end
    love.event.quit(ok and 0 or 1);os.exit(ok and 0 or 1)
end
function love.errorhandler(err) print(err);os.exit(1) end
