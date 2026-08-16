local interpreter = require("engine.interpreter")

local function eq(actual, expected, message)
    if actual ~= expected then
        error((message or "values differ") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual), 0)
    end
end

local calls = {}
interpreter.bindPresentation({
    signalEventAnimation = function(eventId, signal)
        table.insert(calls, { eventId = eventId, signal = signal })
        return true
    end,
})

local ctx = {
    session = {},
    loader = {},
    v = {},
    events = {},
    event = { id = 12 },
    eventId = 12,
}

-- Omitted target means the Event Program's current Map Event. The interpreter
-- forwards one generic semantic request; it never learns what "wave" means.
interpreter.runImmediate({
    { cmd = "ANIMATION_SIGNAL", signal = "wave" },
}, ctx)
eq(#calls, 1, "current-Event signal reaches presentation once")
eq(calls[1].eventId, 12, "current Event id is forwarded")
eq(calls[1].signal, "wave", "semantic signal is forwarded unchanged")

-- Choreography may deliberately target another Event without adding another
-- command shape or another content-specific native hook.
interpreter.runImmediate({
    { cmd = "ANIMATION_SIGNAL", signal = "pray", eventId = 44 },
}, ctx)
eq(#calls, 2, "explicit Event signal reaches presentation")
eq(calls[2].eventId, 44, "explicit Event id wins")
eq(calls[2].signal, "pray", "second semantic signal is generic")

-- Presentation is optional in headless/validation consumers just like the
-- existing presentation seam: signaling must degrade to a harmless no-op.
interpreter.bindPresentation(nil)
local ok, err = pcall(function()
    interpreter.runImmediate({
        { cmd = "ANIMATION_SIGNAL", signal = "wave" },
    }, ctx)
end)
if not ok then error("headless ANIMATION_SIGNAL should be a no-op: " .. tostring(err), 0) end

print("  animation signal command tests passed")