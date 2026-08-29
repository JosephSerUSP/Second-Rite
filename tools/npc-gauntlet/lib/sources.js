'use strict';

const fs = require('fs');
const path = require('path');
const storage = require('./storage');

function walk(dir, out = []) {
    if (!fs.existsSync(dir)) return out;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
        if (entry.name === 'archive' || entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full, out); else out.push(full);
    }
    return out;
}

function discoverSources(projectRoot) {
    const root = storage.assertProjectRoot(projectRoot), candidates = [];
    for (const relativeRoot of ['docs', 'data']) {
        for (const file of walk(path.join(root, relativeRoot))) {
            if (!/\.(md|json)$/i.test(file)) continue;
            const relative = path.relative(root, file).replace(/\\/g, '/');
            if (relative.includes('/archive/')) continue;
            candidates.push({ path: relative, sha256: storage.sha256File(file), bytes: fs.statSync(file).size });
        }
    }
    return candidates;
}

function collectDialogue(value, pointer = '$', out = []) {
    if (Array.isArray(value)) { value.forEach((item, i) => collectDialogue(item, `${pointer}[${i}]`, out)); return out; }
    if (!value || typeof value !== 'object') return out;
    if (typeof value.speaker === 'string' && typeof value.text === 'string' && value.text.trim()) {
        out.push({ speaker: value.speaker, text: value.text.trim(), pointer });
    }
    for (const [key, child] of Object.entries(value)) collectDialogue(child, `${pointer}.${key}`, out);
    return out;
}

function collectMarkdownDialogue(text, out = []) {
    // Keep the extractor deliberately conservative: only a simple
    // `Speaker: line` form is treated as dialogue, so prose headings and
    // design notes are not accidentally presented as NPC facts.
    String(text || '').split(/\r?\n/).forEach((line, index) => {
        const match = line.match(/^\s*[-*]?\s*([A-Za-z][A-Za-z0-9 _'/-]{0,80})\s*:\s+(.+)\s*$/);
        if (match) out.push({ speaker: match[1].trim(), text: match[2].trim(), pointer: `line:${index + 1}` });
    });
    return out;
}

function npcCandidates(projectRoot) {
    const root = storage.assertProjectRoot(projectRoot), byName = new Map();
    for (const file of discoverSources(root).filter(x => x.path.startsWith('data/') && /\.json$/i.test(x.path))) {
        const full = path.join(root, file.path), value = storage.readJson(full, null);
        for (const line of collectDialogue(value)) {
            const list = byName.get(line.speaker) || [];
            list.push({ path: file.path, pointer: line.pointer, text: line.text, sha256: file.sha256 });
            byName.set(line.speaker, list);
        }
    }
    for (const file of discoverSources(root).filter(x => x.path.startsWith('docs/') && /\.md$/i.test(x.path))) {
        const text = fs.readFileSync(path.join(root, file.path), 'utf8');
        for (const line of collectMarkdownDialogue(text)) {
            const list = byName.get(line.speaker) || [];
            list.push({ path: file.path, pointer: line.pointer, text: line.text, sha256: file.sha256 });
            byName.set(line.speaker, list);
        }
    }
    const used = new Set();
    return [...byName.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([displayName, excerpts]) => {
        const base = displayName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 60) || 'npc';
        let id = base, suffix = 2; while (used.has(id)) id = `${base}_${suffix++}`; used.add(id);
        return { id, displayName, excerptCount: excerpts.length, excerpts: excerpts.slice(0, 40) };
    });
}

function compileDossierCandidate(projectRoot, candidate, options = {}) {
    const selected = options.sourcePaths && options.sourcePaths.length
        ? new Set(options.sourcePaths) : null;
    const chosen = (candidate.excerpts || []).filter(excerpt => !selected || selected.has(excerpt.path));
    const excerpts = chosen.map(excerpt => ({
        path: excerpt.path, pointer: excerpt.pointer, sha256: excerpt.sha256,
    }));
    return {
        contractVersion: 1,
        id: candidate.id,
        displayName: candidate.displayName,
        facts: chosen.slice(0, 12).map(excerpt => ({
            kind: 'source', text: excerpt.text, sourceRefs: [{ path: excerpt.path, pointer: excerpt.pointer, sha256: excerpt.sha256 }],
        })),
        privateKnowledge: [], goals: [], behavioralTensions: [], relationships: {}, routines: [],
        sourceRefs: excerpts,
        notes: 'Candidate compiled from live Project dialogue. Add hypotheses explicitly; do not treat omissions as facts.',
    };
}

module.exports = { discoverSources, collectDialogue, collectMarkdownDialogue, npcCandidates, compileDossierCandidate };
