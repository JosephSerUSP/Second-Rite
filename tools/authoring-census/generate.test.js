'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const schema = require('./schema.json');
const census = require('./census.json');
const { validateCensus, renderMarkdown } = require('./generate.js');

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

test('seed census is valid and deterministic', () => {
  assert.deepEqual(validateCensus(census, schema), []);
  const first = renderMarkdown(census, schema);
  const second = renderMarkdown(census, schema);
  assert.equal(first, second);
  assert.match(first, /## Unhealthy surfaces/);
  assert.match(first, /Scene world camera policy/);
});

test('an unregistered missing dimension fails loud', () => {
  const broken = clone(census);
  const target = broken.surfaces.find(surface => surface.id === 'item-database');
  target.authorable = 'missing';

  const errors = validateCensus(broken, schema);
  assert.ok(errors.some(error =>
    error.includes('.authorable: missing coverage is unregistered debt')));
});

test('registered debt cannot outlive the missing dimension', () => {
  const broken = clone(census);
  const target = broken.surfaces.find(surface => surface.id === 'scene-world-camera');
  target.authorable = 'covered';

  const errors = validateCensus(broken, schema);
  assert.ok(errors.some(error =>
    error.includes("deferredDebt: 'authorable' is registered but the dimension is 'covered'")));
});

test('every finite schema domain must have a census surface', () => {
  const broken = clone(census);
  broken.surfaces = broken.surfaces.filter(surface => surface.domain !== 'Animations');

  const errors = validateCensus(broken, schema);
  assert.ok(errors.some(error =>
    error.includes("domain 'Animations' has no census surface")));
});

test('unknown dimensions cannot be smuggled in as debt', () => {
  const broken = clone(census);
  broken.surfaces[0].deferredDebt.push('looksHealthyToMe');

  const errors = validateCensus(broken, schema);
  assert.ok(errors.some(error =>
    error.includes("unknown dimension 'looksHealthyToMe'")));
});
