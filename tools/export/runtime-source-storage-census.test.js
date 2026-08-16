'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const SOURCE_STORAGE_REQUIRE = /require\s*\(\s*["']data\.authored_storage(?:_resolved)?["']\s*\)/g;

// These are source/authoring-side modules by design. A compiled player replaces
// semantic_resources.lua and engine/server.lua, and removes both authored
// storage modules. Any *new* Lua consumer is therefore an architecture change
// that must be explicit rather than silently making physical storage runtime
// vocabulary again.
const ALLOWED = new Set([
    'data/authored_storage_resolved.lua',
    'data/semantic_resources.lua',
    'engine/server.lua',
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

test('authored physical storage has no undeclared Lua runtime consumers', () => {
    const references = [];
    walk(REPO_ROOT, filePath => {
        if (path.extname(filePath).toLowerCase() !== '.lua') return;
        const text = fs.readFileSync(filePath, 'utf8');
        SOURCE_STORAGE_REQUIRE.lastIndex = 0;
        if (SOURCE_STORAGE_REQUIRE.test(text)) references.push(portable(filePath));
    });
    references.sort();

    const unexpected = references.filter(file => !ALLOWED.has(file));
    const missing = [...ALLOWED].filter(file => !references.includes(file));
    assert.deepEqual(unexpected, [],
        `undeclared Lua authored-storage consumers: ${unexpected.join(', ')}`);
    assert.deepEqual(missing, [],
        `source-storage allowlist is stale; remove entries that no longer require it: ${missing.join(', ')}`);
});
