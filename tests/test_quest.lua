local loader = require("data.loader")
local session = require("engine.session")
local quest = require("engine.quest")
local conditions = require("engine.conditions")

local passed, failed = 0, 0
local function check(condition, label)
    if condition then
        passed = passed + 1
        print("  [PASS] " .. label)
    else
        failed = failed + 1
        print("  [FAIL] " .. label)
    end
end

print("=== Testing canonical quest transitions ===")

local offered = session.GameSession.new(loader)
local offerResult = quest.offer(offered, loader, "sparkling_gift")
check(offerResult.outcome == "accepted"
    and offered.flags["quest:sparkling_gift:active"] == true,
    "offer runs authored behavior and marks the quest active once")
local matched, active = conditions.evalPrefixed("questStatus:sparkling_gift:active", offered)
check(matched and active, "questStatus observes the canonical active flag")

local failedCompletion = session.GameSession.new(loader)
failedCompletion.flags["quest:sparkling_gift:active"] = true
local failedGold = failedCompletion.gold
local failure = quest.complete(failedCompletion, loader, "sparkling_gift")
check(failure.outcome == "requirements_failed"
    and failedCompletion.flags["quest:sparkling_gift:active"] == true
    and not failedCompletion.flags["quest:sparkling_gift:completed"],
    "failed completion preserves active state")
check(failedCompletion.gold == failedGold and not failedCompletion:hasItem(8, 1),
    "failed requirements grant no rewards")

local completed = session.GameSession.new(loader)
completed.flags["quest:sparkling_gift:active"] = true
completed:addItem(24, 1)
local initialGold = completed.gold
local success = quest.complete(completed, loader, "sparkling_gift")
check(success.outcome == "completed"
    and not completed:hasItem(24, 1)
    and completed:hasItem(8, 1)
    and completed.gold == initialGold + 45,
    "successful completion consumes requirements and grants rewards once")
check(completed.flags["quest:sparkling_gift:active"] == nil
    and completed.flags["quest:sparkling_gift:completed"] == true,
    "successful completion performs the lifecycle transition once")
local goldAfter = completed.gold
local repeatResult = quest.complete(completed, loader, "sparkling_gift")
check(repeatResult.outcome == "already_completed" and completed.gold == goldAfter
    and completed:hasItem(8, 1),
    "repeated completion cannot grant rewards again")
local _, completedStatus = conditions.evalPrefixed("questStatus:sparkling_gift:completed", completed)
check(completedStatus, "questStatus continues to resolve completed quests")

local overrideDefinition = {
    acceptHook = { { cmd = "SET_FLAG", flag = "custom_offer_ran", value = true } },
    completeHook = { { cmd = "SET_FLAG", flag = "custom_complete_ran", value = true } },
    requirements = { items = {} },
    rewards = {},
}
local overrideLoader = setmetatable({
    getQuest = function(id) return id == "override_fixture" and overrideDefinition or nil end,
}, { __index = loader })
local overridden = session.GameSession.new(overrideLoader)
local overrideOffer = quest.offer(overridden, overrideLoader, "override_fixture")
local overrideComplete = quest.complete(overridden, overrideLoader, "override_fixture")
check(overrideOffer.outcome == "accepted" and overridden.flags.custom_offer_ran == true,
    "top-level acceptHook replaces the quest.offer default through the canonical transition")
check(overrideComplete.outcome == "completed" and overridden.flags.custom_complete_ran == true,
    "top-level completeHook replaces the quest.complete default through the canonical transition")

print(string.format("=== Quest Transition Tests: %d passed, %d failed ===", passed, failed))
assert(failed == 0, tostring(failed) .. " quest transition tests failed")
