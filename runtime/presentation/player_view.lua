local projection = require("presentation.player_projection")

local player_view = {}
player_view.VERSION = 1

function player_view.capture(sceneData, state, ctx)
    local visible = projection.resolve(sceneData, state, ctx)
    return {
        version = player_view.VERSION,
        scene = (sceneData and (sceneData.id or sceneData.name)) or (state and state.id) or nil,
        windows = visible.windows,
    }
end

return player_view
