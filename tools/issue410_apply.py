#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text, encoding="utf-8")


def replace_once(rel: str, old: str, new: str) -> None:
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{rel}: expected exactly one replacement target, found {count}: {old[:80]!r}")
    write(rel, text.replace(old, new, 1))


def sub_once(rel: str, pattern: str, repl: str) -> None:
    text = read(rel)
    text, count = re.subn(pattern, repl, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{rel}: expected exactly one regex target for {pattern!r}, found {count}")
    write(rel, text)


# ---------------------------------------------------------------------------
# Formula: explicit owner nouns while keeping v as a temporary compatibility
# surface until the corpus migration retires it.
# ---------------------------------------------------------------------------
formula_make_context = '''-- Assemble an evaluation context. opts fields (all optional): a, b, target,
-- enemy, ally (battlers), party, enemies (battler lists), session, battle
-- ({ round = n }), locals (process/invocation scratch), sceneState
-- (one pushed Scene instance), and v (legacy compatibility only). session is
-- also used to resolve params through traits and to pull the combat config.
function formula.makeContext(opts, session)
    opts = opts or {}
    session = session or opts.session
    local ctx = {}
    for _, key in ipairs({ "a", "b", "target", "enemy", "ally" }) do
        if opts[key] then ctx[key] = formula.battlerView(opts[key], session) end
    end
    local partyList = opts.party or (session and session.party)
    if partyList then ctx.party = formula.groupView(partyList, session) end
    if opts.enemies then ctx.enemies = formula.groupView(opts.enemies, session) end
    if session then
        -- During the #410 migration old Scenes still author through v. New
        -- Scenes read sceneState. Both point at the same Scene owner in
        -- scene_host, so session-derived helpers (itemCount/tab filtering)
        -- consult the explicit owner first and the compatibility table second.
        ctx.session = formula.sessionView(session, opts.sceneState or opts.v)
        -- Persistent playthrough Variables are a dedicated read-only Formula
        -- noun. This is a deep copy, so a Formula can never obtain the live
        -- authored store even if the sandbox grows richer expression helpers.
        ctx.variables = game_variables.snapshot(session)
        local sys = session.loader and session.loader.system
        ctx.combat = sys and sys.combat or nil
    end
    ctx.battle = opts.battle
    ctx.locals = opts.locals
    ctx.sceneState = opts.sceneState
    ctx.v = opts.v
    -- Domain hosts publish sanitized facts as invocation locals. Keep the v
    -- fallback only until the legacy authored corpus is migrated.
    ctx.event = opts.event or (opts.locals and opts.locals.event)
        or (opts.v and opts.v.event) or nil
    -- Persistent placed-Event gameplay state is exposed only through the
    -- sanitized SELF view supplied by the Event host; Formula never receives
    -- the live session storage bucket.
    ctx.self = opts.self or nil
    -- #386 fixed Scene timing is context, not authored state. scene_host still
    -- bridges it through the Scene table during migration; the explicit noun
    -- wins whenever supplied directly.
    ctx.time = opts.time or (opts.sceneState and opts.sceneState.time)
        or (opts.v and opts.v.time) or nil
    if opts.ingredient1 then ctx.ingredient1 = formula.itemView(opts.ingredient1) end
    if opts.ingredient2 then ctx.ingredient2 = formula.itemView(opts.ingredient2) end
    return ctx
end

local function evaluateExpression'''
sub_once(
    "runtime/engine/formula.lua",
    r"-- Assemble an evaluation context\..*?function formula\.makeContext\(opts, session\).*?\nend\n\nlocal function evaluateExpression",
    formula_make_context,
)

# ---------------------------------------------------------------------------
# Interpreter: explicit SET_LOCAL / SET_SCENE_STATE semantics. SET_VAR remains
# unchanged in behaviour as migration compatibility; new code has no need to
# infer an owner from the host.
# ---------------------------------------------------------------------------
replace_once(
    "runtime/engine/interpreter.lua",
    '''        battle = ctx.battle and { round = ctx.battle.round } or nil,
        v = ctx.v,
        self = event_self_state.formulaView(ctx.session, ctx.event),''',
    '''        battle = ctx.battle and { round = ctx.battle.round } or nil,
        locals = ctx.locals,
        sceneState = ctx.sceneState,
        v = ctx.v,
        event = ctx.event,
        self = event_self_state.formulaView(ctx.session, ctx.event),''',
)

set_state_handlers = '''local function assignFormulaRows(cmd, target, ctx)
    if type(cmd.assignments) == "table" and #cmd.assignments > 0 then
        for _, a in ipairs(cmd.assignments) do
            if type(a) == "table" and a.name then
                target[a.name] = evalFormula(a.value, ctx)
            end
        end
        return
    end
    target[cmd.name] = evalFormula(cmd.value, ctx)
end

handlers.SET_LOCAL = function(cmd, ctx)
    ctx.locals = ctx.locals or {}
    assignFormulaRows(cmd, ctx.locals, ctx)
end

handlers.SET_SCENE_STATE = function(cmd, ctx)
    if type(ctx.sceneState) ~= "table" then
        error("SET_SCENE_STATE requires a Scene-owned state context", 0)
    end
    assignFormulaRows(cmd, ctx.sceneState, ctx)
end

handlers.SET_VAR = function(cmd, ctx)
    -- Legacy #410 migration surface. Its owner is still inferred from the host:
    -- Scene hooks bind v to Scene state; other immediate hosts bind it to
    -- invocation locals. New authored content must use SET_SCENE_STATE or
    -- SET_LOCAL so lifetime is explicit in data.
    assignFormulaRows(cmd, ctx.v, ctx)
end

handlers.MUTATE_TILE'''
sub_once(
    "runtime/engine/interpreter.lua",
    r"handlers\.SET_VAR = function\(cmd, ctx\).*?\nend\n\nhandlers\.MUTATE_TILE",
    set_state_handlers,
)

replace_once(
    "runtime/engine/interpreter.lua",
    '''        target = ctx.target or ctx.b,
        v = ctx.v,
        -- Scene hooks expose the scene's config as read-only-by-convention''',
    '''        target = ctx.target or ctx.b,
        locals = ctx.locals,
        sceneState = ctx.sceneState,
        v = ctx.v,
        -- Scene hooks expose the scene's config as read-only-by-convention''',
)

replace_once(
    "runtime/engine/interpreter.lua",
    '''    ctx.events = ctx.events or {}
    ctx.v = ctx.v or {}
    if ctx.battle then''',
    '''    ctx.events = ctx.events or {}
    -- Explicit process locals. Legacy immediate callers that still seed v
    -- (notably lifecycle event facts) keep one shared table during migration;
    -- Scene hosts supply a distinct locals table before entering here.
    ctx.locals = ctx.locals or ctx.v or {}
    ctx.v = ctx.v or ctx.locals
    if ctx.battle then''',
)

# ---------------------------------------------------------------------------
# Scene host: Scene state and invocation locals are separate even though v
# temporarily aliases Scene state for the un-migrated corpus.
# ---------------------------------------------------------------------------
replace_once(
    "runtime/engine/scene_host.lua",
    '''    -- We have a hook, execute it in immediate mode
    -- Ensure ctx.v is scoped to the scene instance
    ctx.v = state.v
''',
    '''    -- We have a hook, execute it in immediate mode. The Scene instance
    -- owns sceneState across hooks; locals are fresh for this invocation.
    -- v remains a temporary alias to Scene state only for the #410 corpus
    -- migration and is removed with SET_VAR in the follow-up slice.
    ctx.sceneState = state.v
    ctx.locals = {}
    ctx.v = state.v
''',
)

# ---------------------------------------------------------------------------
# Validator: seed and validate the three authored namespaces independently.
# Legacy SET_VAR is mirrored into both possible owners so the existing corpus
# remains valid during the substrate PR; explicit commands are owner-strict.
# ---------------------------------------------------------------------------
replace_once(
    "runtime/engine/validator_rules.lua",
    '''        local v = {}
        for k, val in pairs(HOST_SEEDED_VARS) do v[k] = val end
        for k, val in pairs(seedVars or {}) do v[k] = val end
        return {''',
    '''        local v, locals, sceneState = {}, {}, {}
        for k, val in pairs(HOST_SEEDED_VARS) do v[k] = val end
        local legacySeeds = seedVars and (seedVars.v or seedVars) or {}
        local localSeeds = seedVars and seedVars.locals or {}
        local sceneSeeds = seedVars and seedVars.sceneState or {}
        for k, val in pairs(legacySeeds) do v[k] = val end
        for k, val in pairs(localSeeds) do locals[k] = val end
        for k, val in pairs(sceneSeeds) do sceneState[k] = val end
        return {''',
)

replace_once(
    "runtime/engine/validator_rules.lua",
    '''                        v = v,
                        -- SELF is owner-scoped at runtime.''',
    '''                        v = v,
                        locals = locals,
                        sceneState = sceneState,
                        -- SELF is owner-scoped at runtime.''',
)

collect_script = '''local function collectScriptAssignedVars(text, out)
        if type(text) ~= "string" then return out end
        local function add(name, prefix)
            table.insert(out, { name = (prefix or "") .. name })
        end
        -- Legacy SCRIPT code commonly aliases ctx.v as local v. Until that
        -- corpus migrates, seed all possible owners for those assignments.
        for name in text:gmatch("v%.([%a_][%w_]*)%s*=[^=]") do
            add(name); add(name, "locals:"); add(name, "sceneState:")
        end
        for name in text:gmatch("ctx%.locals%.([%a_][%w_]*)%s*=[^=]") do
            add(name, "locals:")
        end
        for name in text:gmatch("ctx%.sceneState%.([%a_][%w_]*)%s*=[^=]") do
            add(name, "sceneState:")
        end
        return out
    end

    -- Pre-scan:'''
sub_once(
    "runtime/engine/validator_rules.lua",
    r"local function collectScriptAssignedVars\(text, out\).*?\n    end\n\n    -- Pre-scan:",
    collect_script,
)

collect_assigned = '''local function collectAssignedVars(cmds, out)
        out = out or {}
        local function add(target, name, value)
            if type(name) == "string" and name ~= "" then
                table.insert(out, { name = (target or "") .. name, value = value })
            end
        end
        for _, cmd in ipairs(cmds or {}) do
            if type(cmd) == "table" then
                if cmd.cmd == "SET_VAR" or cmd.cmd == "SET_LOCAL" or cmd.cmd == "SET_SCENE_STATE" then
                    local target = cmd.cmd == "SET_LOCAL" and "locals:"
                        or (cmd.cmd == "SET_SCENE_STATE" and "sceneState:" or "")
                    add(target, cmd.name, cmd.value)
                    for _, a in ipairs(cmd.assignments or {}) do
                        if type(a) == "table" then add(target, a.name, a.value) end
                    end
                    -- Legacy SET_VAR is host-owned. Mirror it into both
                    -- candidate owners only during migration; explicit command
                    -- ids never receive this compatibility treatment.
                    if cmd.cmd == "SET_VAR" then
                        add("locals:", cmd.name, cmd.value)
                        add("sceneState:", cmd.name, cmd.value)
                        for _, a in ipairs(cmd.assignments or {}) do
                            if type(a) == "table" then
                                add("locals:", a.name, a.value)
                                add("sceneState:", a.name, a.value)
                            end
                        end
                    end
                elseif cmd.cmd == "SCRIPT" then
                    collectScriptAssignedVars(cmd.code, out)
                end
                for key, val in pairs(cmd) do
                    if type(val) == "table" and key ~= "assignments" and key ~= "vars" then
                        collectAssignedVars(val, out)
                    end
                end
            end
        end
        return out
    end

    -- Shape hint'''
sub_once(
    "runtime/engine/validator_rules.lua",
    r"local function collectAssignedVars\(cmds, out\).*?\n    end\n\n    -- Shape hint",
    collect_assigned,
)

collect_shapes = '''local function collectTableShapedVars(node, out, seen)
        out = out or {}
        local function mark(prefix, name)
            out[(prefix or "") .. name] = true
        end
        if type(node) == "string" then
            local function scan(prefix, noun)
                for name in node:gmatch("#%s*" .. noun .. "%.([%a_][%w_]*)") do mark(prefix, name) end
                for name in node:gmatch(noun .. "%.([%a_][%w_]*)%s*%[") do mark(prefix, name) end
                for name in node:gmatch(noun .. "%.([%a_][%w_]*)%.") do mark(prefix, name) end
            end
            scan("", "v")
            scan("locals:", "locals")
            scan("sceneState:", "sceneState")
            -- Legacy v may represent either owner during the migration.
            for name in node:gmatch("v%.([%a_][%w_]*)") do
                mark("locals:", name); mark("sceneState:", name)
            end
            return out
        end
        if type(node) ~= "table" then return out end
        seen = seen or {}
        if seen[node] then return out end
        seen[node] = true
        for _, val in pairs(node) do collectTableShapedVars(val, out, seen) end
        return out
    end

    -- Stand-in'''
sub_once(
    "runtime/engine/validator_rules.lua",
    r"local function collectTableShapedVars\(node, out, seen\).*?\n    end\n\n    -- Stand-in",
    collect_shapes,
)

resolve_seeds = '''local function resolveSeedVars(assigned, tableShaped)
        local formulaEngine = require("engine.formula")
        local ctx = buildFormulaMockCtx({ v = {}, locals = {}, sceneState = {} })
        local function ownerFor(encoded)
            local name = encoded
            local target = ctx.v
            if encoded:sub(1, 7) == "locals:" then
                name = encoded:sub(8); target = ctx.locals
            elseif encoded:sub(1, 11) == "sceneState:" then
                name = encoded:sub(12); target = ctx.sceneState
            end
            return target, name
        end
        -- Seeding evaluates speculatively, so mute formula warnings here; a
        -- formula that still fails its own check reports through check().
        local realPrint = print
        print = function() end
        for _ = 1, 2 do
            for _, a in ipairs(assigned) do
                local target, name = ownerFor(a.name)
                if target[name] == nil then
                    if type(a.value) == "string" then
                        local ok, result, ferr = pcall(formulaEngine.eval, a.value, ctx)
                        if ok and ferr == nil then target[name] = result end
                    elseif a.value ~= nil then
                        target[name] = a.value
                    end
                end
            end
        end
        print = realPrint
        for _, a in ipairs(assigned) do
            local target, name = ownerFor(a.name)
            if target[name] == nil then
                target[name] = (tableShaped or {})[a.name] and mockTableValue() or 1
            end
        end
        return { v = ctx.v, locals = ctx.locals, sceneState = ctx.sceneState }
    end

    local function seedVarsFor'''
sub_once(
    "runtime/engine/validator_rules.lua",
    r"local function resolveSeedVars\(assigned, tableShaped\).*?\n    end\n\n    local function seedVarsFor",
    resolve_seeds,
)

replace_once(
    "runtime/engine/validator_rules.lua",
    '''        for _, a in ipairs(pushedVars or {}) do table.insert(assigned, a) end
        collectAssignedVars(cmds, assigned)''',
    '''        for _, a in ipairs(pushedVars or {}) do
            table.insert(assigned, a)
            table.insert(assigned, { name = "sceneState:" .. a.name, value = a.value })
        end
        collectAssignedVars(cmds, assigned)''',
)

replace_once(
    "runtime/engine/validator_rules.lua",
    '''                        local formulaEngine = require("engine.formula")
                        local mockCtx = buildFormulaMockCtx(seedVars)
                        for ai, a in ipairs(val) do''',
    '''                        local formulaEngine = require("engine.formula")
                        local mockCtx = buildFormulaMockCtx(seedVars)
                        local assignmentTarget = id == "SET_LOCAL" and mockCtx.locals
                            or (id == "SET_SCENE_STATE" and mockCtx.sceneState or mockCtx.v)
                        for ai, a in ipairs(val) do''',
)

replace_once(
    "runtime/engine/validator_rules.lua",
    '''                                    if ok and result ~= nil then mockCtx.v[a.name] = result
                                    else mockCtx.v[a.name] = 1 end''',
    '''                                    local assignedValue = (ok and result ~= nil) and result or 1
                                    assignmentTarget[a.name] = assignedValue
                                    if id == "SET_VAR" then
                                        -- Compatibility only: old SET_VAR can
                                        -- still mean either owner until PR 2.
                                        mockCtx.locals[a.name] = assignedValue
                                        mockCtx.sceneState[a.name] = assignedValue
                                    end''',
)

# ---------------------------------------------------------------------------
# Registry: explicit commands and help nouns. Copy SET_VAR's authoring shape so
# Studio gets the same multi-assignment ergonomics without a parallel editor.
# ---------------------------------------------------------------------------
engine_path = ROOT / "rtp/revisions/1.0/data/engine.json"
engine = json.loads(engine_path.read_text(encoding="utf-8"))
commands = engine.get("commands", [])
ids = [c.get("id") for c in commands]
if "SET_LOCAL" in ids or "SET_SCENE_STATE" in ids:
    raise SystemExit("engine.json already contains #410 command ids")
try:
    set_var_idx = ids.index("SET_VAR")
except ValueError as exc:
    raise SystemExit("engine.json has no SET_VAR registry entry") from exc
set_var = commands[set_var_idx]

set_local = copy.deepcopy(set_var)
set_local.update({
    "id": "SET_LOCAL",
    "category": "State",
    "label": "Set Local",
    "description": "Sets invocation/process-local scratch state. Read it as locals.<name>. It lasts only for the current immediate execution and is never saved.",
})
set_scene = copy.deepcopy(set_var)
set_scene.update({
    "id": "SET_SCENE_STATE",
    "category": "State",
    "label": "Set Scene State",
    "contexts": ["scene"],
    "description": "Sets transient state owned by the current pushed Scene instance. Read it as sceneState.<name>. It survives across that Scene's hooks but is not saved with the playthrough.",
})
commands[set_var_idx:set_var_idx] = [set_local, set_scene]

formula_help = engine.setdefault("formulaHelp", [])
formula_help[:] = [h for h in formula_help if h.get("token") not in {"locals", "sceneState"}]
v_idx = next((i for i, h in enumerate(formula_help) if h.get("token") == "v"), len(formula_help))
formula_help[v_idx:v_idx] = [
    {"token": "locals", "description": "Process/invocation-local scratch state authored with SET_LOCAL, e.g. locals.roll. Never persistent and not retained between independent immediate executions."},
    {"token": "sceneState", "description": "Transient state owned by the current pushed Scene instance and authored with SET_SCENE_STATE, e.g. sceneState.cursor. Survives across that Scene's hooks but is not saved."},
]
for h in formula_help:
    if h.get("token") == "v":
        h["description"] = "Legacy #410 compatibility namespace for SET_VAR. New content must use locals or sceneState so lifetime is explicit."

scripting_help = engine.setdefault("scriptingHelp", [])
scripting_help[:] = [h for h in scripting_help if h.get("token") not in {"ctx.locals", "ctx.sceneState"}]
ctx_v_idx = next((i for i, h in enumerate(scripting_help) if h.get("token") == "ctx.v"), len(scripting_help))
scripting_help[ctx_v_idx:ctx_v_idx] = [
    {"token": "ctx.locals", "description": "Current invocation/process-local scratch table; same owner exposed to formulas as locals."},
    {"token": "ctx.sceneState", "description": "Current pushed Scene's transient state table when SCRIPT runs in a Scene; same owner exposed to formulas as sceneState."},
]
for h in scripting_help:
    if h.get("token") == "ctx.v":
        h["description"] = "Legacy #410 compatibility table. New SCRIPT code should use ctx.locals or ctx.sceneState explicitly."

engine_path.write_text(json.dumps(engine, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# ---------------------------------------------------------------------------
# Studio: SET_VAR has a bespoke multi-assignment renderer. Reuse it for the two
# owner-explicit commands rather than inventing a second editor language.
# ---------------------------------------------------------------------------
events_rel = "studio/editor/js/events.js"
events = read(events_rel)
replacements = 0
for old, new in [
    ("if (id === 'SET_VAR') {", "if (['SET_VAR', 'SET_LOCAL', 'SET_SCENE_STATE'].includes(id)) {"),
    ("if (cmdId(cmd) === 'SET_VAR') {", "if (['SET_VAR', 'SET_LOCAL', 'SET_SCENE_STATE'].includes(cmdId(cmd))) {"),
]:
    n = events.count(old)
    if n:
        events = events.replace(old, new)
        replacements += n
if replacements == 0:
    raise SystemExit("events.js: could not find SET_VAR bespoke editor branches")
events = events.replace("formula, e.g. v.a * 2", "formula, e.g. 1 + 2")
events = events.replace("Rows evaluate in order — later formulas can read earlier rows via v.",
                        "Rows evaluate in order — later formulas can read earlier rows through this command's state namespace.")
write(events_rel, events)

# ---------------------------------------------------------------------------
# Focused regression coverage in an already-registered unit suite.
# ---------------------------------------------------------------------------
test_rel = "tests/test_game_variables.lua"
test_text = read(test_rel)
marker = 'print(("=== Game Variable Tests: %d passed, %d failed ==="):format(passed, failed))'
if test_text.count(marker) != 1:
    raise SystemExit("test_game_variables.lua summary marker missing or duplicated")
new_tests = r'''

-- #410 owner-explicit transient state substrate. Local scratch and Scene state
-- are distinct Formula nouns; SET_SCENE_STATE must never silently fall back to
-- whichever table an arbitrary immediate host happened to provide.
local transientCtx = { session = restored, loader = loader, party = restored.party, events = {} }
interpreter.runImmediate({
    { cmd = "SET_LOCAL", assignments = {
        { name = "roll", value = 2 },
        { name = "scaled", value = "locals.roll + 3" },
    } },
}, transientCtx)
check(transientCtx.locals.roll == 2 and transientCtx.locals.scaled == 5,
    "SET_LOCAL owns in-order invocation scratch under locals")
check(transientCtx.v == transientCtx.locals,
    "legacy v aliases locals for non-Scene immediate callers during migration")

local sceneState = {}
local sceneCtx = {
    session = restored, loader = loader, party = restored.party, events = {},
    sceneState = sceneState, locals = {}, v = sceneState,
}
interpreter.runImmediate({
    { cmd = "SET_SCENE_STATE", assignments = {
        { name = "cursor", value = 1 },
        { name = "nextCursor", value = "sceneState.cursor + 1" },
    } },
    { cmd = "SET_LOCAL", name = "guard", value = 1 },
}, sceneCtx)
check(sceneState.cursor == 1 and sceneState.nextCursor == 2,
    "SET_SCENE_STATE mutates the Scene owner and supports in-order reads")
check(sceneCtx.locals.guard == 1 and sceneState.guard == nil,
    "Scene invocation locals do not leak into Scene state")
local noSceneOk = pcall(interpreter.runImmediate,
    { { cmd = "SET_SCENE_STATE", name = "bad", value = 1 } },
    { session = restored, loader = loader, events = {} })
check(not noSceneOk, "SET_SCENE_STATE fails loud without a Scene owner")

local ownerCtx = formula.makeContext({
    locals = { scratch = 4 },
    sceneState = { cursor = 2 },
}, restored)
local ownerValue, ownerErr = formula.eval("locals.scratch + sceneState.cursor", ownerCtx)
check(ownerErr == nil and ownerValue == 6,
    "Formula exposes locals and sceneState as distinct owner nouns")
'''
test_text = test_text.replace(marker, new_tests + "\n" + marker, 1)
write(test_rel, test_text)

print("issue #410 substrate patch applied")
