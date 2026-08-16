local controls = require("engine.player_controls")
local scene_host = require("engine.scene_host")

local controller = {}

function controller.isButton(button)
    return controls.contains(button)
end

function controller.press(button, ctx)
    assert(controller.isButton(button), "unknown logical player button")
    return scene_host.buttonpressed(button, ctx)
end

return controller
