-- Every test suite must be reachable from a declared registration (#197).
--
-- Suites are supposed to be listed in main.lua's unittest suite list. Nothing
-- checked that, and three separate PRs independently hooked their suite into
-- `fail_fast.finish()` instead -- not by inventing a bypass, but by copying the
-- repository-hygiene hook that already lived in the file they were editing.
-- A convention three agents have already violated has failed as prose, so it
-- is a check now.
--
-- "Registered" deliberately means reachable, not literally in the list, because
-- the repo has three legitimate non-list mechanisms:
--   * main.lua's unittest suite list           -- the normal case
--   * a dofile in another main.lua CLI mode    -- test_model_census_review
--   * a require from an already-registered suite -- test_state_ticks_core
-- An orphan -- a suite that exists and runs from nowhere -- satisfies none of
-- them and is what this catches.
local M = {}

local function read(path)
    local file, openErr = io.open(path, "rb")
    assert(file, ("cannot read %s: %s"):format(path, tostring(openErr)))
    local data = file:read("*a") or ""
    file:close()
    return data
end

local function trackedSuites()
    local pipe, openErr = io.popen("git ls-files -z tests", "r")
    assert(pipe, "cannot run git ls-files while checking suite registration: " .. tostring(openErr))
    local output = pipe:read("*a") or ""
    pipe:close()

    local suites = {}
    for path in output:gmatch("([^%z]+)%z") do
        local name = path:match("^tests/(test_[%w_]+)%.lua$")
        if name then suites[name] = path end
    end
    assert(next(suites) ~= nil,
        "suite registration guard found no tracked tests/test_*.lua (is this a git checkout?)")
    return suites
end

-- Names a source file registers directly: quoted "test_x" entries (the suite
-- list), dofile("tests/test_x.lua"), and require("tests.test_x").
local function namesReferencedBy(source)
    local found = {}
    for name in source:gmatch('"(test_[%w_]+)"') do found[name] = true end
    for name in source:gmatch('tests/(test_[%w_]+)%.lua') do found[name] = true end
    for name in source:gmatch('tests%.(test_[%w_]+)') do found[name] = true end
    return found
end

function M.run()
    local suites = trackedSuites()

    -- Roots: anything main.lua or fail_fast.lua names. fail_fast is a root
    -- because repository-wide hygiene invariants legitimately run from its
    -- finish() hook; see the comment there for what belongs.
    local registered = {}
    for _, root in ipairs({ "main.lua", "tests/fail_fast.lua" }) do
        for name in pairs(namesReferencedBy(read(root))) do registered[name] = true end
    end

    -- Then close over requires: a suite pulled in by a registered suite runs.
    local grew = true
    while grew do
        grew = false
        for name in pairs(registered) do
            local path = suites[name]
            if path then
                for referenced in pairs(namesReferencedBy(read(path))) do
                    if suites[referenced] and not registered[referenced] then
                        registered[referenced] = true
                        grew = true
                    end
                end
            end
        end
    end

    local orphans = {}
    for name in pairs(suites) do
        if not registered[name] then orphans[#orphans + 1] = name end
    end
    table.sort(orphans)

    if #orphans > 0 then
        error(("%d test suite(s) run from nowhere: %s\n"
            .. "Register each in main.lua's unittest suite list -- that list is the "
            .. "intended mechanism. Do not add a require to fail_fast.finish(); that "
            .. "hook is for repository-wide hygiene invariants, not per-feature suites.")
            :format(#orphans, table.concat(orphans, ", ")), 0)
    end
end

return M
