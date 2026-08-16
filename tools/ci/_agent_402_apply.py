from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_exact(path, old, new, expected=1):
    text = read(path)
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrence(s), found {count}: {old[:120]!r}")
    write(path, text.replace(old, new))
    print(f"updated {path}: {count} exact replacement(s)")


# ---------------------------------------------------------------------------
# Runtime authority: preserve provenance alongside the existing resolved token
# values and expose a diagnostic description without changing frame semantics.
# ---------------------------------------------------------------------------
replace_exact(
    "presentation/sprite_sheet.lua",
    '''local function ensureFileIndex()\n''',
    '''local function copyTokens(tokens)\n    local out = {}\n    for k, v in pairs(tokens or {}) do out[k] = v end\n    return out\nend\n\nlocal function tokenText(tokens)\n    local keys = {}\n    for k in pairs(tokens or {}) do table.insert(keys, k) end\n    table.sort(keys)\n    if #keys == 0 then return "none" end\n    local parts = {}\n    for _, k in ipairs(keys) do\n        table.insert(parts, tostring(k) .. "=" .. tostring(tokens[k]))\n    end\n    return table.concat(parts, ", ")\nend\n\nlocal function timingMetadata(keyTokens, filenameTokens, mergedTokens)\n    local token, value, source\n    if mergedTokens and mergedTokens.fps ~= nil then\n        token = "fps"\n        value = mergedTokens.fps\n        source = keyTokens and keyTokens.fps ~= nil and "key"\n            or (filenameTokens and filenameTokens.fps ~= nil and "filename" or "resolved")\n    elseif mergedTokens and mergedTokens.speed ~= nil then\n        token = "speed"\n        value = mergedTokens.speed\n        source = keyTokens and keyTokens.speed ~= nil and "key"\n            or (filenameTokens and filenameTokens.speed ~= nil and "filename" or "resolved")\n    else\n        return { fps = 4, source = "default", token = nil, value = nil }\n    end\n\n    local numeric = tonumber(value)\n    local fps = numeric and (token == "fps" and numeric or 4 * numeric) or nil\n    return { fps = fps, source = source, token = token, value = value }\nend\n\nlocal function describeResolved(spriteKey, resolved)\n    local timing = timingMetadata(resolved.keyTokens, resolved.filenameTokens, resolved.tokens)\n    local effective\n    if timing.fps then\n        if timing.source == "default" then\n            effective = "Effective: 4 fps from the default"\n        else\n            effective = string.format("Effective: %g fps from %s [%s=%s]",\n                timing.fps, timing.source, tostring(timing.token), tostring(timing.value))\n        end\n    else\n        effective = string.format("Effective timing is invalid: %s [%s=%s]",\n            tostring(timing.source), tostring(timing.token), tostring(timing.value))\n    end\n\n    return {\n        key = spriteKey,\n        resolved = true,\n        path = resolved.path,\n        tokenSourcePath = resolved.filenameTokenPath,\n        keyTokens = copyTokens(resolved.keyTokens),\n        filenameTokens = copyTokens(resolved.filenameTokens),\n        tokens = copyTokens(resolved.tokens),\n        timing = timing,\n        summary = effective\n            .. ". Key tokens: " .. tokenText(resolved.keyTokens)\n            .. ". Filename tokens: " .. tokenText(resolved.filenameTokens)\n            .. ". Priority: fps > speed > default; key overrides filename for the same token.",\n    }\nend\n\nlocal function ensureFileIndex()\n'''
)

replace_exact(
    "presentation/sprite_sheet.lua",
    '''    local fileKey, overrides = parseKey(spriteKey)\n    local paths = {\n''',
    '''    local fileKey, keyTokens = parseKey(spriteKey)\n    local overrides = copyTokens(keyTokens)\n    local paths = {\n'''
)

