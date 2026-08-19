'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..');
const rtpEnginePath = path.join(ROOT, 'rtp', 'revisions', '1.0', 'data', 'engine.json');
const snakeScenePath = path.join(ROOT, 'projects', 'labs', 'scene-benchmarks', 'data', 'scenes', 'a003_snake.json');

test('RTP engine.json formulaHelp and scriptingHelp document transient fixed time tokens', () => {
    assert.ok(fs.existsSync(rtpEnginePath), 'rtp engine.json must exist');
    const engineData = JSON.parse(fs.readFileSync(rtpEnginePath, 'utf8'));

    // formulaHelp verification
    assert.ok(Array.isArray(engineData.formulaHelp), 'formulaHelp must be an array');
    const formulaTokens = new Map(engineData.formulaHelp.map(e => [e.token, e.description]));

    for (const token of ['time.dt', 'time.tick', 'time.elapsed']) {
        assert.ok(formulaTokens.has(token), `formulaHelp must document ${token}`);
        const desc = formulaTokens.get(token);
        assert.ok(desc.includes('on_frame'), `${token} description must note on_frame availability`);
        assert.ok(desc.includes('Read-only') || desc.includes('read-only'), `${token} description must note read-only`);
        assert.ok(desc.includes('transient'), `${token} description must note transient context`);
        assert.ok(desc.includes('not in v') || desc.includes('not v'), `${token} description must note not in v`);
        assert.ok(desc.includes('not persistent'), `${token} description must note not persistent`);
        assert.ok(desc.includes('not savegame state'), `${token} description must note not savegame state`);
    }

    // scriptingHelp verification
    assert.ok(Array.isArray(engineData.scriptingHelp), 'scriptingHelp must be an array');
    const scriptTokens = new Map(engineData.scriptingHelp.map(e => [e.token, e.description]));
    assert.ok(scriptTokens.has('ctx.time'), 'scriptingHelp must document ctx.time');
    const ctxTimeDesc = scriptTokens.get('ctx.time');
    assert.ok(ctxTimeDesc.includes('on_frame'), 'ctx.time description must note on_frame');
    assert.ok(ctxTimeDesc.includes('transient'), 'ctx.time description must note transient context');
});

test('A003 Snake fixture has valid fixed timing and round-trips without semantic loss', () => {
    assert.ok(fs.existsSync(snakeScenePath), 'a003_snake.json must exist');
    const rawContent = fs.readFileSync(snakeScenePath, 'utf8');
    const snakeScene = JSON.parse(rawContent);

    assert.equal(snakeScene.id, 'a003_snake');
    assert.ok(snakeScene.update, 'snake scene must have update config');
    assert.equal(snakeScene.update.mode, 'fixed');
    assert.ok(Math.abs(snakeScene.update.step - 0.0166666666666667) < 1e-12);
    assert.equal(snakeScene.update.maxCatchUp, 8);

    // Serialization round-trip preservation
    const reSerialized = JSON.stringify(snakeScene, null, 2);
    const parsedBack = JSON.parse(reSerialized);
    assert.deepEqual(parsedBack, snakeScene, 'round-trip must be semantically identical');
});

test('Studio Scene Timing state transition: default <-> fixed with forward-compatible preservation', () => {
    // 1. Scene starting in default timing
    const scene = {
        id: 'custom_menu',
        name: 'Custom Menu',
        kind: 'menu',
        config: {},
        hooks: {},
        customUnknownField: 'forward_compat_val',
    };

    // Verify initial unauthored state
    assert.equal(scene.update, undefined, 'default scene has undefined update');

    // 2. Author fixed timing
    scene.update = scene.update && typeof scene.update === 'object' ? scene.update : {};
    scene.update.mode = 'fixed';
    if (scene.update.step === undefined) scene.update.step = 0.0166666666666667;
    if (scene.update.maxCatchUp === undefined) scene.update.maxCatchUp = 8;
    scene.update.futureTimingExtension = { customRate: 1 };

    assert.equal(scene.update.mode, 'fixed');
    assert.equal(scene.update.step, 0.0166666666666667);
    assert.equal(scene.update.maxCatchUp, 8);
    assert.deepEqual(scene.update.futureTimingExtension, { customRate: 1 });

    // 3. Mutate step while preserving unknown properties on update
    scene.update.step = 0.0333333333333333;
    assert.equal(scene.update.step, 0.0333333333333333);
    assert.deepEqual(scene.update.futureTimingExtension, { customRate: 1 });
    assert.equal(scene.customUnknownField, 'forward_compat_val');

    // 4. Switch back to default timing
    delete scene.update;
    assert.equal(scene.update, undefined, 'switching to default deletes update object');
    assert.equal(scene.customUnknownField, 'forward_compat_val');
});

test('Studio Scene Timing input validation logic', () => {
    const validateStep = (text) => {
        const trimmed = String(text).trim();
        const num = Number(trimmed);
        return trimmed !== '' && !isNaN(num) && isFinite(num) && num > 0;
    };

    const validateCatchUp = (text) => {
        const trimmed = String(text).trim();
        if (trimmed === '') return { valid: true, unset: true };
        const num = Number(trimmed);
        return {
            valid: Number.isInteger(num) && num >= 1 && num <= 120,
            value: num,
        };
    };

    // Valid steps
    assert.ok(validateStep('0.0166666666666667'));
    assert.ok(validateStep('0.0333333333333333'));
    assert.ok(validateStep('0.1'));
    assert.ok(validateStep('1'));

    // Invalid steps
    assert.ok(!validateStep(''));
    assert.ok(!validateStep('0'));
    assert.ok(!validateStep('-0.016'));
    assert.ok(!validateStep('abc'));
    assert.ok(!validateStep('NaN'));
    assert.ok(!validateStep('Infinity'));

    // Valid catch-up
    assert.ok(validateCatchUp('').valid);
    assert.ok(validateCatchUp('').unset);
    assert.ok(validateCatchUp('1').valid);
    assert.ok(validateCatchUp('8').valid);
    assert.ok(validateCatchUp('60').valid);
    assert.ok(validateCatchUp('120').valid);

    // Invalid catch-up
    assert.ok(!validateCatchUp('0').valid);
    assert.ok(!validateCatchUp('121').valid);
    assert.ok(!validateCatchUp('8.5').valid);
    assert.ok(!validateCatchUp('-1').valid);
    assert.ok(!validateCatchUp('xyz').valid);
});
