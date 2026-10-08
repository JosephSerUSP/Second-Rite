-- Presentation consumes provider facts without fabricating gameplay topology.
local view = require("presentation.traversal_view")
local host = require("engine.traversal_host")
local door = require("presentation.door_transition")
local viewport = require("presentation.viewport_3d")
local world = require("presentation.continuous_surface_world")
local failFast = require("tests.fail_fast")
local passed = 0
local function check(value, message)
    assert(value, message)
    passed = passed + 1
end

local originalView, originalPose = host.presentationView, door.actorPose
local originalEnsure, originalDraw = host.ensure, viewport.draw
local ok, err = pcall(function()
    local environment = { manifestPath = "fixture/environment.json", bakedLighting = true }
    local actor = { x = 2, y = 3, z = 0.75, frame = 4, facing = -1, moving = false }
    local camera = { profile = "fixed" }
    local raw = { provider = "continuous_surface", environment = environment, actor = actor, camera = camera }
    local game = setmetatable({ currentMapData = { events = {} } }, {
        __index = function(_, key)
            if key == "townTraversal" then error("continuous presentation read bounded-lane state") end
        end,
    })
    host.presentationView = function(session) return session == game and raw or nil end
    local poseCalls = 0
    door.actorPose = function()
        poseCalls = poseCalls + 1
        return { x = 0.25, y = -0.5, frame = 2 }
    end
    local resolved = view.resolve(game)
    check(resolved.provider == raw.provider and resolved.environment == environment
        and resolved.camera == camera and resolved.unlitActors, "neutral package/camera/lighting facts")
    check(resolved.actor.x == 2.25 and resolved.actor.y == 2.5 and resolved.actor.z == 0.75
        and resolved.actor.frame == 2 and resolved.actor.facing == -1 and resolved.actor.moving,
        "door pose applied once")
    check(poseCalls == 1 and actor.x == 2 and actor.y == 3 and actor.frame == 4
        and actor.moving == false, "presentation leaves provider facts unchanged")
    resolved.actor.x = 99
    check(view.actor(game).x == 2.25, "repeated resolution never accumulates offsets")
    check(resolved.boundedLane == nil and raw.boundedLane == nil, "continuous view has no lane vocabulary")
    check(view.legacyViewportSession == nil, "legacy viewport adapter removed")
    check(viewport.isLiveBakedEnvironment(game), "continuous environment uses baked lighting policy")
    game.currentMapData.events = {
        { id = 9, worldPosition = { 2, 3, 1.5 }, model = "fixture.obj" },
    }
    local placements = viewport.collectEventModelPlacements(game)
    check(#placements == 1 and placements[1].z == 1.5,
        "continuous Event models preserve authored world Z without lane grounding")
    host.ensure = function(session) return session == game and {} or nil end
    viewport.draw = function(session, authoredCamera)
        check(session == game and authoredCamera == camera, "world forwards the real session and Scene camera")
    end
    world.draw(game, { camera = camera })

    local lane = { x = 1, y = 2, z = 0.5, visualX = 1.1, visualY = 2.2,
        walkFrameIndex = 3, facing = 1, walking = true, environment = environment, camera = camera }
    local bounded = view.resolve({ townTraversal = lane })
    check(bounded.provider == "bounded_lane" and bounded.boundedLane == lane
        and bounded.environment == environment and bounded.camera == camera, "real bounded-lane facts retained")
    check(math.abs(bounded.actor.x - 1.35) < 1e-9 and math.abs(bounded.actor.y - 1.7) < 1e-9 and bounded.actor.z == 0.5
        and bounded.actor.frame == 2 and bounded.actor.moving, "bounded visual root receives one door offset")
    check(lane.visualX == 1.1 and lane.visualY == 2.2 and lane.walkFrameIndex == 3,
        "bounded source pose unchanged")
    door.actorPose = function() return nil end
    check(view.resolve({ townTraversal = lane }).actor.moving, "bounded walking animation retained")
    lane.walking = false
    check(not view.resolve({ townTraversal = lane }).actor.moving, "bounded idle animation retained")
    check(view.resolve({}) == nil, "grid Maps have no traversal view")
end)
host.presentationView, door.actorPose = originalView, originalPose
host.ensure, viewport.draw = originalEnsure, originalDraw
assert(ok, err)
failFast("test_traversal_view", 0, passed)
return {}
