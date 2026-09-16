-- #930: Scene ctx.v uses the same authored value-kind authority as other
-- authored-state owners.  These two small fixtures are the historical
-- failure shape from B007 and D003: a local helper is accidentally published
-- into Scene state instead of remaining invocation-local.
local scene_host = require("engine.scene_host")

local loader = {
    engine = { scripting = {} },
    scenes = {},
}
local session = { loader = loader }
local ctx = { session = session, loader = loader }

local function rejectsStoredFunction(id, key)
    loader.scenes = {{
        id = id,
        kind = "menu",
        hooks = { on_enter = {{
            cmd = "SCRIPT",
            code = "local function helper() end; ctx.v." .. key .. " = helper",
        }}},
    }}
    local ok, err = pcall(scene_host.init, id, ctx)
    scene_host.init(nil)
    return not ok and tostring(err):find("unsupported Lua type 'function'", 1, true) ~= nil
end

assert(rejectsStoredFunction("historical_b007_tactics", "drawBoard"),
    "B007 drawBoard function must fail at the Scene state handoff")
assert(rejectsStoredFunction("historical_d003_breakout_rpg", "updateDraw"),
    "D003 updateDraw function must fail at the Scene state handoff")

loader.scenes = {{
    id = "local_helper_control",
    kind = "menu",
    hooks = { on_enter = {{
        cmd = "SCRIPT",
        code = "local function helper() end; helper(); ctx.v.ok = true",
    }}},
}}
local ok, err = pcall(scene_host.init, "local_helper_control", ctx)
assert(ok, err)
assert(scene_host.getCurrentState().v.ok == true,
    "invocation-local helper remains legal authored SCRIPT")
scene_host.init(nil)

print("=== Scene State Boundary Tests: 3 passed, 0 failed ===")
