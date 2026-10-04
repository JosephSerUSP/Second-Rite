-- Durable actor-change reporting: what persistently changed about a creature
-- between two points in time.
--
-- This began as the battle level-up report, but level is only one way a
-- creature can develop. Stat-up items, skillbooks, scripted permanent rewards,
-- promotion and automatic form changes all need the same answer: compare the
-- authoritative creature before/after and describe the durable difference.
--
-- Nothing here MUTATES progression. The owning subsystem commits gameplay
-- first; this module only snapshots and projects the resolved facts for
-- presentation. Hosts decide when a transaction deserves a report.
--
-- Party snapshots are keyed by SLOT, never battler identity: a transform can
-- replace the object sitting in session.party[i], and identity-keyed lookup
-- would lose exactly the creature whose before/after report matters most.
-- Expedition-reserve slots use the same rule under snapshot.reserve[i].
local growth = require("engine.growth")
local progression = require("engine.progression")
local traits = require("engine.traits")
local config = require("engine.config")
local state_value = require("engine.state_value")

local progress = {}

-- Growth's PARAMS list stays the single source of which durable parameters the
-- growth report presents. engine.json -> paramLabels owns their player-facing
-- names, shared with the item/trait readouts.
local function paramLabel(param)
    local loader = require("engine.data.loader")
    local labels = (loader and loader.engine and loader.engine.paramLabels) or {}
    return labels[param] or param:upper()
end

local function skillIds(battler)
    local out = {}
    for _, id in ipairs(battler.skills or {}) do out[id] = true end
    return out
end

local function skillName(loader, id)
    local sk = loader and loader.getSkill and loader.getSkill(id)
    return (sk and sk.name) or tostring(id)
end

-- One creature's durable presentation-relevant state, as of now. Current HP,
-- states and equipment are deliberately absent: Actor Change is development,
-- not a generic mutation inspector.
local function snapshotMember(battler, session)
    local params = {}
    for _, p in ipairs(growth.PARAMS) do
        params[p] = traits.getParam(battler, p, session)
    end
    return {
        actorId = battler.actorData and battler.actorData.id,
        name = battler.name,
        portraitKey = (battler.actorData and battler.actorData.portrait) or "",
        level = battler.level or 1,
        exp = battler.exp or 0,
        params = params,
        skills = skillIds(battler),
    }
end

progress.snapshotMember = snapshotMember

local function snapshotSlots(list, session, limit)
    local snap = {}
    for i = 1, limit do
        local c = list and list[i]
        if c then snap[i] = snapshotMember(c, session) end
    end
    return snap
end

-- The creatures currently addressable by field-development hosts. Active party
-- slots stay at numeric keys for battle/API compatibility; expedition reserve
-- lives under `reserve` so ritual promotion can use the exact same transaction
-- contract without pretending reserve creatures are party members. Town storage
-- is intentionally outside this snapshot until a storage host can mutate a
-- creature in place.
function progress.snapshot(session)
    local snap = snapshotSlots(session.party, session, config.MAX_PARTY_SIZE)
    snap.reserve = snapshotSlots(session.reserve, session, config.MAX_PARTY_SIZE)
    return snap
end

local function classify(levelDelta, formChanged, rows, learned, forgotten)
    -- A level-triggered hatch/metamorphosis is still presented as the level
    -- transaction that caused it; a standalone form swap gets its own heading.
    if levelDelta > 0 then return "level", "LEVEL UP!" end
    if levelDelta < 0 then return "level", "LEVEL DOWN!" end
    if formChanged then return "form", "FORM CHANGE!" end

    if #rows > 0 then
        local up, down = false, false
        for _, row in ipairs(rows) do
            if row.delta > 0 then up = true elseif row.delta < 0 then down = true end
        end
        if up and not down then return "attribute", "ATTRIBUTE UP!" end
        if down and not up then return "attribute", "ATTRIBUTE DOWN!" end
        return "attribute", "ATTRIBUTE CHANGE"
    end

    if #learned > 0 and #forgotten == 0 then return "skill", "SKILL LEARNED!" end
    if #forgotten > 0 and #learned == 0 then return "skill", "SKILL FORGOTTEN" end
    if #learned > 0 or #forgotten > 0 then return "skill", "SKILL CHANGE!" end
    return "change", "ACTOR CHANGE"
end

