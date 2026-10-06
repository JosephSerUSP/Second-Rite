-- Small provider registry between logical player input and Map traversal.
--
-- Grid movement remains the legacy/main-host fallback and bounded_lane keeps
-- its existing dedicated host while this investigation is in flight. New
-- traversal families enter through this registry rather than adding genre
-- conditionals to main.lua or player_controller.lua.
local traversal_host = {}

local providers = {
    continuous_surface = require("engine.continuous_surface_provider"),
}

local function resolved(session)
    local map = session and session.currentMapData
    local traversal = map and map.traversal
    local id = type(traversal) == "table" and traversal.provider or nil
    return id and providers[id] or nil
end

function traversal_host.ensure(session)
    local provider = resolved(session)
    if not provider then
        if session then session.continuousTraversal = nil end
        return nil
    end
    if provider.ensure then provider.ensure(session) end
    return provider
end

function traversal_host.update(session, dt, held)
    local provider = traversal_host.ensure(session)
    if not provider or not provider.update then return false end
    return provider.update(session, dt, held) == true
end

function traversal_host.buttonpressed(session, button)
    local provider = traversal_host.ensure(session)
    if not provider or not provider.buttonpressed then return false end
    return provider.buttonpressed(session, button) == true
end

function traversal_host.actorRoot(session)
    local provider = traversal_host.ensure(session)
    if not provider or not provider.actorRoot then return nil end
    return provider.actorRoot(session)
end

function traversal_host.presentationLaneView(session)
    local provider = traversal_host.ensure(session)
    if not provider or not provider.presentationLaneView then return nil end
    return provider.presentationLaneView(session)
end

function traversal_host.serialize(session)
    local provider = traversal_host.ensure(session)
    if not provider or not provider.serialize then return nil end
    return provider.serialize(session)
end

function traversal_host.restore(session, saved)
    local provider = resolved(session)
    if not provider or not provider.restore then return nil end
    return provider.restore(session, saved)
end

return traversal_host
