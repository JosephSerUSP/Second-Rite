local M = {}
local repository = require("tests.repository_root")

local function trackedPowerShellScripts()
    local output = repository.gitLsFiles()
    local scripts = {}
    for path in output:gmatch("([^%z]+)%z") do
        if path:lower():match("%.ps1$") then
            scripts[#scripts + 1] = path
        end
    end

    assert(#scripts > 0, "PowerShell ASCII guard found no tracked .ps1 files (is THESTRA_REPOSITORY_ROOT a git checkout?)")
    return scripts
end

function M.run()
    -- Windows PowerShell 5.1 decodes BOM-less scripts through the active ANSI
    -- codepage. On CP1252 hosts, UTF-8 punctuation can become parser-significant
    -- curly quotes, so tracked .ps1 files must remain byte-for-byte ASCII.
    for _, path in ipairs(trackedPowerShellScripts()) do
        local absolutePath = repository.path(path)
        local file, openErr = io.open(absolutePath, "rb")
        assert(file, ("cannot read tracked PowerShell script %s: %s"):format(path, tostring(openErr)))

        local data = file:read("*a") or ""
        file:close()

        for offset = 1, #data do
            local byte = data:byte(offset)
            if byte > 0x7F then
                error(("%s contains non-ASCII byte 0x%02X at byte %d; tracked .ps1 files must stay ASCII for Windows PowerShell 5.1 compatibility")
                    :format(path, byte, offset), 0)
            end
        end
    end
end

return M
