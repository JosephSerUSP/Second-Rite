'use strict';

const fs = require('node:fs');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '..', '..');
const indexPath = path.join(repoRoot, 'tools', 'editor', 'index.html');
const widgetsPath = path.join(repoRoot, 'tools', 'editor', 'js', 'widgets.js');

function replaceExactly(source, needle, replacement, expectedCount, label) {
    const count = source.split(needle).length - 1;
    if (count !== expectedCount) {
        throw new Error(`${label}: expected ${expectedCount} occurrence(s), found ${count}`);
    }
    return source.split(needle).join(replacement);
}

let index = fs.readFileSync(indexPath, 'utf8');
const generatedScript = '    <script src="js/generated/sprite-timing.js"></script>\n';
if (!index.includes(generatedScript.trim())) {
    index = replaceExactly(
        index,
        '    <script src="js/event_self_state_authoring.js"></script>\n    <script src="js/widgets.js"></script>',
        '    <script src="js/event_self_state_authoring.js"></script>\n'
            + generatedScript
            + '    <script src="js/widgets.js"></script>',
        1,
        'Studio sprite-timing script insertion');
    fs.writeFileSync(indexPath, index);
}

let widgets = fs.readFileSync(widgetsPath, 'utf8');
const authorityMarker = '        const spriteTimingAuthority = window.ThestraSpriteTimingSemantics;';
if (!widgets.includes(authorityMarker)) {
    widgets = replaceExactly(
        widgets,
        '        let assetPreviewGeneration = 0;\n',
        '        let assetPreviewGeneration = 0;\n\n'
            + authorityMarker + '\n'
            + "        if (!spriteTimingAuthority) throw new Error('Generated shared sprite timing semantics were not loaded before widgets.js');\n",
        1,
        'Studio timing authority binding');
}

const duplicateParser = "                        const tokens = {};\n"
    + "                        path.replace(/\\[([^=\\]]+)=([^\\]]+)\\]/g, (m, k, v) => { tokens[k] = parseFloat(v); return ''; });\n"
    + "                        const fps = tokens.fps || (tokens.speed ? 4 * tokens.speed : 4);";
const sharedParser = "                        const parsedTiming = spriteTimingAuthority.parseKey(path);\n"
    + "                        const fps = spriteTimingAuthority.effectiveFps(parsedTiming.tokens);";

const remaining = widgets.split(duplicateParser).length - 1;
if (remaining > 0) {
    if (remaining !== 2) throw new Error(`Studio duplicate sprite parser: expected 2 occurrences, found ${remaining}`);
    widgets = widgets.split(duplicateParser).join(sharedParser);
}
if (widgets.includes('tokens.fps || (tokens.speed ? 4 * tokens.speed : 4)')) {
    throw new Error('Studio handwritten sprite timing expression remains after cutover');
}
fs.writeFileSync(widgetsPath, widgets);

console.log('Studio shared timing host cutover applied.');
