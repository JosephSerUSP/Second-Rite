local event_actor = require("engine.event_actor")
local runtime = require("presentation.event_animation_controller")

local function eq(actual, expected, message)
    if actual ~= expected then
        error((message or "values differ") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual), 0)
    end
end

local function truthy(value, message)
    if not value then error(message or "expected truthy value", 0) end
end

local definitions = {
    townsperson = {
        id = "townsperson",
        initial = "idle",
        states = {
            idle = { animation = "idle", loop = true },
            move = { animation = "walk", loop = true },
            interact = { animation = "talk", loop = false },
        },
        transitions = {
            { from = "idle", to = "move", when = "event.moving" },
            { from = "move", to = "idle", when = "not event.moving" },
            { from = "*", to = "interact", when = "signal.interact" },
            { from = "interact", to = "idle", when = "animation.finished" },
        },
    },
    statue = {
        id = "statue",
        initial = "still",
        states = { still = { animation = "still", loop = true } },
        transitions = {},
    },
}

local session = {
    currentMapIndex = 1,
    currentMapData = { id = 1 },
    animationControllers = definitions,
}
local ev = { id = 7, x = 2, y = 3, facing = "south" }

local initial = runtime.resolve(session, ev, "townsperson")
eq(initial.state, "idle", "per-Event controller starts idle")

event_actor.setMotion(session, ev, 1, 0)
runtime.update(session, 0.1)
local moving = runtime.snapshot(session, ev, "townsperson")
eq(moving.state, "move", "controller observes Event actor locomotion")
eq(moving.animation, "walk", "runtime exposes semantic walk state")

-- A Page change that resolves to the same controller id preserves ephemeral
-- presentation state rather than twitch-resetting every page overlay.
local sameControllerPage = { id = 7, x = 2, y = 3, facing = "west", pageMarker = "other" }
local preserved = runtime.resolve(session, sameControllerPage, "townsperson")
eq(preserved.state, "move", "same resolved controller survives Page change")

-- Changing controller identity is a presentation identity change and resets.
local replaced = runtime.resolve(session, sameControllerPage, "statue")
eq(replaced.state, "still", "controller id change resets instance")

-- Switch it back, prove a semantic one-shot, and completion-driven return.
local restarted = runtime.resolve(session, ev, "townsperson")
eq(restarted.state, "idle", "switching back creates a fresh instance")
truthy(runtime.signal(session, ev, "townsperson", "interact"), "generic signal is accepted")
runtime.update(session, 0)
eq(runtime.snapshot(session, ev, "townsperson").state, "interact", "signal drives one-shot")
truthy(runtime.completeAnimation(session, ev, "townsperson"), "backend completion is accepted")
runtime.update(session, 0.016)
eq(runtime.snapshot(session, ev, "townsperson").state, "idle", "completion returns to idle")

-- Leaving a Map discards the only retained bucket. Returning to the old id
-- therefore cannot strand a stale one-shot on another runtime Event instance.
runtime.signal(session, ev, "townsperson", "interact")
runtime.update(session, 0)
eq(runtime.snapshot(session, ev, "townsperson").state, "interact", "fixture enters one-shot before transfer")
session.currentMapIndex = 2
session.currentMapData = { id = 2 }
local ev2 = { id = 7, x = 8, y = 8 }
eq(runtime.resolve(session, ev2, "townsperson").state, "idle", "new Map/Event identity starts clean")
session.currentMapIndex = 1
session.currentMapData = { id = 1 }
eq(runtime.resolve(session, ev, "townsperson").state, "idle", "revisited Map does not resurrect stale state")

-- Presentation controller runtime is the same kind of transient session cache
-- as eventActorRuntime: it is explicitly resettable and owns no gameplay data.
runtime.reset(session)
eq(session.eventAnimationControllerRuntime, nil, "reset removes transient controller runtime")

print("  Event animation controller runtime tests passed")