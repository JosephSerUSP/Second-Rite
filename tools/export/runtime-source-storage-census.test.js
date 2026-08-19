'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const compiler = require('./runtime-data-compiler');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const SOURCE_STORAGE_REQUIRE = /require\s*\(\s*["']engine\.data\.authored_storage(?:_resolved)?["']\s*\)/g;

// Every production-code consumer here has an explicit player-boundary fate.
// Nothing is allowed merely because it happens not to be reached by today's
// boot smoke. Repository source lives under runtime/; the compiled player's
// logical filesystem intentionally remains flat engine/**.
const SOURCE_ONLY = new Map([
    ['runtime/engine/data/authored_storage_resolved.lua', 'removed'],
    ['runtime/engine/data/semantic_resources.lua', 'replaced'],
    ['runtime/engine/server.lua', 'replaced'],
    ['runtime/engine/model_census_review.lua', 'removed'],
]);

function walk(directory, visit) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
        if (entry.name === '.git' || entry.name === 'node_modules') continue;
        const absolute = path.join(directory, entry.name);
        if (entry.isDirectory()) walk(absolute, visit);
        else if (entry.isFile()) visit(absolute);
    }
}

function portable(filePath) {
    return path.relative(REPO_ROOT, filePath).split(path.sep).join('/');
}

test('authored physical storage has no undeclared Lua consumers', () => {
    const references = [];
    walk(REPO_ROOT, filePath => {
        if (path.extname(filePath).toLowerCase() !== '.lua') return;
        const text = fs.readFileSync(filePath, 'utf8');
        SOURCE_STORAGE_REQUIRE.lastIndex = 0;
        if (SOURCE_STORAGE_REQUIRE.test(text)) references.push(portable(filePath));
    });
    references.sort();

    const allowed = new Set(SOURCE_ONLY.keys());
    const unexpected = references.filter(file => !allowed.has(file));
    const missing = [...allowed].filter(file => !references.includes(file));
    assert.deepEqual(unexpected, [],
        `undeclared Lua authored-storage consumers: ${unexpected.join(', ')}`);
    assert.deepEqual(missing, [],
        `source-storage census is stale; remove entries that no longer require it: ${missing.join(', ')}`);
});

test('every production source-storage consumer has an explicit compiled-player fate', () => {
    assert.ok(compiler.SOURCE_STORAGE_RUNTIME_FILES.includes('engine/data/authored_storage_resolved.lua'),
        'resolved source adapter must be deleted from compiled runtime engine/data/');
    assert.ok(compiler.SOURCE_ONLY_PLAYER_FILES.includes('engine/model_census_review.lua'),
        'physical-source model review harness must be deleted from compiled players');

    const compiledProvider = fs.readFileSync(compiler.DEFAULT_RUNTIME_PROVIDER, 'utf8');
    assert.doesNotMatch(compiledProvider, /authored_storage/,
        'compiled semantic provider must not retain physical storage vocabulary');
    const compiledServer = fs.readFileSync(compiler.DEFAULT_RUNTIME_SERVER, 'utf8');
    assert.doesNotMatch(compiledServer, /engine\.data\.authored_storage/,
        'compiled engine server must not retain authored-resource persistence authority');
});