local function diffMember(session, was, now, liveBattler)
    if not was or not now then return nil end
    local loader = session.loader
    local levelDelta = (now.level or 1) - (was.level or 1)
    local levelChanged = levelDelta ~= 0
    local formChanged = now.actorId ~= was.actorId

    local rows = {}
    for _, p in ipairs(growth.PARAMS) do
        local from, to = was.params[p] or 0, now.params[p] or 0
        local delta = to - from
        -- Preserve the old level-up screen's complete stat table, including a
        -- stat that happened to gain +0 this level. For other Actor Changes,
        -- showing only rows that actually changed keeps a stat fruit concise.
        if delta ~= 0 or levelChanged then
            table.insert(rows, {
                param = p,
                label = paramLabel(p),
                from = from,
                to = to,
                delta = delta,
                deltaText = delta > 0 and ("+" .. delta)
                    or (delta < 0 and tostring(delta) or ""),
            })
        end
    end

    local notes = {}
    local learned, forgotten = {}, {}
    for id in pairs(now.skills or {}) do
        if not (was.skills or {})[id] then table.insert(learned, skillName(loader, id)) end
    end
    for id in pairs(was.skills or {}) do
        if not (now.skills or {})[id] then table.insert(forgotten, skillName(loader, id)) end
    end
    table.sort(learned)
    table.sort(forgotten)

    for _, name in ipairs(learned) do
        table.insert(notes, (loader and loader.formatTerm)
            and loader.formatTerm("battle.learns_skill", "- {0} learns {1}!", now.name, name)
            or ("- " .. now.name .. " learns " .. name .. "!"))
    end
    for _, name in ipairs(forgotten) do
        table.insert(notes, (loader and loader.formatTerm)
            and loader.formatTerm("battle.forgets_skill", "- {0} forgets {1}.", now.name, name)
            or ("- " .. now.name .. " forgets " .. name .. "."))
    end
    if formChanged then
        table.insert(notes, (loader and loader.formatTerm)
            and loader.formatTerm("battle.transform", "- {0} becomes {1}!", was.name, now.name)
            or ("- " .. was.name .. " becomes " .. now.name .. "!"))
    end

    -- Potential unlock is specifically an upward level crossing.
    if levelDelta > 0 and liveBattler then
        for _, evolution in ipairs((liveBattler.actorData and liveBattler.actorData.evolutions) or {}) do
            local required = tonumber(evolution.level)
            if required and was.level < required and now.level >= required then
                table.insert(notes, (loader and loader.formatTerm)
                    and loader.formatTerm("battle.potential_unlocked",
                        "...{0}'s potential has been unlocked!", now.name)
                    or ("..." .. now.name .. "'s potential has been unlocked!"))
            end
        end
    end

    local skillChanged = #learned > 0 or #forgotten > 0
    if not levelChanged and not formChanged and #rows == 0 and not skillChanged then
        return nil
    end

    local kind, title = classify(levelDelta, formChanged, rows, learned, forgotten)
    return {
        kind = kind,
        title = title,
        name = now.name,
        fromName = was.name,
        toName = now.name,
        portraitKey = now.portraitKey or "",
        fromLevel = was.level,
        toLevel = now.level,
        levelDelta = levelDelta,
        levelChanged = levelChanged,
        formChanged = formChanged,
        exp = now.exp,
        expNeeded = progression.nextLevelExp(now.level),
        rows = rows,
        learnedSkills = learned,
        forgottenSkills = forgotten,
        noteText = table.concat(notes, "\n"),
    }
end

local function appendSlotChanges(entries, session, liveSlots, beforeSlots, limit)
    for i = 1, limit do
        local live = liveSlots and liveSlots[i]
        local was = beforeSlots and beforeSlots[i]
        if live and was then
            local entry = diffMember(session, was, snapshotMember(live, session), live)
            if entry then table.insert(entries, entry) end
        end
    end
end

-- Generic Actor Change query. Active party reports come first in party-slot
-- order, followed by expedition-reserve reports in reserve-slot order.
function progress.changes(session, before)
    local entries = {}
    appendSlotChanges(entries, session, session.party, before, config.MAX_PARTY_SIZE)
    appendSlotChanges(entries, session, session.reserve,
        before and before.reserve, config.MAX_PARTY_SIZE)
    return entries
end

-- Compatibility query for the battle host and older callers. The underlying
-- diff is generic; the old Level-Up API continues to mean upward crossings.
function progress.levelUps(session, before)
    local out = {}
    for _, entry in ipairs(progress.changes(session, before)) do
        if (entry.levelDelta or 0) > 0 then table.insert(out, entry) end
    end
    return out
end

-- Publishes one Actor Change entry onto Scene State. `actorChange*` is the new
-- generic contract. `levelUp*` aliases remain during migration because the
-- existing battle window/style consumes those names; both projections are
-- value copies so Scene State never contains aliased subtrees.
function progress.publish(v, entries, index)
    local e = entries and entries[index]
    local rows = e and e.rows or {}

    v.actorChangeRows = state_value.copy(rows, "actor-change rows")
    v.actorChangeName = e and e.name or ""
    v.actorChangeFromName = e and e.fromName or ""
    v.actorChangeToName = e and e.toName or ""
    v.actorChangePortrait = e and e.portraitKey or ""
    v.actorChangeFromLevel = e and e.fromLevel or 0
    v.actorChangeToLevel = e and e.toLevel or 0
    v.actorChangeExp = e and e.exp or 0
    v.actorChangeExpNeeded = e and e.expNeeded or 0
    v.actorChangeNoteText = e and e.noteText or ""
    v.actorChangeKind = e and e.kind or ""
    v.actorChangeTitle = e and e.title or "ACTOR CHANGE"
    v.actorChangeCounter = (entries and #entries > 1 and e)
        and (index .. "/" .. #entries) or ""

    -- Legacy battle presentation aliases. Do not alias actorChangeRows itself:
    -- the Scene host requires authored state to remain a value tree.
    v.levelUpRows = state_value.copy(rows, "level-up rows")
    v.levelUpName = v.actorChangeName
    v.levelUpPortrait = v.actorChangePortrait
    v.levelUpFromLevel = v.actorChangeFromLevel
    v.levelUpToLevel = v.actorChangeToLevel
    v.levelUpExp = v.actorChangeExp
    v.levelUpExpNeeded = v.actorChangeExpNeeded
    v.levelUpNoteText = v.actorChangeNoteText
    v.levelUpCounter = v.actorChangeCounter
end

return progress