local compositor = require("presentation.world_pass_compositor")
local viewport = require("presentation.viewport_3d")

local passed, failed = 0, 0
local function check(condition, message)
    if condition then
        passed = passed + 1
    else
        failed = failed + 1
        io.stderr:write("FAIL: " .. message .. "\n")
    end
end

local function sessionWithScale(value)
    return {
        loader = {
            system = {
                dungeon = {
                    psxRendering = {
                        environmentSupersample = value,
                    },
                },
            },
        },
    }
end

check(compositor.resolveScale(sessionWithScale(nil)) == 1,
    "selective environment AA defaults off")
check(compositor.resolveScale(sessionWithScale(3)) == 3,
    "3x environment supersampling resolves")
check(compositor.resolveScale(sessionWithScale(9)) == 4,
    "environment supersampling is bounded to 4x")
check(compositor.resolveScale(sessionWithScale(1)) == 1,
    "1x uses the ordinary world path")

local function laneSession(value)
    local session = sessionWithScale(value)
    session.townTraversal = { provider = "bounded_lane", environment = {} }
    return session
end

local firstPerson = sessionWithScale(3)
check(not compositor.isFakePrerendered(firstPerson),
    "a first-person grid map is realtime PS1, not fake pre-rendered")
check(not compositor.isEligible(firstPerson),
    "first-person maps never supersample, whatever the project scale")

local eligible = laneSession(3)
check(compositor.isFakePrerendered(eligible),
    "a live bounded-lane map is the fake pre-rendered style")
check(compositor.isEligible(eligible),
    "fake pre-rendered lane maps accept selective AA")
eligible.roomBakePass = "depth"
check(not compositor.isEligible(eligible),
    "room bake diagnostics bypass selective AA")

local prerendered = sessionWithScale(3)
prerendered.townTraversal = { environment = { preRendered = { mode = "layered_2d" } } }
check(not compositor.isEligible(prerendered),
    "literal layered prerender stays on its existing renderer")
check(not compositor.isFakePrerendered(prerendered),
    "literal layered prerender is a real pre-render, not the fake style")

check(viewport.surfacePresentationPass({ category = "billboard" }) == "live",
    "ordinary billboards default to the live pass")
check(viewport.surfacePresentationPass({ category = "wall_clip" }) == "environment",
    "structural dynamic geometry defaults to environment")
check(viewport.surfacePresentationPass({ presentationPass = "live", category = "wall_clip" }) == "live",
    "explicit renderer pass ownership wins")
check(viewport.surfacePresentationPass({ model = true }) == "environment",
    "unclassified placed models retain environment default")

-- #1393: policy-only assertions let a compositor that returned a black world
-- pass its suite. Exercise the actual Canvas hand-off and explicit box resolve.
-- The callback deliberately draws in raster coordinates so this test isolates
-- compositor ownership from WorldCamera/projection behavior.
do
    local previousCanvas = love.graphics.getCanvas()
    local canvas = love.graphics.newCanvas(32, 24)
    local ok, err = pcall(function()
        love.graphics.setCanvas({ canvas, depth = true, stencil = true })
        love.graphics.clear(0, 0, 0, 1, true, true)
        compositor.draw(laneSession(3), nil, nil,
            function(_, _, _, options)
                options = options or {}
                local scale = options.rasterScale or 1
                if options.presentationPass == "environment" then
                    love.graphics.setColor(1, 0.25, 0.125, 1)
                    love.graphics.rectangle("fill", 4 * scale, 4 * scale, 16 * scale, 12 * scale)
                elseif options.presentationPass == "live" then
                    love.graphics.setColor(0.125, 1, 0.25, 1)
                    love.graphics.rectangle("fill", 24, 5, 4, 4)
                end
            end)
        love.graphics.setCanvas()
        local image = canvas:newImageData()
        local er, eg, eb = image:getPixel(10, 10)
        local lr, lg, lb = image:getPixel(25, 6)
        check(er > 0.5 and eg > 0.05 and eb > 0.02,
            "3x environment colour survives the supersample box resolve")
        check(lg > 0.5 and lr < 0.5 and lb < 0.5,
            "native live colour survives after the resolved environment")
    end)
    love.graphics.setCanvas(previousCanvas)
    if canvas.release then canvas:release() end
    check(ok, "pixel compositor path completes: " .. tostring(err))
