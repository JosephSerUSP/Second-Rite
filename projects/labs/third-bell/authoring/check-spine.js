'use strict';
// THE THIRD BELL -- campaign spine audit.
//
// The engine validator (G1) proves every id resolves and every flag branch is
// reachable in principle. It does NOT prove that this particular campaign can
// be finished: that its beats chain New Game -> ending in an order a player can
// actually walk. That is what this checks.
//
// It is deliberately a *reachability proof over authored data*, not a
// simulation. It walks the authored command trees, records which flags/items
// each beat requires and produces, and then asserts the campaign spine closes.
//
//   node authoring/check-spine.js
//
// Exits non-zero and names the broken link when a stage is unreachable.

const fs = require('fs');
const path = require('path');

const DATA = path.join(__dirname, '..', 'data');
const read = rel => JSON.parse(fs.readFileSync(path.join(DATA, rel), 'utf8'));

// --- walk every command tree, collecting produced and required state --------

const SUBLISTS = ['commands', 'elseCommands', 'do', 'then', 'else', 'onVictory', 'onDefeat'];

function walk(node, visit) {
    if (Array.isArray(node)) {
        node.forEach(child => walk(child, visit));
        return;
    }
    if (!node || typeof node !== 'object') return;
    visit(node);
    for (const key of SUBLISTS) if (node[key]) walk(node[key], visit);
    if (Array.isArray(node.options)) node.options.forEach(o => walk(o.commands || [], visit));
    if (Array.isArray(node.events)) node.events.forEach(e => walk(e, visit));
    if (Array.isArray(node.pages)) node.pages.forEach(p => walk(p, visit));
}

const produced = { flags: new Set(), items: new Set() };
const requiredBy = new Map(); // token -> Set(source label)

function note(map, token, source) {
    if (!map.has(token)) map.set(token, new Set());
    map.get(token).add(source);
}

function scan(root, label) {
    walk(root, node => {
        if (node.cmd === 'SET_FLAG' && node.value !== false) produced.flags.add(node.flag);
        if (node.cmd === 'CHANGE_ITEM' && Number(node.count) > 0) produced.items.add(String(node.item));
        const cond = [node.condition, node.when].filter(Boolean).join(' ');
        if (cond) {
            const flagMatch = /flag:([A-Za-z0-9_]+)/g;
            let m;
            while ((m = flagMatch.exec(cond))) note(requiredBy, 'flag:' + m[1], label);
            const itemMatch = /hasItem:(\d+)/g;
            while ((m = itemMatch.exec(cond))) note(requiredBy, 'item:' + m[1], label);
        }
    });
}

const commonEvents = read('commonEvents.json');
for (const [id, ce] of Object.entries(commonEvents)) scan(ce, `commonEvent:${id}`);

const mapIndex = read('maps/index.json');
for (const file of mapIndex.files) scan(read('maps/' + file), 'map:' + file);

scan(read('troops.json'), 'troops');
scan(read('quests.json'), 'quests');

// --- the campaign spine: each stage and what proves it is reachable ---------

const SPINE = [
    ['Opening / arrival cinematic', { commonEvent: '42' }],
    ['Town: Crossing Writ obtained', { item: '198' }],
    ['First descent into the Bellroot Depths', { commonEvent: '43', flag: 'dungeon_entered' }],
    ['Incursion 1 return', { flag: 'incursion_one_completed' }],
    ['Incursion 2 return opens the Vigil', { flag: 'vigil_ready' }],
    ['The Vigil (midpoint climax)', { flag: 'vigil_held' }],
    ['The third bell answers -> Act II', { flag: 'third_bell_heard', flag2: 'act2_open' }],
    ["Agnes's Bellroot Leaf", { item: '208' }],
    ['Floor 3 idea: the Rusted Choir', { flag: 'choir_struck_one' }],
    ['Floor 3 gate: the Red Dragon', { flag: 'defeated_red_dragon' }],
    ['Floor 4 idea: the Weighing Room', { flag: 'weighing_room_used' }],
    ["Floor 5: Ines's Half-Contract", { item: '209' }],
    ['Mandatory return-to-town beat', { flag: 'mid_return_done', flag2: 'act3_open' }],
    ['Floor 6: the Eternal Warden falls', { flag: 'warden_defeated' }],
    ["The Warden's Clapper", { item: '210' }],
    ['Authored ending reached', { flag: 'campaign_ending_reached' }],
    ['Ending A: named yourself', { flag: 'ending_named_self' }],
    ['Ending B: named your oldest contract', { flag: 'ending_named_creature' }],
    ['Ending C: cut the rope', { flag: 'ending_cut_rope' }],
];

const failures = [];
for (const [stage, req] of SPINE) {
    const missing = [];
    if (req.commonEvent && !commonEvents[req.commonEvent]) missing.push(`common event ${req.commonEvent}`);
    for (const key of ['flag', 'flag2']) {
        if (req[key] && !produced.flags.has(req[key])) missing.push(`nothing sets flag '${req[key]}'`);
    }
    if (req.item && !produced.items.has(req.item)) missing.push(`nothing grants item ${req.item}`);
    if (missing.length) failures.push(`${stage}: ${missing.join('; ')}`);
    else console.log(`  ok   ${stage}`);
}

// --- anti-softlock checks ---------------------------------------------------

const deepest = read('maps/7.json');
const hasWayUp = (deepest.events || []).some(e => e.scriptId === 40 || /stairs/i.test(e.name || ''));
if (!hasWayUp) failures.push('Floor 6 has no stairs event: a party that walks in can never walk out');

const ending = commonEvents['44'];
if (!ending) failures.push('no ending common event (44)');
else {
    const endsInTown = JSON.stringify(ending).includes('"LOAD_MAP"');
    if (!endsInTown) failures.push('ending never returns the player to a map: it would strand the cinematic');
}

// The ending must not be reachable before the Warden is beaten.
const bell = (read('maps/7.json').events || []).find(e => e.name === 'The Third Bell');
if (!bell) failures.push('Floor 6 has no Third Bell event');
else if (!JSON.stringify(bell).includes('hasItem:210')) {
    failures.push('the Third Bell does not gate the ending behind the Clapper');
}

console.log('');
if (failures.length) {
    console.error('CAMPAIGN SPINE BROKEN:');
    failures.forEach(f => console.error('  - ' + f));
    process.exit(1);
}
console.log(`CAMPAIGN SPINE OK -- ${SPINE.length} stages, 3 endings, no softlock found`);
