'use strict';

const assert = require('assert');
const path = require('path');
const test = require('node:test');
const { resolveLoveExecutable, run, usage } = require('./project-cli');

test('Project CLI exposes play as a first-class ordinary Project action', () => {
    let played = null;
    const relative = path.join('projects', 'labs', 'scene-benchmarks');
    const code = run(['play', relative], {
        playProject(projectPath) {
            played = projectPath;
        },
    });

    assert.equal(code, 0);
    assert.equal(played, path.resolve(relative));
    assert.match(usage(), /play <project>/);
    assert.match(usage(), /ordinary Test Play boundary/);
});

test('Project CLI play rejects JSON output mode rather than implying a synchronous result', () => {
    assert.throws(
        () => run(['play', 'projects/labs/scene-benchmarks', '--json'], { playProject() {} }),
        /play does not support --json/,
    );
});

test('LOVE_PATH overrides the platform default for Project Test Play', () => {
    assert.equal(resolveLoveExecutable({ LOVE_PATH: '/custom/love' }, 'linux'), '/custom/love');
    assert.equal(resolveLoveExecutable({}, 'win32'), 'C:\\Program Files\\LOVE\\love.exe');
    assert.equal(resolveLoveExecutable({}, 'linux'), 'love');
});

test('lab:benchmarks invokes the generic Project play command rather than Studio', () => {
    const pkg = require('../../package.json');
    assert.equal(pkg.scripts['lab:benchmarks'], 'node tools/editor/project-cli.js play projects/labs/scene-benchmarks');
});
