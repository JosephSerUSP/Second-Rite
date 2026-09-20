-- #919: SCENE_EVENT has a closed transition vocabulary and required targets.
local project_validator = require("engine.project_validator_rules")

local function loaderFor(command)
    local value = {
        system = { rtp = { revision = "test" } },
        engine = { commands = {{ id = "SCENE_EVENT" }} },
        scenes = {
            { id = "map", kind = "map", draw = "windows", hooks = {} },
            { id = "title", kind = "title", draw = "windows", hooks = {
                on_enter = { command },
            } },
            { id = "dialogue", kind = "dialogue", draw = "windows", hooks = {} },
        },
        flows = { exploration = { step = {{ cmd = "SCENE_EVENT", kind = "map" }} } }, maps = {},
    }
    value.getScene = function(id)
        for _, scene in ipairs(value.scenes) do
            if scene.id == id then return scene end
        end
        return nil
    end
    return value
end

local ok, err = pcall(project_validator.run, loaderFor({
    cmd = "SCENE_EVENT", kind = "custom",
}))
assert(not ok and tostring(err):match("SCENE_EVENT has unknown kind 'custom'"),
    "unknown SCENE_EVENT kinds must fail validation as a negative control")

local ok2, err2 = pcall(project_validator.run, loaderFor({
    cmd = "SCENE_EVENT", kind = "push",
}))
assert(not ok2 and tostring(err2):match("kind 'push' requires a scene"),
    "push transitions without a scene must fail validation")

local ok3, err3 = pcall(project_validator.run, loaderFor({
    cmd = "SCENE_EVENT", kind = "push", scene = "map",
}))
assert(ok3, err3)

print("=== SCENE_EVENT Validation Tests: 3 passed, 0 failed ===")
