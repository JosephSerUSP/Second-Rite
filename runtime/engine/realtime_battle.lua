-- Real-time battle scheduler (PE Day 1 M1, #1424).
--
-- docs/design/runtime/semantics/realtime-battle-merge-ledger.md is the design.
-- This module is a SECOND SCHEDULER over production Battle, not a second
-- battle engine: it decides who acts and when (AT gauges on a fixed-step
-- clock, positions, telegraphed deliveries), and every action it decides is
-- resolved by the unchanged `Battle:executeTurn`. HP, damage, costs, items,
-- escape, rewards and outcomes therefore stay with their production owners.
--
-- Determinism: the clock only advances through `step`, one fixed tick at a
-- time; a round is `system.realtimeBattle.ticksPerRound` ticks (ledger O1), and
-- the only randomness is the battle RNG production already uses.

local flow = require("engine.flow")
local formula = require("engine.formula")
local skill_cost = require("engine.skill_cost")
local battleSystem = require("engine.battle")

local realtime = {}

local RT = {}
RT.__index = RT

local AT_FULL = 100

local function distance(ax, ay, bx, by)
    local dx, dy = ax - bx, ay - by
    return math.sqrt(dx * dx + dy * dy)
end

local function conf(loader)
    local c = loader.system and loader.system.realtimeBattle
    if type(c) ~= "table" then
        error("system.realtimeBattle is required by the real-time battle mode", 2)
    end
    local ticks = tonumber(c.ticksPerRound)
    if not ticks or ticks < 1 or ticks ~= math.floor(ticks) then
        error("system.realtimeBattle.ticksPerRound must be a whole number >= 1", 2)
    end
    if type(c.atPerTick) ~= "string" and type(c.atPerTick) ~= "number" then
        error("system.realtimeBattle.atPerTick must be a formula over the battler (a)", 2)
    end
    if type(c.moveSpeed) ~= "number" or c.moveSpeed <= 0 then
        error("system.realtimeBattle.moveSpeed must be a positive number (floor units per tick)", 2)
    end
    return c
end

local function append(into, list)
    for _, ev in ipairs(list or {}) do into[#into + 1] = ev end
end

--- Starts a battle with the named troop through the production
--- `battle.battle_start` phase, exactly as the round host does.
--- opts.positions = { party = { {x, y}, ... }, enemies = { {x, y}, ... } }
function realtime.start(session, troopId, opts)
    opts = opts or {}
    local loader = session.loader
    local c = conf(loader)

    local enemyList, troopData
    local startEvents = flow.run("battle.battle_start", { session = session, troopId = troopId })
    for _, ev in ipairs(startEvents) do
        if ev.type == "spawn_enemies" then
            enemyList = ev.enemies
            troopData = ev.troop
        end
    end
    if not enemyList or #enemyList == 0 then
        error("troop '" .. tostring(troopId) .. "' spawned no enemies", 2)
    end

    local self = setmetatable({}, RT)
    self.session = session
    self.loader = loader
    self.conf = c
    self.battle = battleSystem.Battle.new(session, enemyList)
    self.battle.troop = troopData
    self.tick = 0
    self.paused = false
    self.outcome = nil
    self.pending = {}
    self.projectiles = {}
    self.events = {}
    append(self.events, startEvents)
    -- Facts the presenter reads through realtime.view. Recorded here, where
    -- the transitions happen, so presentation never reconstructs them.
    self.lastHit = nil        -- { target, amount, tick }
    self.lastMiss = nil       -- { actor, tick }
    self.lastRefusal = nil    -- { reason, tick }
    self.lastAction = nil     -- { actor, tick }
    self.strikeTick = nil     -- tick of the last enemy delivery

    local positions = opts.positions or {}
    local function place(list, spots, side)
        for slot, b in pairs(list) do
            local spot = spots[slot]
            if b and not spot then
                error("no starting position for " .. side .. " slot " .. tostring(slot), 3)
            end
            if b then
                b.field = { x = spot[1], y = spot[2] }
                b.at = 0
            end
        end
    end
    place(session.party, positions.party or {}, "party")
    place(self.battle.enemies, positions.enemies or {}, "enemy")
    self.bounds = opts.bounds
    return self
end

function RT:player()
    return self.session.party[1]
end

function RT:isEnemy(b)
    for _, e in pairs(self.battle.enemies) do
        if e == b then return true end
    end
    return false
end

function RT:livingEnemies()
    local out = {}
    for _, e in pairs(self.battle.enemies) do
        if e and not e:isDead() then out[#out + 1] = e end
    end
    return out
end

local function atGain(self, b)
    local per = self.conf.atPerTick
    if type(per) == "number" then return per end
    local view = formula.battlerView(b, self.session)
    return tonumber(formula.eval(per, { a = view, b = view })) or 0
end

-- Resolve one action through the production resolver. Every hit lands here.
function RT:resolve(actor, skill, target, item)
    local before = #self.events
    self.battle:executeTurn({ actor = actor, skill = skill, item = item, target = target }, self.events)
    for i = before + 1, #self.events do
        local ev = self.events[i]
        ev.tick = self.tick
        if ev.type == "damage" then
            self.lastHit = { target = ev.target, amount = ev.value, tick = self.tick }
        end
    end
    self.lastAction = { actor = actor, tick = self.tick }
    self:checkOutcome()
end

-- A delivery that never made contact. The cost is still paid and the
-- cooldown still starts, through the same functions executeTurn uses (O4).
function RT:miss(actor, skill, target)
    skill_cost.spend(skill, actor, self.session, self:isEnemy(actor))
    skill_cost.startCooldown(skill, actor)
    self.events[#self.events + 1] = { type = "miss", actor = actor, skill = skill,
        target = target, tick = self.tick }
    self.lastMiss = { actor = actor, tick = self.tick }
    self.lastAction = { actor = actor, tick = self.tick }
end

function RT:checkOutcome()
    if self.outcome then return end
    local outcome
    for _, ev in ipairs(self.events) do
        if ev.type == "flee_success" then outcome = "escaped" end
    end
    if not outcome then
        if self.battle:isVictory() then outcome = "victory"
        elseif self.battle:isDefeat() then outcome = "defeat" end
    end
    if not outcome then return end
    self.outcome = outcome
    local ctx = { session = self.session, battle = self.battle, party = self.session.party,
        enemies = self.battle.enemies }
    append(self.events, flow.run("battle." .. outcome, ctx))
    for _, b in pairs(self.session.party) do if b then skill_cost.endBattle(b) end end
    for _, b in pairs(self.battle.enemies) do if b then skill_cost.endBattle(b) end end
end

--- Player command. kind = "skill" | "item"; needs a full AT gauge.
--- Returns false plus a reason when the command cannot be taken.
function RT:command(kind, id, target)
    local ok, reason = self:commandInner(kind, id, target)
    if not ok then self.lastRefusal = { reason = reason, tick = self.tick } end
    return ok, reason
end

function RT:commandInner(kind, id, target)
    if self.outcome then return false, "battle over" end
    local actor = self:player()
    if (actor.at or 0) < AT_FULL then return false, "not ready" end
    if kind == "skill" then
        local skill = self.loader.getSkill(id)
        if not skill then error("unknown skill '" .. tostring(id) .. "'", 2) end
        local reason = skill_cost.blockedReason(skill, actor, self.session, false)
        if reason then return false, reason end
        actor.at = 0
        local rt = skill.realtime or {}
        target = target or actor
        if rt.delivery == "range" then
            if distance(actor.field.x, actor.field.y, target.field.x, target.field.y) > rt.range then
                self:miss(actor, skill, target)
                return true
            end
        elseif rt.delivery ~= nil then
            error("player skill '" .. tostring(id) .. "' has unsupported delivery '" .. tostring(rt.delivery) .. "'", 2)
        end
        self:resolve(actor, skill, target)
        return true
    elseif kind == "item" then
        if not self.session:hasItem(id, 1) then return false, "none left" end
        actor.at = 0
        self:resolve(actor, nil, target or actor, { id = id })
        return true
    end
    error("unknown real-time command kind '" .. tostring(kind) .. "'", 2)
end

function RT:move(b, dx, dy)
    b.field.x = b.field.x + dx
    b.field.y = b.field.y + dy
    local bounds = self.bounds
    if bounds then
        b.field.x = math.max(bounds.minX, math.min(bounds.maxX, b.field.x))
        b.field.y = math.max(bounds.minY, math.min(bounds.maxY, b.field.y))
    end
end

-- Enemy turn: production AI chooses, the skill's delivery telegraphs it.
function RT:beginEnemyAction(enemy)
    local action = self.battle:getAIAction(enemy)
    if not action then return end
    local skill, target = action.skill, action.target
    local rt = skill.realtime or {}
    enemy.at = 0
    if rt.delivery == nil then
        self:resolve(enemy, skill, target)
        return
    end
    self.pending[#self.pending + 1] = {
        actor = enemy, skill = skill, target = target, delivery = rt.delivery, rt = rt,
        timer = rt.windupTicks or 0,
        lockX = target.field.x, lockY = target.field.y,
    }
    self.events[#self.events + 1] = { type = "telegraph", actor = enemy, skill = skill,
        target = target, lockX = target.field.x, lockY = target.field.y, tick = self.tick }
end

function RT:deliver(p)
    local actor, skill, target, rt = p.actor, p.skill, p.target, p.rt
    self.strikeTick = self.tick
    if p.delivery == "lunge" then
        actor.field.x, actor.field.y = p.lockX, p.lockY
        if distance(target.field.x, target.field.y, p.lockX, p.lockY) <= rt.radius then
            self:resolve(actor, skill, target)
        else
            self:miss(actor, skill, target)
        end
    elseif p.delivery == "projectiles" then
        local count = rt.count or 1
        local baseAngle = math.atan2(p.lockY - actor.field.y, p.lockX - actor.field.x)
        for i = 1, count do
            local angle = baseAngle + (i - (count + 1) / 2) * (rt.spread or 0)
            self.projectiles[#self.projectiles + 1] = {
                actor = actor, skill = skill, target = target, rt = rt,
                x = actor.field.x, y = actor.field.y,
                vx = math.cos(angle) * rt.speed, vy = math.sin(angle) * rt.speed,
                life = rt.lifeTicks, hit = false, index = i,
            }
        end
        skill_cost.startCooldown(skill, actor)
    else
        error("enemy skill '" .. tostring(skill.id) .. "' has unsupported delivery '" .. tostring(p.delivery) .. "'")
    end
end

function RT:stepProjectiles()
    local alive = {}
    for _, pr in ipairs(self.projectiles) do
        pr.x, pr.y = pr.x + pr.vx, pr.y + pr.vy
        pr.life = pr.life - 1
        if not pr.hit and not pr.target:isDead()
                and distance(pr.x, pr.y, pr.target.field.x, pr.target.field.y) <= pr.rt.radius then
            pr.hit = true
            self:resolve(pr.actor, pr.skill, pr.target)
        end
        if pr.life > 0 and not pr.hit and not self.outcome then alive[#alive + 1] = pr end
    end
    self.projectiles = alive
end

--- Advances the battle by exactly one fixed tick. `input.dx/dy` move the
--- player this tick. Paused or finished battles do not advance.
function RT:step(input)
    if self.outcome or self.paused then return end
    self.tick = self.tick + 1
    local player = self:player()
    -- Input is a direction; speed is the Project's rule, so diagonal
    -- movement is never faster than straight movement.
    local dx, dy = input and input.dx or 0, input and input.dy or 0
    if (dx ~= 0 or dy ~= 0) and not player:isDead() then
        local len = math.max(1, math.sqrt(dx * dx + dy * dy))
        self:move(player, dx / len * self.conf.moveSpeed, dy / len * self.conf.moveSpeed)
    end

    for _, b in pairs(self.session.party) do
        if b and not b:isDead() then b.at = math.min(AT_FULL, (b.at or 0) + atGain(self, b)) end
    end
    for _, e in ipairs(self:livingEnemies()) do
        e.at = math.min(AT_FULL, (e.at or 0) + atGain(self, e))
    end

    local busy = {}
    for _, p in ipairs(self.pending) do busy[p.actor] = true end
    for _, pr in ipairs(self.projectiles) do busy[pr.actor] = true end
    for _, e in ipairs(self:livingEnemies()) do
        if e.at >= AT_FULL and not busy[e] and not self.outcome then self:beginEnemyAction(e) end
    end

    -- Idle enemies close in, per their unit's `realtime.approach`
    -- { speed = units/tick, stopAt = distance }. Busy ones hold position.
    for _, e in ipairs(self:livingEnemies()) do
        local approach = e.actorData and e.actorData.realtime and e.actorData.realtime.approach
        if approach and not busy[e] and not player:isDead() then
            local d = distance(e.field.x, e.field.y, player.field.x, player.field.y)
            if d > approach.stopAt then
                local stepLen = math.min(approach.speed, d - approach.stopAt)
                self:move(e, (player.field.x - e.field.x) / d * stepLen, (player.field.y - e.field.y) / d * stepLen)
            end
        end
    end

    local still = {}
    for _, p in ipairs(self.pending) do
        if self.outcome or p.actor:isDead() then
            -- a dead actor's telegraph never lands
        else
            p.timer = p.timer - 1
            if p.timer <= 0 then self:deliver(p) else still[#still + 1] = p end
        end
    end
    self.pending = still
    self:stepProjectiles()

    if not self.outcome and self.tick % self.conf.ticksPerRound == 0 then
        self.battle:processRoundEnd(self.events)
        self:checkOutcome()
        if not self.outcome then
            append(self.events, flow.run("battle.round_start",
                { session = self.session, battle = self.battle, party = self.session.party }))
        end
    end
end

--- Hands accumulated resolved events to a presenter and clears them.
function RT:drainEvents()
    local out = self.events
    self.events = {}
    return out
end

--- Read-only formula view of the active real-time battle (`rt.*`), shared by
--- scene logic and rendering so both read the same resolved facts. nil when
--- no real-time battle is active.
function realtime.view(session)
    local self = session and session.realtimeBattle
    if not self then return nil end
    local resources = require("engine.battler_resources")
    local function age(fact) return fact and (self.tick - fact.tick) or 1e9 end
    local function battlerFacts(b)
        if not b then return nil end
        local res = {}
        for _, id in ipairs(resources.ids(self.session)) do
            local current, max = resources.get(b, id, self.session)
            res[id] = current
            res[id .. "Max"] = max
        end
        return { x = b.field.x, y = b.field.y, hp = b.hp, maxHp = b:getMaxHp(self.session),
            at = b.at or 0, dead = b:isDead(), res = res }
    end
    local player = self:player()
    local enemy = self.battle.enemies[1]
    local enemyView = battlerFacts(enemy)
    if enemyView then
        local pend
        for _, p in ipairs(self.pending) do if p.actor == enemy then pend = p end end
        enemyView.windup = pend ~= nil
        enemyView.lockX = pend and pend.lockX or enemy.field.x
        enemyView.lockY = pend and pend.lockY or enemy.field.y
        enemyView.strikeAge = self.strikeTick and (self.tick - self.strikeTick) or 1e9
    end
    local fire = {}
    for i = 1, 3 do fire[i] = { x = 0, y = 0, live = false } end
    for _, pr in ipairs(self.projectiles) do
        if pr.index and pr.index <= 3 then fire[pr.index] = { x = pr.x, y = pr.y, live = true } end
    end
    local hit = self.lastHit
    local items = {}
    for id, qty in pairs(self.session.inventory or {}) do items[id] = qty end
    return {
        items = items,
        tick = self.tick, round = self.battle.round, paused = self.paused,
        outcome = self.outcome or "",
        player = battlerFacts(player), enemy = enemyView, fire = fire,
        hitAge = age(hit), hitAmount = hit and hit.amount or 0,
        hitOnPlayer = hit ~= nil and hit.target == player,
        missAge = age(self.lastMiss),
        actAge = (self.lastAction and self.lastAction.actor == player) and age(self.lastAction) or 1e9,
        refusal = self.lastRefusal and self.lastRefusal.reason or "",
        refusalAge = age(self.lastRefusal),
    }
end

realtime.AT_FULL = AT_FULL
return realtime
