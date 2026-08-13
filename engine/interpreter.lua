-- Public interpreter surface. Command semantics remain in interpreter_core.lua.
-- Its deliberately narrow responsibility is #179's resolved-event publication:
-- events leaving the immediate interpreter are
-- stamped with already-resolved facts, and REAP_FALLEN's engine decision is
-- committed before control returns to presentation. No presentation callback
-- owns GameSession membership anymore.
local core = require("engine.interpreter_core")
local resolved_event = require("engine.resolved_event")
local config = require("engine.config")

local interpreter = {}
for k, v in pairs(core) do interpreter[k] = v end

local function copyRoster(src, maxSlots)
    local out = {}
    for i = 1, maxSlots do out[i] = src and src[i] or nil end
    return out
end

-- REAP_FALLEN already decides who dies, how much EXP is banked and which party
-- slot that creature occupied. Historically it deliberately stopped one write
-- short and let processEvent("reap") clear that slot later. That made a visual
-- callback part of domain correctness. Commit the already-decided removals here,
-- after the whole immediate flow has run but before it returns to the scene.
--
-- We build per-event roster snapshots beside the real writes so presentation
-- can still fade one outgoing card at a time. If the final removal empties the
-- field, autoFieldIfEmpty runs here too; only the final reap snapshot exposes
-- those replacements, matching the old last-card completion beat.
local function commitReaps(events, session, firstNew)
    if not session then return end
    local stagedParty = copyRoster(session.party, config.MAX_PARTY_SIZE)
    local stagedReserve = copyRoster(session.reserve, config.MAX_RESERVE_SIZE)
    local fieldReaps = {}

    for i = firstNew, #events do
        local ev = events[i]
        if ev and ev.type == "reap" and ev.slot then
            table.insert(fieldReaps, ev)
            stagedParty[ev.slot] = nil
            session.party[ev.slot] = nil

            ev.resolved = ev.resolved or {}
            ev.resolved.party = copyRoster(stagedParty, config.MAX_PARTY_SIZE)
            ev.resolved.reserve = copyRoster(stagedReserve, config.MAX_RESERVE_SIZE)
        end
    end

    if #fieldReaps > 0 then
        session:autoFieldIfEmpty()
        -- The final visible reap beat reveals any automatic reserve deployment
        -- produced by the authoritative post-reap roster rule.
        resolved_event.attachRoster(fieldReaps[#fieldReaps], session)
    end
end

local function publishUnstamped(events, session, firstNew)
    for i = firstNew, #events do
        local ev = events[i]
        -- effects.apply and battle.lua may already have stamped the event at a
        -- more precise semantic write site. Never replace those exact snapshots
        -- with the later end-of-phase state; this is only a safety net for the
        -- remaining direct interpreter handlers until #178 folds the facade in.
        if ev and ev.resolved == nil then
            resolved_event.attach(ev, session)
        end
    end
end

function interpreter.runImmediate(commands, ctx)
    ctx = ctx or {}
    local initialEventCount = #(ctx.events or {})
    local events = core.runImmediate(commands, ctx)

    -- firstNew is calculated after any STATE_TICKS removals/insertions but the
    -- prefix event count itself is stable: all new events are still after it.
    local firstNew = initialEventCount + 1
    commitReaps(events, ctx.session, firstNew)
    publishUnstamped(events, ctx.session, firstNew)
    return events
end

return interpreter
