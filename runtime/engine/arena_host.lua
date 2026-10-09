-- Encounter simulation owns time/readiness/telegraphs; action_execution owns effects.
local execution = require("engine.action_execution")
local world = require("engine.world_event_actor")
local variables = require("engine.game_variables")
local arena = {}
local numeric = {"readySeconds","enemyPeriod","windupSeconds","range","attackRadius","enemySpeed","stopDistance"}
function arena.resolveSpec(command,evaluate)
    local spec={};for key,value in pairs(command) do spec[key]=value end
    for _,key in ipairs(numeric) do spec[key]=evaluate(command[key]) end
    spec.playerSlot=evaluate(command.playerSlot)
    return spec
end
function arena.validateSpec(spec,loader,authored)
    for _,key in ipairs(numeric) do
        local n=spec[key]
        if authored and type(n)=="string" then
            local ok,err=require("engine.formula").validateSyntax(n)
            assert(ok,"arena "..key.." formula: "..tostring(err))
        else
            assert(type(n)=="number" and n==n and n>0 and n<math.huge,"arena "..key.." must be positive finite")
        end
    end
    local skill=assert(loader.getSkill(spec.skillId),"arena skill does not exist")
    local target=require("engine.targeting").expand(skill.target)
    assert(target.side=="enemy" and target.shape=="single" and target.mode=="choose","arena requires a chosen single-enemy skill")
    assert((skill.cooldown==nil or skill.cooldown==0) and (skill.warmup==nil or skill.warmup==0),
        "arena does not schedule round-timed cooldowns or warmups")
    assert(loader.getUnit(spec.enemyUnitId),"arena enemy Unit does not exist")
    local function immediate(node)
        if type(node)~="table" then return end
        if node.cmd then assert(not require("engine.interpreter").INTERACTIVE_IDS[node.cmd],
            "arena outcomes require immediate commands; interactive dialogue belongs in the destination Scene") end
        for _,value in pairs(node) do immediate(value) end
    end
    immediate(spec.onVictory);immediate(spec.onDefeat)
    assert(type(spec.playerSlot)=="number" and spec.playerSlot%1==0 and spec.playerSlot>=1 and spec.playerSlot<=4,"arena playerSlot must be 1..4")
end
function arena.validate(spec,loader,map,authored)
    arena.validateSpec(spec,loader,authored)
    assert(map.traversal and map.traversal.provider=="continuous_surface","arena requires continuous surface")
    local found
    for _,ev in ipairs(map.events or {}) do if ev.id==spec.eventId then found=ev end end
    assert(found and found.worldPosition and not found.wallEvent,"arena enemy must be a world floor Event")
    local root=require("engine.continuous_surface_provider").createActor({currentMapData=map},found)
    if type(spec.enemySpeed)=="number" then
        assert(spec.enemySpeed<=root._compiled.speed,"arena enemySpeed exceeds the Map movement speed")
    end
    return found
end
local function publish(session,state)
    variables.set(session,"arena",{active=state.active,mode=state.mode,at=state.at,
        hp=state.player.hp,maxHp=state.player:getMaxHp(session),enemyHp=state.enemy.hp,
        enemyMaxHp=state.enemy:getMaxHp(session),message=state.message or "",result=state.result or ""})
