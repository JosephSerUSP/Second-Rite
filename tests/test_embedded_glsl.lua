-- Embedded GLSL must not carry Lua-style comments.
--
-- #1491: #1471 wrote two `--` comment lines inside the vertex shader string in
-- presentation/scene_model_view.lua. `--` is not a GLSL comment, so the shader
-- stopped compiling and every modelScene window errored on its first draw.
-- Nothing headless compiles that shader, so every gate stayed green.
--
-- This suite scans every Lua long string under engine/ and presentation/ that
-- looks like shader source and rejects a line starting with `--`. It is static
-- on purpose: it needs no GL context, so it runs wherever unit tests run.

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

print("[TEST] Starting embedded GLSL tests...")

local function luaFiles(dir, out)
    for _, name in ipairs(love.filesystem.getDirectoryItems(dir)) do
        local path = dir .. "/" .. name
        local info = love.filesystem.getInfo(path)
        if info and info.type == "directory" then
            luaFiles(path, out)
        elseif name:match("%.lua$") then
            out[#out + 1] = path
        end
    end
    return out
end

local function isShader(body)
    return body:find("#ifdef VERTEX", 1, true) or body:find("#ifdef PIXEL", 1, true)
        or body:find("vec4 position(", 1, true) or body:find("vec4 effect(", 1, true)
end

-- Returns offending "file:line" entries for one source text.
local function scan(path, source, out)
    local shaders = 0
    local pos = 1
    while true do
        local s, e, eq = source:find("%[(=*)%[", pos)
        if not s then break end
        local close = "]" .. eq .. "]"
        local cs, ce = source:find(close, e + 1, true)
        if not cs then break end
        local body = source:sub(e + 1, cs - 1)
        if isShader(body) then
            shaders = shaders + 1
            local startLine = select(2, source:sub(1, e):gsub("\n", "")) + 1
            local n = 0
            for line in (body .. "\n"):gmatch("([^\n]*)\n") do
                if line:match("^%s*%-%-") then
                    out[#out + 1] = path .. ":" .. (startLine + n) .. ": " .. line
                end
                n = n + 1
            end
        end
        pos = ce + 1
    end
    return shaders
end

check("negative control: a `--` line inside shader source is detected", function()
    local bad = {}
    scan("control", "local v = [[\n#ifdef VERTEX\n    -- nope\n#endif\n]]\n", bad)
    assert(#bad == 1, "scanner missed the planted Lua comment")
end)

check("no Lua-style comments inside embedded shader source", function()
    local files = luaFiles("presentation", luaFiles("engine", {}))
    local bad, shaders = {}, 0
    for _, path in ipairs(files) do
        shaders = shaders + scan(path, love.filesystem.read(path), bad)
    end
    -- Guards the guard: an empty enumeration would vacuously pass.
    assert(shaders >= 3, "expected at least 3 embedded shaders, found " .. shaders)
    assert(#bad == 0, "Lua `--` comment inside GLSL:\n    " .. table.concat(bad, "\n    "))
end)

print("=== Embedded GLSL Tests: " .. passed .. " passed, " .. failed .. " failed ===")
assert(failed == 0, "embedded GLSL tests had failures")
