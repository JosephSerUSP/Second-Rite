local controller = require("engine.animation_controller")

local function eq(actual, expected, message)
    if actual ~= expected then
        error((message or "values differ") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual), 0)
    end
end

local function truthy(value, message)
    if not value then error(message or "expected truthy value", 0) end
end

local definition = {
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
}

controller.validate(definition, "townsperson")
local instance = controller.new(definition, "townsperson")
local initial = controller.snapshot(instance, definition)
eq(initial.state, "idle", "controller begins at authored initial state")
eq(initial.animation, "idle", "initial state selects semantic animation")
eq(initial.loop, true, "idle loops")

local changed, moving = controller.update(instance, definition, 0.25, {
    event = { moving = true, enabled = true },
})
truthy(changed, "movement fact triggers a transition")
eq(moving.state, "move", "moving Event enters move state")
eq(moving.animation, "walk", "move selects walk animation")
eq(moving.elapsed, 0, "transition resets state-local time")

-- Deterministic dt is state-local and never reads a wall clock.
local _, progressed = controller.update(instance, definition, 0.125, {
    event = { moving = true, enabled = true },
})
eq(progressed.state, "move", "moving remains in move")
eq(progressed.elapsed, 0.125, "explicit dt advances state-local time")

local _, idle = controller.update(instance, definition, 0.1, {
    event = { moving = false, enabled = true },
})
eq(idle.state, "idle", "stopping returns to idle")

-- One generic signal enters a deliberate one-shot. It is consumed by the
-- transition, so a later idle state does not immediately re-enter it.
controller.signal(instance, "interact")
local _, oneShot = controller.update(instance, definition, 0, {
    event = { moving = false, enabled = true },
})
eq(oneShot.state, "interact", "semantic signal enters one-shot")
eq(oneShot.animation, "talk", "one-shot chooses semantic talk animation")
eq(oneShot.loop, false, "interact is a one-shot state")

controller.completeAnimation(instance)
local _, returned = controller.update(instance, definition, 0.016, {
    event = { moving = false, enabled = true },
})
eq(returned.state, "idle", "animation completion returns deterministically")
local _, stillIdle = controller.update(instance, definition, 0.016, {
    event = { moving = false, enabled = true },
})
eq(stillIdle.state, "idle", "consumed signal does not retrigger")

-- Transition priority is authored order and only one transition may fire in a
-- single update, preventing same-frame cycles.
local priority = {
    initial = "a",
    states = {
        a = { animation = "a" },
        b = { animation = "b" },
        c = { animation = "c" },
    },
    transitions = {
        { from = "a", to = "b", when = "event.enabled" },
        { from = "b", to = "c", when = "event.enabled" },
    },
}
local pi = controller.new(priority, "priority")
controller.update(pi, priority, 1, { event = { enabled = true } })
eq(pi.state, "b", "only one transition fires per deterministic update")

local invalidOk = pcall(function()
    controller.validate({
        initial = "idle",
        states = { idle = { animation = "idle" } },
        transitions = { { from = "idle", to = "idle", when = "npc.startedWalking" } },
    }, "bespoke-hook")
end)
truthy(not invalidOk, "content-specific native facts fail loud")

print("  animation controller tests passed")