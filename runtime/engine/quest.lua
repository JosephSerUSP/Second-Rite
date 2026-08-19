-- Canonical quest lifecycle transition owner.
--
-- Conversation graphs decide where dialogue goes next. This module alone
-- decides which authored behavior runs and when quest lifecycle flags mutate.
local flow = require("engine.flow")
local interpreter = require("engine.interpreter")

local quest = {}

local function resolve(loader, questId)
    local definition = loader and loader.getQuest and loader.getQuest(questId)
    if not definition then error("unknown quest '" .. tostring(questId) .. "'", 0) end
    return definition
end

local function runBehavior(phase, hookName, ctx)
    local commands = ctx.quest[hookName]
    if commands then return interpreter.runImmediate(commands, ctx) end
    return flow.run(phase, ctx)
end

local function context(session, loader, questId, definition)
    return {
        session = session,
        loader = loader,
        questId = questId,
        quest = definition,
    }
end

function quest.offer(session, loader, questId)
    local definition = resolve(loader, questId)
    local activeKey = "quest:" .. questId .. ":active"
    local completedKey = "quest:" .. questId .. ":completed"
    if session.flags[completedKey] then return { events = {}, outcome = "already_completed" } end
    if session.flags[activeKey] then return { events = {}, outcome = "already_active" } end

    local events = runBehavior("quest.offer", "acceptHook",
        context(session, loader, questId, definition))
    session.flags[activeKey] = true
    return { events = events or {}, outcome = "accepted" }
end

function quest.complete(session, loader, questId)
    local definition = resolve(loader, questId)
    local activeKey = "quest:" .. questId .. ":active"
    local completedKey = "quest:" .. questId .. ":completed"
    if session.flags[completedKey] then return { events = {}, outcome = "already_completed" } end

    local events = runBehavior("quest.complete", "completeHook",
        context(session, loader, questId, definition)) or {}
    for _, event in ipairs(events) do
        if event.type == "quest_requirements_failed" then
            return { events = events, outcome = "requirements_failed" }
        end
    end

    session.flags[activeKey] = nil
    session.flags[completedKey] = true
    return { events = events, outcome = "completed" }
end

return quest
