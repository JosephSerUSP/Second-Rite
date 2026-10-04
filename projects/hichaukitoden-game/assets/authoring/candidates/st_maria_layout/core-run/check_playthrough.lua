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
                    if option.label == choice then chosen=i end
                end
                assert(chosen, 'Missing choice '..tostring(choice))
                walker:selectChoice(chosen)
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
        assert(lane.nearDoorway(session).anchor==anchor, 'Wrong normal door')
        local event=assert(lane.interact(session))
        run(event.commands)
        assert(session.currentMapData.id==expected, 'Wrong arrival')
        visited[#visited+1]=expected
    end
    exploration.loadMap(session,loader.getMapIndex(loader.system.spawn.mapId))
    assert(session.currentMapData.id==25)
    local _, writ=hasWrit(); assert(not writ)
    session.mp=1
    local before=session.mp
    run(loader.maps[loader.getMapIndex(25)].events[1].commands, 'Leave.')
    assert(session.mp==before, 'Opening a lodging dialogue healed eagerly')
    run(loader.maps[loader.getMapIndex(25)].events[1].commands, 'Rest in Room 3.')
    assert(session.mp>before, 'Rest did not recover MP')
    _, writ=hasWrit(); assert(not writ, 'Lodging granted writ')
    door('exit_door',1001)
    door('to-praca',1005)
    door('door-registry',33)
    run(loader.maps[loader.getMapIndex(33)].events[1].commands)
    _, writ=hasWrit(); assert(writ,'Registry did not grant writ')
    door('exit_door',1005)
    door('to-court',1001)
    door('to-market',1002)
    door('door-bakery',28)
    for _,event in ipairs(session.currentMapData.events) do
        if event.name~='Out to Bakery side street' and event.commands then
            -- Shop event trees are validated separately; open their authored
            -- shop primitives through the native interpreter graph.
            local function find(commands)
                for _,cmd in ipairs(commands) do
                    if cmd.cmd=='OPEN_SHOP' then run({cmd}) end
                    if cmd.commands then find(cmd.commands) end
                    if cmd.options then for _,opt in ipairs(cmd.options) do find(opt.commands or {}) end end
                end
            end
            find(event.commands)
        end
    end
    door('exit_door',1002)
    door('to-quay',1003)
    door('to-forge',1004)
    door('door-forge',29)
    door('exit_door',1004)
    door('to-port',1008)
    door('to-court',1001)
    door('to-praca',1005)
    door('to-churchyard-stair',1009)
    door('to-churchyard',1006)
    door('to-threshold',1007)
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
    print('PLAYTEST LOOP OK '..require('engine.data.json').encode({arrivals=visited,shops=shops,
        proof='Native lane movement and interpreter graphs; no combat or physical Android acceptance implied'}))
end
return M
