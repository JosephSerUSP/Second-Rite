-- Camera-neutral playable-player actor characterization. No renderer or input
-- adapter is needed: this pins root interpolation, cardinal facing and semantic
-- locomotion state while proving overhead cameras can follow the same root.
local player_actor = require("engine.player_actor")
local world_camera = require("presentation.world_camera")

local function assertEq(actual, expected, message)
    if actual ~= expected then
        error((message or "values differ") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual), 0)
    end
end

local function assertNear(actual, expected, message)
    if math.abs(actual - expected) > 0.000001 then
        error((message or "values differ") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual), 0)
    end
end

print("[TEST] Starting playable player-actor tests...")

local sess = { playerX = 4, playerY = 5, playerDir = "E" }
local x, y = player_actor.root(sess)
assertNear(x, 4.5, "resting root X is tile center")
assertNear(y, 5.5, "resting root Y is tile center")
local resting = player_actor.snapshot(sess)
assertEq(resting.clip, "idle", "resting player resolves idle")
assertEq(resting.facing, "E", "resting player preserves facing")

-- Forward east: exploration has already committed x=5. At the start of its
-- visual transition the root reconstructs the old tile center, then crosses to
-- the committed center as transitionTimer counts down.
sess.playerX = 5
sess.transitionDir = "forward"
sess.transitionDuration = 0.20
sess.transitionTimer = 0.20
x, y = player_actor.root(sess)
assertNear(x, 4.5, "forward transition begins on previous tile")
assertNear(y, 5.5, "forward transition preserves perpendicular coordinate")
assertEq(player_actor.snapshot(sess).clip, "walk", "active movement resolves walk")

sess.transitionTimer = 0.10
x, y = player_actor.root(sess)
assertNear(x, 5.0, "forward transition midpoint")
local camera = world_camera.resolve(sess, { profile = "rpg_ortho" })
assertNear(camera.targetX, x, "overhead camera target shares player actor root X")
assertNear(camera.targetY, y, "overhead camera target shares player actor root Y")

sess.transitionTimer = 0
x, y = player_actor.root(sess)
assertNear(x, 5.5, "forward transition settles on committed tile")
assertEq(player_actor.snapshot(sess).clip, "idle", "settled movement returns idle")

-- Backward and strafes are locomotion facts already expressed by exploration.
-- The player actor observes them without deciding which control scheme or
-- camera profile produced those transitions.
sess.playerX, sess.playerY, sess.playerDir = 4, 5, "E"
sess.transitionDir, sess.transitionTimer = "backward", 0.20
x, y = player_actor.root(sess)
assertNear(x, 5.5, "backward reconstructs previous east tile")
assertEq(player_actor.snapshot(sess).facing, "E", "backward keeps body facing east")

sess.playerX, sess.playerY, sess.playerDir = 3, 5, "N"
sess.transitionDir, sess.transitionTimer = "strafe_left", 0.20
x, y = player_actor.root(sess)
assertNear(x, 4.5, "left strafe reconstructs previous tile")
assertEq(player_actor.snapshot(sess).facing, "N", "strafe keeps body facing north")

-- Turning animates the view but does not translate or claim locomotion.
sess.playerX, sess.playerY, sess.playerDir = 4, 5, "W"
sess.transitionDir, sess.transitionTimer = "turn_left", 0.10
x, y = player_actor.root(sess)
assertNear(x, 4.5, "turn transition does not move root X")
assertNear(y, 5.5, "turn transition does not move root Y")
assertEq(player_actor.snapshot(sess).clip, "idle", "turn transition is not walking")

-- The adapter is observational: querying it cannot rewrite gameplay position.
local beforeX, beforeY = sess.playerX, sess.playerY
player_actor.snapshot(sess)
assertEq(sess.playerX, beforeX, "player snapshot does not mutate gameplay X")
assertEq(sess.playerY, beforeY, "player snapshot does not mutate gameplay Y")

local badSession = pcall(function()
    player_actor.root({ playerX = 1, playerY = 2, playerDir = "SE" })
end)
assertEq(badSession, false, "non-cardinal player facing fails loud")

print("  playable player-actor tests passed")
