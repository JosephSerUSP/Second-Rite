'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');

// This test mirrors the invariant enforced by sync-three-vendor.js without
// depending on checked-in generated vendor output. It proves the current npm
// package's retained browser surface is closed under relative module imports.
const ROOT = path.resolve(__dirname, '../../..');
const THREE_ROOT = path.join(ROOT, 'node_modules', 'three');
const RETAINED = [
    ['build/three.module.js', 'three.module.js'],
    ['build/three.core.js', 'three.core.js'],
    ['examples/jsm/controls/OrbitControls.js', 'OrbitControls.js'],
    ['examples/jsm/controls/TransformControls.js', 'TransformControls.js']
];

if (!fs.existsSync(THREE_ROOT)) {
    console.log('Three vendor surface test skipped: node_modules/three is not installed');
    process.exit(0);
}

const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-three-vendor-'));
try {
    for (const [source, dest] of RETAINED) {
        const from = path.join(THREE_ROOT, ...source.split('/'));
        assert(fs.existsSync(from), `installed Three package is missing retained module ${source}`);
        fs.copyFileSync(from, path.join(temp, dest));
    }

    const relativeSpecifier = /(?:from\s*|import\s*)['"](\.\.?\/[^'"]+)['"]/g;
    const missing = [];
    for (const [, dest] of RETAINED) {
        const source = fs.readFileSync(path.join(temp, dest), 'utf8');
        for (const match of source.matchAll(relativeSpecifier)) {
            if (!fs.existsSync(path.resolve(temp, match[1]))) {
                missing.push(`${dest} -> ${match[1]}`);
            }
        }
    }
    assert.deepStrictEqual(missing, [], `retained Three vendor surface is incomplete: ${missing.join(', ')}`);
    console.log('Three vendor surface test OK');
} finally {
    fs.rmSync(temp, { recursive: true, force: true });
}
