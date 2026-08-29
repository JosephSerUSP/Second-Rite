'use strict';

// #967 cross-host probe, Node half.
//
// Takes the JSON the LÖVE host emitted from its own decode of
// runtime/presentation/presentation.json (`lovec <stage>
// presentation-contract-dump`) and asserts it means the same thing as this
// host's decode of the same file.
//
// The point is not that the bytes are equal -- they are the same file. It is
// that two homegrown readers agree on what the bytes SAY. LuaJIT parses this
// with engine/data/json.lua and Node with JSON.parse; a fractional colour
// component or a rectangle origin that round-trips differently between them
// would repaint the browser adapter relative to the game, and no other gate in
// the repository would see it.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..', '..');
const AUTHORED = path.join(REPO, 'runtime', 'presentation', 'presentation.json');

function stripComments(value) {
    if (Array.isArray(value)) return value.map(stripComments);
    if (!value || typeof value !== 'object') return value;
    const out = {};
    for (const key of Object.keys(value).sort()) {
        if (key.startsWith('_')) continue;
        out[key] = stripComments(value[key]);
    }
    return out;
}

// Report every disagreement, not just the first. A single wrong number is a
// typo; a whole palette shifted is a decoder problem, and the difference
// between those two diagnoses is worth one extra traversal.
function diff(a, b, at, out) {
    if (Array.isArray(a) || Array.isArray(b)) {
        if (!Array.isArray(a) || !Array.isArray(b)) return out.push(`${at}: array on one host only`);
        if (a.length !== b.length) return out.push(`${at}: length ${a.length} vs ${b.length}`);
        a.forEach((item, index) => diff(item, b[index], `${at}[${index}]`, out));
        return;
    }
    if (a && b && typeof a === 'object' && typeof b === 'object') {
        const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
        for (const key of [...keys].sort()) {
            if (!(key in a)) { out.push(`${at}.${key}: present only in the Node decode`); continue; }
            if (!(key in b)) { out.push(`${at}.${key}: present only in the LÖVE decode`); continue; }
            diff(a[key], b[key], `${at}.${key}`, out);
        }
        return;
    }
    // Numbers are compared as numbers on purpose: one host may render 8 and
    // the other 8.0, and that is a formatting difference, not a semantic one.
    // A real difference in VALUE, however small, is a failure -- there is no
    // tolerance here, because these numbers become pixels.
    if (typeof a === 'number' && typeof b === 'number') {
        if (!Object.is(a, b)) out.push(`${at}: ${a} (LÖVE) vs ${b} (Node)`);
        return;
    }
    if (a !== b) out.push(`${at}: ${JSON.stringify(a)} (LÖVE) vs ${JSON.stringify(b)} (Node)`);
}

function main() {
    const dumpPath = process.argv[2];
    if (!dumpPath) {
        console.error('usage: node tools/presentation/compare-hosts.js <love-contract-dump.json>');
        process.exit(2);
    }

    const loveView = stripComments(JSON.parse(fs.readFileSync(dumpPath, 'utf8')));
    const nodeView = stripComments(JSON.parse(fs.readFileSync(AUTHORED, 'utf8')));

    const differences = [];
    diff(loveView, nodeView, '$', differences);
    if (differences.length) {
        console.error(`PRESENTATION CONTRACT HOST DISAGREEMENT (${differences.length}):`);
        for (const line of differences) console.error(`  ${line}`);
        process.exit(1);
    }

    // Belt and braces: the two hosts must also agree the contract is the
    // version this tooling supports, rather than agreeing on nonsense.
    assert.strictEqual(loveView.version, 1, 'LÖVE decoded an unsupported contract version');
    console.log('PRESENTATION CONTRACT HOSTS AGREE');
}

main();
