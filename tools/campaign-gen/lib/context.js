// Builds the generation contracts each stage's prompt embeds: excerpts of
// the shared-core ruleset (registry, roles, elements, ...) plus the id
// manifest of everything generated so far, so later stages reference real
// ids instead of hallucinating them.
'use strict';

const fs = require('fs');
const path = require('path');
const authoredStorage = require('../../../studio/editor/authored-storage');

const REPO = path.join(__dirname, '..', '..', '..');

function readJson(rel) {
    return JSON.parse(fs.readFileSync(path.join(REPO, rel), 'utf8'));
}

// Shared-core files (owner decision: ruleset stays fixed; content layer is
// generated). Project bootstrap owns how those files arrive; generation only
// overwrites the content-layer files stage by stage.
const CONTENT_FILES = ['units.json', 'items.json', 'quests.json', 'maps.json',
    'shops.json', 'commonEvents.json'];
const CONTENT_STEMS = Object.fromEntries(CONTENT_FILES.map(file => [file, path.basename(file, '.json')]));

function commandRegistry() {
    // #390: commands/formula help are inherited RTP engineRegistry semantics,
    // while Second Gate owns disjoint Project policy in data/engine.json.
    // Consume the same resolved authored-storage surface as Studio so project
    // generation cannot drift back to reading only the local policy fragment.
    const eng = authoredStorage.loadResource(path.join(REPO, 'data'), 'engine').value;
    return (eng.commands || [])
        .filter(c => (c.contexts || []).some(x => x === 'map' || x === 'common' || x === 'any'))
        .map(c => ({
            id: c.id,
            params: (c.params || []).map(p => `${p.key}:${p.type}`),
            interactive: c.interactive || false,
            description: c.description || '',
        }));
}

function ruleset() {
    const roles = readJson('data/roles.json');
    const elements = readJson('data/elements.json');
    const states = readJson('data/states.json');
    const passives = readJson('data/passives.json');
    const skills = readJson('data/skills.json');
    return {
        roles: Object.keys(roles),
        elements: Object.keys(elements),
        states: Object.keys(states),
        passives: Object.keys(passives),
        skills: Object.entries(skills).map(([id, s]) => ({
            id, name: s.name, target: s.target, scope: s.scope,
        })),
    };
}

// One representative sample per entity type, pulled from the REAL default
// Project -- the schema-by-example that keeps models honest about shape.
function samples() {
    const units = authoredStorage.loadResource(path.join(REPO, 'data'), 'units').value;
    const items = authoredStorage.loadResource(path.join(REPO, 'data'), 'items').value;
    const maps = authoredStorage.loadResource(path.join(REPO, 'data'), 'maps').value;
    const quests = authoredStorage.loadResource(path.join(REPO, 'data'), 'quests').value;
    const town = maps.find(m => m.category === 'town') || maps[0];
    return {
        unit: units.find(a => a.role !== 'Summoner') || units[0],
        item: items[0],
        quest: Object.values(quests)[0],
        map: { ...town, events: (town.events || []).slice(0, 2) },
        event: (town.events || []).find(e => e.script && e.script.length > 1) || (town.events || [])[0],
    };
}

function contentStem(file) {
    const stem = CONTENT_STEMS[file];
    if (!stem) throw new Error(`unknown generated content artifact '${file}'`);
    return stem;
}

function readGeneratedResource(projectDir, file) {
    return authoredStorage.loadResource(path.join(projectDir, 'data'), contentStem(file)).value;
}

function writeGeneratedResource(projectDir, file, value) {
    return authoredStorage.writeResource(path.join(projectDir, 'data'), contentStem(file), value);
}

function manifest(projectDir) {
    const j = file => readGeneratedResource(projectDir, file);
    const units = j('units.json');
    const items = j('items.json');
    const maps = j('maps.json');
    const quests = j('quests.json');
    const shops = j('shops.json');
    const commonEvents = j('commonEvents.json');

    let sprites = [];
    const spritesDir = path.join(projectDir, 'assets', 'sprites');
    if (fs.existsSync(spritesDir)) {
        sprites = fs.readdirSync(spritesDir)
            .filter(f => f.endsWith('.png'))
            .map(f => `assets/sprites/${f}`);
    }

    return {
        units: units.map(a => ({ id: a.id, name: a.name, role: a.role, tier: a.tier })),
        items: items.map(i => ({ id: i.id, name: i.name, type: i.type })),
        maps: maps.map(m => ({ id: m.id, title: m.title, category: m.category })),
        quests: Object.keys(quests),
        shops: Object.keys(shops),
        commonEvents: Object.keys(commonEvents),
        availableSprites: sprites,
    };
}

function resolveLovecPath(configuredPath) {
    if (configuredPath && fs.existsSync(configuredPath)) return configuredPath;
    if (process.env.LOVE_EXE) {
        const lovec = process.env.LOVE_EXE.replace(/love\.exe$/i, 'lovec.exe');
        if (fs.existsSync(lovec)) return lovec;
    }
    const stdPath = 'C:\\Program Files\\LOVE\\lovec.exe';
    if (fs.existsSync(stdPath)) return stdPath;
    return 'lovec';
}

module.exports = {
    REPO, CONTENT_FILES, readJson, commandRegistry, ruleset, samples, manifest,
    contentStem, readGeneratedResource, writeGeneratedResource, resolveLovecPath
};
