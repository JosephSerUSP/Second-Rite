'use strict';

const assert = require('assert');
const test = require('node:test');
const icons = require('./build-icons');

test('tracked Thestra Studio icon containers match the current optical PNGs', () => {
    icons.checkCurrent();
});

test('icon container generation is deterministic and self-validating', () => {
    const first = icons.buildContainers();
    const second = icons.buildContainers();
    assert.ok(first.ico.equals(second.ico));
    assert.ok(first.icns.equals(second.icns));
    icons.validateIco(first.ico);
    icons.validateIcns(first.icns);
});
