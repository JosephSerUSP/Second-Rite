-- Presentation adapter for Maps using the continuous_surface traversal provider.
--
-- The gameplay session remains honest: it owns `continuousTraversal`, not a
-- synthetic town traversal. The existing viewport still has a bounded-lane-
-- shaped environment/player seam, so until that renderer is generalized this
-- adapter supplies an ephemeral compatibility view on a proxy session. Nothing
-- here is serialized or exposed back to gameplay.
local viewport_3d = require("presentation.viewport_3d")
local traversal_host = require("engine.traversal_host")

local continuous_surface_world = {}

local function proxyFor(session, laneView)
    local state = session.continuousTraversal
    local proxy = state and state._presentationProxy
    if not proxy then
        proxy = setmetatable({}, { __index = session })
        if state then state._presentationProxy = proxy end
    end
    proxy.townTraversal = laneView
    return proxy
end

function continuous_surface_world.draw(session, worldPresentation)
    local provider = traversal_host.ensure(session)
    if not provider then
        error("continuous_surface world renderer requires an active traversal provider", 0)
    end
    local laneView = traversal_host.presentationLaneView(session)
    if not laneView then
        error("continuous_surface traversal has no presentation view", 0)
    end
    local proxy = proxyFor(session, laneView)
    local camera = worldPresentation and worldPresentation.camera or nil
    viewport_3d.draw(proxy, camera)
end

return continuous_surface_world
