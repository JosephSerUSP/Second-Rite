'use strict';

const assert = require('assert');
const path = require('path');
const test = require('node:test');
const wrapper = require('./generate-project');

test('explicit Project wrapper keeps generator options and rejoins shell-split goal words', () => {
    const parsed = wrapper.parse([
        '--project', 'projects/labs/tiny-game',
        '--provider', 'gemini',
        '--dry-run',
        'A', 'tiny', 'isolated', 'game',
    ]);
    assert.equal(parsed.project, path.resolve('projects/labs/tiny-game'));
    assert.deepEqual(parsed.forwarded, [
        '--provider', 'gemini',
        '--dry-run',
        'A tiny isolated game',
    ]);
});

test('Project slug and historical generator run id are separate identities', () => {
    assert.equal(wrapper.generatorRunName(path.resolve('projects/labs/tiny-game')), 'tiny_game');
    assert.equal(wrapper.generatorRunName(path.resolve('projects/labs/tiny_game')), 'tiny_game');
});

test('explicit Project wrapper preserves already-quoted goal and equals-form options', () => {
    const parsed = wrapper.parse([
        '--project=projects/labs/tiny-game',
        '--stage=maps',
        '--responses=tools/campaign-gen/proof/tiny',
        'One complete goal',
    ]);
    assert.deepEqual(parsed.forwarded, [
        '--stage=maps',
        '--responses=tools/campaign-gen/proof/tiny',
        'One complete goal',
    ]);
});

test('recorded proof responses are a normal value option, not a model provider', () => {
    const parsed = wrapper.parse([
        '--project', 'projects/labs/tiny-game',
        '--responses', 'tools/campaign-gen/proof/tiny',
        'Tiny game',
    ]);
    assert.deepEqual(parsed.forwarded, [
        '--responses', 'tools/campaign-gen/proof/tiny',
        'Tiny game',
    ]);
});

test('explicit Project wrapper owns name/cleanup safety', () => {
    assert.throws(() => wrapper.parse(['--project', 'x', '--name', 'other', 'goal']), /Do not pass --name/);
    assert.throws(() => wrapper.parse(['--project', 'x', '--clean', 'goal']), /never auto-deleted/);
    assert.throws(() => wrapper.parse(['goal']), /--project is required/);
});
