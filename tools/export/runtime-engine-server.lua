-- Compiled-player implementation of engine.server.
--
-- The source module is a Developer Studio authoring capability: it exposes
-- hot reload plus authored-resource reads/writes over localhost. A packaged or
-- staged player must not ship that authority merely because main.lua shares the
-- same lifecycle calls. Keep the tiny runtime API surface while making every
-- operation inert.
local server = {
    configReloaded = false,
}

function server.start()
    -- Deliberately inert in a compiled player.
end

function server.stop()
    -- Deliberately inert in a compiled player.
end

function server.isActive()
    return false
end

function server.update(_dt)
    -- Deliberately inert in a compiled player.
end

return server
