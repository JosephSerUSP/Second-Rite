-- #237: the runtime must not depend on the development environment.
--
-- The direction that matters:
--
--     Editor  ->  runtime, and the opened project
--     Runtime ->  project
--     Project -X-> editor
--     Export  =   runtime + one project, and nothing from tools/
--
-- #221's manifest already stops editor files ENTERING a build. This stops the
-- other half: shipped runtime code reaching for something the build does not
-- contain. Such a require survives development (where the whole repository is
-- present) and fails only in an exported build -- exactly the release-only
-- class of bug the export boundary exists to eliminate, and one no gate that
-- runs inside the source tree can otherwise see.

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

print("[TEST] Starting runtime boundary tests...")

-- Every directory the runtime manifest declares shippable, plus the roots.
local RUNTIME_DIRS = { "engine", "presentation" }
local RUNTIME_ROOT_FILES = { "main.lua", "conf.lua" }

-- Modules a shipped build cannot contain, because the manifest never stages
-- them. Matching require("x.y") and require('x.y') alike.
local FORBIDDEN_PREFIXES = { "tools", "tests" }

-- The one declared exception. main.lua's `unittest` CLI branch loads the test
-- runner lazily, inside a branch a player build never enters; tests/ is absent
-- from a build, so the require is unreachable there. Declared rather than
-- silently skipped: if this list grows, that is a design decision someone has
-- to make deliberately.
local ALLOWED = {
    ["main.lua:tests.fail_fast"] = "unittest CLI mode; lazy require inside a dev-only branch",
}

