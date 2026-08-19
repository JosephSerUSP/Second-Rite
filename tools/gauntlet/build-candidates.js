'use strict';

const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..', '..');
const GAUNTLET_DIR = path.join(REPO, 'projects', 'experiments', 'gauntlet-unidentified-gear');

function writeJson(filePath, data) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

// -------------------------------------------------------------
// Base RTP tilesets and shared definitions
// -------------------------------------------------------------
const DUNGEON_TILESET = {
    id: 'dungeon_default',
    name: 'Standard Dungeon',
    texture: 'assets/tilesets/dungeon_001.png',
    tileWidth: 64,
    tileHeight: 64,
    base: {
        walls: [{ id: 'dungeon_wall_1', role: 'base_wall', middle: [1, 0], weight: 100 }],
        floors: [{ id: 'dungeon_floor_1', role: 'base_floor', atlas: [0, 1], weight: 100, heightOffset: 0 }],
        ceilings: [{ id: 'dungeon_ceiling', role: 'base_ceiling', atlas: [0, 0], weight: 100 }]
    },
    doors: [{ id: 'dungeon_door', role: 'door', atlas: [1, 1] }],
    features: [],
    fixturePrefabs: []
};

const TOWN_TILESET = {
    id: 'town_default',
    name: 'Town Sanctuary',
    texture: 'assets/tilesets/town_stMaria.png',
    tileWidth: 64,
    tileHeight: 64,
    base: {
        walls: [{ id: 'town_wall_1', role: 'base_wall', middle: [1, 0], weight: 100 }],
        floors: [{ id: 'town_floor_1', role: 'base_floor', atlas: [0, 1], weight: 100, heightOffset: 0 }],
        ceilings: [{ id: 'town_ceiling', role: 'base_ceiling', atlas: [0, 0], weight: 100 }]
    },
    doors: [{ id: 'town_door', role: 'door', atlas: [1, 1] }],
    features: [],
    fixturePrefabs: []
};

const BASE_ROLES = {
    Summoner: { name: 'Summoner', description: 'The player character.' },
    Attacker: { name: 'Attacker', description: 'High offense front-liner.' },
    Defender: { name: 'Defender', description: 'Soaks damage for the party.' },
    Tank: { name: 'Tank', description: 'Heavy guardian.' },
    Support: { name: 'Support', description: 'Buffs allies and restores health.' },
    Healer: { name: 'Healer', description: 'Restores HP.' },
    None: { name: 'None', description: 'No specialization.' }
};

const BASE_ELEMENTS = {
    Red: { name: 'Fire', color: [1, 0.3, 0.2] },
    Blue: { name: 'Ice', color: [0.2, 0.6, 1] },
    Green: { name: 'Wind', color: [0.3, 0.8, 0.4] },
    White: { name: 'Holy', color: [1, 1, 0.8] },
    Black: { name: 'Dark', color: [0.5, 0.2, 0.7] }
};

const BASE_STATES = {
    dead: {
        id: 'dead',
        categories: ['negative'],
        name: 'Dead',
        icon: 11,
        restriction: 4,
        priority: 100,
        traits: [],
        display: { hideIcon: true }
    },
    poison: {
        id: 'poison',
        categories: ['negative', 'common'],
        name: 'Poison',
        icon: 2,
        duration: 3,
        traits: [{ code: 'HRG', value: -0.08 }]
    },
    freeze: {
        id: 'freeze',
        categories: ['negative', 'elemental'],
        name: 'Freeze',
        icon: 3,
        restriction: 4,
        duration: 2,
        traits: [{ code: 'EVA', value: -0.5 }]
    }
};

const BASE_PASSIVES = {
    undeadFortitude: {
        id: 'undeadFortitude',
        name: 'Undead Fortitude',
        description: 'Immune to poison and decay.',
        icon: 103,
        traits: [{ code: 'STATE_IMMUNITY', dataId: 'poison' }]
    },
    swiftReflexes: {
        id: 'swiftReflexes',
        name: 'Swift Reflexes',
        description: 'Boosts evasion and action speed.',
        icon: 103,
        traits: [{ code: 'EVA', value: 0.15 }, { code: 'PARAM_PLUS', dataId: 'asp', value: 3 }]
    },
    arcaneFocus: {
        id: 'arcaneFocus',
        name: 'Arcane Focus',
        description: 'Boosts spell damage.',
        icon: 103,
        traits: [{ code: 'PARAM_PLUS', dataId: 'mat', value: 5 }]
    }
};

const BASE_SKILLS = {
    peck: {
        id: 'peck',
        name: 'Beak Strike',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Green',
        icon: 1,
        description: '[Enemy] A swift piercing peck.',
        effects: [{ type: 'hp_damage', potency: 1.2, power: 'atk' }],
        charges: '99'
    },
    flurry: {
        id: 'flurry',
        name: 'Feather Flurry',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Green',
        icon: 2,
        description: '[Enemy] Strike with rapid agility.',
        effects: [{ type: 'hp_damage', potency: 1.4, power: 'atk' }],
        charges: '5'
    },
    spark: {
        id: 'spark',
        name: 'Spark',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Black',
        icon: 5,
        description: '[Enemy] Zap an enemy with lightning energy.',
        effects: [{ type: 'hp_damage', potency: 1.3, power: 'mat' }],
        charges: '6'
    },
    heal: {
        id: 'heal',
        name: 'Healing Touch',
        target: 'ally-any',
        scope: 'always',
        element: 'White',
        icon: 4,
        description: '[Ally] Restore HP to an ally.',
        effects: [{ type: 'hp_heal', formula: 'a.mat * 0.8 + 30' }],
        charges: '5'
    },
    boneRush: {
        id: 'boneRush',
        name: 'Bone Rush',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Black',
        icon: 5,
        description: '[Enemy] Crushing skeleton charge.',
        effects: [{ type: 'hp_damage', potency: 1.35, power: 'atk' }],
        charges: '99'
    },
    ghoulBite: {
        id: 'ghoulBite',
        name: 'Venomous Bite',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Black',
        icon: 2,
        description: '[Enemy] Bite that can inflict poison.',
        effects: [
            { type: 'hp_damage', potency: 1.1, power: 'atk' },
            { type: 'add_status', status: 'poison', chance: 0.6, duration: 3 }
        ],
        charges: '99'
    },
    cerberusBite: {
        id: 'cerberusBite',
        name: 'Infernal Crunch',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Red',
        icon: 1,
        description: '[Enemy] Double jaws of hellfire.',
        effects: [{ type: 'hp_damage', potency: 1.5, power: 'atk' }],
        charges: '99'
    },
    cerberusBreath: {
        id: 'cerberusBreath',
        name: 'Hellfire Breath',
        target: 'enemies-all',
        scope: 'battle',
        element: 'Red',
        icon: 1,
        description: '[All Enemies] Engulf in hellfire.',
        effects: [{ type: 'hp_damage', potency: 1.2, power: 'mat' }],
        charges: '3'
    },
    waterPulse: {
        id: 'waterPulse',
        name: 'Water Pulse',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Blue',
        icon: 3,
        description: '[Enemy] Arcane rush of high-pressure water.',
        effects: [{ type: 'hp_damage', potency: 1.35, power: 'mat' }],
        charges: '6'
    },
    iceShard: {
        id: 'iceShard',
        name: 'Ice Shard',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Blue',
        icon: 3,
        description: '[Enemy] Chilling spear of frost.',
        effects: [
            { type: 'hp_damage', potency: 1.2, power: 'mat' },
            { type: 'add_status', status: 'freeze', chance: 0.35, duration: 2 }
        ],
        charges: '4'
    },
    heavySlam: {
        id: 'heavySlam',
        name: 'Colossal Slam',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Black',
        icon: 5,
        description: '[Enemy] Heavy crushing blow.',
        effects: [{ type: 'hp_damage', potency: 1.4, power: 'atk' }],
        charges: '99'
    },
    guard: {
        id: 'guard',
        name: 'Stone Bulwark',
        target: 'self',
        scope: 'battle',
        element: 'White',
        icon: 4,
        description: '[Self] Brace for impact.',
        effects: [],
        charges: '99'
    },
    automatonOverload: {
        id: 'automatonOverload',
        name: 'Arcane Overload',
        target: 'enemies-all',
        scope: 'battle',
        element: 'Black',
        icon: 5,
        description: '[All Enemies] Discharge destructive beam.',
        effects: [{ type: 'hp_damage', potency: 1.3, power: 'mat' }],
        charges: '3'
    },
    lightStrike: {
        id: 'lightStrike',
        name: 'Light Strike',
        target: 'enemy-any',
        scope: 'battle',
        element: 'White',
        icon: 4,
        description: '[Enemy] Infuse blade with holy power.',
        effects: [{ type: 'hp_damage', potency: 1.3, power: 'atk' }],
        charges: '99'
    },
    shadowClaw: {
        id: 'shadowClaw',
        name: 'Shadow Claw',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Black',
        icon: 5,
        description: '[Enemy] Sneak attack from behind.',
        effects: [{ type: 'hp_damage', potency: 1.4, power: 'atk' }],
        charges: '6'
    },
    quickStab: {
        id: 'quickStab',
        name: 'Quick Stab',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Black',
        icon: 5,
        description: '[Enemy] Fast strike.',
        effects: [{ type: 'hp_damage', potency: 1.15, power: 'atk' }],
        charges: '99'
    },
    demonRend: {
        id: 'demonRend',
        name: 'Demon Rend',
        target: 'enemy-any',
        scope: 'battle',
        element: 'Black',
        icon: 5,
        description: '[Enemy] Tears at flesh and spirit.',
        effects: [{ type: 'hp_damage', potency: 1.45, power: 'atk' }],
        charges: '99'
    },
    darkWave: {
        id: 'darkWave',
        name: 'Abyssal Wave',
        target: 'enemies-all',
        scope: 'battle',
        element: 'Black',
        icon: 5,
        description: '[All Enemies] Dark flood.',
        effects: [{ type: 'hp_damage', potency: 1.25, power: 'mat' }],
        charges: '3'
    }
};

