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
