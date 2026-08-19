'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const toolRoot = __dirname;
const repoRoot = path.resolve(toolRoot, '..', '..');
const checkOnly = process.argv.slice(2).includes('--check');

// tsc emits source maps as separate files. Runtime Lua deliberately disables
// TypeScriptToLua's sourceMapTraceback runtime because that helper rewrites the
// process-wide debug.traceback hook when a generated leaf is merely required.
// The Lua targets therefore have no sibling map/runtime-hook artifact; only the
// real compiler outputs below belong in the stale-artifact contract.
const outputs = [
    path.join(repoRoot, 'tools', 'editor', 'js', 'generated', 'vertex-shading.js'),
    path.join(repoRoot, 'tools', 'editor', 'js', 'generated', 'vertex-shading.js.map'),
    path.join(repoRoot, 'tools', 'editor', 'js', 'generated', 'sprite-timing.js'),
    path.join(repoRoot, 'tools', 'editor', 'js', 'generated', 'sprite-timing.js.map'),
    path.join(repoRoot, 'engine', 'generated', 'vertex-shading.lua'),
    path.join(repoRoot, 'engine', 'generated', 'sprite-timing.lua'),
];

const adapters = [
    {
        file: path.join(repoRoot, 'tools', 'editor', 'js', 'generated', 'vertex-shading.js'),
        marker: 'THES_SHARED_COMMONJS_VERTEX_SHADING',
        text: '\n// THES_SHARED_COMMONJS_VERTEX_SHADING: generated host adapter; do not edit.\n'
            + "if (typeof module === 'object' && module.exports) module.exports = ThestraVertexShadingSemantics;\n",
    },
    {
        file: path.join(repoRoot, 'tools', 'editor', 'js', 'generated', 'sprite-timing.js'),
        marker: 'THES_SHARED_COMMONJS_SPRITE_TIMING',
        text: '\n// THES_SHARED_COMMONJS_SPRITE_TIMING: generated host adapter; do not edit.\n'
            + "if (typeof module === 'object' && module.exports) module.exports = ThestraSpriteTimingSemantics;\n",
    },
    {
        file: path.join(repoRoot, 'engine', 'generated', 'vertex-shading.lua'),
        marker: 'THES_SHARED_LUA_VERTEX_SHADING',
        text: '\n-- THES_SHARED_LUA_VERTEX_SHADING: generated module adapter; do not edit.\n'
            + 'return ThestraVertexShadingSemantics\n',
    },
    {
        file: path.join(repoRoot, 'engine', 'generated', 'sprite-timing.lua'),
        marker: 'THES_SHARED_LUA_SPRITE_TIMING',
        text: '\n-- THES_SHARED_LUA_SPRITE_TIMING: generated module adapter; do not edit.\n'
            + 'return ThestraSpriteTimingSemantics\n',
    },
];

function compilerScript(name) {
    if (name === 'tsc') return path.join(toolRoot, 'node_modules', 'typescript', 'bin', 'tsc');
    if (name === 'tstl') return path.join(toolRoot, 'node_modules', 'typescript-to-lua', 'dist', 'tstl.js');
    throw new Error(`unknown compiler ${name}`);
}

function runCompiler(name, config) {
    const script = compilerScript(name);
    if (!fs.existsSync(script)) {
        throw new Error(`shared semantics compiler is missing: ${script}. Run npm ci in tools/shared-semantics.`);
    }
    const result = spawnSync(process.execPath, [script, '-p', config], {
        cwd: toolRoot,
        encoding: 'utf8',
        windowsHide: true,
    });
    if (result.status !== 0) {
        process.stdout.write(result.stdout || '');
        process.stderr.write(result.stderr || '');
        throw new Error(`${name} generation failed with exit ${result.status}`);
    }
}

function snapshot() {
    const state = new Map();
    for (const file of outputs) state.set(file, fs.existsSync(file) ? fs.readFileSync(file) : null);
    return state;
}

function restore(state) {
    for (const [file, data] of state) {
        if (data === null) fs.rmSync(file, { force: true });
        else {
            fs.mkdirSync(path.dirname(file), { recursive: true });
            fs.writeFileSync(file, data);
        }
    }
}

function appendAdapters() {
    for (const adapter of adapters) {
        if (!fs.existsSync(adapter.file)) throw new Error(`compiler did not produce ${adapter.file}`);
        const current = fs.readFileSync(adapter.file, 'utf8');
        if (current.includes(adapter.marker)) continue;
        fs.writeFileSync(adapter.file, current.replace(/\s*$/, '') + adapter.text);
    }
}

function normalizedText(data) {
    return data == null ? null : data.toString('utf8').replace(/\r\n/g, '\n');
}

function changedFiles(before) {
    const changed = [];
    for (const file of outputs) {
        const oldData = before.get(file);
        const newData = fs.existsSync(file) ? fs.readFileSync(file) : null;
        if (oldData === null || newData === null
                || normalizedText(oldData) !== normalizedText(newData)) {
            changed.push(path.relative(repoRoot, file).replaceAll('\\', '/'));
        }
    }
    return changed;
}

function outputDigest() {
    const hash = crypto.createHash('sha256');
    let bytes = 0;
    for (const file of outputs) {
        if (!fs.existsSync(file)) throw new Error(`generated output is missing: ${file}`);
        const data = fs.readFileSync(file);
        const relative = path.relative(repoRoot, file).replaceAll('\\', '/');
        hash.update(relative);
        hash.update(normalizedText(data));
        bytes += Buffer.byteLength(normalizedText(data), 'utf8');
    }
    return { sha256: hash.digest('hex'), bytes, files: outputs.length };
}

function main() {
    const before = snapshot();
    let stale = null;
    try {
        runCompiler('tsc', 'tsconfig.js.json');
        runCompiler('tstl', 'tsconfig.lua.json');
        appendAdapters();
        const changed = changedFiles(before);
        if (checkOnly && changed.length) stale = changed;
        const digest = outputDigest();
        console.log(`shared semantics generated: ${digest.files} files, ${digest.bytes} normalized bytes, sha256=${digest.sha256}`);
    } finally {
        if (checkOnly) restore(before);
    }
    if (stale) {
        throw new Error('generated shared semantics are stale; run npm run build in tools/shared-semantics:\n- '
            + stale.join('\n- '));
    }
    if (checkOnly) console.log('shared semantics generated outputs are current.');
}

try {
    main();
} catch (error) {
    console.error(error && error.stack ? error.stack : error);
    process.exitCode = 1;
}