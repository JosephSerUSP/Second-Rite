local controls = require("engine.player_controls")
local scene_host = require("engine.scene_host")

local player_input = {}

function player_input.isButton(button)
    return controls.contains(button)
end

function player_input.press(button, ctx)
    assert(player_input.isButton(button), "unknown logical player button")
    return scene_host.buttonpressed(button, ctx)
end

return player_input
