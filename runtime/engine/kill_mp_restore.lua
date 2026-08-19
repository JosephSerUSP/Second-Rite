-- Provisional production adapter for KILL_MP_RESTORE (#308D).
--
-- This is intentionally one named participant, not a general trait registry:
-- the value still comes from the mature aggregate query and source precedence
-- remains outside this migration.
local traits = require("engine.traits")

local reaction = {}

function reaction.forKiller(killer, session)
    if not killer or not session then return nil end

    return {
        id = "production_kill_mp_restore",
        react = function(fact, api)
            if type(fact) ~= "table" or fact.type ~= "kill" or not fact.killer then
                error("KILL_MP_RESTORE requires a resolved kill fact", 0)
            end

            -- Keep the mature aggregation semantics. Resolve it at the typed
            -- reaction boundary rather than enumerating trait sources here.
            local amount = math.max(0, math.floor(
                traits.getRate(killer, "KILL_MP_RESTORE", session)))
            if amount <= 0 then return end

            -- The semantic capability owns the canonical compatibility event
            -- and text projection; this participant only requests the typed
            -- resource follow-up.
            api.restoreSummonerMp(amount, "kill_mp_restore")
        end,
    }
end

return reaction
