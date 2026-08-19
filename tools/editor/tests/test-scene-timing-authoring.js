'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Timing = require('../js/scene-timing-authoring.js');
const ROOT = path.resolve(__dirname, '..', '..', '..');

(function legacyInspectionIsNonMutating() {
    const scene = { id: 'menu', config: { keep: true }, future: { untouched: true } };
    const before = JSON.stringify(scene);
    assert.equal(Timing.snapshot(scene).mode, 'legacy');
    assert.deepStrictEqual(Timing.validateScene(scene), []);
    assert.strictEqual(JSON.stringify(scene), before,
        'opening/inspecting a legacy Scene must not create Scene.update');
})();

(function enablingFixedAuthorsOnlyTheExistingClockContract() {
    const scene = { id: 'custom', unrelated: { keep: ['verbatim'] } };
    Timing.setMode(scene, 'fixed');
    assert.deepStrictEqual(scene.update, {
        mode: 'fixed', step: 1 / 60, maxCatchUp: 8
    });
    assert.deepStrictEqual(scene.unrelated, { keep: ['verbatim'] });
    assert.deepStrictEqual(Timing.validateScene(scene), []);
})();

(function fixedRoundTripPreservesUnknownSceneAndUpdateFields() {
    const scene = {
        id: 'future',
        update: {
            mode: 'fixed', step: 1 / 30, maxCatchUp: 4,
            futureSchedulerField: { preserve: true }
        },
        futureSceneField: { keep: [1, 2, 3] }
    };
    const opened = JSON.stringify(scene);
    Timing.snapshot(scene);
    Timing.validateScene(scene);
    assert.equal(JSON.stringify(scene), opened, 'opening a fixed Scene must not normalize it');
    Timing.setStep(scene, '0.02');
    Timing.setMaxCatchUp(scene, '12');
    assert.equal(scene.update.step, 0.02);
    assert.equal(scene.update.maxCatchUp, 12);
    assert.deepStrictEqual(scene.update.futureSchedulerField, { preserve: true });
    assert.deepStrictEqual(scene.futureSceneField, { keep: [1, 2, 3] });
})();

(function legacySwitchIsDeliberateAndLossless() {
    const plain = { update: { mode: 'fixed', step: 0.1, maxCatchUp: 3 }, hooks: { on_frame: [] } };
    Timing.setMode(plain, 'legacy');
    assert.equal(Object.prototype.hasOwnProperty.call(plain, 'update'), false);
    assert.deepStrictEqual(plain.hooks, { on_frame: [] });

    const extended = {
        update: { mode: 'fixed', step: 0.1, maxCatchUp: 3, futureSchedulerField: true }
    };
    const before = JSON.stringify(extended);
    assert.throws(() => Timing.setMode(extended, 'legacy'), /without discarding unknown Scene update fields/);
    assert.equal(JSON.stringify(extended), before,
        'legacy switch must fail rather than erase unknown update extensions');
})();

(function invalidValuesFailWithoutPartialMutation() {
    const scene = { update: { mode: 'fixed', step: 1 / 60, maxCatchUp: 8 } };
    for (const [mutate, pattern] of [
        [() => Timing.setStep(scene, 0), /finite positive number of seconds/],
        [() => Timing.setStep(scene, 'nope'), /finite number/],
        [() => Timing.setMaxCatchUp(scene, 0), /integer from 1 to 120/],
        [() => Timing.setMaxCatchUp(scene, 2.5), /integer from 1 to 120/],
        [() => Timing.setMaxCatchUp(scene, 121), /integer from 1 to 120/]
    ]) {
        const before = JSON.stringify(scene);
        assert.throws(mutate, pattern);
        assert.equal(JSON.stringify(scene), before);
    }
})();

(function a003SnakeSurvivesStudioInspectionExactly() {
    const fixturePath = path.join(ROOT, 'projects', 'labs', 'scene-benchmarks', 'data', 'scenes', 'a003_snake.json');
    const scene = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
    const before = JSON.stringify(scene);
    assert.equal(scene.update.mode, 'fixed');
    assert.deepStrictEqual(Timing.validateScene(scene), []);
    const state = Timing.snapshot(scene);
    assert.equal(state.mode, 'fixed');
    assert.equal(state.step, scene.update.step);
    assert.equal(state.maxCatchUp, scene.update.maxCatchUp);
    assert.equal(JSON.stringify(scene), before,
        'opening A003 in Studio must preserve its authored update object exactly');
})();

