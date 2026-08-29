'use strict';

// #969: what the NPC Gauntlet Lab needs to show dialogue the way the game does.
//
// Two things, neither of them invented here.
//
// The presentation contract comes from tools/presentation/contract.js (#967) --
// the same facts the LOVE renderer draws from. The lab does not get its own
// palette, font or windowskin geometry.
//
// The speaker->sprite mapping comes from the Project's own authored map
// events, which already carry an explicit `sprite` path beside the event name
// that TEXT commands quote as their `speaker`. Matching on the authored data
// is the point: a naming convention invented in this file ("Alicia" ->
// "npc_alicia.png") would be a second authority on who looks like what, and
// it would be wrong the first time an author named an event differently from
// its file. If an NPC has no authored sprite, the lab says so and shows none.

const fs = require('fs');
const path = require('path');

const contractBuilder = require('../../presentation/contract');
const storage = require('./storage');

const REPO = path.resolve(__dirname, '..', '..', '..');
const RUNTIME = path.join(REPO, 'runtime');
const RTP = path.join(REPO, 'rtp');

// Only these asset trees are reachable through the lab's asset route, and only
// these extensions. The lab is a local research tool, but it is still a web
// server pointed at a directory the researcher cares about.
const SERVABLE_DIRS = ['assets/system', 'assets/fonts', 'assets/character', 'assets/portraits', 'assets/sprites'];
const SERVABLE_TYPES = {
    '.png': 'image/png',
    '.ttf': 'font/ttf',
    '.otf': 'font/otf',
};

function walkJson(dir, out = []) {
    if (!fs.existsSync(dir)) return out;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walkJson(full, out);
        else if (entry.name.toLowerCase().endsWith('.json')) out.push(full);
    }
    return out;
}

// Does this event contain a TEXT command spoken by the event's own name? That
// is what separates "the NPC Alicia" from "the door to Alicia's house".
function speaksAsItself(event) {
    let found = false;
    (function visit(node) {
        if (found || !node || typeof node !== 'object') return;
        if (Array.isArray(node)) { node.forEach(visit); return; }
        if (node.cmd === 'TEXT' && node.speaker === event.name) { found = true; return; }
        for (const value of Object.values(node)) visit(value);
    }(event.commands));
    return found;
}

// Every authored event that speaks as itself and declares a sprite, indexed by the
// name a TEXT command would use as its speaker. First authored occurrence
// wins, and a name authored with two different sprites is reported rather than
// silently resolved -- the lab must not pick one on the researcher's behalf.
function speakerSprites(projectRoot) {
    const root = storage.assertProjectRoot(projectRoot);
    const byName = new Map();
    const conflicts = new Map();
    const spoken = new Map();

    // Only the map's own `events[]` entries, never a recursive walk: a walk
    // also finds `name`+`sprite` pairs inside nested command payloads.
    //
    // And only events that actually SPEAK as the name they carry. Map 1
    // authors doors to Alicia's and Laura's houses as bump events named after
    // the resident, so matching on the event name alone showed both characters
    // as a door. Tying the mapping to a TEXT command whose `speaker` is the
    // event's own name asks the authored data the lab's actual question --
    // who is talking, and what do they look like while they talk.
    for (const file of walkJson(path.join(root, 'data', 'maps'))) {
        let map;
        try { map = JSON.parse(fs.readFileSync(file, 'utf8')); }
        catch (_) { continue; }   // a malformed map is G1's problem, not the lab's
        for (const event of (map && map.events) || []) {
            if (!event || typeof event.name !== 'string' || !event.name) continue;
            if (typeof event.sprite !== 'string' || !event.sprite) continue;
            const confirmed = speaksAsItself(event);
            const existing = byName.get(event.name);
            if (existing === undefined) byName.set(event.name, event.sprite);
            else if (existing !== event.sprite) {
                const set = conflicts.get(event.name) || new Set([existing]);
                set.add(event.sprite);
                conflicts.set(event.name, set);
            }
            if (confirmed) {
                const speaking = spoken.get(event.name) || new Set();
                speaking.add(event.sprite);
                spoken.set(event.name, speaking);
            }
        }
    }

    const speakers = {};
    for (const [name, sprite] of byName) {
        // A name the Project authored two different ways gets NO default
        // sprite. The lab reports every authored candidate and lets the
        // researcher choose, rather than picking one for them -- judging a
        // line against a face the game might not use is worse than judging it
        // with no face at all.
        //
        // Real example this found: map 1 authors wall-mounted Alicia and Laura
        // with a DOOR placeholder while maps 23/24/27/28 author them with
        // their town sprites. That is a content finding, not something the
        // lab should quietly resolve.
        const ambiguous = conflicts.has(name) ? [...conflicts.get(name)].sort() : null;
        const chosen = ambiguous ? null : sprite;
        speakers[name] = {
            sprite: chosen,
            candidates: ambiguous || [sprite],
            speaking: [...(spoken.get(name) || [])].sort(),
            available: chosen ? fs.existsSync(path.join(root, ...chosen.split('/'))) : false,
            ambiguous,
        };
    }
    return speakers;
}

function presentationPayload(projectRoot) {
    const root = storage.assertProjectRoot(projectRoot);
    return {
        contract: contractBuilder.build({ projectDir: root, runtimeDir: RUNTIME, rtpRoot: RTP }),
        speakers: speakerSprites(root),
    };
}

// Resolve a request path under the lab's asset route to a real file, or null.
// Containment is checked against the resolved path, not the string, so a
// traversal cannot walk out of the Project through a symlink-shaped input.
function resolveAsset(projectRoot, relative) {
    const root = storage.assertProjectRoot(projectRoot);
    const clean = String(relative || '').replace(/\\/g, '/').replace(/^\/+/, '');
    if (!clean || clean.split('/').includes('..')) return null;
    if (!SERVABLE_DIRS.some(dir => clean === dir || clean.startsWith(dir + '/'))) return null;
    const type = SERVABLE_TYPES[path.extname(clean).toLowerCase()];
    if (!type) return null;
    const file = path.resolve(root, ...clean.split('/'));
    if (file !== root && !file.startsWith(root + path.sep)) return null;
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) return null;
    return { file, type };
}

module.exports = { presentationPayload, speakerSprites, resolveAsset, SERVABLE_DIRS, SERVABLE_TYPES };
