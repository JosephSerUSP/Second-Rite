const fs = require('node:fs');
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