(function formulaHelpDocumentsTheRuntimeOwnedTransientClock() {
    const engine = JSON.parse(fs.readFileSync(
        path.join(ROOT, 'rtp', 'revisions', '1.0', 'data', 'engine.json'), 'utf8'));
    const helpByToken = new Map(engine.formulaHelp.map(entry => [entry.token, entry.description]));
    assert.equal(helpByToken.get('time.dt'),
        'Exact logical step in seconds during a fixed Scene on_frame tick. Available only during fixed on_frame; transient context, not a Game Variable, not persistent Scene state, and not saved.');
    assert.equal(helpByToken.get('time.tick'),
        'Scene-instance logical tick index during fixed on_frame. Available only during fixed on_frame; transient context, not a Game Variable, not persistent Scene state, and not saved.');
    assert.equal(helpByToken.get('time.elapsed'),
        'Scene-instance logical elapsed time in seconds during fixed on_frame. Available only during fixed on_frame; transient context, not a Game Variable, not persistent Scene state, and not saved.');
    assert.equal(engine.scriptingHelp.some(entry => entry.token === 'ctx.time'), false,
        'SCRIPT help must not advertise timing facts the current sandbox does not expose');
})();

(function runtimeAndStudioContractRemainAligned() {
    const studio = fs.readFileSync(path.join(ROOT, 'tools', 'editor', 'js', 'scene-timing-studio.js'), 'utf8');
    const viewport = fs.readFileSync(path.join(ROOT, 'tools', 'editor', 'js', 'three-editor-viewport.js'), 'utf8');
    const runtime = fs.readFileSync(path.join(ROOT, 'runtime', 'engine', 'scene_update_contract.lua'), 'utf8');
    const host = fs.readFileSync(path.join(ROOT, 'runtime', 'engine', 'scene_host.lua'), 'utf8');
    const interpreter = fs.readFileSync(path.join(ROOT, 'runtime', 'engine', 'interpreter.lua'), 'utf8');

    assert.match(studio, /Scene Timing/);
    assert.match(studio, /Legacy \/ default/);
    assert.match(studio, /Fixed logical clock/);
    assert.match(studio, /seconds per logical on_frame tick/);
    assert.match(studio, /not Game Variables, not persistent Scene state, and are not saved/);
    assert.match(studio, /dataset\.sceneTimingError/,
        'invalid timing must have a visible inline error surface');
    assert.match(studio, /#ffcccc/,
        'invalid timing input must be visibly highlighted');
    assert.doesNotMatch(studio, /ctx\.time/,
        'Studio must not advertise SCRIPT timing access that the current sandbox does not expose');
    assert.match(viewport, /scene-timing-authoring\.js/);
    assert.match(viewport, /scene-timing-studio\.js/);
    assert.match(viewport, /return \[quaternion\.x, quaternion\.y, quaternion\.z, quaternion\.w\]/);

    assert.match(runtime, /update\.mode ~= "fixed"/);
    assert.match(runtime, /local DEFAULT_MAX_CATCH_UP = 8/);
    assert.match(runtime, /if maxCatchUp == nil then maxCatchUp = DEFAULT_MAX_CATCH_UP end/);
    assert.match(runtime, /local MAX_CATCH_UP_LIMIT = 120/);
    assert.match(runtime, /maxCatchUp > MAX_CATCH_UP_LIMIT/);
    assert.match(host, /state\.v\.time = timeView/);
    assert.match(host, /ctx\.time = timeView/);
    const scriptCtxBlock = interpreter.match(/local scriptCtx = \{([\s\S]*?)\n    \}/);
    assert.ok(scriptCtxBlock, 'SCRIPT sandbox context must remain inspectable');
    assert.doesNotMatch(scriptCtxBlock[1], /time\s*=/,
        'SCRIPT timing help must not be added until the existing sandbox actually exposes it');
})();

console.log('Scene fixed-timing Studio tests OK');
