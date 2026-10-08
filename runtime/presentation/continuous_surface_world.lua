-- Presentation adapter for Maps using the continuous_surface traversal provider.
--
-- Gameplay owns `continuousTraversal`; the shared viewport now reads traversal
-- environment/actor facts through the provider-neutral traversal_view seam.
-- No synthetic `townTraversal` record is installed on a proxy session.
local viewport_3d = require("presentation.viewport_3d")
local traversal_host = require("engine.traversal_host")

local continuous_surface_world = {}

function continuous_surface_world.draw(session, worldPresentation)
    local provider = traversal_host.ensure(session)
    if not provider then
        error("continuous_surface world renderer requires an active traversal provider", 0)
    end
    local camera = worldPresentation and worldPresentation.camera or nil
    viewport_3d.draw(session, camera)
end

return continuous_surface_world
