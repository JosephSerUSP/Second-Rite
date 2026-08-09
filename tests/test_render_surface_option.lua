-- The Options ASPECT entry (#199 follow-up): the interpreter API that the
-- authored scene hook calls, and the precedence rule that decides which surface
-- a launch actually uses.
local surface = require("presentation.surface")
local interpreter = require("engine.interpreter")
local loader = require("data.loader")
local session = require("engine.session")

local function eq(actual, expected, label)
    assert(actual == expected, label .. ": expected " .. tostring(expected)
        .. ", got " .. tostring(actual))
end

local originalProfile = surface.getProfileId()
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

print("[TEST] Starting render surface option tests...")

loader.init()
local vSession = session.GameSession.new(loader)
local function ctxFor()
    return { session = vSession, loader = loader, v = {} }
end

-- A fake host, standing in for main.lua's presentation hooks. The real one
-- rebuilds the canvas; what matters to the engine is only that the profile
-- moves and the choice is reported back.
local hostCalls = {}
local function bindFakeHost()
    interpreter.bindPresentation({
        setRenderSurface = function(id)
            if not surface.getProfile(id) then return false end
            surface.setProfile(id)
            hostCalls[#hostCalls + 1] = id
            return true
        end,
        getRenderSurface = function() return surface.getProfileId() end,
        listRenderSurfaces = function() return surface.profileIds() end,
    })
end

check("cycle walks classic -> four_three -> wide -> classic", function()
    bindFakeHost()
    surface.setProfile("classic")
    -- Exercised through the same SCRIPT seam the options hook uses, rather
    -- than reaching into the per-context api table.
    local ctx = ctxFor()
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.v.aspect = api.cycleRenderSurface()" },
    }, ctx)
    eq(ctx.v.aspect, "four_three", "first cycle")
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.v.aspect = api.cycleRenderSurface()" },
    }, ctx)
    eq(ctx.v.aspect, "wide", "second cycle")
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.v.aspect = api.cycleRenderSurface()" },
    }, ctx)
    eq(ctx.v.aspect, "classic", "third cycle wraps")
end)

check("getRenderSurface reports the active profile", function()
    bindFakeHost()
    surface.setProfile("four_three")
    local ctx = ctxFor()
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.v.aspect = api.getRenderSurface()" },
    }, ctx)
    eq(ctx.v.aspect, "four_three", "reported profile")
end)

check("an unknown profile is refused, leaving the surface untouched", function()
    bindFakeHost()
    surface.setProfile("classic")
    local ctx = ctxFor()
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.v.ok = api.setRenderSurface('ultrawide')" },
    }, ctx)
    eq(ctx.v.ok, false, "refused")
    eq(surface.getProfileId(), "classic", "profile unchanged")
end)

-- Headless consumers (validator, golden harnesses) bind no presentation hooks.
-- The option must degrade to a no-op there rather than erroring, exactly like
-- the developer overlay toggles alongside it.
check("headless run with no presentation bound degrades to a no-op", function()
    interpreter.bindPresentation(nil)
    local ctx = ctxFor()
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.v.aspect = api.getRenderSurface()" },
    }, ctx)
    eq(ctx.v.aspect, "classic", "defaults to classic")
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.v.ok = api.setRenderSurface('wide')" },
    }, ctx)
    eq(ctx.v.ok, false, "set reports failure rather than erroring")
end)

check("user settings round-trip and survive a cache reset", function()
    local user_settings = require("engine.user_settings")
    user_settings.reset()
    local wrote = user_settings.set("renderSurfaceProfile", "four_three")
    if wrote then
        user_settings.reset()
        eq(user_settings.get("renderSurfaceProfile", "classic"), "four_three",
            "stored choice survives a reload")
        user_settings.set("renderSurfaceProfile", nil)
    else
        -- No writable filesystem in this harness; the contract is only that it
        -- reports failure instead of erroring.
        eq(wrote, false, "reports failure without a filesystem")
    end
end)

check("a missing stored setting falls back to the supplied default", function()
    local user_settings = require("engine.user_settings")
    user_settings.reset()
    eq(user_settings.get("thisKeyDoesNotExist", "fallback"), "fallback",
        "default returned")
end)

surface.setProfile(originalProfile)
interpreter.bindPresentation(nil)
print(string.format("=== Render Surface Option Tests: %d passed, %d failed ===",
    passed, failed))
if failed > 0 then
    require("tests.fail_fast")("render surface option tests failed", failed)
end