end

local function countNonBlack(image, width, height)
    local count = 0
    for y = 0, height - 1 do
        for x = 0, width - 1 do
            local r, g, b = image:getPixel(x, y)
            if math.max(r, g, b) > 0.02 then count = count + 1 end
        end
    end
    return count
end

-- Drive the production viewport as well. The synthetic test above distinguishes
-- resolve failure from camera/model failure; this one catches the latter. Map 28
-- is a shipped live-3D interior with the same calibrated town-sideview camera
-- family used by the #1393 native staging control, including a large authored
-- projection-window Y offset. Compare 3x occupancy against the ordinary 1x
-- render so a Walker-sized remnant cannot certify a black environment.
do
    local loader = require("engine.data.loader")
    local sessionModule = require("engine.session")
    local exploration = require("engine.exploration")
    local surface = require("presentation.surface")
    loader.init()
    local game = sessionModule.GameSession.new(loader)
    game:initializeStartingParty()
    exploration.loadMap(game, loader.getMapIndex(28))

    local previousProfile = surface.getProfileId()
    local psx = loader.system.dungeon.psxRendering
    local previousScale = psx.environmentSupersample

    local function nonBlackPixels(scale)
        psx.environmentSupersample = scale
        surface.setProfile("wide")
        local width, height = surface.renderSize()
        local canvas = surface.newRasterCanvas(width, height)
        local previousCanvas = love.graphics.getCanvas()
        local capturedSupersample = nil
        local originalNewRasterCanvas = surface.newRasterCanvas
        if scale > 1 then
            surface.newRasterCanvas = function(w, h, settings)
                local target = originalNewRasterCanvas(w, h, settings)
                if (not settings or not settings.format)
                        and w == width * scale and h == height * scale then
                    capturedSupersample = target
                end
                return target
            end
        end
        local ok, result = pcall(function()
            love.graphics.setCanvas({ canvas, depth = true, stencil = true })
            love.graphics.clear(0, 0, 0, 1, true, true)
            love.graphics.setColor(1, 1, 1, 1)
            viewport.draw(game, game.townTraversal.camera)
            love.graphics.setCanvas()
            local image = canvas:newImageData()
            local count = countNonBlack(image, width, height)
            local ssCount = nil
            if capturedSupersample then
                local ssWidth, ssHeight = capturedSupersample:getDimensions()
                ssCount = countNonBlack(capturedSupersample:newImageData(), ssWidth, ssHeight)
            end
            return { native = count, supersample = ssCount }
        end)
        surface.newRasterCanvas = originalNewRasterCanvas
        love.graphics.setCanvas(previousCanvas)
        if canvas.release then canvas:release() end
        if not ok then error(result, 0) end
        return result
    end

    local ok, err = pcall(function()
        local nativeResult = nonBlackPixels(1)
        local supersampledResult = nonBlackPixels(3)
        print(string.format("  [INFO] selective-AA wide pixels: 1x=%d 3x=%d envSS=%s",
            nativeResult.native, supersampledResult.native,
            tostring(supersampledResult.supersample)))
        check(nativeResult.native > 1000,
            "live-3D fixture has a meaningful ordinary world render")
        check(supersampledResult.native > nativeResult.native * 0.5,
            "3x selective AA retains the environment rather than only live remnants")
    end)
    psx.environmentSupersample = previousScale
    surface.setProfile(previousProfile)
    check(ok, "real selective-AA viewport path completes: " .. tostring(err))
end

print(string.format("WORLD PASS COMPOSITOR TESTS: %d passed, %d failed", passed, failed))
assert(failed == 0, string.format("world pass compositor suite had %d failure(s)", failed))