const BASE_TROOPS = {
    base: {
        id: 'base',
        name: 'Every Battle',
        abstract: true,
        description: 'Base battle logic',
        members: [],
        events: []
    }
};

const TOWN_LAYOUT = [
    '#########',
    '#...#...#',
    '#.......#',
    '#...#...#',
    '#.......#',
    '#...#...#',
    '#.......#',
    '#...#...#',
    '#########'
];

const DUNGEON_LAYOUT = [
    '#########',
    '#.......#',
    '#.###.#.#',
    '#.#...#.#',
    '#.#.###.#',
    '#...#...#',
    '#####.###',
    '#.......#',
    '#########'
];

// -------------------------------------------------------------
// Candidate A Generator: The High-Roller's Ruin
// -------------------------------------------------------------
function buildCandidateA(projectDir) {
    console.log(`Building Candidate A in ${projectDir}...`);

    const system = {
        ui: {
            activeFont: 'monogram-extended',
            fontSize: 16,
            fontOffsetY: -4,
            fontNormalize: true
        },
        spawn: { mapId: 1, x: 4, y: 7, dir: 'N' },
        newGame: {
            goldMin: 150,
            goldMax: 150,
            party: {
                fixedMembers: [
                    { id: 'moa', level: 3, name: 'Saban', slot: 1 },
                    { id: 'pixie', level: 3, name: 'Puck', slot: 2 }
                ]
            }
        },
        rtp: { revision: '1.0' }
    };
    writeJson(path.join(projectDir, 'data', 'system.json'), system);
    writeJson(path.join(projectDir, 'data', 'terms.json'), { 'menu.equip_slots': ['WPN', 'AMR', 'ACC'] });
    writeJson(path.join(projectDir, 'data', 'roles.json'), BASE_ROLES);
    writeJson(path.join(projectDir, 'data', 'elements.json'), BASE_ELEMENTS);
    writeJson(path.join(projectDir, 'data', 'states.json'), BASE_STATES);
    writeJson(path.join(projectDir, 'data', 'passives.json'), BASE_PASSIVES);
    writeJson(path.join(projectDir, 'data', 'skills.json'), BASE_SKILLS);

    // tilesets
    writeJson(path.join(projectDir, 'data', 'tilesets', 'town_default.json'), TOWN_TILESET);
    writeJson(path.join(projectDir, 'data', 'tilesets', 'dungeon_default.json'), DUNGEON_TILESET);

    // units
    writeJson(path.join(projectDir, 'data', 'units', 'index.json'), {
        files: ['moa.json', 'pixie.json', 'skeleton.json', 'ghoul.json', 'mimic.json', 'cerberus.json']
    });

    const growth = [
        { from: 2, to: 10, maxHp: 80, atk: 25, def: 20, mat: 15, mdf: 15 },
        { from: 11, to: 20, maxHp: 120, atk: 35, def: 30, mat: 25, mdf: 25 }
    ];

    writeJson(path.join(projectDir, 'data', 'units', 'moa.json'), {
        id: 'moa', name: 'Moa Runner', level: 3, role: 'Attacker', smallBattler: 'moa',
        tier: 1, discipline: 'cooking', elements: ['Green'],
        favoriteFoods: [1],
        baseParams: { maxHp: 50, atk: 20, def: 12, mat: 8, mdf: 10, asp: 12, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['peck', 'flurry'], passives: ['swiftReflexes']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'pixie.json'), {
        id: 'pixie', name: 'Pixie Cleric', level: 3, role: 'Support', smallBattler: 'pixie[fps=15]',
        tier: 1, discipline: 'alchemy', elements: ['White'],
        favoriteFoods: [1],
        baseParams: { maxHp: 40, atk: 10, def: 8, mat: 18, mdf: 20, asp: 10, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['spark', 'heal'], passives: ['arcaneFocus']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'skeleton.json'), {
        id: 'skeleton', name: 'Vanguard Skeleton', level: 3, role: 'Attacker', smallBattler: 'Skeleton',
        tier: 1, discipline: 'blacksmithing', elements: ['Black'],
        favoriteFoods: [1],
        baseParams: { maxHp: 48, atk: 22, def: 14, mat: 5, mdf: 8, asp: 8, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['boneRush'], passives: ['undeadFortitude']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'ghoul.json'), {
        id: 'ghoul', name: 'Crypt Ghoul', level: 4, role: 'Attacker', smallBattler: 'Ghoul',
        tier: 1, discipline: 'blacksmithing', elements: ['Black'],
        favoriteFoods: [1],
        baseParams: { maxHp: 70, atk: 24, def: 16, mat: 10, mdf: 12, asp: 6, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['ghoulBite'], passives: ['undeadFortitude']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'mimic.json'), {
        id: 'mimic', name: 'Crypt Mimic', level: 4, role: 'Attacker', smallBattler: 'mimic',
        tier: 1, discipline: 'tinkering', elements: ['Black'],
        favoriteFoods: [1],
        baseParams: { maxHp: 80, atk: 26, def: 20, mat: 12, mdf: 14, asp: 9, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['boneRush', 'flurry'], passives: ['undeadFortitude']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'cerberus.json'), {
        id: 'cerberus', name: 'Tomb Sentinel Cerberus', level: 6, role: 'Attacker', smallBattler: 'cerberus',
        tier: 2, discipline: 'blacksmithing', elements: ['Red'],
        favoriteFoods: [1],
        baseParams: { maxHp: 240, atk: 30, def: 20, mat: 22, mdf: 18, asp: 11, mpd: 2, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['cerberusBite', 'cerberusBreath'], passives: ['undeadFortitude']
    });

    // troops
    const troops = Object.assign({}, BASE_TROOPS, {
        troop_skeletons: {
            id: 'troop_skeletons', name: 'Skeleton Patrol',
            members: [{ actor: 'skeleton', level: 3 }, { actor: 'skeleton', level: 3 }]
        },
        troop_ghoul: {
            id: 'troop_ghoul', name: 'Lurking Ghoul',
            members: [{ actor: 'ghoul', level: 4 }]
        },
        troop_mimic: {
            id: 'troop_mimic', name: 'Hungry Mimic',
            members: [{ actor: 'mimic', level: 4 }]
        },
        troop_boss_sentinel: {
            id: 'troop_boss_sentinel', name: 'Tomb Sentinel',
            members: [{ actor: 'cerberus', level: 6 }]
        }
    });
    writeJson(path.join(projectDir, 'data', 'troops.json'), troops);

    // items
    const items = [
        { id: 1, name: 'Medicinal Herb', type: 'consumable', description: 'Restores 35 HP to one ally.', icon: 51, effects: [{ type: 'hp', value: 35 }] },
        { id: 101, name: 'Identify Scroll', type: 'consumable', description: 'Ancient parchment that reveals true item traits.', icon: 55, effects: [] },
        {
            id: 201, name: 'Blood-Stained ????', type: 'equipment', equipType: 'Weapon', icon: 1,
            description: 'A heavy broadsword caked in dark crimson rust. The blade hums with ominous warmth (???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'atk', value: 32 },
                { code: 'PARAM_PLUS', dataId: 'def', value: -6 },
                { code: 'HRG', value: -0.10 }
            ]
        },
        {
            id: 202, name: 'Vanguard Blood-Drinker', type: 'equipment', equipType: 'Weapon', icon: 1,
            description: 'The cursed blade of a fallen captain (+32 ATK, -6 DEF). Bleeds the wielder for 10% HP each combat round.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'atk', value: 32 },
                { code: 'PARAM_PLUS', dataId: 'def', value: -6 },
                { code: 'HRG', value: -0.10 }
            ]
        },
        {
            id: 203, name: 'Obsidian ?????', type: 'equipment', equipType: 'Armor', icon: 2,
            description: 'Jet-black plate armor forged from volcanic glass. Exceptionally heavy, with faint heat inside (???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'def', value: 26 },
                { code: 'PARAM_PLUS', dataId: 'mdf', value: 14 },
                { code: 'PARAM_PLUS', dataId: 'asp', value: -5 },
                { code: 'ELEMENT_RESIST', dataId: 'Red', value: 1.6 }
            ]
        },
        {
            id: 204, name: 'Obsidian Bulwark', type: 'equipment', equipType: 'Armor', icon: 2,
            description: 'Dense volcanic armor (+26 DEF, +14 MDF, -5 ASP). Its crystalline structure makes the wearer 60% more vulnerable to Fire attacks.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'def', value: 26 },
                { code: 'PARAM_PLUS', dataId: 'mdf', value: 14 },
                { code: 'PARAM_PLUS', dataId: 'asp', value: -5 },
                { code: 'ELEMENT_RESIST', dataId: 'Red', value: 1.6 }
            ]
        },
        {
            id: 205, name: 'Wicked Ring ????', type: 'equipment', equipType: 'Accessory', icon: 3,
            description: 'A sinister bone ring that pulsates against the skin (???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'atk', value: 12 },
                { code: 'PARAM_PLUS', dataId: 'mat', value: 12 },
                { code: 'PARAM_RATE', dataId: 'maxHp', value: 0.80 }
            ]
        },
        {
            id: 206, name: 'Ring of Desperate Zeal', type: 'equipment', equipType: 'Accessory', icon: 3,
            description: 'A zealot ring (+12 ATK, +12 MAT). Reduces Max HP by 20% in exchange for raw offensive ferocity.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'atk', value: 12 },
                { code: 'PARAM_PLUS', dataId: 'mat', value: 12 },
                { code: 'PARAM_RATE', dataId: 'maxHp', value: 0.80 }
            ]
        },
        {
            id: 207, name: 'Ancient Relic ????', type: 'equipment', equipType: 'Weapon', icon: 1,
            description: 'An unweathered silver shortsword sealed with faint white script (???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'atk', value: 16 },
                { code: 'ELEMENT_ATTACK', dataId: 'White' }
            ]
        },
        {
            id: 208, name: 'Blessed Silver Blade', type: 'equipment', equipType: 'Weapon', icon: 1,
            description: 'A consecrated shortsword (+16 ATK). Infuses basic attacks with Holy Light, devastating undead.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'atk', value: 16 },
                { code: 'ELEMENT_ATTACK', dataId: 'White' }
            ]
        }
    ];
    writeJson(path.join(projectDir, 'data', 'items.json'), items);

    // maps
    writeJson(path.join(projectDir, 'data', 'maps', 'index.json'), { files: ['1.json', '2.json'] });

    const map1 = {
        id: 1,
        title: 'Camp of the Vanguard',
        intro: 'A fortified outpost above the Crypt of the Cursed Vanguard.',
        depth: 0,
        tileset: 'town_default',
        ceilingStyle: 'sky',
        music: 'town1',
        layout: TOWN_LAYOUT,
        events: [
            {
                id: 1, name: 'Expedition Master Valen', x: 4, y: 5, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'Valen: "Welcome, Summoner. The crypt below holds weapons of terrible power from the fallen vanguard."' },
                    { cmd: 'TEXT', text: 'Valen: "You can equip unknown relics immediately to harness their immense raw stats (+32 ATK!). But beware: hidden curses will bleed you or invite fiery doom!"' },
                    { cmd: 'TEXT', text: 'Valen: "The Town Appraiser charges 150 Gold per appraisal. Choose wisely when to gamble and when to appraise."' }
                ]
            },
            {
                id: 2, name: 'Town Appraiser Master Balthazar', x: 2, y: 3, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'Balthazar: "I can appraise unknown items for 150 Gold each. Which relic shall I inspect?"' },
                    {
                        cmd: 'CHOICE',
                        options: [
                            {
                                label: 'Appraise Blood-Stained ???? (150G)',
                                condition: 'hasItem:201',
                                commands: [
                                    { cmd: 'GAIN_GOLD', amount: '-150' },
                                    { cmd: 'CHANGE_ITEM', item: 201, count: -1 },
                                    { cmd: 'CHANGE_ITEM', item: 202, count: 1 },
                                    { cmd: 'TEXT', text: 'Balthazar: "By the gods! This is the Vanguard Blood-Drinker! It grants +32 ATK but drains 10% HP every combat round!"' }
                                ]
                            },
                            {
                                label: 'Appraise Obsidian ????? (150G)',
                                condition: 'hasItem:203',
                                commands: [
                                    { cmd: 'GAIN_GOLD', amount: '-150' },
                                    { cmd: 'CHANGE_ITEM', item: 203, count: -1 },
                                    { cmd: 'CHANGE_ITEM', item: 204, count: 1 },
                                    { cmd: 'TEXT', text: 'Balthazar: "This is Obsidian Bulwark (+26 DEF, +14 MDF). But its volcanic stone increases Fire damage taken by +60%!"' }
                                ]
                            },
                            {
                                label: 'Appraise Wicked Ring ???? (150G)',
                                condition: 'hasItem:205',
                                commands: [
                                    { cmd: 'GAIN_GOLD', amount: '-150' },
                                    { cmd: 'CHANGE_ITEM', item: 205, count: -1 },
                                    { cmd: 'CHANGE_ITEM', item: 206, count: 1 },
                                    { cmd: 'TEXT', text: 'Balthazar: "Ring of Desperate Zeal (+12 ATK, +12 MAT)! It reduces Max HP by 20%!"' }
                                ]
                            },
                            {
                                label: 'Rest at Camp (Full Recovery)',
                                commands: [
                                    { cmd: 'RECOVER_PARTY' }
                                ]
                            },
                            { label: 'Leave', commands: [] }
                        ]
                    }
                ]
            },
            {
                id: 3, name: 'Dungeon Descent Stairs', x: 4, y: 1, trigger: 'step',
                commands: [
                    { cmd: 'TEXT', text: 'Descending into the Crypt of the Cursed Vanguard...' },
                    { cmd: 'LOAD_MAP', mapId: 2 }
                ]
            }
        ]
    };
    writeJson(path.join(projectDir, 'data', 'maps', '1.json'), map1);

    const map2 = {
        id: 2,
        title: 'Crypt of the Cursed Vanguard',
        intro: 'Ancient burial halls echoing with demonic whispers.',
        depth: 1,
        tileset: 'dungeon_default',
        ceilingStyle: 'stone',
        music: 'dungeon1',
        layout: DUNGEON_LAYOUT,
        events: [
            {
                id: 1, name: 'Ascent Stairs to Camp', x: 4, y: 7, trigger: 'step',
                commands: [
                    { cmd: 'LOAD_MAP', mapId: 1 }
                ]
            },
            {
                id: 2, name: 'Sarcophagus of the Captain', x: 1, y: 1, trigger: 'interact',
                commands: [
                    {
                        cmd: 'CONDITIONAL_BRANCH',
                        condition: 'flag:chest_weapon_opened',
                        commands: [
                            { cmd: 'TEXT', text: 'The sarcophagus is empty.' }
                        ],
                        elseCommands: [
                            { cmd: 'TEXT', text: 'You open the iron sarcophagus and retrieve a Blood-Stained ???? (+32 ATK, -6 DEF preview) and an Ancient Relic ???? (+16 ATK)!' },
                            { cmd: 'CHANGE_ITEM', item: 201, count: 1 },
                            { cmd: 'CHANGE_ITEM', item: 207, count: 1 },
                            { cmd: 'SET_FLAG', flag: 'chest_weapon_opened', value: true }
                        ]
                    }
                ]
            },
            {
                id: 3, name: 'Vanguard Armory Vault', x: 7, y: 1, trigger: 'interact',
                commands: [
                    {
                        cmd: 'CONDITIONAL_BRANCH',
                        condition: 'flag:chest_armor_opened',
                        commands: [
                            { cmd: 'TEXT', text: 'The weapon rack has already been scavenged.' }
                        ],
                        elseCommands: [
                            { cmd: 'TEXT', text: 'You discover Obsidian ????? (+26 DEF, +14 MDF, -5 ASP preview) and a Wicked Ring ???? (+12 ATK, +12 MAT)!' },
                            { cmd: 'CHANGE_ITEM', item: 203, count: 1 },
                            { cmd: 'CHANGE_ITEM', item: 205, count: 1 },
                            { cmd: 'SET_FLAG', flag: 'chest_armor_opened', value: true }
                        ]
                    }
                ]
            },
            {
                id: 4, name: 'Skeleton Vanguard Guard', x: 3, y: 5, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'Skeletal guardians rattle forward with rusty blades!' },
                    { cmd: 'BATTLE', troop: 'troop_skeletons' }
                ]
            },
            {
                id: 5, name: 'Lurking Crypt Ghoul', x: 5, y: 5, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'A foul crypt ghoul emerges from the shadows!' },
                    { cmd: 'BATTLE', troop: 'troop_ghoul' }
                ]
            },
            {
                id: 6, name: 'Boss Door: Tomb Sentinel Sanctum', x: 4, y: 3, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'A colossal three-headed hellhound, the Tomb Sentinel Cerberus, guards the inner crypt! It breathes devastating hellfire!' },
                    { cmd: 'TEXT', text: 'Do you challenge the Tomb Sentinel?' },
                    {
                        cmd: 'CHOICE',
                        options: [
                            {
                                label: 'Engage the Tomb Sentinel in Combat',
                                commands: [
                                    { cmd: 'BATTLE', troop: 'troop_boss_sentinel' },
                                    { cmd: 'TEXT', text: 'The Tomb Sentinel collapses in an explosion of ash! You have triumphed over Candidate A!' }
                                ]
                            },
                            { label: 'Fall back and prepare gear', commands: [] }
                        ]
                    }
                ]
            }
        ]
    };
    writeJson(path.join(projectDir, 'data', 'maps', '2.json'), map2);

    console.log(`Candidate A files authored.`);
}

