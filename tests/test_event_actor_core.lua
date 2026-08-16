-- Characterization of the camera-neutral Map Event actor state machine.
local event_actor = require("engine.event_actor")

local function assertEq(actual, expected, message)
    if actual ~= expected then
        error((message or "values differ") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual), 0)
    end
end

local function assertTrue(value, message)
    if not value then error(message or "expected truthy value", 0) end
end

print("[TEST] Starting Event actor animation-state tests...")

local sess = { currentMapIndex = 1, currentMapData = { id = "first" } }
local ev = { id = 7, x = 4, y = 5, facing = "north" }

-- A query starts from authored spatial/facing facts without allocating runtime
-- state. This matters for render/inspection consumers that merely observe.
local initial = event_actor.snapshot(sess, ev)
assertEq(initial.rootX, 4, "authored root X")
assertEq(initial.rootY, 5, "authored root Y")
assertEq(initial.facing, "N", "authored facing alias normalized")
assertEq(initial.locomotion, "idle", "default locomotion")
assertEq(initial.clip, "idle", "default semantic clip")
assertEq(sess.eventActorRuntime, nil, "snapshot does not allocate transient state")
assertEq(event_actor.normalizeFacing("left"), "W", "left alias")
assertEq(event_actor.normalizeFacing("DOWN"), "S", "uppercase alias")

-- Motion selects semantic locomotion/facing, never asset-specific clip ids.
local moving = event_actor.setMotion(sess, ev, 1, 0)
assertEq(moving.locomotion, "moving", "cardinal motion enters moving state")
assertEq(moving.facing, "E", "east motion faces east")
assertEq(moving.clip, "walk", "moving resolves walk semantic clip")

local stopped = event_actor.setMotion(sess, ev, 0, 0)
assertEq(stopped.locomotion, "idle", "zero motion enters idle")
assertEq(stopped.facing, "E", "stopping preserves last facing")
assertEq(stopped.clip, "idle", "stopping resolves idle clip")

local west = event_actor.setMotion(sess, ev, -1, 0)
assertEq(west.facing, "W", "west motion faces west")
local beforeBadMotion = event_actor.snapshot(sess, ev)
local diagonalOk = pcall(function() event_actor.setMotion(sess, ev, 1, 1) end)
assertTrue(not diagonalOk, "diagonal motion fails loud")
local afterBadMotion = event_actor.snapshot(sess, ev)
assertEq(afterBadMotion.facing, beforeBadMotion.facing,
    "failed diagonal motion does not mutate facing")
assertEq(afterBadMotion.locomotion, beforeBadMotion.locomotion,
    "failed diagonal motion does not mutate locomotion")

-- Stable root is independent from animation state. A camera may follow this
-- root without inheriting sprite bob, pivots or future gesture offsets.
local rooted = event_actor.setRoot(sess, ev, 12.25, 13.5)
assertEq(rooted.rootX, 12.25, "runtime root X")
assertEq(rooted.rootY, 13.5, "runtime root Y")
assertEq(rooted.facing, "W", "root movement does not alter facing")
assertEq(rooted.locomotion, "moving", "root movement does not alter locomotion")

-- Timed one-shot masks locomotion but does not erase it. When it finishes the
-- resolver naturally falls back to the still-current moving/facing state.
event_actor.setMotion(sess, ev, 1, 0)
local gesture = event_actor.playOneShot(sess, ev, "gesture", 0.25)
assertEq(gesture.clip, "gesture", "one-shot overrides base clip")
assertEq(gesture.overrideKind, "one_shot", "one-shot kind exposed")
assertEq(gesture.locomotion, "moving", "one-shot preserves locomotion state")
event_actor.update(sess, 0.10)
assertEq(event_actor.snapshot(sess, ev).clip, "gesture", "timed one-shot remains active")
event_actor.update(sess, 0.15)
local resumed = event_actor.snapshot(sess, ev)
assertEq(resumed.clip, "walk", "timed one-shot falls back to locomotion clip")
assertEq(resumed.facing, "E", "timed one-shot preserves facing")

-- Asset-driven one-shots own no guessed FPS/duration. They end explicitly.
event_actor.playOneShot(sess, ev, "surprised")
event_actor.update(sess, 99)
assertEq(event_actor.snapshot(sess, ev).clip, "surprised",
    "completion-driven one-shot survives arbitrary dt")
local completed, afterComplete = event_actor.completeOverride(sess, ev)
assertTrue(completed, "completion reports an active override was cleared")
assertEq(afterComplete.clip, "walk", "explicit completion resumes base clip")

-- A held pose has the same priority but intentionally persists until cleared.
event_actor.holdPose(sess, ev, "kneel")
event_actor.update(sess, 99)
local held = event_actor.snapshot(sess, ev)
assertEq(held.clip, "kneel", "held pose persists")
assertEq(held.overrideKind, "pose", "held pose kind exposed")
event_actor.clearOverride(sess, ev)
assertEq(event_actor.snapshot(sess, ev).clip, "walk", "clearing pose resumes base clip")

-- Runtime identity is scoped by Map + Event id. Same event id on another map
-- starts from that map's authored facts instead of leaking state across maps.
sess.currentMapIndex = 2
local evOnSecondMap = { id = 7, x = 20, y = 30, direction = "south" }
local secondDefault = event_actor.snapshot(sess, evOnSecondMap)
assertEq(secondDefault.rootX, 20, "same event id on another map gets authored root")
assertEq(secondDefault.facing, "S", "same event id on another map gets authored facing")
event_actor.setRoot(sess, evOnSecondMap, 21, 31)
event_actor.setFacing(sess, evOnSecondMap, "left")

sess.currentMapIndex = 1
local firstAgain = event_actor.snapshot(sess, ev)
assertEq(firstAgain.rootX, 12.25, "first map runtime root survives map switch")
assertEq(firstAgain.facing, "E", "first map facing survives map switch")

assertTrue(event_actor.resetMap(sess, 1), "resetMap reports existing first-map runtime")
local firstReset = event_actor.snapshot(sess, ev)
assertEq(firstReset.rootX, 4, "resetMap restores authored root on next query")
assertEq(firstReset.facing, "N", "resetMap restores authored facing on next query")

sess.currentMapIndex = 2
assertEq(event_actor.snapshot(sess, evOnSecondMap).rootX, 21,
    "resetMap leaves other map runtime intact")
event_actor.reset(sess)
assertEq(sess.eventActorRuntime, nil, "reset drops all transient actor state")
assertEq(event_actor.snapshot(sess, evOnSecondMap).rootX, 20,
    "full reset falls back to authored root")

-- Mutations require stable Event identity and invalid semantic states fail loud.
local noIdOk = pcall(function()
    event_actor.setFacing(sess, { x = 1, y = 1 }, "N")
end)
assertTrue(not noIdOk, "mutable actor without event id fails loud")
local badFacingOk = pcall(function() event_actor.setFacing(sess, evOnSecondMap, "diagonal") end)
assertTrue(not badFacingOk, "invalid facing fails loud")
local badLocomotionOk = pcall(function()
    event_actor.setLocomotion(sess, evOnSecondMap, "flying")
end)
assertTrue(not badLocomotionOk, "invalid locomotion fails loud")
local badDurationOk = pcall(function()
    event_actor.playOneShot(sess, evOnSecondMap, "gesture", 0)
end)
assertTrue(not badDurationOk, "non-positive one-shot duration fails loud")

print("  event actor animation-state tests passed")
