const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.resolve(__dirname, '..', '..', '..');
const hierarchy = require(path.join(root, 'studio', 'editor', 'js', 'map-hierarchy.js'));

function category(map, index) {
    return map.category || (index === 0 ? 'town' : 'dungeon');
}

test('map hierarchy builds arbitrary-depth authored parentage while leaving unparented maps at root', () => {
    const maps = [
        { id: 17, title: 'Praca', category: 'town' },
        { id: 24, title: 'House', category: 'town', parentMapId: 17 },
        { id: 30, title: 'Corridor', category: 'town', parentMapId: 24 },
        { id: 31, title: 'Room', category: 'town', parentMapId: 30 },
        { id: 2, title: 'Dungeon', category: 'dungeon' },
    ];

    const forest = hierarchy.buildForest(maps, category);
    assert.deepEqual(forest.rootsByCategory.town.map(node => node.map.id), [17]);
    assert.deepEqual(forest.rootsByCategory.dungeon.map(node => node.map.id), [2]);
    assert.equal(forest.rootsByCategory.town[0].children[0].map.id, 24);
    assert.equal(forest.rootsByCategory.town[0].children[0].children[0].map.id, 30);
    assert.equal(forest.rootsByCategory.town[0].children[0].children[0].children[0].map.id, 31);
});

test('numeric and string map ids resolve as the same authored reference', () => {
    const maps = [
        { id: 17, category: 'town' },
        { id: 24, category: 'town', parentMapId: '17' },
    ];
    const forest = hierarchy.buildForest(maps, category);
    assert.equal(forest.rootsByCategory.town[0].children[0].map.id, 24);
    assert.equal(hierarchy.findMapById(maps, '24').id, 24);
});

test('orphaned parent references stay visible at root with a problem instead of disappearing', () => {
    const maps = [
        { id: 1, category: 'town' },
        { id: 2, category: 'town', parentMapId: 999 },
    ];
    const forest = hierarchy.buildForest(maps, category);
    assert.deepEqual(forest.rootsByCategory.town.map(node => node.map.id), [1, 2]);
    assert.match(forest.rootsByCategory.town[1].problem, /does not exist/);
});

test('cycles never recurse and are excluded from parent choices', () => {
    const maps = [
        { id: 1, category: 'town', parentMapId: 2 },
        { id: 2, category: 'town', parentMapId: 1 },
        { id: 3, category: 'town', parentMapId: 1 },
    ];
    const forest = hierarchy.buildForest(maps, category);
    assert.deepEqual(forest.rootsByCategory.town.map(node => node.map.id), [1, 2, 3]);
    forest.rootsByCategory.town.forEach(node => assert.match(node.problem, /cycle/));
    assert.equal(hierarchy.wouldCreateCycle(maps, 1, 2), true);
    assert.deepEqual(hierarchy.validParentMaps(maps, 1), []);
});

test('a map cannot be reparented underneath one of its descendants', () => {
    const maps = [
        { id: 1, category: 'town' },
        { id: 2, category: 'town', parentMapId: 1 },
        { id: 3, category: 'town', parentMapId: 2 },
        { id: 4, category: 'town' },
    ];
    assert.equal(hierarchy.wouldCreateCycle(maps, 1, 2), true);
    assert.equal(hierarchy.wouldCreateCycle(maps, 1, 3), true);
    assert.equal(hierarchy.wouldCreateCycle(maps, 1, 4), false);
    assert.deepEqual(hierarchy.validParentMaps(maps, 1).map(map => map.id), [4]);
});

test('Studio wires hierarchy authoring through Map Properties and loads the helper before map-editor', () => {
    const markup = fs.readFileSync(path.join(root, 'studio', 'editor', 'index.html'), 'utf8');
    const editor = fs.readFileSync(path.join(root, 'studio', 'editor', 'js', 'map-editor.js'), 'utf8');
    assert.ok(markup.includes('id="prop-map-parent"'));
    assert.ok(markup.indexOf('js/map-hierarchy.js') < markup.indexOf('js/map-editor.js'));
    assert.match(editor, /ThestraMapHierarchy\.buildForest/);
    assert.match(editor, /parentMapId/);
});
