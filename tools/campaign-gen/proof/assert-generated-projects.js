'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

function readJson(root, relative) {
    return JSON.parse(fs.readFileSync(path.join(root, relative), 'utf8'));
}

function readUnits(root) {
    const index = readJson(root, 'data/units/index.json');
    return (index.files || []).map(file => readJson(root, `data/units/${file}`));
}

function allText(root) {
    const chunks = [];
    function walk(dir) {
        for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            const absolute = path.join(dir, entry.name);
            if (entry.isDirectory()) walk(absolute);
            else if (entry.isFile() && /\.(json|md)$/i.test(entry.name)) chunks.push(fs.readFileSync(absolute, 'utf8'));
        }
    }
    walk(root);
    return chunks.join('\n');
}

function assertNoSecondGateGrammar(root) {
    const text = allText(root);
    for (const forbidden of ['Second Gate', 'Summoner', 'Saban', 'Pixie', 'Cerberus', 'windBlade', 'Wind Blade']) {
        assert.ok(!text.includes(forbidden), `${path.basename(root)} leaked canonical game vocabulary: ${forbidden}`);
    }
    const assets = path.join(root, 'assets');
    const assetEntries = fs.existsSync(assets) ? fs.readdirSync(assets) : [];
    assert.deepStrictEqual(assetEntries, [], `${path.basename(root)} unexpectedly copied Project assets from Second Gate`);
}

function assertBotanists(root) {
    const roles = readJson(root, 'data/roles.json');
    const elements = readJson(root, 'data/elements.json');
    const skills = readJson(root, 'data/skills.json');
    const items = readJson(root, 'data/items.json');
    const quests = readJson(root, 'data/quests.json');
    const units = readUnits(root);
    const plan = readJson(root, 'game-plan.json');

    assert.deepStrictEqual(Object.keys(elements).sort(), ['Fungal', 'Verdant']);
    assert.deepStrictEqual(Object.keys(roles).sort(), ['FieldBotanist', 'GlasshouseKeeper', 'Hazard', 'Mycologist']);
    assert.deepStrictEqual(Object.keys(skills).sort(), ['clip_sample', 'spore_cloud', 'sterile_spray']);
    assert.deepStrictEqual(units.map(unit => unit.id).sort(), ['glass_mold', 'ivo_reed', 'mara_quill', 'senna_moss']);
    assert.deepStrictEqual(items, []);
    assert.deepStrictEqual(quests, {});
    assert.deepStrictEqual(plan.stages, ['units', 'maps']);
    assert.strictEqual(readJson(root, 'data/system.json').rtp.revision, '1.0');
    assertNoSecondGateGrammar(root);
}

function assertRelay(root) {
    const emptyObjects = ['elements.json', 'roles.json', 'skills.json', 'states.json', 'passives.json', 'quests.json', 'shops.json', 'troops.json'];
    for (const file of emptyObjects) assert.deepStrictEqual(readJson(root, `data/${file}`), {}, `${file} should stay empty`);
    assert.deepStrictEqual(readJson(root, 'data/items.json'), []);
    assert.deepStrictEqual(readJson(root, 'data/commonEvents.json'), []);
    assert.deepStrictEqual(readJson(root, 'data/units/index.json'), { files: [] });
    const plan = readJson(root, 'game-plan.json');
    assert.deepStrictEqual(plan.stages, []);
    assert.strictEqual(plan.capabilities.combat, false);
    assert.strictEqual(plan.capabilities.customScenes, true);
    const sceneIndex = readJson(root, 'data/scenes/index.json');
    assert.ok(sceneIndex.files.length >= 5, 'relay proof should be Scene-driven');
    assert.strictEqual(readJson(root, 'data/system.json').rtp.revision, '1.0');
    assertNoSecondGateGrammar(root);
}

if (process.argv.length !== 4) {
    throw new Error('Usage: node assert-generated-projects.js <botanists-project> <relay-project>');
}
const botanists = path.resolve(process.argv[2]);
const relay = path.resolve(process.argv[3]);
assertBotanists(botanists);
assertRelay(relay);
console.log('ISSUE 486 GENERATED PROJECT GRAMMAR PROOF OK');
