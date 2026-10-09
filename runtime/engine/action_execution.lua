local interpreter = require("engine.interpreter")
local config = require("engine.config")
local skill_cost = require("engine.skill_cost")
local resolved_event = require("engine.resolved_event")
local formation = require("engine.formation")
local compareIds = require("engine.inventory").compareIds
local action = {}

-- Shared single-action mutation. Hosts own scheduling, phases and outcomes.
-- Context supplies session, allies/enemies, applyItem and evaluateCover.
function action.execute(self, turn, roundEvents)
    local targeting = require("engine.targeting")
    local config = require("engine.config")
    
    local acted = not turn.actor:isDead()
    local targetDead = false
    if turn.target and turn.target.isDead and turn.target:isDead() then
        local spec = turn.item and (turn.item.target or "ally") or (turn.skill and turn.skill.target)
        if spec then
            local expanded = targeting.expand(spec)
            if expanded.state ~= "dead" and expanded.state ~= "any" then
                targetDead = true
            end
        end
    end

    if targetDead then
        local autoRedirect = false
        if self.session and self.session.autoRedirect ~= nil then
            autoRedirect = self.session.autoRedirect
        elseif config.combat and config.combat.autoRedirect ~= nil then
            autoRedirect = config.combat.autoRedirect
        end

        if autoRedirect then
            local spec = turn.item and (turn.item.target or "ally") or (turn.skill and turn.skill.target)
            if spec then
                local newTargets = targeting.resolve(turn.actor, spec, self, nil, turn.item or turn.skill)
                if newTargets and #newTargets > 0 and not newTargets[1]:isDead() then
                    turn.target = newTargets[1]
                    targetDead = false
                end
            end
        end
    end

    if not turn.actor:isDead() then
        if turn.actor.isRestricted and turn.actor:isRestricted() then
            local loader = self.session and self.session.loader
            local msg = (loader and loader.formatTerm) and loader.formatTerm("battle.is_asleep", "{0} is unable to act!", turn.actor.name) or (turn.actor.name .. " is unable to act!")
            table.insert(roundEvents, {
                type = "text",
                text = msg
            })
        elseif targetDead then
            local loader = self.session and self.session.loader
            local msg = (loader and loader.formatTerm) and loader.formatTerm("battle.target_dead", "{0}'s target is already dead!", turn.actor.name) or (turn.actor.name .. "'s target is already dead!")
            table.insert(roundEvents, {
                type = "text",
                text = msg
            })
        elseif turn.item then
            -- F7: apply the used item's effects and consume it. This
            -- spends the creature's turn exactly like a skill would.
            local evs = self:applyItem(turn.item, turn.actor, turn.target)
            for _, ev in ipairs(evs) do
                table.insert(roundEvents, ev)
            end
        else
            local loader = self.session.loader
            local spec = turn.skill.target
            local targets = targeting.resolve(turn.actor, spec, self, turn.target, turn.skill)
            targets = self:evaluateCover(turn.actor, spec, targets, roundEvents)

            -- Pay for the casting HERE -- the one place a skill actually
            -- resolves -- so the charge path and the Overcast path cannot
            -- drift apart, and so a skill that never resolves (actor died,
            -- target gone) is never charged for.
            local isEnemy = false
            for slot = 1, config.MAX_PARTY_SIZE do
                if self.enemies[slot] == turn.actor then isEnemy = true break end
            end
            local paid = skill_cost.spend(turn.skill, turn.actor, self.session, isEnemy)
            skill_cost.startCooldown(turn.skill, turn.actor)
            if paid == "overcast" then
                local overcastEvent = {
                    type = "overcast",
                    actor = turn.actor,
                    skill = turn.skill,
                    value = turn.skill.overcast and turn.skill.overcast.mp or 0,
                    text = loader.formatTerm("battle.overcast",
                        "- {0} overcasts {1}! ({2} MP)", turn.actor.name,
                        turn.skill.name, turn.skill.overcast and turn.skill.overcast.mp or 0),
                }
                -- skill_cost.spend already committed MP. Publish the resulting
                -- value so live presentation can reveal it without replaying
                -- the cost (the old snapshot wrapper accidentally made
                -- Overcast free in live battles).
                resolved_event.attach(overcastEvent, self.session)
                table.insert(roundEvents, overcastEvent)
            end

            table.insert(roundEvents, {
                type = "action",
                actor = turn.actor,
                skill = turn.skill,
                target = targets[1] or turn.target or turn.actor,
                animation = turn.skill and turn.skill.animation or nil,
            })
            
            local seq = nil
            if turn.skill.actionSequence then
                seq = loader.actionSequences[turn.skill.actionSequence]
            end
            local commands = (seq and seq.commands) or turn.skill.actionSequenceCommands
            if not commands then
                local defaultSeq = loader.actionSequences and loader.actionSequences["default"]
                commands = defaultSeq and defaultSeq.commands
            end
            if not commands then
                commands = { { cmd = "APPLY_EFFECT" } }
            end
            
            local seqCtx = {
                a = turn.actor,
                target = targets[1] or turn.target or turn.actor,
                targets = targets,
                skill = turn.skill,
                battle = self,
                session = self.session,
                loader = loader,
                events = {},
                refs = {}
            }
            
            interpreter.runImmediate(commands, seqCtx)
            
            for _, ev in ipairs(seqCtx.events) do
                table.insert(roundEvents, ev)
            end
        end
        
    end
    return acted
