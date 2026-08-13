'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const THREE_ROOT = path.join(ROOT, 'node_modules', 'three');
const TARGET = path.join(__dirname, 'vendor', 'three');

// Keep this list explicit. The browser backend is deliberately a tiny retained
// surface rather than a copy of the whole npm package, but `three.module.js`
// itself imports `./three.core.js` in current Three releases. Missing a build
// dependency makes the dynamic import fail only when the 3D workspace is first
// opened, while the ordinary 2D editor continues to look healthy.
const files = [
    ['build/three.module.js', 'three.module.js'],
    ['build/three.core.js', 'three.core.js'],
    ['examples/jsm/controls/OrbitControls.js', 'OrbitControls.js'],
    // #277: the item model preview renders through the same backend as the map
    // workspace rather than keeping a second hand-written OBJ parser and
    // projection. The map viewport builds geometry from authoritative runtime
    // bundles and needs no loader; the picker reads authored .obj/.mtl directly
    // and does, so these are vendored for it.
    ['examples/jsm/loaders/OBJLoader.js', 'OBJLoader.js'],
    ['examples/jsm/loaders/MTLLoader.js', 'MTLLoader.js']
];

if (!fs.existsSync(THREE_ROOT)) {
    throw new Error('Three.js is not installed. Run npm install before launching the Developer Studio.');
}

fs.mkdirSync(TARGET, { recursive: true });
files.forEach(([source, dest]) => {
    const from = path.join(THREE_ROOT, ...source.split('/'));
    if (!fs.existsSync(from)) {
        throw new Error(`Three.js editor dependency is missing from the installed package: ${source}`);
    }
    const to = path.join(TARGET, dest);
    fs.copyFileSync(from, to);
});

// Ratchet the retained vendor surface against future Three package changes.
// Every relative static import/export from a copied module must resolve inside
// TARGET. Bare imports (notably OrbitControls -> "three") are intentionally
// resolved by the editor import map and are not checked here.
const relativeSpecifier = /(?:from\s*|import\s*)['"](\.\.?\/[^'"]+)['"]/g;
const missing = [];
for (const [, dest] of files) {
    const filePath = path.join(TARGET, dest);
    const source = fs.readFileSync(filePath, 'utf8');
    for (const match of source.matchAll(relativeSpecifier)) {
        const resolved = path.resolve(path.dirname(filePath), match[1]);
        if (!fs.existsSync(resolved)) {
            missing.push(`${dest} -> ${match[1]}`);
        }
    }
}
if (missing.length) {
    throw new Error(
        'Three.js retained vendor surface is incomplete. Add the missing relative dependencies to sync-three-vendor.js:\n' +
        missing.map(item => `  - ${item}`).join('\n')
    );
}

console.log(`Prepared Three.js editor backend in ${path.relative(ROOT, TARGET)} (${files.length} modules)`);