replace_exact(
    "presentation/sprite_sheet.lua",
    '''    local indexed = ensureFileIndex()[fileKey:lower()]\n    if indexed then\n        table.insert(paths, indexed.path)\n        for k, v in pairs(indexed.tokens) do\n            if overrides[k] == nil then overrides[k] = v end\n        end\n    end\n\n    for _, path in ipairs(paths) do\n        if love.filesystem.getInfo(path) then\n            return { path = path, tokens = overrides }\n        end\n    end\n    return nil\nend\n\n-- Load/cache one sprite sheet. A false cache entry preserves the historical\n''',
    '''    local indexed = ensureFileIndex()[fileKey:lower()]\n    local filenameTokens = {}\n    local filenameTokenPath = nil\n    if indexed then\n        table.insert(paths, indexed.path)\n        filenameTokens = copyTokens(indexed.tokens)\n        filenameTokenPath = indexed.path\n        for k, v in pairs(indexed.tokens) do\n            if overrides[k] == nil then overrides[k] = v end\n        end\n    end\n\n    for _, path in ipairs(paths) do\n        if love.filesystem.getInfo(path) then\n            return {\n                path = path,\n                tokens = overrides,\n                keyTokens = copyTokens(keyTokens),\n                filenameTokens = filenameTokens,\n                filenameTokenPath = filenameTokenPath,\n            }\n        end\n    end\n    return nil\nend\n\n-- Authoring/diagnostic description of the exact runtime resolution. This is\n-- intentionally produced here rather than re-derived in Studio: key tokens\n-- override the same filename token, while fps has priority over speed globally.\nfunction sprite_sheet.describe(spriteKey)\n    if not spriteKey or spriteKey == "" then\n        return { key = spriteKey, resolved = false, summary = "No sprite key selected." }\n    end\n    local resolved = sprite_sheet.resolveFile(spriteKey)\n    if not resolved then\n        return {\n            key = spriteKey,\n            resolved = false,\n            summary = "Unresolved sprite key: " .. tostring(spriteKey),\n        }\n    end\n    return describeResolved(spriteKey, resolved)\nend\n\n-- Asset-picker inspection has a concrete file rather than an authored key.\n-- Parse that filename through the same token grammar and timing priority so\n-- Studio can show the file's defaults without owning a second interpretation.\nfunction sprite_sheet.describePath(path)\n    if not path or path == "" then\n        return { path = path, resolved = false, summary = "No sprite file selected." }\n    end\n    local filename = tostring(path):match("([^/\\\\]+)$") or tostring(path)\n    local stem = filename:gsub("%.png$", "")\n    local _, filenameTokens = parseKey(stem)\n    local resolved = {\n        path = path,\n        tokens = copyTokens(filenameTokens),\n        keyTokens = {},\n        filenameTokens = copyTokens(filenameTokens),\n        filenameTokenPath = path,\n    }\n    return describeResolved(nil, resolved)\nend\n\n-- Load/cache one sprite sheet. A false cache entry preserves the historical\n'''
)

# Runtime regression evidence: same-token key override and cross-token fps
# priority are both explicit, plus raw file inspection.
replace_exact(
    "tests/test_sprite_sheet.lua",
    '''eq(overridden.tokens.fps, 9, "key fps overrides filename token")\n\n-- Loading, horizontal square-cell slicing and cache reuse have one implementation.\n''',
    '''eq(overridden.tokens.fps, 9, "key fps overrides filename token")\neq(overridden.keyTokens.fps, 9, "key token provenance is retained")\neq(overridden.filenameTokens.fps, 15, "filename token provenance is retained")\n\nlocal fileDefault = sprites.describe("pixie")\neq(fileDefault.timing.fps, 15, "description reports effective filename fps")\neq(fileDefault.timing.source, "filename", "description attributes inherited fps to filename")\neq(fileDefault.timing.token, "fps", "description names winning token")\ntruthy(fileDefault.summary:find("Filename tokens: fps=15", 1, true), "summary exposes filename provenance")\n\nlocal keyOverride = sprites.describe("pixie[fps=9]")\neq(keyOverride.timing.fps, 9, "description reports key override fps")\neq(keyOverride.timing.source, "key", "description attributes override to authored key")\n\n-- fps has priority over speed even when the speed token is the key-authored one.\nlocal crossPriority = sprites.describe("pixie[speed=2]")\neq(crossPriority.keyTokens.speed, 2, "key speed provenance")\neq(crossPriority.filenameTokens.fps, 15, "filename fps provenance")\neq(crossPriority.timing.fps, 15, "fps outranks speed globally")\neq(crossPriority.timing.source, "filename", "winning filename fps is reported truthfully")\n\nlocal pathDefault = sprites.describePath("assets/smallBattlers/Pixie[fps=15].png")\neq(pathDefault.timing.fps, 15, "file inspection uses runtime timing grammar")\neq(pathDefault.timing.source, "filename", "file inspection attributes token to filename")\n\n-- Loading, horizontal square-cell slicing and cache reuse have one implementation.\n'''
)

