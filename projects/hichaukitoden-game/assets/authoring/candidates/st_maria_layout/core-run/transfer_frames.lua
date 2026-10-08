-- Capture the actual player at every directed interaction zone, not hand-picked poses.
local M={}
function M.run(loader)
    local surface=require('presentation.surface')
    local host=require('engine.scene_host')
    local renderer=require('presentation.renderer')
    local compositor=require('presentation.frame_renderer')
    local lane=require('engine.bounded_lane')
    local exploration=require('engine.exploration')
    require('engine.user_settings').pinForCapture({touchGamepadEnabled=true})
    surface.setProfile(require('presentation.touch_gamepad').configureDeviceSurface(1920,1080))
    local clock=0;love.timer.getTime=function() return clock end
    local game=require('engine.cli_tools').makeHarnessSession(loader)
    renderer.init(game);require('presentation.viewport_3d').init();host.init(nil)
    local ctx={session=game,loader=loader,party=game.party};local frames={}

    -- The old proof carried a hand-written map id list. That silently stopped
    -- being exhaustive when the Passage House gained its stair-hall Map. Let
    -- authored traversal semantics define the fixture instead: every town Map
    -- using bounded_lane contributes all of its directed doorway zones.
    local maps={}
    for _,map in ipairs(loader.maps or {}) do
        if map.category=='town' and type(map.traversal)=='table'
                and map.traversal.provider=='bounded_lane' then
            maps[#maps+1]=map
        end
    end
    table.sort(maps,function(a,b) return tonumber(a.id)<tonumber(b.id) end)

    for _,map in ipairs(maps) do
        local mapId=map.id
        for _,authoredDoor in ipairs(map.traversal.doorways or {}) do
            -- Load through the doorway itself. Besides making each capture
            -- independent, this asks bounded_lane.initialize to resolve the
            -- correct authored level from the arrival anchor. A multi-storey
            -- Map therefore proves gallery doors on the gallery and ground
            -- doors on the ground instead of trying to walk through a stair.
            exploration.loadMap(game,loader.getMapIndex(mapId),{arrival=authoredDoor.anchor})
            local state=game.townTraversal
            local door
            for _,candidate in ipairs(state.doorways or {}) do
                if candidate.anchor==authoredDoor.anchor then door=candidate;break end
            end
            door=assert(door,'Missing loaded doorway '..tostring(authoredDoor.anchor))
            local anchor=assert(state.environment.anchors[door.anchor])
            local button=assert(lane.doorwayButton(game,door))
            local event=assert(lane.eventFor(game,door))
            assert(lane.interact(game,button)==event,'Graphic pose does not activate '..door.anchor)
            local boundaryChecks=0
            for _,side in ipairs({-1,1}) do
                for _,offset in ipairs({door.radius-.05,door.radius+.05}) do
                    local target=anchor.position[2]+side*offset
                    if target>=state.minY and target<=state.maxY then
                        local step=target-state.y
                        lane.update(game,math.abs(step)/state.speed,step<0 and -1 or 1);lane.update(game)
                        local active=lane.interact(game,button)==event
                        assert(active==(offset<door.radius),'Transfer bounds mismatch '..door.anchor)
                        boundaryChecks=boundaryChecks+1
                    end
                end
            end
            local delta=anchor.position[2]-state.y
            lane.update(game,math.abs(delta)/state.speed,delta<0 and -1 or 1);lane.update(game)
            host.goto_scene('map',ctx);host.update(1,ctx);renderer.update(1)
            local w,h=surface.renderSize();local canvas=surface.newRasterCanvas(w,h)
            for i=1,2 do
                clock=clock+.25;love.graphics.setCanvas({canvas,depth=true,stencil=true})
                love.graphics.clear(0,0,0,1,true,true);love.graphics.setColor(1,1,1,1)
                compositor.draw(host,renderer,game,loader,h);love.graphics.setCanvas()
            end
            frames[#frames+1]={label=tostring(mapId)..'-'..door.anchor,mapId=mapId,anchor=door.anchor,
                eventName=event.name,button=button,laneY=state.y,groundZ=state.z,radius=door.radius,
                level=state.level,boundaryChecks=boundaryChecks,
                sourceSHA256=state.environment.manifest.provenance and state.environment.manifest.provenance.sourceSHA256,
                composition=state.lastPrerenderComposition,
                image=love.data.encode('string','base64',canvas:newImageData():encode('png'))}
            canvas:release()
        end
    end
    assert(#frames>0,'No bounded-lane town doorway zones were captured')
    print('TRANSFER FRAMES BEGIN');print(require('engine.data.json').encode(frames));print('TRANSFER FRAMES END')
end
return M
