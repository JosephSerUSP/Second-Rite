-- NEGATIVE CONTROL ONLY: wrap the production cache while deliberately hiding
-- mapStructureRevision advances from it. This simulates a broken structural
-- invalidation implementation: in-place mutations keep the same cache identity
-- and stale prepared geometry can be returned.
local good = require("presentation.prepared_map_cache_good")
local broken = {}

function broken.install(viewport, opts)
    local manager = good.install(viewport, opts)
    local realPrepare = viewport.prepareStructure
    local pinnedRevision = setmetatable({}, { __mode = "k" })

    viewport.prepareStructure = function(session)
        if not session or rawget(session, "__preparedMapCacheProxy") then
            return realPrepare(session)
        end
        local actual = session.mapStructureRevision
        local pinned = pinnedRevision[session]
        if pinned == nil then
            pinned = actual or 0
            pinnedRevision[session] = pinned
        end
        session.mapStructureRevision = pinned
        local ok, result = pcall(realPrepare, session)
        session.mapStructureRevision = actual
        if not ok then error(result, 0) end
        return result
    end

    return manager
end

return broken
