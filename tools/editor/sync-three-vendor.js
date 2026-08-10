'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const THREE_ROOT = path.join(ROOT, 'node_modules', 'three');
const TARGET = path.join(__dirname, 'vendor', 'three');

const files = [
    ['build/three.module.js', 'three.module.js'],
    ['examples/jsm/controls/OrbitControls.js', 'OrbitControls.js']
];

if (!fs.existsSync(THREE_ROOT)) {
    throw new Error('Three.js is not installed. Run npm install before launching the Developer Studio.');
}

fs.mkdirSync(TARGET, { recursive: true });
files.forEach(([source, dest]) => {
    const from = path.join(THREE_ROOT, ...source.split('/'));
    const to = path.join(TARGET, dest);
    fs.copyFileSync(from, to);
});
console.log(`Prepared Three.js editor backend in ${path.relative(ROOT, TARGET)}`);
