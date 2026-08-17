'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const lifecycle = require('../editor/project-lifecycle');
const context = require('./lib/context');

const installRoot = path.resolve(__dirname, '..', '..');

function withSparseProject(fn) {
    const parent = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-generator-context-'));
    const projectRoot = path.join(parent, 'project');
    lifecycle.createProject({ mode: 'sparse', target: projectRoot, installRoot, name: 'Neutral Context Test' });
    try { return fn(projectRoot); }
    finally { fs.rmSync(parent, { recursive: true, force: true }); }
}

test('generator ruleset is read from the generated Project, not canonical Second Gate', () => {
    withSparseProject(projectRoot => {
        const initial = context.ruleset(projectRoot);
        assert.deepStrictEqual(initial.roles, []);
        assert.deepStrictEqual(initial.elements, []);
        assert.deepStrictEqual(initial.skills, []);

        fs.writeFileSync(path.join(projectRoot, 'data', 'roles.json'), JSON.stringify({ FieldResearcher: { name: 'Field Researcher' } }, null, 2));
        fs.writeFileSync(path.join(projectRoot, 'data', 'elements.json'), JSON.stringify({ Spore: { name: 'Spore' } }, null, 2));
        fs.writeFileSync(path.join(projectRoot, 'data', 'skills.json'), JSON.stringify({ sampleLeaf: { id: 'sampleLeaf', name: 'Sample Leaf', target: 'enemy-any', scope: 'battle', element: 'Spore', effects: [] } }, null, 2));

        const local = context.ruleset(projectRoot);
        assert.deepStrictEqual(local.roles, ['FieldResearcher']);
        assert.deepStrictEqual(local.elements, ['Spore']);
        assert.deepStrictEqual(local.skills.map(skill => skill.id), ['sampleLeaf']);
        assert.ok(!local.roles.includes('Summoner'));
        assert.ok(!local.elements.includes('White'));
        assert.ok(!local.skills.some(skill => skill.id === 'windBlade'));
    });
});

test('generator command context resolves reusable RTP semantics through sparse Project', () => {
    withSparseProject(projectRoot => {
        const commands = context.commandRegistry(projectRoot);
        assert.ok(commands.length > 0, 'sparse Project should resolve inherited RTP command registry');
        assert.ok(commands.every(command => typeof command.id === 'string' && command.id.length > 0));
    });
});

test('neutral schemas contain structural contracts, not live Second Gate examples', () => {
    const text = JSON.stringify(context.schemas());
    for (const forbidden of ['Summoner', 'Wind Blade', 'windBlade', 'Pixie', 'Cerberus', 'Second Gate']) {
        assert.ok(!text.includes(forbidden), `neutral schema unexpectedly contains ${forbidden}`);
    }
    assert.match(text, /Project-defined role id/);
    assert.match(text, /Empty RPG databases are valid/);
});