end

function action.applyItem(self, action, actor, target)
    local events = {}
    local session = self.session
    local loader = session.loader

    local item = nil
    if action.id then
        item = loader.getItem(action.id)
    elseif action.itemIndex then
        local stacks = {}
        for itemId, qty in pairs(session.inventory or {}) do
            if qty > 0 then table.insert(stacks, itemId) end
        end
        table.sort(stacks, compareIds)
        item = stacks[action.itemIndex] and loader.getItem(stacks[action.itemIndex])
    end

    if not item then return events end

    -- Verify item is still in stock
    local curQty = (session.inventory and session.inventory[item.id]) or 0
    if curQty <= 0 then
        table.insert(events, {
            type = "text",
            text = loader.formatTerm("battle.no_items_left", "No {0} remaining!", item.name or "?"),
        })
        return events
    end

    local targeting = require("engine.targeting")
    local itemSpec = (action and action.targetSpec) or item.target or "ally"
    local targets = targeting.resolve(actor, itemSpec, self, target, item)
    targets = self:evaluateCover(actor, itemSpec, targets, events)
    local effectiveTarget = targets[1] or target or actor

    table.insert(events, {
        type = "text",
        text = loader.formatTerm("battle.uses_item", "{0} uses {1}!", actor.name, item.name or "?"),
        animation = item.animation,
        itemTarget = effectiveTarget,
    })
    
    local seq = nil
    if item.actionSequence then
        seq = loader.actionSequences[item.actionSequence]
    end
    local commands = (seq and seq.commands) or item.actionSequenceCommands
    if not commands then
        local defaultItemSeq = loader.actionSequences and loader.actionSequences["default_item"]
        commands = defaultItemSeq and defaultItemSeq.commands
    end
    if not commands then
        commands = { { cmd = "APPLY_EFFECT" } }
    end
    
    local seqCtx = {
        a = actor,
        target = effectiveTarget,
        targets = targets,
        item = item,
        battle = self,
        session = session,
        loader = loader,
        events = {},
        refs = {}
    }
    
    interpreter.runImmediate(commands, seqCtx)
    
    for _, ev in ipairs(seqCtx.events) do
        table.insert(events, ev)
    end

    -- Consumption is authoritative alongside every other round mutation. The
    -- scene no longer snapshots selected fields and therefore cannot leave
    -- inventory on a different clock from HP/MP/state.
    session:addItem(item.id, -1)
    return events
end

function action.evaluateCover(self, actor, spec, targets, roundEvents)
    if not spec or not targets or #targets == 0 then return targets end
    local targeting = require("engine.targeting")
    local traits = require("engine.traits")
    local config = require("engine.config")

    local expanded = targeting.expand(spec)
    if expanded.side == "enemy" and expanded.shape == "single" and expanded.cover == "respect" then
        local origTarget = targets[1]
        local targetGroup, targetSlot
        targetSlot = formation.slotOf(self.allies, origTarget)
        if targetSlot then
            targetGroup = self.allies
        else
            targetSlot = formation.slotOf(self.enemies, origTarget)
            if targetSlot then targetGroup = self.enemies end
        end
        if targetGroup and targetSlot and formation.rowOf(targetSlot) == "back" then
            local frontSlot = formation.alignedFrontSlot(targetSlot)
            local protector = targetGroup[frontSlot]
            if protector and not protector:isDead() and not (protector.isRestricted and protector:isRestricted()) then
                if #traits.findAllSources(protector, "COVER_ALIGNED_BACK", self.session) > 0 then
                    targets = { protector }
                    if roundEvents and self.session and self.session.loader then
                        table.insert(roundEvents, {
                            type = "text",
                            text = self.session.loader.formatTerm("battle.cover_intercept", "- {0} steps in to protect {1}!", protector.name, origTarget.name)
                        })
                    end
                end
            end
        end
    end
    return targets
end

return action
