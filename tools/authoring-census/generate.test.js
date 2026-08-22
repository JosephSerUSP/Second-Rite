'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const path = require('node:path');

const schema = require('./schema.json');
const census = require('./census.json');
const { validateCensus, renderMarkdown } = require('./generate.js');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

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

test('generated state documents are pinned to LF checkout bytes', () => {
  const documents = [
    'docs/AUTHORING-STATE.md',
    'docs/ENGINE-STATE.md'
  ];
  const output = execFileSync(
    'git',
    ['check-attr', 'eol', '--', ...documents],
    { cwd: REPO_ROOT, encoding: 'utf8' }
  );
  const lines = new Set(output.trim().split(/\r?\n/));

  for (const document of documents) {
    assert.ok(
      lines.has(`${document}: eol: lf`),
      `${document} must keep eol=lf so core.autocrlf cannot change gate input bytes`
    );
  }
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
  // Camera authoring itself was closed by #619; its remaining registered
  // debt is the canonical visual fixture. Mutate a dimension that is
  // actually missing in the current seed so this test follows semantic ID +
  // current debt rather than a historical surface state.
  target.goldenFixture = 'covered';

  const errors = validateCensus(broken, schema);
  assert.ok(errors.some(error =>
    error.includes("deferredDebt: 'goldenFixture' is registered but the dimension is 'covered'")));
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
