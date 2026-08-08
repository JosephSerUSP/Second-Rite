-- Regression guard for #145: Reserve is an ordered list, not a formation grid.
-- This is intentionally structural: it pins the declarative scene contract and
-- the swap-source seam without depending on pixel output or G5.


package.path = package.path .. ";./?.lua;./engine/?.lua"

local function findWindow(scene, id)
    for _, win in ipairs((scene and scene.windows) or {}) do
        if win.id == id then return win end
    end
    return nil
end

local function firstList(win)
    for _, entry in ipairs((win and win.content) or {}) do
        if entry.type == "list" then return entry end
    end
    return nil
end

do
    local loader = require("data.loader")

    local reserve = assert(loader.getScene("reserve"), "reserve scene missing")
    local roster = assert(findWindow(reserve, "reserve_roster"), "reserve_roster window missing")
    local rosterList = assert(firstList(roster), "reserve_roster list content missing")

    assert(roster.style == "list", "dedicated Reserve roster must use list presentation")
    -- The capacity is config.MAX_RESERVE_SIZE, not a literal. Reserve went
    -- from 8 slots to 4 when window_renderer stopped hardcoding it (211bcbf);
    -- a test that repeats the number just reintroduces the magic constant
    -- that change removed.
    local config = require("engine.config")
    assert(roster.visibleRows == config.MAX_RESERVE_SIZE,
        "expedition Reserve list must expose one row per reserve slot")
    assert(rosterList.listId == "reserve", "Reserve roster must read the canonical reserve source")
    -- The left cell is still pinned literally; the right cell is pinned by what
    -- it RENDERS (below), because its expression legitimately changed shape to
    -- suppress the level on empty rows. Asserting its source text here is what
    -- made a correct fix look like a regression.
    assert(rosterList.format == "{name}",
        "Reserve rows must use the shared name list vocabulary")
    assert(rosterList.highlight and rosterList.highlight:find("swapSemanticSourceIndex", 1, true),
        "Reserve swap source must be represented by a list-row highlight")

    -- An empty slot must not advertise a level. `Lv.{level}` printed "Lv.0" on
    -- every empty row, because empty rows carry only { index, empty, name }.
    -- Both branches are pinned here through the engine's own evaluator: no
    -- golden frame covers a POPULATED reserve row, so nothing else would catch
    -- the inverse regression of blanking a real creature's level.
    local formula = require("engine.formula")
    local expr = rosterList.formatRight:match("^{(.*)}$")
    assert(expr, "the reserve row's level cell must be one {expr} covering the "
        .. "whole cell, so an empty row can render nothing. A literal prefix "
        .. "outside the braces (\"Lv.{level}\") always prints, which is what "
        .. "put \"Lv.0\" on every empty row.")
    assert(formula.eval(expr, { empty = true, name = "--Empty--" }) == "",
        "an empty reserve row must render no level")
    assert(formula.eval(expr, { level = 7, name = "Saban" }) == "Lv.7",
        "a populated reserve row must still render its level")

    local scripts = reserve.scripts or {}
    local up = assert(scripts.navigateReserveUp, "Reserve up-navigation script missing")
    local down = assert(scripts.navigateReserveDown, "Reserve down-navigation script missing")
    assert(up:find("v.cursorIdx > 1", 1, true) and up:find("v.cursorIdx = v.cursorIdx - 1", 1, true),
        "Reserve Up must move one list row at a time")
    assert(down:find("v.cursorIdx < 4", 1, true) and down:find("v.cursorIdx = v.cursorIdx + 1", 1, true),
        "Reserve Down must move one list row at a time")

    -- NOTE: the assertions below match authored SCRIPT source text, so
    -- reformatting a script breaks them while behavior is unchanged. The
    -- right fix is a behavioral test driving these hooks through the real
    -- interpreter -- NOT a mock script runner here, which would be a second
    -- implementation of something the engine already does (SPEC: one
    -- implementation, never an approximation). Tracked as its own issue.
    local popup = assert(scripts.executeReservePopup, "Reserve popup script missing")
    assert(popup:find("v.swapSemanticSourceIndex = v.popupTargetIndex", 1, true),
        "swap gameplay source must be stored independently from presentation")
    assert(popup:find("v.swapSourceIndex = v.popupTargetIsReserve and nil or v.popupTargetIndex", 1, true),
        "Reserve-origin swaps must not feed the legacy grid ghost coordinate path")
    local swap = assert(scripts.executeSwap, "Reserve swap script missing")
    assert(swap:find("v.swapSemanticSourceIndex or v.swapSourceIndex", 1, true),
        "swap execution must consume the semantic source index")

    -- Recruitment established the vocabulary #145 is standardizing on. Keep
    -- the dedicated Reserve screen and recruitment placement surface aligned.
    local recruit = assert(loader.getScene("recruit"), "recruit scene missing")
    local recruitRoster = assert(findWindow(recruit, "reserve_roster"),
        "recruitment Reserve list missing")
    local recruitList = assert(firstList(recruitRoster), "recruitment Reserve list content missing")
    assert(recruitRoster.style == "list", "recruitment Reserve surface regressed to a grid")
    assert(recruitList.format == rosterList.format and recruitList.formatRight == rosterList.formatRight,
        "Reserve row vocabulary drifted between recruitment and management")

    print("  [PASS] Reserve roster uses list navigation and list-row swap pickup semantics")
end