# ---------------------------------------------------------------------------
# Tiny headless CLI membrane for Studio. One JSON argument distinguishes an
# authored key from a concrete file path, so shell/positional token syntax never
# leaks into the authoring surface.
# ---------------------------------------------------------------------------
replace_exact(
    "engine/cli_tools.lua",
    '''function cli.runPreviewAnim(animId, animJson, spritePath, loader)\n''',
    '''function cli.runSpriteMeta(specJson)\n    local json = require("data.json")\n    local payload\n    local ok, err = pcall(function()\n        local spec = json.decode(specJson or "{}")\n        local sprite_sheet = require("presentation.sprite_sheet")\n        if type(spec) ~= "table" then error("sprite metadata request must be an object", 0) end\n        if spec.key ~= nil then\n            payload = sprite_sheet.describe(spec.key)\n        elseif spec.path ~= nil then\n            payload = sprite_sheet.describePath(spec.path)\n        else\n            error("sprite metadata request must name key or path", 0)\n        end\n    end)\n    if not ok then payload = { error = tostring(err) } end\n    print("SPRITE META BEGIN")\n    print(json.encode(payload))\n    print("SPRITE META END")\nend\n\nfunction cli.runPreviewAnim(animId, animJson, spritePath, loader)\n'''
)

replace_exact(
    "main.lua",
    '''            elseif val == "preview-anim" then\n                cli.isPreviewAnimMode = true\n                cli.previewAnimId = arg[i + 1]\n                cli.previewAnimJson = arg[i + 2]\n                cli.previewAnimSprite = arg[i + 3]\n                i = i + 3\n''',
    '''            elseif val == "sprite-meta" then\n                cli.isSpriteMetaMode = true\n                cli.spriteMetaSpec = arg[i + 1]\n                i = i + 1\n            elseif val == "preview-anim" then\n                cli.isPreviewAnimMode = true\n                cli.previewAnimId = arg[i + 1]\n                cli.previewAnimJson = arg[i + 2]\n                cli.previewAnimSprite = arg[i + 3]\n                i = i + 3\n'''
)

replace_exact(
    "main.lua",
    '''    -- A3: headless animation preview, then quit.\n    if cli.isPreviewAnimMode then\n''',
    '''    -- Studio sprite timing/provenance inspection. This is intentionally a\n    -- runtime query so the editor never grows a competing precedence model.\n    if cli.isSpriteMetaMode then\n        cli_tools.runSpriteMeta(cli.spriteMetaSpec)\n        love.event.quit(0)\n        return\n    end\n\n    -- A3: headless animation preview, then quit.\n    if cli.isPreviewAnimMode then\n'''
)

