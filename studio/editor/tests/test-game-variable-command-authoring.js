'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const engine = JSON.parse(fs.readFileSync(
  path.join(ROOT, 'rtp', 'revisions', '1.0', 'data', 'engine.json'), 'utf8'));
const eventsSource = fs.readFileSync(
  path.join(ROOT, 'studio', 'editor', 'js', 'events.js'), 'utf8');

function command(id) {
  return engine.commands.find(entry => entry.id === id);
}

test('persistent Game Variable commands are registry-driven on every Event Program host', () => {
  const setVar = command('SET_GAME_VARIABLE');
  const unsetVar = command('UNSET_GAME_VARIABLE');
  const setSwitch = command('SET_GAME_SWITCH');

  assert.ok(setVar && unsetVar && setSwitch);
  assert.deepEqual(setVar.contexts, ['any']);
  assert.deepEqual(unsetVar.contexts, ['any']);
  assert.deepEqual(setSwitch.contexts, ['any']);
  assert.equal(setVar.params.find(param => param.key === 'value').type, 'stateValue');
  assert.equal(setSwitch.params.find(param => param.key === 'value').type, 'flag');
});

test('shared command modal treats stateValue as a Formula-context expression', () => {
  assert.match(eventsSource,
    /paramDef\.type === 'formula' \|\| paramDef\.type === 'stateValue' \|\| paramDef\.type === 'script'/);
  assert.match(eventsSource, /paramDef\.type === 'stateValue'/);
  assert.match(eventsSource, /Persistent state value context/);
  assert.match(eventsSource, /deterministic persistent-state expression/);
});

test('Formula help advertises persistent Variable reads separately from flow-local v', () => {
  const variableHelp = engine.formulaHelp.find(entry => entry.token === 'variables.name');
  const localHelp = engine.formulaHelp.find(entry => entry.token === 'v');
  assert.ok(variableHelp);
  assert.match(variableHelp.description, /Persistent playthrough Game Variable/);
  assert.ok(localHelp);
  assert.match(localHelp.description, /Flow-local variables/);
});
