'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Self = require('../js/event_self_state_authoring.js');

const fixture = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../../tests/fixtures/event_self_state_authoring.json'), 'utf8'));
const engineRegistry = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../../rtp/revisions/1.0/data/engine.json'), 'utf8'));
const commandById = Object.fromEntries(engineRegistry.commands.map(command => [command.id, command]));
assert.deepStrictEqual(commandById.SET_SELF_SWITCH.contexts, ['map', 'common']);
assert.strictEqual(commandById.SET_SELF_SWITCH.params.find(param => param.key === 'value').type, 'flag');
assert.deepStrictEqual(commandById.SET_SELF_VARIABLE.params.find(param => param.key === 'operation').options,
    ['set', 'add', 'subtract', 'multiply', 'divide']);
assert.strictEqual(commandById.SET_SELF_VARIABLE.params.find(param => param.key === 'value').type, 'stateValue',
    'SELF Variable writes must share #407 structured state-value authoring');
assert.ok(engineRegistry.formulaHelp.some(entry => entry.token === 'self.switches.<name>'));
assert.ok(engineRegistry.formulaHelp.some(entry => entry.token === 'self.variables.<name>'));

const id1 = Self.createInstanceId(() => '11111111-1111-4111-8111-111111111111');
const id2 = Self.createInstanceId(() => '22222222-2222-4222-8222-222222222222');
assert.strictEqual(id1, 'event:11111111-1111-4111-8111-111111111111');
assert.notStrictEqual(id1, id2, 'recreated placements must receive distinct stable identity');
assert.strictEqual(Self.ensureInstanceId({ instanceId: id1 }, () => 'unused'), id1,
    'existing placement identity must remain stable');
const pasted = { id: 9, instanceId: id1, scriptId: 7 };
Self.assignFreshInstanceId(pasted, () => '33333333-3333-4333-8333-333333333333');
assert.strictEqual(pasted.scriptId, 7, 'copy/paste keeps reusable behavior');
assert.strictEqual(pasted.instanceId, 'event:33333333-3333-4333-8333-333333333333');
assert.notStrictEqual(pasted.instanceId, id1, 'copy/paste must refresh placement identity');

const spec = Self.serializePageConditions({
    switchEnabled: true,
    switchName: 'A',
    switchValue: true,
    variableEnabled: true,
    variableName: 'phase',
    variableOperator: '>=',
    variableType: 'number',
    variableValue: '2',
});
assert.deepStrictEqual(spec, {
    switch: { name: 'A', value: true },
    variable: { name: 'phase', operator: '>=', value: 2 },
});
const fixtureSpec = Self.serializePageConditions({
    switchEnabled: true,
    switchName: 'open',
    switchValue: true,
    variableEnabled: true,
    variableName: 'phase',
    variableOperator: '>=',
    variableType: 'number',
    variableValue: '2',
});
assert.deepStrictEqual(fixtureSpec, fixture.pageSelfConditions,
    'Studio serialization must match the shared runtime parity fixture');
assert.strictEqual(Self.summarize(spec), 'SELF A=ON & SELF phase >= 2');
assert.deepStrictEqual(Self.pageFormState(spec), {
    switchEnabled: true,
    switchName: 'A',
    switchValue: true,
    variableEnabled: true,
    variableName: 'phase',
    variableOperator: '>=',
    variableType: 'number',
    variableValue: '2',
});

assert.deepStrictEqual(Self.serializePageConditions({
    variableEnabled: true,
    variableName: 'mood',
    variableOperator: '==',
    variableType: 'string',
    variableValue: 'awake',
}), { variable: { name: 'mood', operator: '==', value: 'awake' } });

assert.deepStrictEqual(Self.serializePageConditions({
    variableEnabled: true,
    variableName: 'visited',
    variableOperator: 'is_set',
    variableType: 'number',
    variableValue: 'not-used',
}), { variable: { name: 'visited', operator: 'is_set' } });

assert.strictEqual(Self.serializePageConditions({}), undefined);
assert.throws(() => Self.serializePageConditions({ switchEnabled: true, switchName: '' }), /needs a name/);
assert.throws(() => Self.serializePageConditions({
    variableEnabled: true, variableName: 'phase', variableOperator: '>=', variableType: 'number', variableValue: 'NaN',
}), /finite number/);
assert.throws(() => Self.serializePageConditions({
    variableEnabled: true, variableName: 'phase', variableOperator: '>=', variableType: 'string', variableValue: '2',
}), /require a Number/);

console.log('Event SELF authoring tests passed');
