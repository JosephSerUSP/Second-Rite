'use strict';

// #392: minimum Project-owned authored skeleton. Reusable semantic defaults
// come from pinned RTP revision 1.0; this file contains only identity/startup
// structure a brand-new Project must own itself.

function titleScene(projectName = 'New Project') {
    const name = String(projectName || 'New Project').trim() || 'New Project';
    return {
        id: 'title',
        name: 'Title Screen',
        kind: 'menu',
        draw: 'windows',
        windows: [
            {
                id: 'project_title',
                rect: { x: 6, y: 7, w: 20, h: 5 },
                style: 'frame',
                // Generic window text uses {expr} for Formula interpolation;
                // it does not implement a {term:...} token. The Project name
                // is already known at materialization time, so author it
                // literally rather than shipping an invalid Formula that
                // renders as the evaluator's fallback 0.
                content: [{ type: 'text', text: name }],
            },
            {
                id: 'title_menu',
                rect: { x: 9, y: 14, w: 14, h: 5 },
                style: 'list',
                visibleRows: 2,
                content: [{ type: 'list', listId: 'term:title.options', cursor: 'v.idx' }],
            },
        ],
        hooks: {
            on_enter: [{ cmd: 'SET_VAR', name: 'idx', value: 1 }],
            on_up: [{ cmd: 'SET_VAR', name: 'idx', value: 'v.idx == 1 and 2 or 1' }],
            on_down: [{ cmd: 'SET_VAR', name: 'idx', value: 'v.idx == 1 and 2 or 1' }],
            on_select: [
                {
                    cmd: 'IF',
                    condition: 'v.idx == 1',
                    then: [
                        { cmd: 'RESET_SESSION' },
                        { cmd: 'LOAD_MAP', mapId: 1 },
                        { cmd: 'SCENE_EVENT', kind: 'goto', scene: 'map' },
                    ],
                },
                {
                    cmd: 'IF',
                    condition: 'v.idx == 2',
                    then: [{ cmd: 'QUIT_GAME' }],
                },
            ],
        },
        config: {},
    };
}

function mapScene() {
    const fallback = [{ cmd: 'FALLBACK' }];
    return {
        id: 'map',
        name: 'Map',
        kind: 'map',
        config: {},
        hooks: {
            on_up: fallback,
            on_down: fallback,
            on_left: fallback,
            on_right: fallback,
            on_select: fallback,
        },
    };
}

function startMap() {
    return {
        id: 1,
        title: 'First Map',
        category: 'town',
        depth: 0,
        safe: true,
        layout: [
            '#######',
            '#.....#',
            '#.....#',
            '#.....#',
            '#######',
        ],
        spawn: { x: 3, y: 2, dir: 'N' },
        events: [],
    };
}

function files(projectName = 'New Project') {
    const name = String(projectName || 'New Project').trim() || 'New Project';
    return new Map([
        ['data/system.json', {
            ui: { activeFont: 'Jersey10-Regular', fontSize: 16 },
            spawn: { mapId: 1, x: 3, y: 2, dir: 'N' },
            newGame: { goldMin: 0, goldMax: 0, party: { fixedMembers: [] } },
            rtp: { revision: '1.0' },
        }],
        ['data/terms.json', {
            project: { title: name },
            title: { options: ['Begin', 'Exit'] },
            log: { wall_blocks: 'A wall blocks the way.' },
        }],
        ['data/elements.json', {}],
        ['data/items.json', []],
        ['data/lore.json', []],
        ['data/quests.json', {}],
        ['data/shops.json', {}],
        ['data/sounds.json', {}],
        ['data/actionSequences.json', {}],
        ['data/commonEvents.json', []],
        ['data/skills.json', {}],
        ['data/passives.json', {}],
        ['data/states.json', {}],
        ['data/roles.json', {}],
        ['data/animations.json', {}],
        ['data/troops.json', {}],
        ['data/iconPalettes.json', {}],
        ['data/iconKeyProfiles.json', {}],
        ['data/flows/battle.json', {}],
        ['data/flows/exploration.json', {}],
        ['data/units/index.json', { files: [] }],
        ['data/maps/index.json', { files: ['1.json'] }],
        ['data/maps/1.json', startMap()],
        ['data/scenes/index.json', { files: ['title.json', 'map.json'] }],
        ['data/scenes/title.json', titleScene(name)],
        ['data/scenes/map.json', mapScene()],
        // #485 explicit-empty keyed registry marker. This file is valid only
        // while it is the registry's sole JSON file. Studio removes it when
        // the first tileset record is authored; populated keyed registries do
        // not maintain an ordered shared index.
        ['data/tilesets/index.json', { files: [] }],
    ]);
}

module.exports = { files, mapScene, startMap, titleScene };
