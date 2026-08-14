'use strict';

const assert = require('assert');
const path = require('path');
const test = require('node:test');
const wrapper = require('./generate-project');

test('explicit Project wrapper keeps generator options and rejoins shell-split pitch words', () => {
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

test('explicit Project wrapper preserves already-quoted pitch and equals-form options', () => {
    const parsed = wrapper.parse([
        '--project=projects/labs/tiny-game',
        '--stage=maps',
        'One complete pitch',
    ]);
    assert.deepEqual(parsed.forwarded, ['--stage=maps', 'One complete pitch']);
});

test('explicit Project wrapper owns name/cleanup safety', () => {
    assert.throws(() => wrapper.parse(['--project', 'x', '--name', 'other', 'pitch']), /Do not pass --name/);
    assert.throws(() => wrapper.parse(['--project', 'x', '--clean', 'pitch']), /never auto-deleted/);
    assert.throws(() => wrapper.parse(['pitch']), /--project is required/);
});
