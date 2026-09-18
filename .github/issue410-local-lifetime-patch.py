from pathlib import Path

path = Path("runtime/engine/interpreter.lua")
text = path.read_text()
old = """    -- Explicit process locals. Legacy immediate callers that still seed v
    -- (notably lifecycle event facts) keep one shared table during migration;
    -- Scene hosts supply a distinct locals table before entering here.
    ctx.locals = ctx.locals or ctx.v or {}
    ctx.v = ctx.v or ctx.locals
"""
new = """    -- Explicit process locals are owned by one immediate invocation. The
    -- public runImmediate boundary refreshes them between independent runs;
    -- runImmediateCore only supplies a table for internal callers. Legacy v
    -- remains a separate compatibility namespace so its historical lifetime is
    -- not silently redefined by the new owner-explicit substrate.
    ctx.locals = ctx.locals or {}
    ctx.v = ctx.v or {}
"""
if old not in text:
    raise SystemExit("expected runImmediateCore locals block not found")
text = text.replace(old, new, 1)

old = """function interpreter.runImmediate(commands, ctx)
    ctx = ctx or {}
    local initialEventCount = #(ctx.events or {})
    local events = runImmediateCore(commands, ctx)
    local firstNew = initialEventCount + 1
    commitReaps(events, ctx.session, firstNew)
    publishUnstamped(events, ctx.session, firstNew)
    return events
end
"""
new = """function interpreter.runImmediate(commands, ctx)
    ctx = ctx or {}
    -- A reused host context must not accidentally extend process-local lifetime
    -- across two independent immediate executions. Keep the completed table on
    -- ctx for diagnostics after a run, but recognize and replace that exact
    -- table at the next invocation. Hosts may still provide a fresh locals
    -- table explicitly for the invocation they are starting (SceneHost does).
    if ctx._completedImmediateLocals ~= nil
        and ctx.locals == ctx._completedImmediateLocals then
        ctx.locals = nil
    end
    local initialEventCount = #(ctx.events or {})
    local events = runImmediateCore(commands, ctx)
    ctx._completedImmediateLocals = ctx.locals
    local firstNew = initialEventCount + 1
    commitReaps(events, ctx.session, firstNew)
    publishUnstamped(events, ctx.session, firstNew)
    return events
end
"""
if old not in text:
    raise SystemExit("expected runImmediate wrapper not found")
path.write_text(text.replace(old, new, 1))

path = Path("tests/test_game_variables.lua")
text = path.read_text()
old = """check(transientCtx.locals.roll == 2 and transientCtx.locals.scaled == 5,
    \"SET_LOCAL owns in-order invocation scratch under locals\")
check(transientCtx.v == transientCtx.locals,
    \"legacy v aliases locals for non-Scene immediate callers during migration\")

local sceneState = {}
"""
new = """check(transientCtx.locals.roll == 2 and transientCtx.locals.scaled == 5,
    \"SET_LOCAL owns in-order invocation scratch under locals\")
check(transientCtx.v ~= transientCtx.locals and transientCtx.v.roll == nil,
    \"new process locals stay distinct from the legacy v compatibility namespace\")
local firstInvocationLocals = transientCtx.locals
interpreter.runImmediate({
    { cmd = \"SET_LOCAL\", name = \"fresh\", value = \"locals.roll == nil and 1 or 0\" },
}, transientCtx)
check(transientCtx.locals ~= firstInvocationLocals
        and transientCtx.locals.roll == nil and transientCtx.locals.fresh == 1,
    \"independent immediate executions receive fresh process-local state\")

local sceneState = {}
"""
if old not in text:
    raise SystemExit("expected transient-state regression block not found")
path.write_text(text.replace(old, new, 1))