// -------------------------------------------------------------
// Candidate B Generator: The Alchemical Spire
// -------------------------------------------------------------
function buildCandidateB(projectDir) {
    console.log(`Building Candidate B in ${projectDir}...`);

    const system = {
        ui: {
            activeFont: 'monogram-extended',
            fontSize: 16,
            fontOffsetY: -4,
            fontNormalize: true
        },
        spawn: { mapId: 1, x: 4, y: 7, dir: 'N' },
        newGame: {
            goldMin: 100,
            goldMax: 100,
            party: {
                fixedMembers: [
                    { id: 'undine', level: 3, name: 'Aqua', slot: 1 },
                    { id: 'golem', level: 3, name: 'Slate', slot: 2 }
                ]
            }
        },
        rtp: { revision: '1.0' }
    };
    writeJson(path.join(projectDir, 'data', 'system.json'), system);
    writeJson(path.join(projectDir, 'data', 'terms.json'), { 'menu.equip_slots': ['WPN', 'AMR', 'ACC'] });
    writeJson(path.join(projectDir, 'data', 'roles.json'), BASE_ROLES);
    writeJson(path.join(projectDir, 'data', 'elements.json'), BASE_ELEMENTS);
    writeJson(path.join(projectDir, 'data', 'states.json'), BASE_STATES);
    writeJson(path.join(projectDir, 'data', 'passives.json'), BASE_PASSIVES);
    writeJson(path.join(projectDir, 'data', 'skills.json'), BASE_SKILLS);

    // tilesets
    writeJson(path.join(projectDir, 'data', 'tilesets', 'town_default.json'), TOWN_TILESET);
    writeJson(path.join(projectDir, 'data', 'tilesets', 'dungeon_default.json'), DUNGEON_TILESET);

    // units
    writeJson(path.join(projectDir, 'data', 'units', 'index.json'), {
        files: ['undine.json', 'golem.json', 'wisp.json', 'lamia.json', 'homunculus.json', 'proteus.json']
    });

    const growth = [
        { from: 2, to: 10, maxHp: 80, atk: 25, def: 20, mat: 15, mdf: 15 },
        { from: 11, to: 20, maxHp: 120, atk: 35, def: 30, mat: 25, mdf: 25 }
    ];

    writeJson(path.join(projectDir, 'data', 'units', 'undine.json'), {
        id: 'undine', name: 'Undine Mystic', level: 3, role: 'Support', smallBattler: 'undine',
        tier: 1, discipline: 'alchemy', elements: ['Blue'],
        favoriteFoods: [1],
        baseParams: { maxHp: 45, atk: 12, def: 12, mat: 22, mdf: 18, asp: 10, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['waterPulse', 'iceShard', 'heal'], passives: ['arcaneFocus']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'golem.json'), {
        id: 'golem', name: 'Clay Golem', level: 3, role: 'Defender', smallBattler: 'Golem',
        tier: 1, discipline: 'blacksmithing', elements: ['Black'],
        favoriteFoods: [1],
        baseParams: { maxHp: 75, atk: 18, def: 24, mat: 6, mdf: 12, asp: 4, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['heavySlam', 'guard'], passives: ['undeadFortitude']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'wisp.json'), {
        id: 'wisp', name: 'Arcane Wisp', level: 3, role: 'Attacker', smallBattler: 'wisp',
        tier: 1, discipline: 'tinkering', elements: ['Black'],
        favoriteFoods: [1],
        baseParams: { maxHp: 35, atk: 10, def: 8, mat: 20, mdf: 18, asp: 14, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['spark'], passives: ['swiftReflexes']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'lamia.json'), {
        id: 'lamia', name: 'Spire Lamia', level: 4, role: 'Attacker', smallBattler: 'lamia',
        tier: 1, discipline: 'alchemy', elements: ['Blue'],
        favoriteFoods: [1],
        baseParams: { maxHp: 65, atk: 20, def: 14, mat: 22, mdf: 16, asp: 10, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['waterPulse', 'flurry'], passives: ['arcaneFocus']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'homunculus.json'), {
        id: 'homunculus', name: 'Lab Homunculus', level: 4, role: 'Attacker', smallBattler: 'homunculus',
        tier: 1, discipline: 'alchemy', elements: ['Green'],
        favoriteFoods: [1],
        baseParams: { maxHp: 60, atk: 22, def: 16, mat: 14, mdf: 12, asp: 8, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['heavySlam', 'peck'], passives: ['swiftReflexes']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'proteus.json'), {
        id: 'proteus', name: 'Arch-Automaton Proteus', level: 6, role: 'Attacker', smallBattler: 'proteus',
        tier: 2, discipline: 'tinkering', elements: ['Black'],
        favoriteFoods: [1],
        baseParams: { maxHp: 260, atk: 26, def: 24, mat: 26, mdf: 22, asp: 9, mpd: 2, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['heavySlam', 'automatonOverload'], passives: ['arcaneFocus']
    });

    // troops
    const troops = Object.assign({}, BASE_TROOPS, {
        troop_wisps: {
            id: 'troop_wisps', name: 'Wisp Duo',
            members: [{ actor: 'wisp', level: 3 }, { actor: 'wisp', level: 3 }]
        },
        troop_lamia: {
            id: 'troop_lamia', name: 'Spire Lamia',
            members: [{ actor: 'lamia', level: 4 }]
        },
        troop_homunculi: {
            id: 'troop_homunculi', name: 'Homunculus Guard',
            members: [{ actor: 'homunculus', level: 4 }, { actor: 'homunculus', level: 4 }]
        },
        troop_boss_automaton: {
            id: 'troop_boss_automaton', name: 'Arch-Automaton Proteus',
            members: [{ actor: 'proteus', level: 6 }]
        }
    });
    writeJson(path.join(projectDir, 'data', 'troops.json'), troops);

    // items
    const items = [
        { id: 1, name: 'Alchemical Salve', type: 'consumable', description: 'Restores 40 HP to one ally.', icon: 51, effects: [{ type: 'hp', value: 40 }] },
        { id: 101, name: 'Divination Charm', type: 'consumable', description: 'Arcane lens that reveals the true name and traits of unknown relics.', icon: 55, effects: [] },
        {
            id: 201, name: 'Vibrant Ring ????', type: 'equipment', equipType: 'Accessory', icon: 3,
            description: 'A lightweight electrum band vibrating at a dizzying frequency (???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'asp', value: 8 },
                { code: 'PARAM_PLUS', dataId: 'atk', value: 2 },
                { code: 'ACTION_PLUS', value: 1.0 }
            ]
        },
        {
            id: 202, name: 'Chronos Humming Ring', type: 'equipment', equipType: 'Accessory', icon: 3,
            description: 'Masterwork time-dilation ring (+8 ASP, +2 ATK). Grants the wearer 1 additional action every battle turn.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'asp', value: 8 },
                { code: 'PARAM_PLUS', dataId: 'atk', value: 2 },
                { code: 'ACTION_PLUS', value: 1.0 }
            ]
        },
        {
            id: 203, name: 'Glacial Shard ????', type: 'equipment', equipType: 'Weapon', icon: 1,
            description: 'A crystal rod rimmed with eternal frost. Heavy, chilling the fingertips (???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'mat', value: 14 },
                { code: 'PARAM_PLUS', dataId: 'def', value: 4 },
                { code: 'PARAM_PLUS', dataId: 'asp', value: -3 },
                { code: 'ELEMENT_ATTACK', dataId: 'Blue' },
                { code: 'ATTACK_STATE', dataId: 'freeze', value: 0.35 }
            ]
        },
        {
            id: 204, name: 'Crystalline Frost-Wand', type: 'equipment', equipType: 'Weapon', icon: 1,
            description: 'Cryo-attuned rod (+14 MAT, +4 DEF, -3 ASP). Infuses attacks with Ice and inflicts Freeze on strike.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'mat', value: 14 },
                { code: 'PARAM_PLUS', dataId: 'def', value: 4 },
                { code: 'PARAM_PLUS', dataId: 'asp', value: -3 },
                { code: 'ELEMENT_ATTACK', dataId: 'Blue' },
                { code: 'ATTACK_STATE', dataId: 'freeze', value: 0.35 }
            ]
        },
        {
            id: 205, name: 'Volatile Conduit ????', type: 'equipment', equipType: 'Accessory', icon: 3,
            description: 'A cracked conductive sphere crackling with raw arcane surge (???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'mat', value: 22 },
                { code: 'PARAM_PLUS', dataId: 'mdf', value: -10 },
                { code: 'ELEMENT_RESIST', dataId: 'Black', value: 1.7 }
            ]
        },
        {
            id: 206, name: 'Surge Overload Conduit', type: 'equipment', equipType: 'Accessory', icon: 3,
            description: 'Unstable capacitor (+22 MAT, -10 MDF). Vastly boosts spell power, but increases damage taken from Lightning/Dark attacks by 70%.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'mat', value: 22 },
                { code: 'PARAM_PLUS', dataId: 'mdf', value: -10 },
                { code: 'ELEMENT_RESIST', dataId: 'Black', value: 1.7 }
            ]
        },
        {
            id: 207, name: 'Heavy Plated ????', type: 'equipment', equipType: 'Armor', icon: 2,
            description: 'A reinforced alloy cuirass of colossal density (???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'def', value: 30 },
                { code: 'PARAM_PLUS', dataId: 'asp', value: -8 }
            ]
        },
        {
            id: 208, name: 'Giga-Alloy Carapace', type: 'equipment', equipType: 'Armor', icon: 2,
            description: 'Fortress-grade armor (+30 DEF, -8 ASP). Greatly reduces physical damage at the expense of turn speed.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'def', value: 30 },
                { code: 'PARAM_PLUS', dataId: 'asp', value: -8 }
            ]
        }
    ];
    writeJson(path.join(projectDir, 'data', 'items.json'), items);

    // maps
    writeJson(path.join(projectDir, 'data', 'maps', 'index.json'), { files: ['1.json', '2.json'] });

    const map1 = {
        id: 1,
        title: 'Alchemist Laboratory Base',
        intro: 'A sterile spire workshop overlooking the testing corridors.',
        depth: 0,
        tileset: 'town_default',
        ceilingStyle: 'sky',
        music: 'town1',
        layout: TOWN_LAYOUT,
        events: [
            {
                id: 1, name: 'Chief Alchemist Vesper', x: 4, y: 5, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'Vesper: "Greetings, Alchemist. The Spire testing chambers contain experimental relics."' },
                    { cmd: 'TEXT', text: 'Vesper: "Each unidentified relic displays stat fingerprints. An electrum ring with +8 ASP might secretly grant a second turn action; a wand with +14 MAT might trigger ice freezes or severe elemental vulnerabilities!"' },
                    { cmd: 'TEXT', text: 'Vesper: "There is a Divination Altar located halfway through the spire that will inspect one relic for free."' }
                ]
            },
            {
                id: 2, name: 'Spire Laboratory Workbench', x: 2, y: 3, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'Laboratory Workbench: Rest here to restore your party to full vigor.' },
                    { cmd: 'RECOVER_PARTY' }
                ]
            },
            {
                id: 3, name: 'Spire Entry Gate', x: 4, y: 1, trigger: 'step',
                commands: [
                    { cmd: 'TEXT', text: 'Entering the Alchemical Spire Testing Corridors...' },
                    { cmd: 'LOAD_MAP', mapId: 2 }
                ]
            }
        ]
    };
    writeJson(path.join(projectDir, 'data', 'maps', '1.json'), map1);

    const map2 = {
        id: 2,
        title: 'Spire Testing Corridors',
        intro: 'Humming alchemical tubes and arcane conduit pathways.',
        depth: 1,
        tileset: 'dungeon_default',
        ceilingStyle: 'stone',
        music: 'dungeon1',
        layout: DUNGEON_LAYOUT,
        events: [
            {
                id: 1, name: 'Stairs to Spire Base', x: 4, y: 7, trigger: 'step',
                commands: [
                    { cmd: 'LOAD_MAP', mapId: 1 }
                ]
            },
            {
                id: 2, name: 'Alchemical Storage Pod Alpha', x: 1, y: 1, trigger: 'interact',
                commands: [
                    {
                        cmd: 'CONDITIONAL_BRANCH',
                        condition: 'flag:pod_alpha_opened',
                        commands: [
                            { cmd: 'TEXT', text: 'Storage Pod Alpha is empty.' }
                        ],
                        elseCommands: [
                            { cmd: 'TEXT', text: 'You open Pod Alpha and obtain Vibrant Ring ???? (+8 ASP, +2 ATK preview) and Glacial Shard ???? (+14 MAT, +4 DEF, -3 ASP)!' },
                            { cmd: 'CHANGE_ITEM', item: 201, count: 1 },
                            { cmd: 'CHANGE_ITEM', item: 203, count: 1 },
                            { cmd: 'SET_FLAG', flag: 'pod_alpha_opened', value: true }
                        ]
                    }
                ]
            },
            {
                id: 3, name: 'Alchemical Storage Pod Beta', x: 7, y: 1, trigger: 'interact',
                commands: [
                    {
                        cmd: 'CONDITIONAL_BRANCH',
                        condition: 'flag:pod_beta_opened',
                        commands: [
                            { cmd: 'TEXT', text: 'Storage Pod Beta is empty.' }
                        ],
                        elseCommands: [
                            { cmd: 'TEXT', text: 'You open Pod Beta and obtain Volatile Conduit ???? (+22 MAT, -10 MDF) and Heavy Plated ???? (+30 DEF, -8 ASP)!' },
                            { cmd: 'CHANGE_ITEM', item: 205, count: 1 },
                            { cmd: 'CHANGE_ITEM', item: 207, count: 1 },
                            { cmd: 'SET_FLAG', flag: 'pod_beta_opened', value: true }
                        ]
                    }
                ]
            },
            {
                id: 4, name: 'Divination Altar', x: 4, y: 5, trigger: 'interact',
                commands: [
                    {
                        cmd: 'CONDITIONAL_BRANCH',
                        condition: 'flag:divination_used',
                        commands: [
                            { cmd: 'TEXT', text: 'The Divination Altar has exhausted its psychic charge for this run.' }
                        ],
                        elseCommands: [
                            { cmd: 'TEXT', text: 'Divination Altar: Place an unidentified relic on the crystal lens to identify it.' },
                            {
                                cmd: 'CHOICE',
                                options: [
                                    {
                                        label: 'Identify Vibrant Ring ????',
                                        condition: 'hasItem:201',
                                        commands: [
                                            { cmd: 'CHANGE_ITEM', item: 201, count: -1 },
                                            { cmd: 'CHANGE_ITEM', item: 202, count: 1 },
                                            { cmd: 'SET_FLAG', flag: 'divination_used', value: true },
                                            { cmd: 'TEXT', text: 'The Altar reveals: Chronos Humming Ring! Confirmed trait: ACTION_PLUS (+1 extra action turn in combat!).' }
                                        ]
                                    },
                                    {
                                        label: 'Identify Glacial Shard ????',
                                        condition: 'hasItem:203',
                                        commands: [
                                            { cmd: 'CHANGE_ITEM', item: 203, count: -1 },
                                            { cmd: 'CHANGE_ITEM', item: 204, count: 1 },
                                            { cmd: 'SET_FLAG', flag: 'divination_used', value: true },
                                            { cmd: 'TEXT', text: 'The Altar reveals: Crystalline Frost-Wand! Confirmed trait: Ice Element Attack + 35% Freeze rate.' }
                                        ]
                                    },
                                    {
                                        label: 'Identify Volatile Conduit ????',
                                        condition: 'hasItem:205',
                                        commands: [
                                            { cmd: 'CHANGE_ITEM', item: 205, count: -1 },
                                            { cmd: 'CHANGE_ITEM', item: 206, count: 1 },
                                            { cmd: 'SET_FLAG', flag: 'divination_used', value: true },
                                            { cmd: 'TEXT', text: 'The Altar reveals: Surge Overload Conduit (+22 MAT, -10 MDF). Warning trait: +70% vulnerability to Lightning/Dark!' }
                                        ]
                                    },
                                    { label: 'Cancel', commands: [] }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                id: 5, name: 'Spire Patrol Homunculi', x: 3, y: 3, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'Spire Homunculus sentinels intercept you!' },
                    { cmd: 'BATTLE', troop: 'troop_homunculi' }
                ]
            },
            {
                id: 6, name: 'Arch-Automaton Chamber Door', x: 4, y: 1, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'Before you stands Arch-Automaton Proteus, charging a devastating Arcane Overload beam!' },
                    { cmd: 'TEXT', text: 'Engage Arch-Automaton Proteus?' },
                    {
                        cmd: 'CHOICE',
                        options: [
                            {
                                label: 'Battle Arch-Automaton Proteus',
                                commands: [
                                    { cmd: 'BATTLE', troop: 'troop_boss_automaton' },
                                    { cmd: 'TEXT', text: 'Proteus collapses into inactive scrap! Candidate B completed successfully!' }
                                ]
                            },
                            { label: 'Retreat and configure gear', commands: [] }
                        ]
                    }
                ]
            }
        ]
    };
    writeJson(path.join(projectDir, 'data', 'maps', '2.json'), map2);

    console.log(`Candidate B files authored.`);
}