end
local function context(session,enemy,player)
    local ctx={session=session,allies={player},enemies={enemy}}
    ctx.applyItem=execution.applyItem
    ctx.evaluateCover=execution.evaluateCover
    function ctx:getAllActiveBattlers()
        local list={}
        for _,group in ipairs({self.allies,self.enemies}) do
            for _,b in ipairs(require("engine.formation").denseMembers(group)) do list[#list+1]=b end
        end
        return list
    end
    return ctx
end
function arena.start(session,spec)
    assert(not session.arenaEncounter,"arena encounter already active")
    local event=arena.validate(spec,session.loader,session.currentMapData)
    local player=assert(session.party[spec.playerSlot],"arena player slot is empty")
    assert(not player:isDead(),"arena player is dead")
    local enemy=require("engine.session").Battler.new(session.loader.getUnit(spec.enemyUnitId))
    enemy.hp=enemy:getMaxHp(session)
    local state={active=true,spec=spec,event=event,player=player,enemy=enemy,elapsed=0,at=0,
        mode="simulation",enemyTimer=0,events={},actionCount=0,enemyActionCount=0}
    state.combat=context(session,enemy,player)
    require("engine.skill_cost").beginBattle(enemy,session.loader)
    require("engine.skill_cost").beginBattle(player,session.loader)
    state.root=world.create(session,event)
    session.arenaEncounter=state
    publish(session,state)
    return state
end
local function finish(session,state,result)
    state.active=false;state.result=result;state.mode="terminal";state.telegraph=nil
    world.remove(session,state.event)
    require("engine.skill_cost").endBattle(state.player)
    require("engine.skill_cost").endBattle(state.enemy)
    session.arenaEncounter=nil
    session.arenaResult={result=result,actionCount=state.actionCount,enemyActionCount=state.enemyActionCount,elapsed=state.elapsed}
    publish(session,state)
    local commands=result=="victory" and state.spec.onVictory or state.spec.onDefeat
    local ctx={session=session,loader=session.loader,party=session.party,event=state.event}
    local events=require("engine.interpreter").runImmediate(commands or {},ctx)
    require("engine.scene_host").consumeEvents(events,ctx)
    if not session.arenaEncounter then publish(session,state) end
end
local function checkEnd(session,state)
    if state.enemy:isDead() then finish(session,state,"victory");return true end
    if state.player:isDead() then finish(session,state,"defeat");return true end
end
function arena.inRange(x,y,tx,ty,radius)
    return (x-tx)^2+(y-ty)^2<=radius^2
end
function arena.input(session,button)
    local state=session.arenaEncounter
    if not state then return false end
    if button=="cancel" then
        if state.mode=="targeting" then state.mode="command" else state.mode="simulation" end
        state.message=""
    elseif button=="confirm" then
        if state.mode=="simulation" then
            if state.at>=1 then state.mode="command" end
        elseif state.mode=="command" then state.mode="targeting"
        else
            local x,y=require("engine.traversal_host").actorRoot(session)
            if not arena.inRange(x,y,state.root.x,state.root.y,state.spec.range) then
                state.message="out_of_range"
            elseif not require("engine.usability").canUseSkill(session.loader.getSkill(state.spec.skillId),state.player,state.enemy,
                    {session=session,battle=state.combat,isEnemy=false}) then state.message="unavailable"
            else
                execution.execute(state.combat,{actor=state.player,target=state.enemy,skill=session.loader.getSkill(state.spec.skillId)},state.events)
                state.actionCount=state.actionCount+1;state.at=0;state.mode="simulation";state.message=""
                checkEnd(session,state)
            end
        end
    end
    if state.active then publish(session,state) end
    return true
end
function arena.update(session,dt)
    local state=session.arenaEncounter
    if not state then return false end
    assert(type(dt)=="number" and dt>=0 and dt<math.huge,"arena dt must be finite nonnegative")
    if state.mode~="simulation" then return true end
    state.elapsed=state.elapsed+dt;state.at=math.min(1,state.at+dt/state.spec.readySeconds)
    local x,y,z=require("engine.traversal_host").actorRoot(session)
    if state.telegraph then
        state.telegraph.remaining=state.telegraph.remaining-dt
        world.move(session,state.event,0,0,0)
        if state.telegraph.remaining<=0 then
            local zone=state.telegraph;state.telegraph=nil;state.enemyTimer=0
            if arena.inRange(x,y,zone.x,zone.y,zone.radius) then
                execution.execute(state.combat,{actor=state.enemy,target=state.player,skill=session.loader.getSkill(state.spec.skillId)},state.events)
                state.enemyActionCount=state.enemyActionCount+1
                if checkEnd(session,state) then return false end
            end
        end
    else
        local dx,dy=x-state.root.x,y-state.root.y
        local distance=math.sqrt(dx*dx+dy*dy)
        local scale=distance>state.spec.stopDistance and state.spec.enemySpeed or 0
        local speed=state.root._compiled.speed
        world.move(session,state.event,dt, distance>0 and dx/distance*scale/speed or 0,distance>0 and dy/distance*scale/speed or 0)
        state.enemyTimer=state.enemyTimer+dt
        if state.enemyTimer>=state.spec.enemyPeriod then
            state.telegraph={x=x,y=y,z=z,radius=state.spec.attackRadius,remaining=state.spec.windupSeconds}
        end
    end
    publish(session,state)
    return false
end
return arena
