#!/usr/bin/env node
'use strict';

// One-way #215 migration. The shared editor writer is the only writer used
// here: this proves the production save path can materialize and reassemble
// fragmented scenes before the legacy monolith is removed.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const storage = require('../../studio/editor/authored-storage');

const root = path.resolve(__dirname, '../..', 'data');
const monolith = path.join(root, 'scenes.json');
const backup = path.join(root, '.scenes.pre-split.json');
const original = fs.readFileSync(monolith, 'utf8');
const scenes = JSON.parse(original);
// The legacy monolith has a few compact object literals. The editor writer's
// canonical two-space form is the byte-level baseline for the migration.
const canonical = JSON.stringify(scenes, null, 2) + '\n';

const spec = storage.resourceSpec('scenes');
assert.strictEqual(spec.kind, 'ordered_collection');
assert.strictEqual(spec.representation, 'fragments');

assert(!fs.existsSync(backup), `migration backup already exists: ${backup}`);
fs.renameSync(monolith, backup);
try {
    storage.writeResource(root, 'scenes', scenes, spec);
    const reassembled = storage.loadResource(root, 'scenes', spec).value;
    assert.strictEqual(JSON.stringify(reassembled, null, 2) + '\n', canonical,
        'fragment round-trip differs from the editor-save serialization of the pre-split scenes monolith');
    fs.unlinkSync(backup);
} catch (error) {
    if (!fs.existsSync(monolith) && fs.existsSync(backup)) fs.renameSync(backup, monolith);
    throw error;
}

console.log(`Migrated ${scenes.length} scenes to data/scenes/ with a byte-identical round-trip.`);