# ---------------------------------------------------------------------------
# Studio server: lazy, uncached query to current staged Project/runtime. Asset
# renames therefore cannot leave a stale provenance answer behind.
# ---------------------------------------------------------------------------
server_anchor = '''    } else if (req.method === 'GET' && req.url.startsWith('/api/assets')) {\n'''
server_insert = '''    } else if (req.method === 'GET' && req.url.startsWith('/api/sprite-resolution')) {\n        const parsedUrl = new URL(req.url, 'http://127.0.0.1:8080');\n        const spriteKey = parsedUrl.searchParams.get('key');\n        const rawPath = parsedUrl.searchParams.get('path');\n        let spec;\n\n        if (spriteKey !== null) {\n            if (spriteKey.length > 512) {\n                res.writeHead(400, { 'Content-Type': 'application/json' });\n                res.end(JSON.stringify({ error: 'sprite key is too long' }));\n                return;\n            }\n            spec = { key: spriteKey };\n        } else if (rawPath !== null) {\n            const normalized = rawPath.replace(/\\\\/g, '/');\n            if (!/^assets\\/(smallBattlers|sprites|system)\\/[^/]+$/i.test(normalized)) {\n                res.writeHead(400, { 'Content-Type': 'application/json' });\n                res.end(JSON.stringify({ error: 'sprite path must name one file in a runtime sprite directory' }));\n                return;\n            }\n            let absolute;\n            try { absolute = inProject(...normalized.split('/')); } catch (e) { absolute = null; }\n            if (!absolute || !fs.existsSync(absolute) || !fs.statSync(absolute).isFile()) {\n                res.writeHead(404, { 'Content-Type': 'application/json' });\n                res.end(JSON.stringify({ error: 'sprite file no longer exists' }));\n                return;\n            }\n            spec = { path: normalized };\n        } else {\n            res.writeHead(400, { 'Content-Type': 'application/json' });\n            res.end(JSON.stringify({ error: 'sprite-resolution requires key or path' }));\n            return;\n        }\n\n        execOpenedProject(previewExe, ['sprite-meta', JSON.stringify(spec)], {\n            timeout: 10000,\n            windowsHide: true,\n            maxBuffer: 1024 * 1024\n        }, (err, stdout) => {\n            const text = String(stdout || '');\n            const match = text.match(/SPRITE META BEGIN\\s*\\r?\\n([\\s\\S]*?)\\r?\\nSPRITE META END/);\n            if (!match) {\n                res.writeHead(500, { 'Content-Type': 'application/json' });\n                res.end(JSON.stringify({ error: err ? String(err.message || err) : 'runtime returned no sprite metadata' }));\n                return;\n            }\n            try {\n                const payload = JSON.parse(match[1]);\n                res.writeHead(payload && payload.error ? 400 : 200, { 'Content-Type': 'application/json' });\n                res.end(JSON.stringify(payload));\n            } catch (e) {\n                res.writeHead(500, { 'Content-Type': 'application/json' });\n                res.end(JSON.stringify({ error: 'invalid sprite metadata response: ' + e.message }));\n            }\n        });\n\n    } else if (req.method === 'GET' && req.url.startsWith('/api/assets')) {\n'''
replace_exact("tools/editor/server.js", server_anchor, server_insert)

# ---------------------------------------------------------------------------
# Studio inspection tooltips. Pixels/layout remain untouched; the tooltip text
# comes verbatim from runtime metadata. The old local CSS-animation parser is
# intentionally left behavior-preserving and is not used as provenance truth.
# ---------------------------------------------------------------------------
replace_exact(
    "tools/editor/js/widgets.js",
    '''        let assetPreviewGeneration = 0;\n\n        window.createSnapshotModal''',
    '''        let assetPreviewGeneration = 0;\n\n        const requestSpriteTiming = (spec) => {\n            const query = spec && Object.prototype.hasOwnProperty.call(spec, 'key')\n                ? 'key=' + encodeURIComponent(spec.key || '')\n                : 'path=' + encodeURIComponent((spec && spec.path) || '');\n            return fetch(`${API_URL}/api/sprite-resolution?${query}`)\n                .then(r => r.json().then(data => ({ ok: r.ok, data })))\n                .then(({ ok, data }) => {\n                    if (!ok) throw new Error((data && data.error) || 'sprite timing lookup failed');\n                    return data;\n                });\n        };\n\n        window.createSnapshotModal'''
)

replace_exact(
    "tools/editor/js/widgets.js",
    '''            thumbWrap.title = 'Double-click to select image';\n\n            // Sprite strips play on their own layer so the wrapper keeps the\n''',
    '''            thumbWrap.title = 'Double-click to select image';\n            let timingTitleGeneration = 0;\n\n            const refreshTimingTitle = (spriteKey) => {\n                const generation = ++timingTitleGeneration;\n                thumbWrap.title = 'Double-click to select image';\n                if (!animate || !spriteKey) return;\n                requestSpriteTiming({ key: spriteKey }).then(meta => {\n                    if (generation !== timingTitleGeneration) return;\n                    const detail = meta && meta.summary ? meta.summary : 'No timing metadata.';\n                    thumbWrap.title = 'Double-click to select image\\n' + detail\n                        + (meta && meta.path ? '\\nResolved file: ' + meta.path : '');\n                }).catch(err => {\n                    if (generation === timingTitleGeneration) {\n                        thumbWrap.title = 'Double-click to select image\\nTiming provenance unavailable: ' + err.message;\n                    }\n                });\n            };\n\n            // Sprite strips play on their own layer so the wrapper keeps the\n'''
)

replace_exact(
    "tools/editor/js/widgets.js",
    '''            function updateThumb(path) {\n                animLayer.classList.remove('sprite-sheet-anim');\n''',
    '''            function updateThumb(path) {\n                refreshTimingTitle(path);\n                animLayer.classList.remove('sprite-sheet-anim');\n'''
)

