local M = {}
function M.run(loader)
    local session = require('engine.session').GameSession.new(loader)
    session:initializeStartingParty()
    local exploration = require('engine.exploration')
    local lane = require('engine.bounded_lane')
    local interpreter = require('engine.interpreter')
    local director = require('engine.director')
    local conditions = require('engine.conditions')
    local visited, shops = {}, {}
    local function hasWrit() return conditions.evalPrefixed('hasItem:198', session) end
    -- Content conversations must be played, not replaced with isolated shop primitives.
    require('tests.test_weaponsmith_dialogue')
    local singletonSprites={['assets/character/npc_alicia.png']=0,
        ['assets/character/npc_laura.png']=0,['assets/character/town/npc_gate_guard.png']=0}
    for _,map in ipairs(loader.maps) do
        for _,event in ipairs(map.events or {}) do
            if singletonSprites[event.sprite] then singletonSprites[event.sprite]=singletonSprites[event.sprite]+1 end
        end
    end
    for sprite,count in pairs(singletonSprites) do assert(count==1,'Duplicate town character: '..sprite..' count '..count) end
    local climbs={}
    for mapId=1001,1009 do
        local probe=require('engine.session').GameSession.new(loader)
        exploration.loadMap(probe,loader.getMapIndex(mapId))
        local state=probe.townTraversal
        assert(state.environment.collisionMesh and #state.groundProfile>1,'Missing walking support on '..mapId)
        local mesh=assert(love.filesystem.read(state.environment.collisionMesh))
        local vertices={}
        for x,y,z in mesh:gmatch('\nv ([^ ]+) ([^ ]+) ([^\r\n]+)') do
            vertices[#vertices+1]={tonumber(x),tonumber(y),tonumber(z)}
        end
        assert(#vertices==#state.groundProfile*2,'Walking mesh omits profile samples')
        for i,point in ipairs(state.groundProfile) do
            for side=1,2 do
                local v=vertices[(i-1)*2+side]
                assert(math.abs(v[2]-point.y)<.00001 and math.abs(v[3]-point.z)<.00001,'Walking mesh disagrees with native ground')
            end
        end
        lane.update(probe,(state.y-state.minY)/state.speed,-1); lane.update(probe)
        local lo,hi=state.z,state.z
        for tick=1,3000 do
            lane.update(probe,1/30,1)
            lo=math.min(lo,state.z);hi=math.max(hi,state.z)
            if state.y==state.maxY then break end
        end
        assert(state.y==state.maxY,'Cannot traverse full walking support on '..mapId)
        if hi-lo>.4 then climbs[#climbs+1]=mapId end
    end
    assert(#climbs>=2,'Town still exports only flat walking profiles')
    local function run(commands, choice)
        local ctx = {session=session, loader=loader, party=session.party,
            recoverParty=function() session:rest() end}
        local graph = interpreter.runInteractive(commands, ctx)
        local walker = director.GraphWalker.new(session, graph)
        for tick=1,1000 do
            local node = walker:getCurrentNode()
            if not node then return end
            if node.type == 'CHOICE' then
                local chosen
                for i, option in ipairs(node.options) do
                    local requested=type(choice)=='table' and choice[1] or choice
                    if option.label == requested then chosen=i end
                end
                assert(chosen, 'Missing choice '..tostring(choice))
                walker:selectChoice(chosen)
                if type(choice)=='table' then table.remove(choice,1) end
            elseif node.type == 'ACTION' then
                if node.action == 'RUN_IMMEDIATE' then
                    interpreter.runImmediate(node.commands, ctx)
                    walker:advance()
                elseif node.action == 'CALL_COMMON_EVENT_ACTION' then
                    local ce=assert(loader.commonEvents[tostring(node.commonEventId)])
                    local first=interpreter.compileTop(graph.nodes,ce.commands,'ce_'..tick,node.next,ctx)
                    walker:goToNode(first)
                elseif node.action == 'OPEN_SHOP' then
                    assert(loader.shops[tostring(node.shopId)])
                    shops[#shops+1]=node.shopId
                    walker:advance()
                elseif node.action == 'WAIT_EVENT' then
                    walker:advance()
                elseif node.action == 'OFFER_QUEST' then
                    require('engine.quest').offer(session,loader,node.questId);walker:advance()
                elseif node.action == 'COMPLETE_QUEST' then
                    require('engine.quest').complete(session,loader,node.questId);walker:advance()
                else error('Unhandled native graph action '..tostring(node.action)) end
            else walker:advance() end
        end
        error('Graph did not finish')
    end
    local function walk(target)
        for tick=1,1800 do
            local y=session.townTraversal.y
            if math.abs(y-target)<.04 then return end
            lane.update(session,1/60,target>y and 1 or -1)
        end
        error('Could not walk to '..target)
    end
    local function door(anchor, expected)
        walk(assert(session.townTraversal.environment.anchors[anchor]).position[2])
        local doorway
        for _, candidate in ipairs(session.townTraversal.doorways) do
            if candidate.anchor == anchor then doorway=candidate end
        end
        local button = assert(lane.doorwayButton(session, doorway))
        assert(lane.nearDoorway(session, button).anchor==anchor, 'Wrong directed door')
        if button == 'DOWN' then
            assert(lane.interact(session,'UP')~=lane.eventFor(session,doorway),'UP opened a DOWN exit')
        end
        local event=assert(lane.interact(session,button))
        local transfer
        for _,command in ipairs(event.commands) do
            if command.cmd=='LOAD_MAP' then transfer=command end
        end
        run(event.commands)
        assert(session.currentMapData.id==expected, 'Wrong arrival')
        if session.townTraversal then
            assert(transfer and transfer.arrival, 'Town transfer has no named arrival')
            local state=session.townTraversal
            local destination=assert(state.environment.anchors[transfer.arrival], 'Missing destination doorway')
            assert(math.abs(state.y-destination.position[2])<.00001,
                'Transfer landed away from its destination doorway: '..anchor)
        end
        visited[#visited+1]=expected
    end
    exploration.loadMap(session,loader.getMapIndex(loader.system.spawn.mapId))
    assert(session.currentMapData.id==25)
    local _, writ=hasWrit(); assert(not writ)
    session.mp=1
    local before=session.mp
    local caretaker,homeExit
    for _,event in ipairs(session.currentMapData.events) do
        if event.name=='Passage House caretaker' then caretaker=event end
        if event.instanceId=='st-maria-lodging-exit_door' then homeExit=event end
    end
    assert(caretaker and homeExit and caretaker~=homeExit,'Room 3 caretaker replaced its exit')
    run(caretaker.commands, 'Leave.')
    assert(session.mp==before, 'Opening a lodging dialogue healed eagerly')
    run(caretaker.commands, 'Rest in Room 3.')
    assert(session.mp>before, 'Rest did not recover MP')
    _, writ=hasWrit(); assert(not writ, 'Lodging granted writ')
    door('exit_door',1001)
    door('to-praca',1005)
    door('door-registry',33)
    run(loader.maps[loader.getMapIndex(33)].events[1].commands)
    _, writ=hasWrit(); assert(writ,'Registry did not grant writ')
    door('exit_door',1005)
    door('door-chapel',22)
    local agnes
    for _,event in ipairs(session.currentMapData.events) do if event.name=='Agnes' then agnes=event end end
    walk(assert(agnes).worldPosition[2])
    run(agnes.commands)
    assert(session.flags.agnes_met,'The chapel cannot introduce Agnes')
    door('exit_door',1005)
    door('to-court',1001)
    door('to-market',1002)
    door('door-bakery',28)
    local alicia
    for _,event in ipairs(session.currentMapData.events) do if event.name=='Alicia' then alicia=event end end
    run(assert(alicia).commands,{'Buy','Ask about the town','Leave'})
    require('engine.quest').offer(session,loader,'silent_shipment')
    run(alicia.commands,{'Goblins? I should tell the guard.','Leave'})
    assert(session.flags.shipment_investigated,'The single Alicia cannot advance the shipment quest')
    door('exit_door',1002)
    door('to-quay',1003)
    door('door-pub',21)
    local pubOwner
    for _,event in ipairs(session.currentMapData.events) do
        if event.instanceId=='st-maria-pub-owner' then pubOwner=event end
    end
    assert(pubOwner,'The pub owner is missing')
    walk(pubOwner.worldPosition[2])
    run(pubOwner.commands,'Leave')
    door('exit_door',1003)
    door('to-forge',1004)
    door('door-forge',29)
    door('exit_door',1004)
    door('to-port',1008)
    door('to-court',1001)
    door('to-praca',1005)
    door('to-churchyard-climb',1006)
    door('to-praca-climb',1005)
    door('to-churchyard-stair',1009)
    door('to-churchyard',1006)
    door('to-threshold',1007)
    local guard
    for _,event in ipairs(session.currentMapData.events) do if event.name=='Guard' then guard=event end end
    run(assert(guard,'Guard is not stationed at the Labyrinth').commands)
    assert(session.flags['quest:silent_shipment:completed'],'Gate guard cannot finish Alicia shipment report')
    door('labyrinth-gate',2)
    assert(session.flags.dungeon_entered and session.flags.stratum_bellroot_seen)
    local stairs
    for _,event in ipairs(session.events or session.currentMapData.events) do
        if event.scriptId==40 then stairs=event end
    end
    assert(stairs,'First floor entrance stairs are missing')
    run(loader.commonEvents['40'].commands,'Climb up')
    assert(session.currentMapData.id==1007 and session.flags.first_return)
    visited[#visited+1]=1007
    door('to-churchyard',1006)
    door('to-churchyard-stair',1009)
    door('to-praca',1005)
    door('to-court',1001)
    door('door-passage-house',25)
    local saved=require('engine.savegame')
    local restored=saved.deserialize(saved.serialize(session,loader,'town'),loader)
    assert(restored.currentMapData.id==25 and restored.flags.first_return)
    local _, restoredWrit=conditions.evalPrefixed('hasItem:198',restored)
    assert(restoredWrit)
    print('PLAYTEST LOOP OK '..require('engine.data.json').encode({arrivals=visited,shops=shops,climbingMaps=climbs,
        proof='Native lane movement and interpreter graphs; no combat or physical Android acceptance implied'}))
end
return M
