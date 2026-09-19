-- Options FONT entry: interpreter API that the authored scene hook calls,
-- and user_settings integration.
local interpreter = require("engine.interpreter")
local loader = require("engine.data.loader")
local session = require("engine.session")
local user_settings = require("engine.user_settings")

local function eq(actual, expected, label)
    assert(actual == expected, label .. ": expected " .. tostring(expected)
        .. ", got " .. tostring(actual))
end

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

print("[TEST] Starting font option tests...")

loader.init()
local vSession = session.GameSession.new(loader)
local function ctxFor()
    return { session = vSession, loader = loader, sceneState = {} }
end

local currentFont = "monogram-extended-italic"
local hostCalls = {}
local function bindFakeHost()
    interpreter.bindPresentation({
        setFont = function(name)
            currentFont = name
            hostCalls[#hostCalls + 1] = name
            return true
        end,
        getFont = function() return currentFont end,
        listFonts = function() return { "monogram-extended-italic", "monogram-extended" } end,
    })
end

user_settings.pinForCapture()

check("cycle walks monogram-extended-italic -> monogram-extended -> monogram-extended-italic", function()
    bindFakeHost()
    currentFont = "monogram-extended-italic"
    local ctx = ctxFor()
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.sceneState.font = api.cycleFont()" },
    }, ctx)
    eq(ctx.sceneState.font, "monogram-extended", "first cycle")
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.sceneState.font = api.cycleFont()" },
    }, ctx)
    eq(ctx.sceneState.font, "monogram-extended-italic", "second cycle wraps")
end)

check("getFont reports the active font", function()
    bindFakeHost()
    currentFont = "monogram-extended"
    local ctx = ctxFor()
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.sceneState.font = api.getFont()" },
    }, ctx)
    eq(ctx.sceneState.font, "monogram-extended", "reported font")
end)

check("setFont switches font and records call", function()
    bindFakeHost()
    currentFont = "monogram-extended-italic"
    local ctx = ctxFor()
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.sceneState.ok = api.setFont('monogram-extended')" },
    }, ctx)
    eq(ctx.sceneState.ok, true, "setFont succeeded")
    eq(currentFont, "monogram-extended", "font updated")
end)

check("headless run with no presentation bound degrades gracefully", function()
    interpreter.bindPresentation(nil)
    local ctx = ctxFor()
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.sceneState.font = api.getFont()" },
    }, ctx)
    eq(ctx.sceneState.font, "monogram-extended-italic", "headless default")
end)

user_settings.reset()
interpreter.bindPresentation(nil)
print("=== Font Option Tests: " .. passed .. " passed, " .. failed .. " failed ===")
assert(failed == 0, "font option tests had failures")
