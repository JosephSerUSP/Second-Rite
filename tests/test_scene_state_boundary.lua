-- #930 / #1160: the per-hook authored-value handoff check is DEFERRED, not
-- enforced. Whole-v state_value validation rejects load-bearing live refs on
-- main (battle's Battle object graph, reserve's popupMemberRef view), so the
-- handoff crashed live play and the G5 harness. It returns once #410 migrates
-- live refs out of v. What stays enforced is the transition-vars copy
-- boundary: seeded SCENE_EVENT vars cross state_value before on_enter.
local scene_host = require("engine.scene_host")

local loader = {
    engine = { scripting = {} },
    scenes = {},
}
local session = { loader = loader }
local ctx = { session = session, loader = loader }

-- Transition-vars boundary still rejects metatables through state_value.
loader.scenes = {{
    id = "vars_boundary_control",
    kind = "menu",
    hooks = { on_enter = {{ cmd = "SET_VAR", name = "ok", value = "true" }} },
}}
local ok, err = pcall(scene_host.push, "vars_boundary_control", ctx,
    { bad = setmetatable({}, { __index = function() end }) })
-- A metatable-bearing seed must fail at the transition copy boundary.
assert(not ok, "transition vars with a metatable must fail at the copy boundary")
scene_host.init(nil)

-- Invocation-local helpers remain legal authored SCRIPT.
loader.scenes = {{
    id = "local_helper_control",
    kind = "menu",
    hooks = { on_enter = {{
        cmd = "SCRIPT",
        code = "local function helper() end; helper(); ctx.v.ok = true",
    }}},
}}
local ok2, err2 = pcall(scene_host.init, "local_helper_control", ctx)
assert(ok2, err2)
assert(scene_host.getCurrentState().v.ok == true,
    "invocation-local helper remains legal authored SCRIPT")
scene_host.init(nil)

print("=== Scene State Boundary Tests: 2 passed, 0 failed ===")
