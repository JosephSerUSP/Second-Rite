-- Repository-verification tests run inside the staged Project, whose process
-- working directory is runtime truth for native facilities such as Effekseer.
-- They therefore must not infer the repository checkout from ambient CWD.
-- The staged-unit launcher supplies exactly one explicit repository authority.
local M = {}

local function root()
    local value = os.getenv("THESTRA_REPOSITORY_ROOT")
    assert(value and value ~= "",
        "repository verification requires THESTRA_REPOSITORY_ROOT from the staged-unit launcher")
    value = value:gsub("[/\\]+$", "")
    assert(not value:find('"', 1, true),
        "THESTRA_REPOSITORY_ROOT cannot contain a double quote")
    return value
end

local function nativeRelative(path)
    local separator = package.config:sub(1, 1)
    return tostring(path):gsub("[/\\]", separator)
end

function M.path(relativePath)
    return root() .. package.config:sub(1, 1) .. nativeRelative(relativePath)
end

function M.loadLua(relativePath)
    local absolutePath = M.path(relativePath)
    local chunk, loadErr = loadfile(absolutePath)
    assert(chunk, ("cannot load repository Lua file %s: %s"):format(relativePath, tostring(loadErr)))
    return chunk()
end

function M.gitLsFiles(scope)
    local suffix = ""
    if scope and scope ~= "" then
        assert(not tostring(scope):find('"', 1, true), "git ls-files scope cannot contain a double quote")
        suffix = ' -- "' .. tostring(scope) .. '"'
    end
    local command = ('git -C "%s" ls-files -z%s'):format(root(), suffix)
    local pipe, openErr = io.popen(command, "r")
    assert(pipe, "cannot run git ls-files for repository verification: " .. tostring(openErr))
    local output = pipe:read("*a") or ""
    local ok, closeReason, closeCode = pipe:close()
    assert(ok ~= nil and ok ~= false,
        ("git ls-files failed (%s %s)"):format(tostring(closeReason), tostring(closeCode)))
    return output
end

return M
