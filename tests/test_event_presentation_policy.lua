local event_actor = require("engine.event_actor")
local policy = require("presentation.event_presentation_policy")

local function assertEq(actual, expected, message)
    if actual ~= expected then
        error((message or "values differ") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual), 0)
    end
end

local function assertTrue(value, message)
    if not value then error(message or "expected truthy value", 0) end
end

local controllers = {
    townsperson = {
        id = "townsperson",
        initial = "idle",
        states = {
            idle = { animation = "controller_idle", loop = true },
            move = { animation = "controller_walk", loop = true },
        },
        transitions = {
            { from = "idle", to = "move", when = "event.moving" },
            { from = "move", to = "idle", when = "not event.moving" },
        },
    },
    statue = {
        id = "statue",
        initial = "still",
        states = { still = { animation = "stone_still", loop = true } },
        transitions = {},
    },
}

local sess = {
    currentMapIndex = 1,
    currentMapData = { id = "presentation_policy" },
    animationControllers = controllers,
    loader = {
        animationControllers = controllers,
        commonEvents = {
            ["10"] = { animationController = "townsperson" },
        },
    },
}

-- Character presentation tracks the actor's semantic locomotion/facing rather
-- than inferring animation from an authored movement type.
local npc = { id = 1, x = 2, y = 3, facing = "south" }
local npcIdle = policy.resolve(sess, npc, npc, { visual = "sprite" })
assertEq(npcIdle.mode, "npc", "ordinary sprite Event defaults to NPC presentation")
assertEq(npcIdle.render_dir, "down", "NPC authored facing projects to renderer direction")
assertEq(npcIdle.moving, false, "idle NPC is not moving")
assertEq(npcIdle.clip, "idle", "NPC receives actor semantic clip")

local moving = event_actor.setMotion(sess, npc, 0, -1)
assertEq(moving.facing, "N", "actor movement proof faces north")
local npcMoving = policy.resolve(sess, npc, npc, { visual = "sprite" })
assertEq(npcMoving.render_dir, "up", "NPC render facing follows actor state")
assertEq(npcMoving.moving, true, "NPC locomotion projects to presentation")
assertEq(npcMoving.clip, "walk", "NPC walk clip projects semantically")

-- Object presentation is intentionally insulated from actor locomotion. A
-- gameplay system moving an object root must not silently opt it into NPC walk
-- cycles or movement-derived facing.
local chest = { id = 2, x = 4, y = 5, facing = "west" }
event_actor.setMotion(sess, chest, 1, 0)
local chestState = policy.resolve(sess, chest, chest, {
    visual = "model",
    interactionFocus = { kind = "low_prop" },
})
assertEq(chestState.mode, "object", "interaction-focused prop resolves as object")
assertEq(chestState.render_dir, "left", "object keeps authored facing")
assertEq(chestState.moving, false, "object ignores actor locomotion by default")
assertEq(chestState.clip, nil, "object does not inherit NPC walk/idle clip")

local door = { id = 3, x = 6, y = 7, wallEvent = true, direction = "east" }
event_actor.setMotion(sess, door, 0, -1)
local doorState = policy.resolve(sess, door, door, { visual = "sprite" })
assertEq(doorState.mode, "door", "wall Event resolves to door policy")
assertEq(doorState.render_dir, "right", "door transform keeps authored direction")
assertEq(doorState.moving, false, "door never inherits walk-cycle locomotion")

-- Special archetypes can override presentation policy without mutating the
-- underlying actor. This is a presentation extension seam, not a new movement
-- hook or Event actor state axis.
local puppetState = policy.resolve(sess, chest, chest, { visual = "model" }, {
    mode = "puppet",
    tracksFacing = true,
    tracksLocomotion = true,
})
assertEq(puppetState.mode, "puppet", "custom mode is presentation-only")
assertEq(puppetState.render_dir, "right", "custom policy may track actor facing")
assertEq(puppetState.moving, true, "custom policy may opt into actor locomotion")
assertEq(puppetState.clip, "walk", "custom locomotion tracking exposes semantic clip")

local explicitState = policy.resolve(sess, npc, npc, { visual = "sprite" }, {
    render_dir = "left",
    moving = false,
    clip = "gesture",
})
assertEq(explicitState.render_dir, "left", "explicit render direction overrides projection")
assertEq(explicitState.moving, false, "explicit moving override wins")
assertEq(explicitState.clip, "gesture", "explicit presentation clip wins")

local badDirOk = pcall(function()
    policy.resolve(sess, npc, npc, { visual = "sprite" }, { render_dir = "diagonal" })
end)
assertTrue(not badDirOk, "invalid presentation direction fails loud")

-- Installation decorates the viewport's one canonical asset/page resolver; it
-- does not create a second asset-selection path. Installation is idempotent.
local fakeViewport = {
    resolveEventPresentation = function(ev)
        return { visual = "sprite", sprite = "dummy.png", page = ev }
    end,
}
policy.install(fakeViewport)
local installedResolver = fakeViewport.resolveEventPresentation
policy.install(fakeViewport)
assertEq(fakeViewport.resolveEventPresentation, installedResolver, "policy install is idempotent")
local decorated = fakeViewport.resolveEventPresentation(npc, sess)
assertEq(decorated.sprite, "dummy.png", "asset presentation survives policy decoration")
assertTrue(type(decorated.renderState) == "table", "viewport presentation receives renderState")
assertEq(decorated.renderState.mode, "npc", "decorated viewport state carries mode")
assertEq(decorated.renderState.render_dir, "up", "decorated viewport state carries actor-facing projection")
assertEq(decorated.renderState.moving, true, "decorated viewport state carries locomotion projection")
assertEq(decorated.animationController, nil, "Event without a controller stays on the legacy semantic clip")
assertEq(decorated.renderState.clip, "walk", "no controller preserves Event actor walk clip")

-- Common Event fallback, Page/Event override, and explicit suppression all use
-- the existing presentation precedence rather than a controller-only resolver.
local inherited = { id = 20, x = 1, y = 1, scriptId = 10 }
local inheritedPres = fakeViewport.resolveEventPresentation(inherited, sess)
assertEq(inheritedPres.animationController, "townsperson", "Common Event supplies controller when Event is absent")
assertEq(inheritedPres.controllerState.state, "idle", "inherited controller creates an Event-local instance")
assertEq(inheritedPres.renderState.clip, "controller_idle", "controller-selected semantic animation reaches render state")

local overridden = { id = 21, x = 1, y = 1, scriptId = 10, animationController = "statue" }
local overridePres = fakeViewport.resolveEventPresentation(overridden, sess)
assertEq(overridePres.animationController, "statue", "Event/Page value overrides Common Event controller")
assertEq(overridePres.renderState.clip, "stone_still", "override controller selects its own semantic animation")

local suppressed = { id = 22, x = 1, y = 1, scriptId = 10, animationController = false }
local suppressPres = fakeViewport.resolveEventPresentation(suppressed, sess)
assertEq(suppressPres.animationController, false, "explicit false suppresses Common Event controller")
assertEq(suppressPres.controllerState, nil, "suppressed controller allocates no controller state")
assertEq(suppressPres.renderState.clip, "idle", "suppression falls back to ordinary actor semantic clip")

print("  event presentation policy tests passed")