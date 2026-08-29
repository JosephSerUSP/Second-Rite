'use strict';

// #969 pilot tests.
//
// The pixels are #968's problem (the adapter is measured against the real LOVE
// renderer). What is the LAB's problem is everything it decides for itself:
// which sprite a speaker gets, whether it admits when it does not know, and
// whether the asset route it opened can be walked out of.

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');

const presentation = require('./lib/presentation');

const REPO = path.resolve(__dirname, '..', '..');
const PROJECT = path.join(REPO, 'projects', 'hichaukitoden-game');

test('speakers resolve to the sprite the Project authors for them', () => {
    const speakers = presentation.speakerSprites(PROJECT);
    assert.ok(Object.keys(speakers).length > 10, 'expected the Project to author many named events');

    const agnes = speakers.Agnes;
    assert.ok(agnes, 'Agnes is an authored map event');
    assert.strictEqual(agnes.sprite, 'assets/character/town/npc_agnes.png');
    assert.strictEqual(agnes.available, true);
    assert.strictEqual(agnes.ambiguous, null);
});

test('a speaker the Project authors two ways gets no sprite, and says why', () => {
    // Real content state as of this commit: map 1 authors wall-mounted Alicia
    // and Laura as bump events wearing a door placeholder, while maps
    // 23/24/27/28 author them with their town sprites. The lab must report
    // that rather than pick, so a researcher never judges a line against a
    // face the game might not use.
    const speakers = presentation.speakerSprites(PROJECT);
    for (const name of ['Alicia', 'Laura']) {
        const entry = speakers[name];
        assert.ok(entry, `${name} is an authored map event`);
        assert.strictEqual(entry.sprite, null, `${name} must get no default sprite while ambiguous`);
        assert.ok(Array.isArray(entry.ambiguous) && entry.ambiguous.length > 1,
            `${name} must report every authored candidate`);
        assert.ok(entry.ambiguous.includes(`assets/character/town/npc_${name.toLowerCase()}.png`),
            `${name}'s town sprite must be among the candidates`);
    }
});

test('nested command payloads are not mistaken for events', () => {
    // The first implementation walked the whole map recursively and matched
    // any object carrying `name` and `sprite`, which resolved characters to
    // door graphics buried inside command payloads. Only `events[]` counts.
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gauntlet-presentation-'));
    const maps = path.join(root, 'data', 'maps');
    fs.mkdirSync(maps, { recursive: true });
    fs.mkdirSync(path.join(root, 'docs'), { recursive: true });
    fs.writeFileSync(path.join(maps, '1.json'), JSON.stringify({
        id: 1,
        events: [{
            name: 'Real', sprite: 'assets/character/town/real.png',
            commands: [{ name: 'Decoy', sprite: 'assets/sprites/decoy.png', cmd: 'TEXT', text: 'x' }],
        }],
    }));

    const speakers = presentation.speakerSprites(root);
    assert.deepStrictEqual(Object.keys(speakers), ['Real']);
    assert.strictEqual(speakers.Real.sprite, 'assets/character/town/real.png');
    assert.strictEqual(speakers.Real.available, false, 'the fixture ships no image, so it must say so');
});

test('the presentation payload carries the contract, not a copy of it', () => {
    const payload = presentation.presentationPayload(PROJECT);
    assert.strictEqual(payload.contract.version, 1);
    assert.ok(/^[0-9a-f]{64}$/.test(payload.contract.identity), 'the payload must carry a contract identity to cache on');
    assert.ok(payload.contract.atlas.windowskin.parts.tl, 'the atlas comes from the contract');
    assert.ok(payload.speakers.Agnes);
});

test('the asset route serves only Project presentation assets', () => {
    for (const allowed of [
        'assets/system/windowskin_back.png',
        'assets/character/town/npc_agnes.png',
        'assets/fonts/monogram-extended-italic.ttf',
    ]) {
        assert.ok(presentation.resolveAsset(PROJECT, allowed), `${allowed} should be servable`);
    }

    for (const refused of [
        'data/system.json',                              // authored data is not an asset
        'assets/system/../../data/system.json',          // traversal through an allowed prefix
        '../runtime/presentation/presentation.json',     // out of the Project entirely
        'assets/system/README.md',                       // allowed tree, unservable type
        'assets/models/whatever.glb',                    // tree that is not presentation
        '',
    ]) {
        assert.strictEqual(presentation.resolveAsset(PROJECT, refused), null, `${refused} must be refused`);
    }
});
