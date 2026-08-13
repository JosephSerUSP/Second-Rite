-- Player-equivalent logical input membrane (#375).
--
-- External policies speak only the fixed logical controller vocabulary. This
-- module deliberately knows no gameplay operations: it delegates to
-- scene_host.buttonpressed, the same pre-semantic dispatch used after physical
-- keys are translated by engine/input_map.lua.
local input_map = require("engine.input_map")
local scene_host = require("engine.scene_host")

local controller = {}

function controller.isButton(button)
    return input_map.isButton(button)
end

function controller.press(button, ctx)
    if not controller.isButton(button) then
        error("unknown logical player button '" .. tostring(button) .. "'", 2)
    end
    return scene_host.buttonpressed(button, ctx)
end

return controller
