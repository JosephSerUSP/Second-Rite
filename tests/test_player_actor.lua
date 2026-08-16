-- Playable-overhead player actor characterization. No renderer needed: this
-- pins interpolation/state semantics, world-relative input intent, and the
-- tiny-character asset selection.
local player_actor = require("engine.player_actor")
local overhead_input = require("engine.overhead_playtest_input")
local world_camera = require("presentation.world_camera")
local player_visual = require("presentation.player_character_visual")

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

local function assertContains(value, needle, message)
    if type(value) ~= "string" or not value:find(needle, 1, true) then
        error((message or "string mismatch") .. ": expected '" .. tostring(value)
            .. "' to contain '" .. tostring(needle) .. "'", 0)
    end
end

print("[TEST] Starting playable overhead player-actor tests...")

assertEq(overhead_input.worldFacingForKey("w"), "N", "overhead W means world north")
assertEq(overhead_input.worldFacingForKey("d"), "E", "overhead D means world east")
assertEq(overhead_input.worldFacingForKey("s"), "S", "overhead S means world south")
assertEq(overhead_input.worldFacingForKey("a"), "W", "overhead A means world west")
assertEq(overhead_input.worldFacingForKey("q"), nil, "non-WASD input is not remapped")

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

-- Backward and strafes remain valid inputs to player_actor because first-person
-- mode still authors those transitions. Overhead WASD adapts to facing+forward
-- before this layer, so both camera modes share the same root semantics.
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

-- #599's root-rotation zero is SOUTH. Only that directional Walk bake is used;
-- other moving facings intentionally keep their correct turnaround still.
local southWalk = player_visual.resolve({ clip = "walk", facing = "S" }, 0, "knight")
assertContains(southWalk, "knight_volumetric/walk_f01.png",
    "south movement consumes authored Walk bake")
local eastFallback = player_visual.resolve({ clip = "walk", facing = "E" }, 0, "knight")
assertContains(eastFallback, "knight_volumetric/dir_east.png",
    "east movement falls back to truthful directional still")
local mageNorth = player_visual.resolve({ clip = "idle", facing = "N" }, 0, "mage")
assertContains(mageNorth, "mage_planar/dir_north.png", "mage profile maps north still")
local rogueWest = player_visual.resolve({ clip = "idle", facing = "W" }, 0, "rogue")
assertContains(rogueWest, "rogue_faceted/dir_west.png", "rogue profile maps west still")

local laterWalk = player_visual.resolve({ clip = "walk", facing = "S" }, 0.13, "mage")
assertContains(laterWalk, "mage_planar/walk_f05.png", "walk proof samples real later pose")

local ids = player_visual.profileIds()
assertEq(#ids, 3, "three tiny-character playtest profiles")
assertEq(ids[1], "knight", "knight is default comparison profile")

local badSession = pcall(function() player_actor.root({ playerX = 1, playerY = 2, playerDir = "SE" }) end)
assertEq(badSession, false, "non-cardinal player facing fails loud")

print("  playable overhead player-actor tests passed")