local function luaFilesIn(dir, out)
    out = out or {}
    for _, name in ipairs(love.filesystem.getDirectoryItems(dir)) do
        local full = dir .. "/" .. name
        local info = love.filesystem.getInfo(full)
        if info and info.type == "directory" then
            luaFilesIn(full, out)
        elseif name:match("%.lua$") then
            out[#out + 1] = full
        end
    end
    return out
end

local function scan()
    local files = {}
    for _, name in ipairs(RUNTIME_ROOT_FILES) do
        if love.filesystem.getInfo(name) then files[#files + 1] = name end
    end
    for _, dir in ipairs(RUNTIME_DIRS) do
        if love.filesystem.getInfo(dir) then luaFilesIn(dir, files) end
    end
    return files
end

check("runtime code requires nothing from tools/ or tests/", function()
    local files = scan()
    assert(#files > 0, "scanned no runtime files at all -- the test is not looking where it thinks")
    local violations = {}
    for _, file in ipairs(files) do
        local source = love.filesystem.read(file)
        assert(source, "could not read " .. file)
        for quote in source:gmatch('require%s*%(?%s*["\']([%w_%.%-/]+)["\']') do
            local root = quote:match("^([%w_%-]+)")
            for _, forbidden in ipairs(FORBIDDEN_PREFIXES) do
                if root == forbidden then
                    local key = file .. ":" .. quote
                    if not ALLOWED[key] then
                        violations[#violations + 1] = key
                    end
                end
            end
        end
    end
    assert(#violations == 0,
        "runtime code depends on the development environment (absent from every export):\n    "
        .. table.concat(violations, "\n    "))
end)

-- #150 slice-1 ratchet. This is intentionally narrower than the eventual
-- engine -> presentation gate: engine/scenes/battle.lua is still owner-
-- supervised under #260. What has been made true here must not regress while
-- that last known seam is resolved.
check("scene_host has no direct presentation dependency", function()
    local source = love.filesystem.read("engine/scene_host.lua")
    assert(source, "could not read engine/scene_host.lua")
    local violations = {}
    for module in source:gmatch('require%s*%(?%s*["\']([%w_%.%-/]+)["\']') do
        if module:match("^presentation[%.%/]") then
            violations[#violations + 1] = module
        end
    end
    assert(#violations == 0,
        "scene_host depends directly on presentation again: " .. table.concat(violations, ", "))
end)

local function geometryPresentationViolations(source)
    local violations = {}
    for module in source:gmatch('require%s*%(?%s*["\']([%w_%.%-/]+)["\']') do
        if module:match("^presentation[%.%/]") then
            violations[#violations + 1] = "require:" .. module
        end
    end
    for call in source:gmatch("love%.graphics%.([%w_]+)%s*%(") do
        violations[#violations + 1] = "love.graphics." .. call
    end
    return violations
end

-- #282: geometry compilation is an engine concern; GPU upload and material
-- binding are presentation concerns. Scan the whole package rather than the
-- four files that happened to be leaking when the issue was opened so a new
-- topology cannot quietly reintroduce the same dependency under another name.
check("geometry boundary scanner detects a planted presentation dependency", function()
    local planted = [[
        local model = require("engine.geometry.model")
        local mesh = require("presentation.mesh")
        love.graphics.newMesh({}, {})
    ]]
    local found = geometryPresentationViolations(planted)
    assert(#found == 2,
        "geometry boundary scanner should flag planted require + graphics call, got " .. tostring(#found))
end)

check("engine geometry has no presentation or love.graphics dependency", function()
    local files = luaFilesIn("engine/geometry", {})
    assert(#files > 0, "scanned no engine/geometry Lua files")
    local violations = {}
    for _, file in ipairs(files) do
        local source = love.filesystem.read(file)
        assert(source, "could not read " .. file)
        for _, found in ipairs(geometryPresentationViolations(source)) do
            violations[#violations + 1] = file .. ":" .. found
        end
    end
    assert(#violations == 0,
        "engine geometry crossed upward into presentation/GPU finalization:\n    "
        .. table.concat(violations, "\n    "))
end)

check("neutral geometry builder output is deterministic and inspectable", function()
    local neutral = require("engine.geometry.model")
    local function build()
        local builder = neutral.newBuilder("boundary fixture")
        builder:setMaterial("stone")
        builder:triangle(
            { 0, 0, 0, 0, 0 },
            { 1, 0, 0, 1, 0 },
            { 0, 1, 0, 0, 1 })
        builder:setMaterial("glass")
        builder:triangle(
            { -2, 0, 3, 0, 0, 0, 0, 1, 0.25, 0.5, 0.75, 0.5 },
            { -1, 0, 3, 1, 0, 0, 0, 1, 0.25, 0.5, 0.75, 0.5 },
            { -2, 1, 3, 0, 1, 0, 0, 1, 0.25, 0.5, 0.75, 0.5 })
        return builder:build()
    end
    local a, b = build(), build()
    local function encode(model)
        local out = { tostring(model.vertexCount) }
        local bounds = model.bounds
        for _, key in ipairs({ "minX", "minY", "minZ", "maxX", "maxY", "maxZ" }) do
            out[#out + 1] = string.format("%.17g", bounds[key])
        end
        for _, group in ipairs(model.groups) do
            out[#out + 1] = group.material
            for _, vertex in ipairs(group.vertices) do
                for index = 1, 12 do
                    out[#out + 1] = string.format("%.17g", vertex[index])
                end
            end
        end
        return table.concat(out, "|")
    end
    assert(encode(a) == encode(b), "identical builder inputs produced different CPU models")
    assert(a.vertexCount == 6 and #a.groups == 2,
        "builder did not preserve triangle count/material grouping")
    assert(a.groups[1].material == "stone" and a.groups[2].material == "glass",
        "material group order changed")
    assert(a.bounds.minX == -2 and a.bounds.minY == 0 and a.bounds.minZ == 0
        and a.bounds.maxX == 1 and a.bounds.maxY == 1 and a.bounds.maxZ == 3,
        "builder bounds changed")
    local generated = a.groups[1].vertices[1]
    assert(generated[6] == 0 and generated[7] == 0 and generated[8] == 1,
        "generated face normal changed")
    local authored = a.groups[2].vertices[1]
    assert(authored[6] == 0 and authored[7] == 0 and authored[8] == 1
        and authored[9] == 0.25 and authored[12] == 0.5,
        "authored normal/color payload changed")
    assert(a.groups[1].mesh == nil and a.groups[1].texture == nil,
        "neutral builder unexpectedly attached presentation state")
end)

-- Preserve the semantic ordering that the current one-slot transition manager
-- consumes. This is deliberately not a claim that exit-then-enter replacement
-- is the best future visual policy; it makes the existing fact observable so a
-- later queue/crossfade change is explicit rather than an accidental #150 diff.
check("scene goto publishes exit then enter transition facts", function()
    local scene_host = require("engine.scene_host")
    local seen = {}
    local previous = scene_host.bindPresentation({
        transition = function(event)
            seen[#seen + 1] = {
                kind = event.kind, effect = event.effect,
                duration = event.duration, color = event.color,
            }
        end,
    })
    local ok, err = pcall(function()
        local ctx = {
            loader = {
                scenes = {
                    { id = "from", anim = { exit = { effect = "fadeOut", duration = 0.3 } } },
                    { id = "to", anim = { enter = { effect = "fadeIn", duration = 0.4 } } },
                },
            },
        }
        scene_host.init(nil)
        scene_host.push("from", ctx)
        scene_host.goto_scene("to", ctx)
        assert(#seen == 2, "goto should publish exactly exit + enter, got " .. tostring(#seen))
        assert(seen[1].kind == "exit" and seen[1].effect == "fadeOut"
            and seen[1].duration == 0.3, "first transition fact is not authored exit")
        assert(seen[2].kind == "enter" and seen[2].effect == "fadeIn"
            and seen[2].duration == 0.4, "second transition fact is not authored enter")
    end)
    scene_host.bindPresentation(previous)
    scene_host.init(nil)
    if not ok then error(err, 0) end
end)

-- #150 final explicit-context ratchet. Slice 2A first made ordinary main.lua
-- mutations explicit while battle remained owner-supervised. The owner-approved
-- final slice removes that last exception, so the rule can now scan every
-- shipped engine Lua file rather than merely the entrypoint.
local function contextlessSceneMutations(source)
    local violations = {}

    local function scan(method, needsSecondArg)
        local pattern = "scene_host%." .. method .. "%s*%("
        local from = 1
        while true do
            local startPos, openEnd = source:find(pattern, from)
            if not startPos then break end
            local i = openEnd + 1
            local depth = 1
            local quote = nil
            local escaped = false
            local topComma = false
            local hasArg = false

            while i <= #source and depth > 0 do
                local ch = source:sub(i, i)
                if quote then
                    if escaped then
                        escaped = false
                    elseif ch == "\\" then
                        escaped = true
                    elseif ch == quote then
                        quote = nil
                    end
                elseif ch == '"' or ch == "'" then
                    quote = ch
                    if depth == 1 then hasArg = true end
                elseif ch == "(" then
                    depth = depth + 1
                    if depth == 2 then hasArg = true end
                elseif ch == ")" then
                    depth = depth - 1
                elseif ch == "," and depth == 1 then
                    topComma = true
                elseif depth == 1 and not ch:match("%s") then
                    hasArg = true
                end
                i = i + 1
            end

            assert(depth == 0, "unterminated scene_host." .. method .. " call in source scanner")
            local contextless = needsSecondArg and not topComma or (not needsSecondArg and not hasArg)
            if contextless then
                violations[#violations + 1] = method .. "@" .. tostring(startPos)
            end
            from = i
        end
    end

    scan("push", true)
    scan("goto_scene", true)
    scan("pop", false)
    return violations
end

check("scene mutation scanner detects omitted contexts (negative control)", function()
    local planted = [[
        scene_host.goto_scene("map")
        scene_host.push("menu")
        scene_host.pop()
    ]]
    local found = contextlessSceneMutations(planted)
    assert(#found == 3,
        "scene mutation scanner should flag planted goto+push+pop omissions, got " .. tostring(#found))
end)

check("shipped runtime scene mutations carry explicit context", function()
    local files = { "main.lua" }
    luaFilesIn("engine", files)
    local violations = {}
    for _, file in ipairs(files) do
        local source = love.filesystem.read(file)
        assert(source, "could not read " .. file)
        for _, found in ipairs(contextlessSceneMutations(source)) do
            violations[#violations + 1] = file .. ":" .. found
        end
    end
    assert(#violations == 0,
        "runtime contains contextless scene mutations: " .. table.concat(violations, ", "))
end)

check("main has no currentScene compatibility surface", function()
    local source = love.filesystem.read("main.lua")
    assert(source, "could not read main.lua")
    assert(not source:find("currentScene", 1, true),
        "main.lua reintroduced the writable currentScene compatibility surface")
end)

check("scene_host has no remembered-context compatibility fallback", function()
    local source = love.filesystem.read("engine/scene_host.lua")
    assert(source, "could not read engine/scene_host.lua")
    assert(not source:find("lastCtx", 1, true),
        "scene_host reintroduced lastCtx remembered-context fallback")
    assert(not source:find("rememberCtx", 1, true),
        "scene_host reintroduced rememberCtx compatibility API")
    assert(not source:find("ctx = ctx or", 1, true),
        "scene_host silently substitutes an implicit context again")
end)

-- A gate that cannot fail proves nothing. This asserts the scanner actually
-- sees a forbidden require rather than passing because its pattern is wrong --
-- the failure mode that makes a green boundary gate worthless.
check("the scanner detects a forbidden require (negative control)", function()
    local sample = [[
        local ok = require("engine.session")
        local bad = require("tools.editor.server")
    ]]
    local found = {}
    for quote in sample:gmatch('require%s*%(?%s*["\']([%w_%.%-/]+)["\']') do
        local root = quote:match("^([%w_%-]+)")
        for _, forbidden in ipairs(FORBIDDEN_PREFIXES) do
            if root == forbidden then found[#found + 1] = quote end
        end
    end
    assert(#found == 1 and found[1] == "tools.editor.server",
        "scanner failed to flag a planted violation; it would pass on a real one too")
end)

-- The declared exception must stay real. If main.lua stops requiring the test
-- runner, the entry should be removed rather than left to rot into a licence
-- for some future require nobody reviewed.
check("every declared exception is still present in the source", function()
    for key, why in pairs(ALLOWED) do
        local file, module = key:match("^(.-):(.+)$")
        local source = love.filesystem.read(file)
        assert(source, "declared exception names a file that does not exist: " .. file)
        local pattern = module:gsub("%.", "%%.")
        assert(source:find('require%s*%(?%s*["\']' .. pattern .. '["\']'),
            "stale exception -- " .. file .. " no longer requires " .. module
            .. " (" .. why .. "); remove it from ALLOWED")
    end
end)

print(string.format("=== Runtime Boundary Tests: %d passed, %d failed ===", passed, failed))
return failed == 0
