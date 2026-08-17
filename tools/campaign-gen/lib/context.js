// Builds the generation contracts each stage embeds. Generator context is
// intentionally Project-local: Thestra/RTP contributes semantic engine
// language, while game grammar comes only from the generated Project.
'use strict';

const fs = require('fs');
const path = require('path');
const authoredStorage = require('../../editor/authored-storage');

const REPO = path.join(__dirname, '..', '..', '..');

// Files the model is allowed to author or repair. Every entry resolves through
// authored-storage inside the generated Project; no entry points at the
// canonical repository data/ tree.
const GENERATED_FILES = [
    'system.json', 'terms.json',
    'elements.json', 'roles.json', 'skills.json', 'states.json', 'passives.json',
    'units.json', 'items.json', 'quests.json', 'shops.json', 'maps.json',
    'commonEvents.json', 'scenes.json', 'troops.json',
];
const GENERATED_STEMS = Object.fromEntries(
    GENERATED_FILES.map(file => [file, path.basename(file, '.json')])
);
// Compatibility name retained for callers/tests while the historical tool
// directory is still called campaign-gen.
const CONTENT_FILES = GENERATED_FILES;

function generatedStem(file) {
    const stem = GENERATED_STEMS[file];
    if (!stem) throw new Error(`unknown generated Project artifact '${file}'`);
    return stem;
}

function readGeneratedResource(projectDir, file) {
    return authoredStorage.loadResource(path.join(projectDir, 'data'), generatedStem(file)).value;
}

function writeGeneratedResource(projectDir, file, value) {
    return authoredStorage.writeResource(path.join(projectDir, 'data'), generatedStem(file), value);
}

function commandRegistry(projectDir) {
    // `engine` resolves the Project's declared RTP engineRegistry plus any
    // explicit Project-local overlay. This is reusable engine language, not a
    // copy of Second Gate game policy.
    const eng = authoredStorage.loadResource(path.join(projectDir, 'data'), 'engine').value;
    return (eng.commands || [])
        .filter(c => (c.contexts || []).some(x => x === 'map' || x === 'common' || x === 'scene' || x === 'any'))
        .map(c => ({
            id: c.id,
            params: (c.params || []).map(p => `${p.key}:${p.type}`),
            contexts: c.contexts || [],
            interactive: c.interactive || false,
            description: c.description || '',
        }));
}

function ruleset(projectDir) {
    const read = file => readGeneratedResource(projectDir, file);
    const roles = read('roles.json') || {};
    const elements = read('elements.json') || {};
    const states = read('states.json') || {};
    const passives = read('passives.json') || {};
    const skills = read('skills.json') || {};
    const troops = read('troops.json') || {};
    return {
        roles: Object.keys(roles),
        elements: Object.keys(elements),
        states: Object.keys(states),
        passives: Object.keys(passives),
        skills: Object.entries(skills).map(([id, s]) => ({
            id, name: s && s.name, target: s && s.target, scope: s && s.scope,
            element: s && s.element,
        })),
        troops: Object.keys(troops),
    };
}

