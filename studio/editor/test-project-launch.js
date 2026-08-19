'use strict';

const assert = require('assert');
const test = require('node:test');
const { parseLaunchArgs } = require('./start-studio');

test('Studio launch extracts --project without leaking it to Electron app args', () => {
    assert.deepEqual(parseLaunchArgs(['--project', 'C:/Games/Tiny', '--inspect']), {
        project: 'C:/Games/Tiny',
        passthrough: ['--inspect'],
    });
    assert.deepEqual(parseLaunchArgs(['--project=../lab', 'extra']), {
        project: '../lab',
        passthrough: ['extra'],
    });
});

test('Studio launch keeps ordinary arguments and rejects empty Project switches', () => {
    assert.deepEqual(parseLaunchArgs(['foo', 'bar']), { project: null, passthrough: ['foo', 'bar'] });
    assert.throws(() => parseLaunchArgs(['--project']), /requires a path/);
    assert.throws(() => parseLaunchArgs(['--project=']), /requires a path/);
});
