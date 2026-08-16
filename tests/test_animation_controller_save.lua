local loader = require("data.loader")
local session = require("engine.session")
local savegame = require("engine.savegame")

local function assertEq(actual, expected, message)
    if actual ~= expected then
        error((message or "values differ") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual), 0)
    end
end

local s = session.GameSession.new(loader)
s.eventAnimationControllerRuntime = {
    mapKey = "1",
    events = {
        ["7"] = {
            controllerId = "townsperson",
            instance = {
                state = "interact",
                elapsed = 0.25,
                signals = { wave = true },
                animationFinished = true,
            },
        },
    },
}

local serialized = savegame.serialize(s, loader, "town")
assertEq(serialized.eventAnimationControllerRuntime, nil,
    "ephemeral Event animation-controller state is not serialized")

local restored = savegame.deserialize(serialized, loader)
assertEq(restored.eventAnimationControllerRuntime, nil,
    "load does not resurrect presentation-controller runtime")

print("  animation controller save-boundary tests passed")