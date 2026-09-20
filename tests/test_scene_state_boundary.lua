-- #410: Scene State receives deterministic transition seeds while each hook
-- gets fresh Process Locals.
local scene_host = require("engine.scene_host")

local loader = {
    engine = { scripting = {} },
    scenes = {},
}
local session = { loader = loader }
local ctx = { session = session, loader = loader }

-- Transition-state boundary rejects metatables through state_value.
loader.scenes = {{
    id = "vars_boundary_control",
    kind = "menu",
    hooks = { on_enter = {{ cmd = "SET_SCENE_STATE", name = "ok", value = "true" }} },
}}
local ok, err = pcall(scene_host.push, "vars_boundary_control", ctx,
    { bad = setmetatable({}, { __index = function() end }) })
-- A metatable-bearing seed must fail at the transition copy boundary.
assert(not ok, "transition Scene State with a metatable must fail at the copy boundary")
scene_host.init(nil)

-- Scene scripts explicitly receive Scene State.
loader.scenes = {{
    id = "local_helper_control",
    kind = "menu",
    hooks = { on_enter = {{
        cmd = "SCRIPT",
        code = "local function helper() end; helper(); locals.marker = 7; ctx.sceneState.ok = locals.marker == 7",
    }}},
}}
local ok2, err2 = pcall(scene_host.init, "local_helper_control", ctx)
assert(ok2, err2)
assert(scene_host.getCurrentState().v.ok == true,
    "Scene scripts receive explicit Scene State and Process Locals")
scene_host.init(nil)

-- A SCRIPT-emitted transition uses the same explicit payload noun as
-- SCENE_EVENT, so authored scene helpers cannot revive the removed `vars`
-- handoff by bypassing the registry command.
loader.scenes = {
    {
        id = "script_transition_source",
        kind = "menu",
        hooks = { on_enter = {{
            cmd = "SCRIPT",
            code = "api.emit({ type = 'scene_change', kind = 'push', scene = 'script_transition_target', sceneState = { idx = 3 } })",
        }}},
    },
    {
        id = "script_transition_target",
        kind = "menu",
    },
}
local ok3, err3 = pcall(scene_host.init, "script_transition_source", ctx)
assert(ok3, err3)
assert(scene_host.getCurrent() == "script_transition_target"
    and scene_host.getCurrentState().v.idx == 3,
    "SCRIPT scene_change passes explicit Scene State to the pushed scene")
scene_host.init(nil)

print("=== Scene State Boundary Tests: 3 passed, 0 failed ===")
