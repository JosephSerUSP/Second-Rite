-- Export actual bounded-lane camera poses for offline Blender consumption.
local function exportViews()
    local n=#arg
    local root,mapPath,output=arg[n-2],arg[n-1],arg[n]
    package.path=root..'/runtime/?.lua;'..package.path
    local json=require('engine.data.json')
    local lane=require('engine.bounded_lane')
    local calibration=require('presentation.world_camera_calibration')
    local surface=require('presentation.surface')
    local viewport=require('presentation.viewport_3d')
    local f=assert(io.open(mapPath,'rb'));local text=f:read('*a');f:close()
    local map=json.decode(text)
    local spec=map.traversal
    local session={}
    local anchors={[spec.spawnAnchor]={position={spec.lane.depthX,spec.lane.minY,spec.lane.groundZ}}}
    lane.initialize(session,map,{anchors=anchors})
    local positions={0,1,.5,2,5,8,11.5,spec.lane.maxY,.35,spec.lane.maxY-.35}
    for i=0,8 do positions[#positions+1]=.6+i*(spec.lane.maxY-1.2)/8 end
    for i=0,15 do positions[#positions+1]=.6+i*(spec.lane.maxY-1.2)/15 end
    local result={sourceMap=mapPath:match("[^/\\]+$"),authoredCamera=spec.camera,views={}}
    for _,y in ipairs(positions) do
        session.townTraversal.y=y;lane.update(session)
        for _,width in ipairs({256,426}) do
            local frame=spec.camera.projectionFrame
            surface.setProfile(width==256 and 'classic' or 'wide')
            local centerX,horizonY=viewport.authoredCompositionCenter(spec.camera)
            result.views[#result.views+1]={y=y,width=width,record=calibration.resolve(session,{
                profile=spec.camera.profile,authoredCamera=spec.camera,
                projectionFrame={targetWidth=width,targetHeight=240,
                    baseViewportWidth=frame.baseViewportWidth,baseViewportHeight=frame.baseViewportHeight,
                    compositionWidth=frame.baseViewportWidth,canonicalCenterX=centerX,canonicalHorizonY=horizonY}})}
        end
    end
    f=assert(io.open(output,'wb'));f:write(json.encode(result));f:close()
    print('LANE CAMERAS OK');love.event.quit()
end

function love.load()
    local ok,err=xpcall(exportViews,debug.traceback)
    if not ok then print(err);love.event.quit(1) end
end
