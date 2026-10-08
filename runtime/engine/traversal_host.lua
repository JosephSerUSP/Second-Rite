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

local function clearHostedState(session)
    -- Today the registry has one provider. Keeping this cleanup in the registry
    -- rather than exploration means leaving a hosted topology cannot leak its
    -- actor state into the next grid/bounded-lane Map, and future providers can
    -- extend the registry without teaching Map loading their state fields.
    if session then session.continuousTraversal = nil end
end

function traversal_host.ensure(session)
    local provider = resolved(session)
    if not provider then
        clearHostedState(session)
        return nil
    end
    if provider.ensure then provider.ensure(session) end
    return provider
end

-- Called by the Map lifecycle after a destination Map has become current.
-- `arrival` is the existing LOAD_MAP arrival string; providers may interpret
-- it using their own authored environment topology. Returning nil means this
-- registry does not own the Map, so legacy grid/bounded-lane setup continues.
function traversal_host.enterMap(session, arrival)
    local provider = resolved(session)
    if not provider then
        clearHostedState(session)
        return nil
    end
    if provider.enterMap then return provider.enterMap(session, arrival) end
    if provider.ensure then return provider.ensure(session) end
    return true
end

function traversal_host.isActive(session)
    local provider = traversal_host.ensure(session)
    if not provider then return false end
    if provider.isActive then return provider.isActive(session) == true end
    return true
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

function traversal_host.nearestEvent(session, radius, predicate)
    local provider = traversal_host.ensure(session)
    if not provider or not provider.nearestEvent then return nil end
    return provider.nearestEvent(session, radius, predicate)
end

-- Ask the active traversal capability for the ordinary Map Event a confirm
-- press should address. The second return value distinguishes "no provider"
-- from "provider owns interaction but nothing is in range", so the host never
-- falls through into hidden grid interaction on a continuous Map.
function traversal_host.interactionEvent(session, predicate)
    local provider = traversal_host.ensure(session)
    if not provider then return nil, false end
    if not provider.nearestEvent then return nil, true end
    return provider.nearestEvent(session, nil, predicate), true
end

-- Provider-owned raw presentation facts. This engine host does not add camera,
-- sprite, transition, or bounded-lane policy; presentation code may decorate
-- the returned environment/actor record without teaching the provider about a
-- renderer. Legacy bounded_lane remains outside this registry for now.
function traversal_host.presentationView(session)
    local provider = traversal_host.ensure(session)
    if not provider or not provider.presentationView then return nil end
    return provider.presentationView(session)
end

function traversal_host.serialize(session)
    local provider = traversal_host.ensure(session)
    if not provider or not provider.serialize then return nil end
    return provider.serialize(session)
end

function traversal_host.restore(session, saved)
    local provider = resolved(session)
    if not provider or not provider.restore then
        clearHostedState(session)
        return nil
    end
    return provider.restore(session, saved)
end

return traversal_host
