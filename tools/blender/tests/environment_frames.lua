-- Generic stage-only review through runtime camera and native compositor.
local module = {}

local function visiblePixelCount(canvas)
    local image = canvas:newImageData()
    local width, height = image:getDimensions()
    local count = 0
    for y = 0, height - 1 do
        for x = 0, width - 1 do
            local r, g, b = image:getPixel(x, y)
            if math.max(r, g, b) > 0.02 then count = count + 1 end
        end
    end
    if image.release then image:release() end
    return count
end

function module.run(loader)
    local json = require('engine.data.json')
    local config = json.decode(assert(love.filesystem.read('environment-review.json')))
    require('engine.user_settings').pinForCapture({touchGamepadEnabled=config.device ~= nil})
    local surface = require('presentation.surface')
    local touch = require('presentation.touch_gamepad')
    if config.device then
        surface.setProfile(touch.configureDeviceSurface(config.device[1], config.device[2]))
    else surface.setProfile(config.surface) end
    local exploration = require('engine.exploration')
    local lane = require('engine.bounded_lane')
    local host = require('engine.scene_host')
    local renderer = require('presentation.renderer')
    local compositor = require('presentation.frame_renderer')
    local view = require('presentation.viewport_3d')
    local calibration = require('presentation.world_camera_calibration')
    local game = require('engine.cli_tools').makeHarnessSession(loader)
    renderer.init(game); view.init(); host.init(nil)
    local result = {}
    for _, position in ipairs(config.positions) do
        -- A position is a lane Y, or {level=, y=} on a map with storeys.
        local y = type(position) == 'table' and position.y or position
        local level = type(position) == 'table' and position.level or nil
        exploration.loadMap(game, loader.getMapIndex(config.mapId))
        if level then
            assert(lane.place(game, level, y), 'Review level missing')
            assert(math.abs(game.townTraversal.y - y) < 1e-6, 'Review position outside level')
        else
            assert(y >= game.townTraversal.minY and y <= game.townTraversal.maxY, 'Review position outside lane')
            game.townTraversal.y = y
            game.townTraversal.z = lane.groundAt(game, y)
        end
        lane.update(game)
        local ctx = {session=game, loader=loader, party=game.party}
        host.goto_scene('map', ctx); host.update(1, ctx); renderer.update(1)
        local width, height = surface.renderSize()
        local cameraSpec = game.townTraversal.camera
        local frame = cameraSpec.projectionFrame
        local centerX, horizonY = view.authoredCompositionCenter(cameraSpec)
        local record = calibration.resolve(game, {profile=cameraSpec.profile, authoredCamera=cameraSpec,
            projectionFrame={targetWidth=width, targetHeight=height,
                baseViewportWidth=frame.baseViewportWidth, baseViewportHeight=frame.baseViewportHeight,
                compositionWidth=frame.baseViewportWidth, canonicalCenterX=centerX, canonicalHorizonY=horizonY}})

        -- #1393: the full frame can contain Walker/UI pixels even when the world
        -- itself is black. Render the viewport alone through the SAME production
        -- compositor and report its visible contribution. The Python wrapper
        -- rejects Walker-sized remnants before writing review evidence.
        local probe = surface.newRasterCanvas(width, height)
        love.graphics.setCanvas({probe, depth=true, stencil=true})
        love.graphics.clear(0,0,0,1,true,true); love.graphics.setColor(1,1,1,1)
        view.draw(game, game.townTraversal.camera)
        love.graphics.setCanvas()
        local viewportVisiblePixels = visiblePixelCount(probe)
        probe:release()

        local canvas = surface.newRasterCanvas(width, height)
        for draw = 1, 2 do
            love.graphics.setCanvas({canvas, depth=true, stencil=true})
            love.graphics.clear(0,0,0,1,true,true); love.graphics.setColor(1,1,1,1)
            if config.unobstructed then view.draw(game, game.townTraversal.camera)
            else compositor.draw(host, renderer, game, loader, height) end
            love.graphics.setCanvas()
            if draw == 1 then love.timer.sleep(0.2) end
        end
        local png = canvas:newImageData():encode('png')
        result[#result+1] = {y=y, level=level, z=game.townTraversal.z, width=width, height=height,
            cameraOffsetX=game.townTraversal.cameraOffsetX, surface=surface.getProfileId(), cameraRecord=record,
            viewportVisiblePixels=viewportVisiblePixels,
            image=love.data.encode('string','base64',png)}
        canvas:release()
    end
    print('ENVIRONMENT FRAMES BEGIN'); print(json.encode(result)); print('ENVIRONMENT FRAMES END')
end
return module
