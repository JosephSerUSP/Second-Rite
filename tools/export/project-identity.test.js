'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const identity = require('./project-identity');

function projectRoot(name) {
    const parent = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-project-identity-'));
    const root = path.join(parent, name);
    fs.mkdirSync(path.join(root, 'data'), { recursive: true });
    return { parent, root };
}

test('an authored Project identity owns product, window, executable, and save identity', () => {
    const fixture = projectRoot('unrelated-directory-name');
    try {
        fs.writeFileSync(path.join(fixture.root, identity.PROJECT_IDENTITY_RELATIVE), JSON.stringify({
            schemaVersion: 1,
            name: 'Glass Orchard',
            identity: 'GlassOrchard',
            productName: 'Glass Orchard',
            executableName: 'Glass Orchard Player',
            buildSlug: 'glass-orchard',
            windowTitle: 'Glass Orchard — Chapter One',
            productVersion: '2.4.0',
        }), 'utf8');
        assert.deepEqual(identity.readProjectIdentity(fixture.root), {
            name: 'Glass Orchard',
            identity: 'GlassOrchard',
            productName: 'Glass Orchard',
            executableName: 'Glass Orchard Player',
            buildSlug: 'glass-orchard',
            windowTitle: 'Glass Orchard — Chapter One',
            productVersion: '2.4.0',
        });
    } finally {
        fs.rmSync(fixture.parent, { recursive: true, force: true });
    }
});

test('a Project without identity metadata receives only neutral Project-derived defaults', () => {
    const fixture = projectRoot('tiny-detective');
    try {
        const value = identity.readProjectIdentity(fixture.root);
        assert.equal(value.name, 'tiny-detective');
        assert.equal(value.productName, 'tiny-detective');
        assert.equal(value.executableName, 'tiny-detective');
        assert.equal(value.buildSlug, 'tiny-detective');
        assert.equal(value.identity, 'tiny-detective');
        assert.equal(value.windowTitle, 'tiny-detective');
        assert.equal(value.productVersion, identity.DEFAULT_PRODUCT_VERSION);
        assert.ok(!JSON.stringify(value).includes('Second Rite'));
        assert.ok(!JSON.stringify(value).includes('SecondRite'));
    } finally {
        fs.rmSync(fixture.parent, { recursive: true, force: true });
    }
});

test('unsafe or malformed Project identity fails loud', () => {
    const fixture = projectRoot('broken-project');
    const file = path.join(fixture.root, identity.PROJECT_IDENTITY_RELATIVE);
    try {
        for (const value of [
            { schemaVersion: 2, name: 'X' },
            { schemaVersion: 1, name: '' },
            { schemaVersion: 1, name: 'X', identity: '../shared-save' },
            { schemaVersion: 1, name: 'X', buildSlug: '../escape' },
            { schemaVersion: 1, name: 'X', executableName: 'bad/name' },
            { schemaVersion: 1, name: 'X', productName: 'bad:name' },
        ]) {
            fs.writeFileSync(file, JSON.stringify(value), 'utf8');
            assert.throws(() => identity.readProjectIdentity(fixture.root));
        }
        fs.writeFileSync(file, '{not-json', 'utf8');
        assert.throws(() => identity.readProjectIdentity(fixture.root), /not readable JSON/);
    } finally {
        fs.rmSync(fixture.parent, { recursive: true, force: true });
    }
});
