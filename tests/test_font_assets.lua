-- Every shipped font file must actually be a font.
--
-- #662: assets/fonts/RobotoMono-Regular.ttf was a saved GitHub HTML page
-- committed under a .ttf name -- 312 KB of markup, zero NUL bytes. Because
-- the editor's GET /api/fonts is a straight directory listing of
-- assets/fonts/*.ttf|*.otf, it became a selectable entry in Studio's Active
-- UI Font picker that could never load. Nothing referenced it from data
-- (data/engine.json `fonts.options` is a curated list), so no id
-- cross-reference check could see it and it sat there unnoticed.
--
-- The rule this suite enforces is therefore about the *directory*, not about
-- what data happens to reference: a file sitting where fonts are enumerated
-- must be a font. It is checked by content, because the extension is exactly
-- the thing that lied.

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

print("[TEST] Starting font asset tests...")

-- The four sfnt magic numbers. A font file begins with one of these; anything
-- else is not something love.graphics.newFont can open.
local SFNT_MAGIC = {
    ["\0\1\0\0"] = "TrueType outlines",
    ["OTTO"] = "OpenType/CFF outlines",
    ["true"] = "Apple TrueType",
    ["ttcf"] = "TrueType Collection",
}

local function hex(s)
    local out = {}
    for i = 1, #s do out[#out + 1] = string.format("%02X", s:byte(i)) end
    return table.concat(out, " ")
end

-- Pure predicate over the leading bytes, so it can be exercised with synthetic
-- input below and not only against whatever happens to be on disk today.
local function sfntKind(head)
    if type(head) ~= "string" or #head < 4 then return nil end
    return SFNT_MAGIC[head:sub(1, 4)]
end

local function fontFilesIn(dir)
    local out = {}
    local info = love.filesystem.getInfo(dir)
    if not info or info.type ~= "directory" then return out end
    for _, name in ipairs(love.filesystem.getDirectoryItems(dir)) do
        local path = dir .. "/" .. name
        local entry = love.filesystem.getInfo(path)
        if entry and entry.type == "file" then out[#out + 1] = path end
    end
    table.sort(out)
    return out
end

-- Every directory that ships fonts: the Project's own, plus each pinned RTP
-- revision. Discovered rather than listed, so a new revision is covered the
-- day it lands.
local function fontDirectories()
    local dirs = { "assets/fonts" }
    local revisions = love.filesystem.getInfo("rtp/revisions")
    if revisions and revisions.type == "directory" then
        for _, rev in ipairs(love.filesystem.getDirectoryItems("rtp/revisions")) do
            local path = "rtp/revisions/" .. rev .. "/assets/fonts"
            local info = love.filesystem.getInfo(path)
            if info and info.type == "directory" then dirs[#dirs + 1] = path end
        end
    end
    return dirs
end

-- Negative controls first. A guard nobody has watched fail is not known to
-- work, and this one passes trivially on a clean tree -- exactly the shape of
-- check that rots into a no-op. These pin the predicate itself.
check("predicate accepts each sfnt magic", function()
    assert(sfntKind("\0\1\0\0rest") == "TrueType outlines", "TrueType magic rejected")
    assert(sfntKind("OTTOrest") == "OpenType/CFF outlines", "OTTO magic rejected")
    assert(sfntKind("truerest") == "Apple TrueType", "true magic rejected")
    assert(sfntKind("ttcfrest") == "TrueType Collection", "ttcf magic rejected")
end)

check("predicate rejects the #662 payload shape", function()
    -- The exact opening bytes of the file that caused this suite to exist.
    assert(sfntKind("\n\n\n\n<!DOCTYPE html>") == nil, "HTML accepted as a font")
    assert(sfntKind("<!DOCTYPE html>") == nil, "HTML accepted as a font")
    assert(sfntKind("wOFF") == nil, "WOFF accepted; love cannot open it")
    assert(sfntKind("wOF2") == nil, "WOFF2 accepted; love cannot open it")
    assert(sfntKind("") == nil, "empty file accepted as a font")
    assert(sfntKind("\0\1\0") == nil, "truncated header accepted as a font")
    assert(sfntKind(nil) == nil, "nil accepted as a font")
end)

local dirs = fontDirectories()

check("at least one font directory was found", function()
    assert(#dirs > 0, "no font directories discovered; the scan is looking in the wrong place")
end)

local totalFonts = 0
for _, dir in ipairs(dirs) do
    local files = fontFilesIn(dir)
    check(dir .. ": directory is not empty", function()
        assert(#files > 0, "no files found under " .. dir
            .. "; either the fonts moved or this suite is scanning nothing")
    end)
    totalFonts = totalFonts + #files

    for _, path in ipairs(files) do
        check(path .. " is a real font", function()
            local head = love.filesystem.read(path, 4)
            local kind = sfntKind(head)
            assert(kind, path .. " does not begin with an sfnt magic number."
                .. " First 4 bytes: " .. hex(head or "")
                .. ". Expected 00 01 00 00, OTTO, true or ttcf."
                .. " A file here is offered by the editor font picker, so it must be"
                .. " loadable -- see #662, where a saved GitHub HTML page was committed"
                .. " as a .ttf. If you downloaded this, re-fetch the raw asset.")
        end)
    end
end

check("the scan actually inspected fonts", function()
    -- Guards the guard: if enumeration silently returned nothing, every
    -- per-file assertion above would vacuously pass.
    assert(totalFonts >= 20, "expected at least 20 font files across "
        .. #dirs .. " directories, inspected " .. totalFonts)
end)

print("=== Font Asset Tests: " .. passed .. " passed, " .. failed .. " failed ===")
assert(failed == 0, "font asset tests had failures")