// Explicit neutral schema descriptions replace the old "copy a live Second
// Gate record" context. These examples are structural sentinels only: prompts
// tell the model to choose ids/names from the goal and never reuse example ids.
function schemas() {
    return {
        ownership: 'All authored ids, names, rules and balance values belong to this generated Project. Empty RPG databases are valid when the game plan does not need them.',
        elements: {
            storage: 'object keyed by Project-defined element id',
            record: { name: 'string', icon: 'integer optional', strongAgainst: ['element-id'], weakAgainst: ['element-id'] },
        },
        roles: {
            storage: 'object keyed by Project-defined role id',
            record: { name: 'string', description: 'string optional' },
        },
        skills: {
            storage: 'object keyed by skill id; each record repeats id',
            record: {
                id: 'string', name: 'string', target: 'engine-supported target id', scope: 'battle|always',
                element: 'Project element id optional', description: 'string optional',
                effects: [{ type: 'engine-supported effect type', potency: 'number optional', power: 'atk|mat optional', formula: 'Formula optional' }],
            },
        },
        units: {
            storage: 'ordered array; ids may be strings and must be unique',
            record: {
                id: 'Project unit id', name: 'string', level: 'positive integer', role: 'Project role id optional',
                elements: ['Project element id'], skills: ['Project skill id'], passives: ['Project passive id'],
                baseParams: { maxHp: 'number', atk: 'number', def: 'number', mat: 'number', mdf: 'number' },
                initialParty: 'boolean optional', unlocked: 'boolean optional', isRecruitable: 'boolean optional',
            },
            note: 'Do not invent sprite/portrait asset references unless that asset exists in MANIFEST.availableAssets.',
        },
        items: {
            storage: 'array; empty is valid',
            record: { id: 'unique integer or Project-supported id', name: 'string', type: 'string', description: 'string optional', effects: 'array optional', traits: 'array optional', meta: 'object optional' },
        },
        maps: {
            storage: 'ordered array with unique ids',
            record: {
                id: 'unique integer', title: 'string', category: 'Project-defined category string', depth: 'number optional', safe: 'boolean optional',
                layout: ['equal-width strings using # walls and . floor'], spawn: { x: '0-based integer', y: '0-based integer', dir: 'N|E|S|W' },
                events: [{ id: 'unique-on-map id', x: '0-based integer', y: '0-based integer', trigger: 'interact|touch|auto optional', script: [{ cmd: 'RTP command id' }] }],
            },
        },
        scenes: {
            storage: 'ordered array with unique string ids',
            record: {
                id: 'string', name: 'string', kind: 'menu|map|custom engine-supported kind', draw: 'windows|world',
                world: 'renderer id required when draw=world', windows: 'array optional', hooks: 'object of command arrays', config: 'object',
            },
        },
        startup: {
            system: 'Project document. Preserve rtp.revision. spawn/newGame may be omitted or minimal when a custom Scene does not need RPG party startup.',
            terms: 'Project text/identity document; project.title is the authored game title.',
        },
    };
}

function listAssets(projectDir) {
    const assetsRoot = path.join(projectDir, 'assets');
    if (!fs.existsSync(assetsRoot)) return [];
    const out = [];
    function walk(dir) {
        for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            const absolute = path.join(dir, entry.name);
            if (entry.isDirectory()) walk(absolute);
            else if (entry.isFile()) out.push(path.relative(projectDir, absolute).replace(/\\/g, '/'));
        }
    }
    walk(assetsRoot);
    return out.sort();
}

function manifest(projectDir) {
    const j = file => readGeneratedResource(projectDir, file);
    const units = j('units.json') || [];
    const items = j('items.json') || [];
    const maps = j('maps.json') || [];
    const quests = j('quests.json') || {};
    const shops = j('shops.json') || {};
    const commonEvents = j('commonEvents.json') || {};
    const scenes = j('scenes.json') || [];

    return {
        ruleset: ruleset(projectDir),
        units: units.map(a => ({ id: a.id, name: a.name, role: a.role })),
        items: items.map(i => ({ id: i.id, name: i.name, type: i.type })),
        maps: maps.map(m => ({ id: m.id, title: m.title, category: m.category })),
        quests: Object.keys(quests),
        shops: Object.keys(shops),
        commonEvents: Array.isArray(commonEvents)
            ? commonEvents.map(e => e && e.id).filter(Boolean)
            : Object.keys(commonEvents),
        scenes: scenes.map(s => ({ id: s.id, name: s.name, kind: s.kind })),
        availableAssets: listAssets(projectDir),
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
    REPO, CONTENT_FILES, GENERATED_FILES,
    commandRegistry, generatedStem, manifest, readGeneratedResource, resolveLovecPath,
    ruleset, schemas, writeGeneratedResource,
};