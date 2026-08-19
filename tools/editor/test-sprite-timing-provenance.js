const fs = require('node:fs');
const assert = require('node:assert/strict');

const server = fs.readFileSync('tools/editor/server.js', 'utf8');
const localResolver = fs.readFileSync('tools/editor/sprite-resolution-local.js', 'utf8');
const widgets = fs.readFileSync('tools/editor/js/widgets.js', 'utf8');
const main = fs.readFileSync('runtime/main.lua', 'utf8');
const cli = fs.readFileSync('runtime/engine/cli_tools.lua', 'utf8');
const runtime = fs.readFileSync('runtime/presentation/sprite_sheet.lua', 'utf8');

// #794 changed the authority boundary: sprite timing/resolution are pure shared
// executable semantics, so Studio must execute the generated JS locally rather
// than cold-boot LÖVE for filename parsing. LÖVE still owns its filesystem and
// presentation facilities, and the retained CLI membrane is a parity/diagnostic
// control rather than Studio's production request path.
assert.match(runtime, /require\("engine\.generated\.sprite-timing"\)/,
    'runtime must consume generated shared sprite-timing semantics');
assert.match(runtime, /require\("engine\.generated\.sprite-resolution"\)/,
    'runtime must consume generated shared sprite-resolution semantics');
assert.match(localResolver, /require\('\.\/js\/generated\/sprite-timing'\)/,
    'Studio resolver must consume generated shared sprite-timing semantics');
assert.match(localResolver, /require\('\.\/js\/generated\/sprite-resolution'\)/,
    'Studio resolver must consume generated shared sprite-resolution semantics');
assert.match(server, /createLocalSpriteResolver/,
    'Studio server must answer sprite resolution through the local shared-semantics host');
assert.doesNotMatch(server, /\['sprite-meta', JSON\.stringify\(spec\)\]/,
    'Studio production sprite resolution must not restore the retired LÖVE subprocess');

// The runtime-side inspection membrane remains useful for parity/provenance
// checks and must continue to describe the same authored-key/filename result.
assert.match(runtime, /function sprite_sheet\.describe\(spriteKey\)/,
    'runtime sprite service must expose authored-key provenance');
assert.match(runtime, /function sprite_sheet\.describePath\(path\)/,
    'runtime sprite service must expose filename provenance');
assert.match(main, /val == "sprite-meta"/,
    'main must retain the runtime inspection membrane for parity/diagnostics');
assert.match(cli, /SPRITE META BEGIN/,
    'CLI must retain structured runtime sprite metadata output');
assert.match(server, /\/api\/sprite-resolution/,
    'Studio server must expose sprite resolution metadata');
assert.match(widgets, /requestSpriteTiming\(\{ key: spriteKey \}\)/,
    'sprite field must inspect the authored key');
assert.match(widgets, /requestSpriteTiming\(\{ path \}\)/,
    'asset picker must inspect the selected filename');
assert.match(widgets, /meta\.summary/,
    'Studio must display provenance summary from the shared semantic result');

console.log('sprite timing provenance contract: OK');
