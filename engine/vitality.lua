local traits = require("engine.traits")

local vitality = {}

-- A safety ceiling for projects which have not authored combat.overhealCap yet.
-- The cap is a multiplier of the creature's CURRENT effective Max HP. It is a
-- ceiling for recovery, not a second HP pool: current HP remains battler.hp and
-- damage consumes it normally.
local DEFAULT_OVERHEAL_CAP = 1.5

function vitality.maxHpComponents(battler, session)
    if not battler then
        return { base = 0, permanentPlus = 0, underlying = 0, active = 0, activeModifier = 0 }
    end
    local base = traits.getBaseParam(battler, "maxHp")
    local permanentPlus = (battler.paramPlus and battler.paramPlus.maxHp) or 0
    local underlying = math.max(1, math.floor(base + permanentPlus))
    local active = traits.getParam(battler, "maxHp", session)
    return {
        base = base,
        permanentPlus = permanentPlus,
        underlying = underlying,
        active = active,
        -- Includes every currently-active trait contribution (states, gear,
        -- passives, Savor and PARAM_RATE), deliberately separate from the
        -- persistent paramPlus bucket above.
        activeModifier = active - underlying,
    }
end

-- HP thresholds use current HP / CURRENT effective Max HP. The ratio is not
-- clamped, so an Overhealed creature can deterministically report > 1.0 (and
-- therefore > 100%). This is the same interpretation traits.evaluateCondition
-- already uses for authored "HP < N%" conditions.
function vitality.hpRatio(battler, session)
    local maxHp = traits.getParam(battler, "maxHp", session)
    if maxHp <= 0 then return 0 end
    return (battler.hp or 0) / maxHp
end

function vitality.overhealCapRatio(effectData, session)
    if not (effectData and effectData.overheal == true) then return 1 end
    local combat = session and session.loader and session.loader.system
        and session.loader.system.combat or {}
    local ratio = effectData.overhealCap or combat.overhealCap or DEFAULT_OVERHEAL_CAP
    ratio = tonumber(ratio) or DEFAULT_OVERHEAL_CAP
    return math.max(1, ratio)
end

function vitality.recoveryCap(effectData, battler, session)
    local maxHp = traits.getParam(battler, "maxHp", session)
    return math.max(maxHp, math.floor(maxHp * vitality.overhealCapRatio(effectData, session)))
end

-- Applies positive recovery without ever reducing existing HP. That last rule
-- matters once Overheal exists: an ordinary potion/regen tick used at 120/100
-- restores zero; it must not silently snap the creature back to 100/100.
function vitality.applyHeal(effectData, battler, amount, session)
    if not battler then return 0, 0 end
    amount = math.max(0, math.floor(tonumber(amount) or 0))
    local before = battler.hp or 0
    local cap = vitality.recoveryCap(effectData, battler, session)
    local after = math.max(before, math.min(cap, before + amount))
    battler.hp = after
    return after - before, cap
end

-- Capacity growth grants the amount of NEW capacity as current HP, but never
-- double-counts HP which was already present as Overheal. Thus 80/100 +25 ->
-- 105/125, while 130/100 +25 -> 130/125.
function vitality.applyMaxHpIncrease(battler, beforeMax, afterMax)
    if not battler or afterMax <= beforeMax then return 0 end
    local beforeHp = battler.hp or 0
    local gain = afterMax - beforeMax
    battler.hp = math.max(beforeHp, math.min(afterMax, beforeHp + gain))
    return battler.hp - beforeHp
end

-- Capacity loss is a clamp, never damage. Callers report it as max_hp_change /
-- hp_clamp events rather than damage/death so damage reactions cannot fire.
function vitality.applyMaxHpDecrease(battler, afterMax)
    if not battler then return 0 end
    local beforeHp = battler.hp or 0
    battler.hp = math.min(beforeHp, afterMax)
    return beforeHp - battler.hp
end

function vitality.maxHpTransition(battler, beforeMax, afterMax)
    local hpGranted, hpClamped = 0, 0
    if afterMax > beforeMax then
        hpGranted = vitality.applyMaxHpIncrease(battler, beforeMax, afterMax)
    elseif afterMax < beforeMax then
        hpClamped = vitality.applyMaxHpDecrease(battler, afterMax)
    end
    return {
        before = beforeMax,
        after = afterMax,
        delta = afterMax - beforeMax,
        hpGranted = hpGranted,
        hpClamped = hpClamped,
    }
end

return vitality