replace_exact(
    "tools/editor/js/widgets.js",
    '''            box.removeAttribute('data-preview-ready');\n            img.style.display = 'none';\n''',
    '''            box.removeAttribute('data-preview-ready');\n            box.title = 'Asset preview';\n            img.style.display = 'none';\n'''
)

replace_exact(
    "tools/editor/js/widgets.js",
    '''                if (isStrip) {\n                    // Same convention as the sprite thumbnails above: cell size\n''',
    '''                if (isStrip) {\n                    // Timing provenance comes from the runtime resolver, not this\n                    // visual preview's historical CSS animation helper. The query\n                    // is inspection-only and does not block preview painting/G6.\n                    requestSpriteTiming({ path }).then(meta => {\n                        if (generation === assetPreviewGeneration && meta && meta.summary) {\n                            box.title = meta.summary + '\\nFile: ' + path;\n                        }\n                    }).catch(err => {\n                        if (generation === assetPreviewGeneration) {\n                            box.title = 'Timing provenance unavailable: ' + err.message;\n                        }\n                    });\n\n                    // Same convention as the sprite thumbnails above: cell size\n'''
)

# A focused source-contract test makes it hard to accidentally move provenance
# back into an editor-only parser. Runtime semantic details remain covered by
# the Lua unit test above.
contract_test = ROOT / "tools/editor/test-sprite-timing-provenance.js"
contract_test.write_text(r'''const fs = require('node:fs');
const assert = require('node:assert/strict');

const server = fs.readFileSync('tools/editor/server.js', 'utf8');
const widgets = fs.readFileSync('tools/editor/js/widgets.js', 'utf8');
const main = fs.readFileSync('main.lua', 'utf8');
const cli = fs.readFileSync('engine/cli_tools.lua', 'utf8');
const runtime = fs.readFileSync('presentation/sprite_sheet.lua', 'utf8');

assert.match(runtime, /function sprite_sheet\.describe\(spriteKey\)/,
    'runtime sprite service must own authored-key provenance');
assert.match(runtime, /function sprite_sheet\.describePath\(path\)/,
    'runtime sprite service must own filename provenance');
assert.match(main, /val == "sprite-meta"/,
    'main must expose the runtime inspection membrane');
assert.match(cli, /SPRITE META BEGIN/,
    'CLI must return structured sprite metadata');
assert.match(server, /\/api\/sprite-resolution/,
    'Studio server must expose runtime sprite inspection');
assert.match(server, /\['sprite-meta', JSON\.stringify\(spec\)\]/,
    'Studio server must query LÖVE rather than reimplement precedence');
assert.match(widgets, /requestSpriteTiming\(\{ key: spriteKey \}\)/,
    'sprite field must inspect the authored key');
assert.match(widgets, /requestSpriteTiming\(\{ path \}\)/,
    'asset picker must inspect the selected filename');
assert.match(widgets, /meta\.summary/,
    'Studio must display the runtime-authored provenance summary');

console.log('sprite timing provenance contract: OK');
''', encoding="utf-8")
print("created tools/editor/test-sprite-timing-provenance.js")

# Ensure the new Node contract is part of the always-run tooling boundary suite.
replace_exact(
    ".github/workflows/verify.yml",
    '''node --test tools/export/export-game.test.js tools/export/rtp-resource-resolver.test.js tools/editor/test-project-root.js tools/editor/test-chrome-ownership.js tools/editor/tests/test-map-encounter-cadence.js tools/campaign-gen/test-fixture-project.js''',
    '''node --test tools/export/export-game.test.js tools/export/rtp-resource-resolver.test.js tools/editor/test-project-root.js tools/editor/test-chrome-ownership.js tools/editor/test-sprite-timing-provenance.js tools/editor/tests/test-map-encounter-cadence.js tools/campaign-gen/test-fixture-project.js'''
)

# Cheap structural safety before the Action commits.
for path in [
    "presentation/sprite_sheet.lua", "tests/test_sprite_sheet.lua", "engine/cli_tools.lua",
    "main.lua", "tools/editor/server.js", "tools/editor/js/widgets.js",
    ".github/workflows/verify.yml", "tools/editor/test-sprite-timing-provenance.js",
]:
    if not (ROOT / path).exists():
        raise SystemExit(f"missing expected output {path}")

print("#402 codemod complete")
