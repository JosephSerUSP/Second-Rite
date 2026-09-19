'use strict';

// #410 authored corpus migration. The registry is inherited from RTP, so this
// intentionally edits only the RTP registry source, never a Project's
// engine.json policy overlay. Use --write to materialize the deterministic
// output; the default is a no-write census suitable for review/CI.
const fs = require('node:fs');
const path = require('node:path');
const ROOT = path.resolve(__dirname, '..', '..');
const WRITE = process.argv.includes('--write');
const stats = { files: 0, scene: 0, locals: 0, guards: 0, split: 0, dead: 0, seeds: 0 };

function rel(file) { return path.relative(ROOT, file).replaceAll('\\', '/'); }
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function json(raw, value) {
    if (!raw.includes('\n')) return JSON.stringify(value);
    const indent = (raw.match(/\n( +)"/) || [])[1]?.length || 2;
    return JSON.stringify(value, null, indent) + (raw.endsWith('\n') ? '\n' : '');
}
function files(dir, out = []) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (entry.name === '.git' || entry.name === 'node_modules') continue;
        const file = path.join(dir, entry.name);
        if (entry.isDirectory()) files(file, out);
        else if (entry.name.endsWith('.json')) out.push(file);
    }
    return out;
}
function isProjectEngine(file) {
    const r = rel(file);
    return /^projects\/[^/]+\/data\/engine\.json$/.test(r);
}
function isRtpEngine(file) { return rel(file) === 'rtp/revisions/1.0/data/engine.json'; }
function sceneOwned(file) {
    const r = rel(file);
    return /\/data\/scenes\//.test(r) || /\/data\/scene_overrides\.json$/.test(r)
        || /^studio\/editor\/templates\/scenes\//.test(r);
}
function dead(file, command) {
    const r = rel(file);
    return command?.cmd === 'SET_VAR' && (
        (r === 'projects/hichaukitoden-game/data/maps/8.json' && command.name === 'return_count')
        || (/\/data\/flows\/progression\.json$/.test(r)
            && (command.name === 'reachedLevel' || command.name === 'levelsGained'))
    );
}
function stateString(value, scene) {
    if (typeof value !== 'string') return value;
    if (scene) return value
        .replace(/\bctx\.v\b/g, 'ctx.sceneState')
        .replace(/\bv\._guard\b/g, 'locals._guard')
        .replace(/\bv\./g, 'sceneState.')
        .replace(/\bv:/g, 'sceneState:')
        .replace(/\blocal\s+v\s*=\s*ctx\.sceneState\b/g, 'local sceneState = ctx.sceneState');
    return value
        .replace(/\bctx\.v\b/g, 'ctx.locals')
        .replace(/\bv\./g, 'locals.')
        .replace(/\blocal\s+v\s*=\s*ctx\.locals\b/g, 'local locals = ctx.locals');
}
function owner(command, scene) {
    const rows = Array.isArray(command.assignments) ? command.assignments : [];
    const names = [command.name, ...rows.map(row => row?.name)].filter(Boolean);
    if (!scene) return 'local';
    return names.includes('_guard') ? 'local' : 'scene';
}
function split(command) {
    if (!Array.isArray(command.assignments)) return [command];
    const groups = [];
    for (const row of command.assignments) {
        const nextOwner = row?.name === '_guard' ? 'local' : 'scene';
        if (!groups.length || groups.at(-1).owner !== nextOwner) {
            const next = clone(command); delete next.name; delete next.value; next.assignments = [];
            groups.push({ owner: nextOwner, command: next });
        }
        groups.at(-1).command.assignments.push(row);
    }
    return groups.map(group => group.command);
}
function transform(value, scene, file) {
    if (Array.isArray(value)) {
        const out = [];
        for (const item of value) {
            if (scene && item?.cmd === 'SET_VAR' && Array.isArray(item.assignments)
                    && item.assignments.some(row => row?.name === '_guard')
                    && item.assignments.some(row => row?.name && row.name !== '_guard')) {
                stats.split += 1;
                for (const part of split(item)) out.push(transform(part, scene, file));
            } else {
                const next = transform(item, scene, file);
                if (next !== null) out.push(next);
            }
        }
        return out;
    }
    if (!value || typeof value !== 'object') return stateString(value, scene);
    if (dead(file, value)) { stats.dead += 1; return null; }
    const next = {};
    for (const [key, child] of Object.entries(value)) next[key] = transform(child, scene, file);
    if (next.cmd === 'SET_VAR') {
        const target = owner(next, scene);
        next.cmd = target === 'scene' ? 'SET_SCENE_STATE' : 'SET_LOCAL';
        if (target === 'scene') stats.scene += 1;
        else { stats.locals += 1; if (scene) stats.guards += 1; }
    }
    if (next.cmd === 'SCENE_EVENT' && Object.hasOwn(next, 'vars')) {
        if (Object.hasOwn(next, 'sceneState')) throw new Error(`${rel(file)} contains both SCENE_EVENT vars and sceneState`);
        next.sceneState = next.vars; delete next.vars; stats.seeds += 1;
    }
    return next;
}
function migrateRegistry(file) {
    const raw = fs.readFileSync(file, 'utf8'), data = JSON.parse(raw);
    data.formulaHelp = (data.formulaHelp || []).filter(item => item.token !== 'v').map(item => ({
        ...item, description: stateString(item.description, true)
    }));
    data.scriptingHelp = (data.scriptingHelp || []).filter(item => item.token !== 'ctx.v');
    data.commands = (data.commands || []).filter(item => item.id !== 'SET_VAR');
    for (const command of data.commands) {
        if (command.id !== 'SCENE_EVENT') continue;
        for (const param of command.params || []) if (param.key === 'vars') param.key = 'sceneState';
        command.description = stateString(command.description, true)
            ?.replace(/Optional vars/g, 'Optional Scene State')
            ?.replace(/pushed scene's v/g, "pushed scene's Scene State");
    }
    return [raw, json(raw, transform(data, true, file))];
}
function migrate(file) {
    const raw = fs.readFileSync(file, 'utf8');
    // Do not parse/re-serialize an unrelated JSON artifact. Apart from making
    // the review unusable, that would turn spelling such as 0.0 into 0 and
    // falsely claim it was migration output.
    if (!isRtpEngine(file) && !/SET_VAR|\bv\.|ctx\.v|"vars"|v:/.test(raw)) return;
    // A Project engine.json is a policy overlay, not a registry: never add
    // inherited commands/help to it. Its layout and window formulas are still
    // authored Scene reads and must migrate with the rest of the corpus.
    const next = isRtpEngine(file) ? migrateRegistry(file)[1]
        : json(raw, transform(JSON.parse(raw), sceneOwned(file) || isProjectEngine(file), file));
    if (next === raw) return;
    stats.files += 1;
    if (WRITE) fs.writeFileSync(file, next, 'utf8');
}
for (const root of ['projects', 'rtp', 'studio/editor/templates']) files(path.join(ROOT, root)).forEach(migrate);
console.log(JSON.stringify({ mode: WRITE ? 'write' : 'dry-run', ...stats }, null, 2));
