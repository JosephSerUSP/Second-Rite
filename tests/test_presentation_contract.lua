-- #967: the installation presentation contract is the ONE spelling of the
-- windowskin/target atlas geometry and the UI colour vocabulary, shared by the
-- LOVE renderer and the browser adapter (#968).
--
-- This suite is the negative control that makes that architecture enforceable
-- rather than advisory. Without it, an author can quietly reintroduce a
-- hardcoded quad or colour in presentation/ui.lua, the browser adapter keeps
-- consuming the contract, the two silently disagree, and every other gate
-- stays green because the runtime still renders exactly what it always did.
--
-- So it asserts two different things:
--   1. the contract is well formed and its reader is genuinely fail-loud;
--   2. presentation/ui.lua contains no literal spelling of a promoted fact.
-- (2) is a source-text check on purpose. A behavioural check cannot tell a
-- value that came from the contract apart from the same value typed inline.

local contract = require("presentation.presentation_contract")
local ui = require("presentation.ui")

local passed, failed = 0, 0
local function check(label, fn)
    local ok, err = pcall(fn)
    if ok then
        passed = passed + 1
        print("  [PASS] " .. label)
    else
        failed = failed + 1
        print("  [FAIL] " .. label .. ": " .. tostring(err))
    end
end

print("[TEST] Starting presentation contract tests...")

check("contract declares version 1 and the three fact groups", function()
    assert(contract.data.version == 1, "contract version must be 1")
    for _, group in ipairs({ "metrics", "atlas", "palettes" }) do
        assert(type(contract.data[group]) == "table", "contract is missing '" .. group .. "'")
    end
end)

check("every atlas rectangle is a positive-area integer rect", function()
    for _, atlasPath in ipairs({ "atlas.windowskin.parts", "atlas.target.parts" }) do
        local parts = contract.at(atlasPath)
        local seen = 0
        for key in pairs(parts) do
            if key:sub(1, 1) ~= "_" then
                local r = contract.rect(atlasPath .. "." .. key)
                assert(r[3] > 0 and r[4] > 0, atlasPath .. "." .. key .. " has zero area")
                seen = seen + 1
            end
        end
        assert(seen >= 8, atlasPath .. " must define at least the eight ring parts, saw " .. seen)
    end
end)

check("the windowskin ring covers its declared border thickness", function()
    -- The corners are square at the border thickness and the edges are that
    -- thick on their short axis. A contract whose parts disagree with its own
    -- `border` would draw a ring with a seam, so the numbers are checked
    -- against each other rather than trusted individually.
    local border = contract.number("atlas.windowskin.border")
    for _, corner in ipairs({ "tl", "tr", "bl", "br" }) do
        local r = contract.rect("atlas.windowskin.parts." .. corner)
        assert(r[3] == border and r[4] == border,
            "corner '" .. corner .. "' is not " .. border .. "x" .. border)
    end
    assert(contract.rect("atlas.windowskin.parts.top")[4] == border, "top edge is not border-thick")
    assert(contract.rect("atlas.windowskin.parts.bot")[4] == border, "bottom edge is not border-thick")
    assert(contract.rect("atlas.windowskin.parts.left")[3] == border, "left edge is not border-thick")
    assert(contract.rect("atlas.windowskin.parts.right")[3] == border, "right edge is not border-thick")
end)

check("the target ring covers its own declared border thickness", function()
    local border = contract.number("atlas.target.border")
    for _, corner in ipairs({ "tl", "tr", "bl", "br" }) do
        local r = contract.rect("atlas.target.parts." .. corner)
        assert(r[3] == border and r[4] == border,
            "target corner '" .. corner .. "' is not " .. border .. "x" .. border)
    end
end)

check("panel minimum geometry is one fact, not two", function()
    -- drawPanel bails below it and rescaleRect floors its opening rect at it.
    -- They were two independent literals before #967 and could drift apart.
    local minW = contract.number("metrics.panelMinWidth")
    local minH = contract.number("metrics.panelMinHeight")
    local _, _, w, h = ui.rescaleRect(0, 0, 200, 100, 0)
    assert(w == minW, "rescaleRect floors width at " .. w .. ", contract says " .. minW)
    assert(h == minH, "rescaleRect floors height at " .. h .. ", contract says " .. minH)
end)

check("exposed ui metrics come from the contract", function()
    assert(ui.tileSize == contract.number("metrics.tileSize"), "ui.tileSize drifted from the contract")
    assert(ui.lineHeight == ui.tileSize, "lineHeight must stay exactly one tile")
    assert(ui.screenWidthTiles == contract.number("metrics.screenWidthTiles"), "screenWidthTiles drifted")
    assert(ui.screenHeightTiles == contract.number("metrics.screenHeightTiles"), "screenHeightTiles drifted")
    assert(ui.gaugeHeight == contract.number("metrics.gaugeHeight"), "gaugeHeight drifted")
end)

check("exposed ui colour vocabulary comes from the contract", function()
    local function sameColor(actual, path)
        local expected = contract.color(path)
        assert(type(actual) == "table", path .. " is not exposed as a colour")
        assert(#actual == #expected, path .. " has the wrong component count")
        for i = 1, #expected do
            assert(actual[i] == expected[i], path .. " component " .. i .. " drifted")
        end
    end
    sameColor(ui.gaugeColors.hp.dark, "palettes.gauge.hp.dark")
    sameColor(ui.gaugeColors.hp.light, "palettes.gauge.hp.light")
    for _, key in ipairs({ "charges", "mp", "hp", "blocked" }) do
        sameColor(ui.costColors[key], "palettes.cost." .. key)
    end
    for _, key in ipairs({ "good", "bad", "neutral", "label" }) do
        sameColor(ui.toneColors[key], "palettes.tone." .. key)
    end
end)

check("mutating an exposed colour cannot corrupt the contract", function()
    -- The reader hands out fresh tables precisely so one careless consumer
    -- cannot repaint the vocabulary for every other consumer in the process.
    local first = contract.color("palettes.tone.good")
    first[1] = -999
    local second = contract.color("palettes.tone.good")
    assert(second[1] ~= -999, "contract.color returned shared state")
end)

check("the reader fails loudly on a missing or malformed fact", function()
    -- Fail-visible is the whole resource policy (#965 audit S5). A reader that
    -- returns nil for an absent fact would let a typo render as black or as
    -- nothing at all, which is the failure mode the audit rejects.
    assert(not pcall(contract.number, "metrics.thisKeyDoesNotExist"),
        "a missing key must raise, not return nil")
    assert(not pcall(contract.number, "palettes.tone.good"),
        "asking for a colour as a number must raise")
    assert(not pcall(contract.color, "metrics.tileSize"),
        "asking for a number as a colour must raise")
    assert(not pcall(contract.rect, "metrics"),
        "asking for a non-rectangle as a rectangle must raise")
end)

check("presentation/ui.lua spells no promoted fact as a literal", function()
    local source = love.filesystem.read("presentation/ui.lua")
    assert(source, "could not read presentation/ui.lua to audit it")

    -- Every atlas rectangle, as it would be typed into love.graphics.newQuad.
    -- A quad built from four contract numbers never produces this text, so a
    -- hit is a reintroduced literal and nothing else.
    local function scanRects(path)
        local parts = contract.at(path)
        for key in pairs(parts) do
            if key:sub(1, 1) ~= "_" then
                local r = contract.rect(path .. "." .. key)
                local literal = string.format("newQuad(%d, %d, %d, %d", r[1], r[2], r[3], r[4])
                assert(not source:find(literal, 1, true),
                    "presentation/ui.lua reintroduced the atlas literal '" .. literal
                    .. "'; it belongs to presentation/presentation.json (#967)")
            end
        end
    end
    scanRects("atlas.windowskin.parts")
    scanRects("atlas.target.parts")

    -- Every promoted colour, in the `{ r, g, b, a }` form ui.lua used to spell.
    local colorPaths = {
        "palettes.gauge.hp.dark", "palettes.gauge.hp.light",
        "palettes.cost.charges", "palettes.cost.mp", "palettes.cost.hp", "palettes.cost.blocked",
        "palettes.tone.good", "palettes.tone.bad", "palettes.tone.neutral", "palettes.tone.label",
        "palettes.chrome.panelTitle", "palettes.chrome.selected", "palettes.chrome.dim",
        "palettes.chrome.textShadow",
    }
    for _, path in ipairs(colorPaths) do
        local c = contract.color(path)
        local pieces = {}
        for i = 1, #c do
            -- Match the two spellings a Lua author actually writes: `0.42` and
            -- `1`. `%.2f` on 1 would be `1.00`, which nobody types.
            pieces[i] = (c[i] == math.floor(c[i])) and tostring(math.floor(c[i]))
                or tostring(c[i]):gsub("0+$", ""):gsub("%.$", "")
        end
        local literal = "{ " .. table.concat(pieces, ", ") .. " }"
        assert(not source:find(literal, 1, true),
            "presentation/ui.lua reintroduced the colour literal '" .. literal
            .. "' for " .. path .. "; it belongs to presentation/presentation.json (#967)")
    end
end)

require("tests.fail_fast")("test_presentation_contract", failed, passed)