// -------------------------------------------------------------
// Candidate C Generator: The Purifier's Crucible
// -------------------------------------------------------------
function buildCandidateC(projectDir) {
    console.log(`Building Candidate C in ${projectDir}...`);

    const system = {
        ui: {
            activeFont: 'monogram-extended',
            fontSize: 16,
            fontOffsetY: -4,
            fontNormalize: true
        },
        spawn: { mapId: 1, x: 4, y: 7, dir: 'N' },
        newGame: {
            goldMin: 80,
            goldMax: 80,
            party: {
                fixedMembers: [
                    { id: 'angel', level: 3, name: 'Seraph', slot: 1 },
                    { id: 'imp', level: 3, name: 'Fizz', slot: 2 }
                ]
            }
        },
        rtp: { revision: '1.0' }
    };
    writeJson(path.join(projectDir, 'data', 'system.json'), system);
    writeJson(path.join(projectDir, 'data', 'terms.json'), { 'menu.equip_slots': ['WPN', 'AMR', 'ACC'] });
    writeJson(path.join(projectDir, 'data', 'roles.json'), BASE_ROLES);
    writeJson(path.join(projectDir, 'data', 'elements.json'), BASE_ELEMENTS);
    writeJson(path.join(projectDir, 'data', 'states.json'), BASE_STATES);
    writeJson(path.join(projectDir, 'data', 'passives.json'), BASE_PASSIVES);
    writeJson(path.join(projectDir, 'data', 'skills.json'), BASE_SKILLS);

    // tilesets
    writeJson(path.join(projectDir, 'data', 'tilesets', 'town_default.json'), TOWN_TILESET);
    writeJson(path.join(projectDir, 'data', 'tilesets', 'dungeon_default.json'), DUNGEON_TILESET);

    // units
    writeJson(path.join(projectDir, 'data', 'units', 'index.json'), {
        files: ['angel.json', 'imp.json', 'demon.json', 'diablos.json']
    });

    const growth = [
        { from: 2, to: 10, maxHp: 80, atk: 25, def: 20, mat: 15, mdf: 15 },
        { from: 11, to: 20, maxHp: 120, atk: 35, def: 30, mat: 25, mdf: 25 }
    ];

    writeJson(path.join(projectDir, 'data', 'units', 'angel.json'), {
        id: 'angel', name: 'Cathedral Angel', level: 3, role: 'Defender', smallBattler: 'Angel',
        tier: 1, discipline: 'blacksmithing', elements: ['White'],
        favoriteFoods: [1],
        baseParams: { maxHp: 50, atk: 16, def: 18, mat: 16, mdf: 20, asp: 8, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['lightStrike', 'heal'], passives: ['undeadFortitude']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'imp.json'), {
        id: 'imp', name: 'Imp Scout', level: 3, role: 'Attacker', smallBattler: 'Imp',
        tier: 1, discipline: 'tinkering', elements: ['Black'],
        favoriteFoods: [1],
        baseParams: { maxHp: 42, atk: 20, def: 10, mat: 12, mdf: 10, asp: 14, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['shadowClaw', 'quickStab'], passives: ['swiftReflexes']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'demon.json'), {
        id: 'demon', name: 'Corrupt Demon', level: 4, role: 'Attacker', smallBattler: 'Demon',
        tier: 1, discipline: 'blacksmithing', elements: ['Black'],
        favoriteFoods: [1],
        baseParams: { maxHp: 75, atk: 24, def: 14, mat: 18, mdf: 14, asp: 9, mpd: 1, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['demonRend', 'spark'], passives: ['swiftReflexes']
    });
    writeJson(path.join(projectDir, 'data', 'units', 'diablos.json'), {
        id: 'diablos', name: 'Corrupted Seraph Diablos', level: 6, role: 'Attacker', smallBattler: 'diablos',
        tier: 2, discipline: 'blacksmithing', elements: ['Black'],
        favoriteFoods: [1],
        baseParams: { maxHp: 280, atk: 28, def: 20, mat: 24, mdf: 20, asp: 10, mpd: 2, mxa: 4, mxp: 2 },
        growthBands: growth, skills: ['demonRend', 'darkWave'], passives: ['undeadFortitude']
    });

    // troops
    const troops = Object.assign({}, BASE_TROOPS, {
        troop_imps: {
            id: 'troop_imps', name: 'Imp Raiders',
            members: [{ actor: 'imp', level: 3 }, { actor: 'imp', level: 3 }]
        },
        troop_demon: {
            id: 'troop_demon', name: 'Demon Stalker',
            members: [{ actor: 'demon', level: 4 }]
        },
        troop_demon_pack: {
            id: 'troop_demon_pack', name: 'Demonic Vanguard',
            members: [{ actor: 'demon', level: 4 }, { actor: 'imp', level: 3 }]
        },
        troop_boss_diablos: {
            id: 'troop_boss_diablos', name: 'Corrupted Seraph',
            members: [{ actor: 'diablos', level: 6 }]
        }
    });
    writeJson(path.join(projectDir, 'data', 'troops.json'), troops);

    // items
    const items = [
        { id: 1, name: 'Sacred Balm', type: 'consumable', description: 'Restores 35 HP to one ally.', icon: 51, effects: [{ type: 'hp', value: 35 }] },
        { id: 101, name: 'Holy Water Flask', type: 'consumable', description: 'Consecrated water that cleanses corruption and reveals unknown relics.', icon: 55, effects: [] },
        {
            id: 201, name: 'Tarnished Blade ????', type: 'equipment', equipType: 'Weapon', icon: 1,
            description: 'A blackened holy sword stained with demonic ichor (+20 ATK, -4 DEF, ???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'atk', value: 20 },
                { code: 'PARAM_PLUS', dataId: 'def', value: -4 },
                { code: 'HRG', value: -0.08 }
            ]
        },
        {
            id: 202, name: 'Radiant Sunblade', type: 'equipment', equipType: 'Weapon', icon: 1,
            description: 'Purified in the Sacred Font (+24 ATK, +4 DEF, Light element). Heals the bearer for +5% HP each round.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'atk', value: 24 },
                { code: 'PARAM_PLUS', dataId: 'def', value: 4 },
                { code: 'ELEMENT_ATTACK', dataId: 'White' },
                { code: 'HRG', value: 0.05 }
            ]
        },
        {
            id: 203, name: 'Corrupted Mail ????', type: 'equipment', equipType: 'Armor', icon: 2,
            description: 'Twisted iron mail emitting dark vapor (+24 DEF, -10 ASP, ???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'def', value: 24 },
                { code: 'PARAM_PLUS', dataId: 'asp', value: -10 }
            ]
        },
        {
            id: 204, name: "Paladin's Cuirass", type: 'equipment', equipType: 'Armor', icon: 2,
            description: 'Cleansed in sacred waters (+28 DEF, +12 MDF, -2 ASP). Grants absolute immunity to poison.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'def', value: 28 },
                { code: 'PARAM_PLUS', dataId: 'mdf', value: 12 },
                { code: 'PARAM_PLUS', dataId: 'asp', value: -2 },
                { code: 'STATE_IMMUNITY', dataId: 'poison' }
            ]
        },
        {
            id: 205, name: "Demon's Clasp ????", type: 'equipment', equipType: 'Accessory', icon: 3,
            description: 'A razor-sharp demonic talisman that hungers for blood (+16 ATK, +16 MAT, ???????).',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'atk', value: 16 },
                { code: 'PARAM_PLUS', dataId: 'mat', value: 16 },
                { code: 'PARAM_RATE', dataId: 'def', value: 0.70 }
            ]
        },
        {
            id: 206, name: "Saint's Reliquary", type: 'equipment', equipType: 'Accessory', icon: 3,
            description: 'Purified holy reliquary (+16 ATK, +16 MAT, +8 DEF). Protects against death with a sacred ward.',
            traits: [
                { code: 'PARAM_PLUS', dataId: 'atk', value: 16 },
                { code: 'PARAM_PLUS', dataId: 'mat', value: 16 },
                { code: 'PARAM_PLUS', dataId: 'def', value: 8 },
                { code: 'ON_PERMADEATH', value: 1 }
            ]
        }
    ];
    writeJson(path.join(projectDir, 'data', 'items.json'), items);

    // maps
    writeJson(path.join(projectDir, 'data', 'maps', 'index.json'), { files: ['1.json', '2.json'] });

    const map1 = {
        id: 1,
        title: 'Sacred Cathedral Outpost',
        intro: 'A consecrated redoubt bordering the Sunken Catacomb.',
        depth: 0,
        tileset: 'town_default',
        ceilingStyle: 'sky',
        music: 'town1',
        layout: TOWN_LAYOUT,
        events: [
            {
                id: 1, name: 'High Priestess Althea', x: 4, y: 5, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'Althea: "Blessings upon you, Summoner. The catacomb below is choked with corrupted demonic gear."' },
                    { cmd: 'TEXT', text: 'Althea: "You can equip these corrupted relics directly for immediate brute strength, but their curses will wither your soul."' },
                    { cmd: 'TEXT', text: 'Althea: "If you carry them to the Sacred Purification Font in the depths of the catacomb, you can transform them permanently into divine artifacts!"' }
                ]
            },
            {
                id: 2, name: 'Cathedral Altar of Rest', x: 2, y: 3, trigger: 'interact',
                commands: [
                    { cmd: 'RECOVER_PARTY' }
                ]
            },
            {
                id: 3, name: 'Catacomb Descent', x: 4, y: 1, trigger: 'step',
                commands: [
                    { cmd: 'TEXT', text: 'Descending into the Sunken Catacomb...' },
                    { cmd: 'LOAD_MAP', mapId: 2 }
                ]
            }
        ]
    };
    writeJson(path.join(projectDir, 'data', 'maps', '1.json'), map1);

    const map2 = {
        id: 2,
        title: 'Sunken Catacomb',
        intro: 'Submerged crypts consecrated by ancient saints now corrupted by demons.',
        depth: 1,
        tileset: 'dungeon_default',
        ceilingStyle: 'stone',
        music: 'dungeon1',
        layout: DUNGEON_LAYOUT,
        events: [
            {
                id: 1, name: 'Stairs to Cathedral', x: 4, y: 7, trigger: 'step',
                commands: [
                    { cmd: 'LOAD_MAP', mapId: 1 }
                ]
            },
            {
                id: 2, name: 'Demonic Reliquary 1', x: 1, y: 1, trigger: 'interact',
                commands: [
                    {
                        cmd: 'CONDITIONAL_BRANCH',
                        condition: 'flag:catacomb_chest1_opened',
                        commands: [{ cmd: 'TEXT', text: 'The dark reliquary is empty.' }],
                        elseCommands: [
                            { cmd: 'TEXT', text: 'You wrench open the demonic reliquary! Acquired Tarnished Blade ???? (+20 ATK, -4 DEF) and Corrupted Mail ???? (+24 DEF, -10 ASP)!' },
                            { cmd: 'CHANGE_ITEM', item: 201, count: 1 },
                            { cmd: 'CHANGE_ITEM', item: 203, count: 1 },
                            { cmd: 'SET_FLAG', flag: 'catacomb_chest1_opened', value: true }
                        ]
                    }
                ]
            },
            {
                id: 3, name: 'Demonic Reliquary 2', x: 7, y: 1, trigger: 'interact',
                commands: [
                    {
                        cmd: 'CONDITIONAL_BRANCH',
                        condition: 'flag:catacomb_chest2_opened',
                        commands: [{ cmd: 'TEXT', text: 'The chest is already empty.' }],
                        elseCommands: [
                            { cmd: 'TEXT', text: 'You claim the Demon\'s Clasp ???? (+16 ATK, +16 MAT, ???????)!' },
                            { cmd: 'CHANGE_ITEM', item: 205, count: 1 },
                            { cmd: 'SET_FLAG', flag: 'catacomb_chest2_opened', value: true }
                        ]
                    }
                ]
            },
            {
                id: 4, name: 'Sacred Purification Font', x: 4, y: 5, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'The Sacred Purification Font radiates warm golden light. Dip a corrupted item to cleanse and transfigure it:' },
                    {
                        cmd: 'CHOICE',
                        options: [
                            {
                                label: 'Purify Tarnished Blade ???? -> Radiant Sunblade',
                                condition: 'hasItem:201',
                                commands: [
                                    { cmd: 'CHANGE_ITEM', item: 201, count: -1 },
                                    { cmd: 'CHANGE_ITEM', item: 202, count: 1 },
                                    { cmd: 'TEXT', text: 'The blade blazes with holy fire! Transfigured into Radiant Sunblade (+24 ATK, +4 DEF, Light, +5% HP regen per round)!' }
                                ]
                            },
                            {
                                label: 'Purify Corrupted Mail ???? -> Paladin\'s Cuirass',
                                condition: 'hasItem:203',
                                commands: [
                                    { cmd: 'CHANGE_ITEM', item: 203, count: -1 },
                                    { cmd: 'CHANGE_ITEM', item: 204, count: 1 },
                                    { cmd: 'TEXT', text: 'The dark miasma clears! Transfigured into Paladin\'s Cuirass (+28 DEF, +12 MDF, -2 ASP, Poison Immunity)!' }
                                ]
                            },
                            {
                                label: 'Purify Demon\'s Clasp ???? -> Saint\'s Reliquary',
                                condition: 'hasItem:205',
                                commands: [
                                    { cmd: 'CHANGE_ITEM', item: 205, count: -1 },
                                    { cmd: 'CHANGE_ITEM', item: 206, count: 1 },
                                    { cmd: 'TEXT', text: 'The demonic skull dissolves into gold! Transfigured into Saint\'s Reliquary (+16 ATK, +16 MAT, +8 DEF, Ward against Death)!' }
                                ]
                            },
                            { label: 'Leave the font', commands: [] }
                        ]
                    }
                ]
            },
            {
                id: 5, name: 'Demon Stalker Encounter', x: 3, y: 3, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'A ferocious Corrupt Demon bars the pathway!' },
                    { cmd: 'BATTLE', troop: 'troop_demon' }
                ]
            },
            {
                id: 6, name: 'Boss Sanctum: Corrupted Seraph Diablos', x: 4, y: 1, trigger: 'interact',
                commands: [
                    { cmd: 'TEXT', text: 'Before the grand altar looms Corrupted Seraph Diablos, wielding abyssal dark magic!' },
                    { cmd: 'TEXT', text: 'Challenge Diablos now?' },
                    {
                        cmd: 'CHOICE',
                        options: [
                            {
                                label: 'Challenge Corrupted Seraph Diablos',
                                commands: [
                                    { cmd: 'BATTLE', troop: 'troop_boss_diablos' },
                                    { cmd: 'TEXT', text: 'Diablos falls! Sanctity is restored! Candidate C completed!' }
                                ]
                            },
                            { label: 'Step back to prepare', commands: [] }
                        ]
                    }
                ]
            }
        ]
    };
    writeJson(path.join(projectDir, 'data', 'maps', '2.json'), map2);

    console.log(`Candidate C files authored.`);
}

function main() {
    buildCandidateA(path.join(GAUNTLET_DIR, 'candidate-a'));
    buildCandidateB(path.join(GAUNTLET_DIR, 'candidate-b'));
    buildCandidateC(path.join(GAUNTLET_DIR, 'candidate-c'));
    console.log('All candidates authored successfully!');
}

if (require.main === module) {
    main();
}

module.exports = { buildCandidateA, buildCandidateB, buildCandidateC };
