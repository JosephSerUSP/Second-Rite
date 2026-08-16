-- World-space scene drawing: the counterpart to window_renderer for scenes
-- declaring "draw": "world" in scenes.json. A world scene renders a 3D/world
-- view first, then its (usually dynamic) windows are layered on top by
-- window_renderer, exactly like any "draw": "windows" scene.
--
-- Replaces the old "absence of a draw flag falls back to legacy Lua drawing"
-- rule (purged 24.07.2026): every scene now names how it draws, and an
-- unknown world id is a hard error rather than a silent blank screen.
local world_renderer = {}

-- Keep recently materialized map structures resident across world-scene travel.
-- The adapters wrap viewport_3d's existing seams; renderer.lua already holds
-- this same module table, so installing here affects every map draw without
-- adding cache or Event presentation policy to the renderer itself.
local viewport_3d = require("presentation.viewport_3d")
require("presentation.prepared_map_cache").install(viewport_3d)
require("presentation.event_presentation_policy").install(viewport_3d)

-- world id (scenes.json `world`) -> draw function. Kept as a registry so
-- scene_host stays free of per-scene special cases.
local drawers = {
    map = function(ctx, worldPresentation)
        -- Scene-owned world presentation supplies the durable default camera;
        -- gameplay Map topology remains untouched.
        require("presentation.vertex_shading_resolver").withComposite(ctx.session, function()
            require("presentation.renderer").drawMap(worldPresentation)
        end)
    end,
}

function world_renderer.ids()
    local ids = {}
    for id in pairs(drawers) do table.insert(ids, id) end
    table.sort(ids)
    return ids
end

function world_renderer.draw(worldId, ctx, worldPresentation)
    local fn = drawers[worldId]
    if not fn then
        error("scene declares unknown world '" .. tostring(worldId) .. "'", 0)
    end
    fn(ctx, worldPresentation)
end

return world_renderer