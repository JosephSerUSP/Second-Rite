#!/usr/bin/env node
'use strict';

// A small content-level audit for the machine-authored route. It does not
// simulate combat; G1 owns schema/reference correctness, while this checks
// that the intended New Game -> return -> climax -> ending spine still exists
// after a future data edit.

const fs = require('fs');
const path = require('path');

const project = path.resolve(__dirname, '..');
const data = path.join(project, 'data');
const read = (relative) => JSON.parse(fs.readFileSync(path.join(data, relative), 'utf8'));
const errors = [];

function requireValue(condition, message) {
    if (!condition) errors.push(message);
}

function walk(value, callback) {
    if (Array.isArray(value)) value.forEach((item) => walk(item, callback));
    else if (value && typeof value === 'object') {
        callback(value);
        Object.values(value).forEach((item) => walk(item, callback));
    }
}

function containsCommand(commands, predicate) {
    let found = false;
    walk(commands, (node) => {
        if (node.cmd && predicate(node)) found = true;
    });
    return found;
}

const commonEvents = read('commonEvents.json');
const town = read('maps/1.json');
const floor1 = read('maps/2.json');
const floor2 = read('maps/3.json');
const floor3 = read('maps/4.json');
const troops = read('troops.json');

requireValue(containsCommand(commonEvents['42'].commands, (node) => node.flag === 'ash_arrival_seen'), 'opening does not publish ash_arrival_seen');
for (const id of ['50', '51', '52', '53']) {
    requireValue(commonEvents[id] && Array.isArray(commonEvents[id].commands), `missing authored common event ${id}`);
}

const byName = (map, name) => (map.events || []).find((event) => event.name === name);
const townGate = byName(town, 'Gate Guard');
const alicia = byName(town, 'Alicia');
const agnes = byName(town, 'EV012');
requireValue(containsCommand(townGate && townGate.commands, (node) => node.cmd === 'CALL_COMMON_EVENT' && node.commonEventId === 50), 'town gate does not call Ash Choir Gate');
requireValue(containsCommand(alicia && alicia.commands, (node) => node.cmd === 'CALL_COMMON_EVENT' && node.commonEventId === 51), 'Alicia does not own the return beat');
requireValue(containsCommand(agnes && agnes.commands, (node) => node.cmd === 'CALL_COMMON_EVENT' && node.commonEventId === 53), 'Agnes does not own the epilogue reaction');

for (const [map, expectedTitle, expectedEvent] of [
    [floor1, 'Floor 1: The Gray Threshold', 'Ash Ledger'],
    [floor2, 'Floor 2: The Salt Gallery', 'Salt Mirror'],
    [floor3, 'Floor 3: The Ash Choir', 'Ash Choir'],
]) {
    requireValue(map.title === expectedTitle, `expected ${expectedTitle}, found ${map.title}`);
    requireValue(Boolean(byName(map, expectedEvent)), `${expectedTitle} is missing ${expectedEvent}`);
}

const choir = byName(floor3, 'Ash Choir');
requireValue(containsCommand(choir && choir.commands, (node) => node.cmd === 'BATTLE' && node.troop === 'boss_ash_choir'), 'Ash Choir has no guardian battle');
requireValue(containsCommand(choir && choir.commands, (node) => node.cmd === 'CALL_COMMON_EVENT' && node.commonEventId === 52), 'guardian victory does not reach the ending');
requireValue(troops.boss_ash_choir && troops.boss_ash_choir.members.length === 2, 'boss_ash_choir troop is missing or malformed');

const ending = commonEvents['52'].commands;
requireValue(containsCommand(ending, (node) => node.cmd === 'CHOICE' && node.options && node.options.length === 2), 'ending does not offer two authored interpretations');
requireValue(containsCommand(ending, (node) => node.cmd === 'SET_FLAG' && node.flag === 'ash_ending_reached'), 'ending does not publish ash_ending_reached');
requireValue(containsCommand(ending, (node) => node.cmd === 'LOAD_MAP' && Number(node.mapId) === 1), 'ending has no return-to-town epilogue transfer');

if (errors.length) {
    console.error('CAMPAIGN SPINE FAIL');
    errors.forEach((error) => console.error(`- ${error}`));
    process.exit(1);
}

console.log('CAMPAIGN SPINE OK — New Game, two expeditions, return beat, climax, and two endings');
