'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const SAFE = /^[a-z0-9][a-z0-9_-]{0,63}$/;

function assertProjectRoot(projectRoot) {
    const root = path.resolve(projectRoot || '');
    if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) throw new Error(`Project root does not exist: ${root}`);
    if (!fs.existsSync(path.join(root, 'data')) && !fs.existsSync(path.join(root, 'docs'))) throw new Error(`Not a Project root (missing data/ or docs/): ${root}`);
    return root;
}
function assertSafeName(name) { if (typeof name !== 'string' || !SAFE.test(name)) throw new Error(`unsafe name '${name}'`); return name; }
function researchRoot(projectRoot) { return path.join(assertProjectRoot(projectRoot), 'docs', 'research', 'npc-gauntlets'); }
function outputRoot(installRoot, projectRoot) { const resolved = path.resolve(projectRoot), slug = path.basename(resolved).replace(/[^a-z0-9_-]/gi, '_').toLowerCase(), identity = sha256(resolved).slice(0, 8); return path.join(path.resolve(installRoot || process.cwd()), 'out', 'npc-gauntlets', `${slug}-${identity}`); }
function ensureDir(dir) { fs.mkdirSync(dir, { recursive: true }); return dir; }
function sha256(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function sha256File(file) { return sha256(fs.readFileSync(file)); }
function stableJson(value) {
    if (Array.isArray(value)) return `[${value.map(stableJson).join(',')}]`;
    if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(',')}}`;
    return JSON.stringify(value);
}
function writeAtomic(file, value, raw = false) {
    ensureDir(path.dirname(file));
    const text = raw ? String(value) : JSON.stringify(value, null, 2) + '\n';
    const temp = `${file}.${process.pid}.${Date.now()}.${crypto.randomBytes(6).toString('hex')}.tmp`;
    fs.writeFileSync(temp, text, 'utf8');
    fs.renameSync(temp, file);
    return file;
}
function readJson(file, fallback) {
    if (!fs.existsSync(file)) return fallback;
    return JSON.parse(fs.readFileSync(file, 'utf8'));
}
function listJson(dir) {
    if (!fs.existsSync(dir)) return [];
    return fs.readdirSync(dir).filter(file => file.endsWith('.json')).sort();
}
function safeJoin(root, relative) {
    const base = path.resolve(root), target = path.resolve(base, relative);
    if (target !== base && !target.startsWith(base + path.sep)) throw new Error(`path escapes root: ${relative}`);
    return target;
}
function copyTree(source, target) {
    if (!fs.existsSync(source)) return;
    fs.mkdirSync(target, { recursive: true });
    for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
        const from = path.join(source, entry.name), to = path.join(target, entry.name);
        if (entry.isDirectory()) copyTree(from, to); else fs.copyFileSync(from, to);
    }
}

module.exports = { assertProjectRoot, assertSafeName, researchRoot, outputRoot, ensureDir,
    sha256, sha256File, stableJson, writeAtomic, readJson, listJson, safeJoin, copyTree };
