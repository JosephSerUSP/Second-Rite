-- Public interpreter surface. Command semantics remain in interpreter_core.lua.
-- Its deliberately narrow responsibility is #179's resolved-event publication
-- plus authored-to-presentation boundary normalization that requires the current
-- safe formula context (#394). Presentation never evaluates gameplay formulas.
local core = require("engine.interpreter_core")
local resolved_event = require("engine.resolved_event")
local config = require("engine.config")
local formulaEngine = require("engine.formula")

local interpreter = {}
for k, v in pairs(core) do interpreter[k] = v end

local boundPresentation = {}
local activeFormulaContext = nil
local IMAGE_TRANSFORM_FIELDS = { "x", "y", "opacity", "scale", "rotation" }

local function makeFormulaContext(ctx)
    ctx = ctx or {}
    local fctx = formulaEngine.makeContext({
        a = ctx.a, b = ctx.b, target = ctx.target, enemy = ctx.enemy, ally = ctx.ally,
        party = ctx.party, enemies = ctx.enemies,
        battle = ctx.battle and { round = ctx.battle.round } or nil,
        v = ctx.v,
        ingredient1 = ctx.ingredient1,
        ingredient2 = ctx.ingredient2,
    }, ctx.session)
    for name, battler in pairs(ctx.refs or {}) do
        fctx[name] = formulaEngine.battlerView(battler, ctx.session)
    end
    return fctx
end

local function resolveImagePictureSpec(commandId, spec, ctx)
    local resolved = {}
    for key, value in pairs(spec or {}) do resolved[key] = value end

    local fctx = nil
    for _, field in ipairs(IMAGE_TRANSFORM_FIELDS) do
        local value = spec and spec[field]
        if value ~= nil then
            if type(value) == "number" then
                resolved[field] = value
            elseif type(value) == "string" then
                fctx = fctx or makeFormulaContext(ctx)
                local result, err = formulaEngine.eval(value, fctx)
                if err then
                    error(commandId .. "." .. field .. " formula '" .. value
                        .. "' failed: " .. tostring(err), 0)
                end
                if type(result) ~= "number" then
                    error(commandId .. "." .. field .. " formula '" .. value
                        .. "' must resolve to a number, got " .. type(result), 0)
                end
                resolved[field] = result
            else
                error(commandId .. "." .. field .. " must be a number or formula string, got "
                    .. type(value), 0)
            end
        end
    end
    return resolved
end

-- interpreter_core owns the presentation dependency-inversion seam. Keep one
-- transparent proxy installed so only image-picture transforms gain authored
-- formula resolution. Every other presentation hook is forwarded untouched.
local presentationProxy = setmetatable({}, {
    __index = function(_, name)
        local fn = boundPresentation[name]
        if type(fn) ~= "function" then return nil end
        if name == "showImagePicture" then
            return function(spec)
                return fn(resolveImagePictureSpec("SHOW_IMAGE_PICTURE", spec, activeFormulaContext))
            end
        elseif name == "moveImagePicture" then
            return function(spec)
                return fn(resolveImagePictureSpec("MOVE_IMAGE_PICTURE", spec, activeFormulaContext))
            end
        end
        return fn
    end,
})

function interpreter.bindPresentation(hooks)
    local previous = boundPresentation
    boundPresentation = hooks or {}
    core.bindPresentation(presentationProxy)
    return previous
end

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

    -- Picture formulas must see the same v/session/battler views as the command
    -- executing immediately before them. Scope the active context to this one
    -- synchronous core run, and restore it even when a malformed formula throws.
    local previousFormulaContext = activeFormulaContext
    activeFormulaContext = ctx
    local ok, events = pcall(core.runImmediate, commands, ctx)
    activeFormulaContext = previousFormulaContext
    if not ok then error(events, 0) end

    -- firstNew is calculated after any STATE_TICKS removals/insertions but the
    -- prefix event count itself is stable: all new events are still after it.
    local firstNew = initialEventCount + 1
    commitReaps(events, ctx.session, firstNew)
    publishUnstamped(events, ctx.session, firstNew)
    return events
end

return interpreter
