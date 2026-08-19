-- Source-local Unit reactions over resolved semantic events (#554).
--
-- The domain host publishes the fact; this module only selects the Unit's
-- authored programs in their stored array order and executes them through the
-- ordinary interpreter.  It deliberately defines no callback taxonomy.
local formula = require("engine.formula")
local interpreter = require("engine.interpreter")

local reactions = {}

local function triggerRegistry(loader)
    return (loader.engine and loader.engine.unitReactionTriggers) or {}
end

function reactions.knownTrigger(loader, id)
    for _, trigger in ipairs(triggerRegistry(loader)) do
        if trigger.id == id then return trigger end
    end
    return nil
end

function reactions.run(unit, triggerId, ctx)
    local loader = ctx.loader or (ctx.session and ctx.session.loader)
    if not reactions.knownTrigger(loader, triggerId) then
        error("unknown Unit reaction trigger '" .. tostring(triggerId) .. "'", 0)
    end
    local events = ctx.events or {}
    ctx.events = events
    for index, reaction in ipairs((unit.actorData and unit.actorData.reactions) or {}) do
        if reaction.trigger == triggerId then
            if reaction.condition == nil or reaction.condition == ""
                or formula.eval(reaction.condition, formula.makeContext({ v = ctx.v }, ctx.session)) then
                -- The authored id is stable provenance for diagnostics. It is
                -- never inferred from array position, while array position is
                -- the explicit deterministic execution order.
                ctx.reaction = { id = reaction.id, trigger = triggerId, index = index }
                interpreter.execList(reaction.commands, ctx)
                ctx.reaction = nil
            end
        end
    end
    return events
end

return reactions
