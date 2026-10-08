-- Presentation adapter for Maps using the continuous_surface traversal provider.
--
-- Gameplay owns `continuousTraversal`. Provider-neutral presentation facts live
-- in presentation.traversal_view; the final legacy-viewport translation is
-- isolated there until viewport_3d finishes migrating its remaining historic
-- townTraversal reads. No fake traversal state is installed on GameSession or
-- exposed by the gameplay provider.
local viewport_3d = require("presentation.viewport_3d")
local traversal_host = require("engine.traversal_host")
local traversal_view = require("presentation.traversal_view")

local continuous_surface_world = {}

function continuous_surface_world.draw(session, worldPresentation)
    local provider = traversal_host.ensure(session)
    if not provider then
        error("continuous_surface world renderer requires an active traversal provider", 0)
    end
    local camera = worldPresentation and worldPresentation.camera or nil
    viewport_3d.draw(traversal_view.legacyViewportSession(session), camera)
end

return continuous_surface_world
