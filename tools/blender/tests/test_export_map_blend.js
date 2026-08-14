'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const exporter = require('../export_map_blend');

test('parseArgs keeps map, output, seed and project root explicit', () => {
    assert.deepStrictEqual(
        exporter.parseArgs(['8', '--output', 'x.blend', '--seed', '42', '--project-root', 'P']),
        { map: '8', output: 'x.blend', seed: '42', projectRoot: 'P' }
    );
});

test('readMap resolves an id through project data/maps', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'map-blend-test-'));
    try {
        fs.mkdirSync(path.join(root, 'data', 'maps'), { recursive: true });
        fs.writeFileSync(path.join(root, 'data', 'maps', '8.json'), JSON.stringify({ id: 8, name: 'Room' }));
        const loaded = exporter.readMap('8', root);
        assert.equal(loaded.map.id, 8);
        assert.equal(exporter.defaultOutput(loaded.map, root), path.join(root, 'exports', 'maps', '8-Room.blend'));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('exportMapBlend passes the authoritative bundle to Blender and cleans the temporary file', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'map-blend-test-'));
    try {
        fs.mkdirSync(path.join(root, 'data', 'maps'), { recursive: true });
        fs.writeFileSync(path.join(root, 'data', 'maps', '8.json'), JSON.stringify({ id: 8, name: 'Room' }));
        const calls = [];
        const output = path.join(root, 'out.blend');
        await exporter.exportMapBlend({
            map: '8',
            output,
            projectRoot: root,
            installRoot: root,
            services: { projectRoot: { PROJECT_ROOT: root, INSTALL_ROOT: root }, compileRenderable: null },
            blender: 'fake-blender',
            compileRenderable: async request => ({ version: 1, map: request.map, materials: [], surfaces: [] }),
            execFileSync: (exe, args) => {
                calls.push({ exe, args });
                const divider = args.indexOf('--');
                const bundlePath = args[divider + 1];
                assert.deepStrictEqual(JSON.parse(fs.readFileSync(bundlePath, 'utf8')), {
                    version: 1,
                    map: { id: 8, name: 'Room' },
                    materials: [],
                    surfaces: [],
                });
            },
        });
        assert.equal(output, path.resolve(root, 'out.blend'));
        assert.equal(calls.length, 1);
        assert.equal(calls[0].exe, 'fake-blender');
        assert.ok(calls[0].args.some(value => String(value).endsWith('import_map_bundle.py')));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
