#!/usr/bin/env node
'use strict';

// #699 pre-move acid test. Copy only the current Second Gate Project-owned
// material outside the checkout, then exercise it through installed Thestra.
// After #700 changes the default Project root, this test should keep the same
// contract and merely copy that new Project location.
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const semanticRoots = require('../semantic-roots');
const exporter = require('../export/export-game');
const projectIdentity = require('../export/project-identity');
const lifecycle = require('./project-lifecycle');
const projectPlay = require('./project-play');

const ROOTS = semanticRoots.resolveSemanticRoots();

function copyProjectOwned(source, target) {
    fs.mkdirSync(target, { recursive: true });
    for (const owned of lifecycle.PROJECT_DIRS) {
        const from = path.join(source, owned);
        if (!fs.existsSync(from)) continue;
        fs.cpSync(from, path.join(target, owned), { recursive: true, force: true });
    }
}

function runCommand(executable, args, options = {}) {
    const result = childProcess.spawnSync(executable, args, {
        cwd: options.cwd || ROOTS.installRoot,
        env: Object.assign({}, process.env, options.env || {}),
        encoding: 'utf8',
        maxBuffer: 32 * 1024 * 1024,
        timeout: options.timeout || 180000,
        windowsHide: true,
    });
    const output = `${result.stdout || ''}${result.stderr || ''}`;
    if (result.error) throw result.error;
    if (result.status !== 0) {
        throw new Error(`${path.basename(executable)} ${args.join(' ')} failed (${result.status}):\n${output}`);
    }
    return output;
}

function validateStage(lovec, stageDir) {
    const output = runCommand(lovec, ['.', 'validate'], {
        cwd: stageDir,
        env: { SDL_AUDIODRIVER: 'dummy' },
    });
    if (!output.includes('VALIDATE OK')) {
        throw new Error(`copied Second Gate validation did not report VALIDATE OK:\n${output}`);
    }
}

function assertMaterializedIdentity(stageDir, expected) {
    const conf = fs.readFileSync(path.join(stageDir, 'conf.lua'), 'utf8');
    if (conf.includes('__THESTRA_PROJECT_')) throw new Error('staged conf.lua retained an identity template token');
    if (!conf.includes(`t.identity = ${JSON.stringify(expected.identity)}`)) {
        throw new Error(`staged conf.lua lost Project LÖVE identity ${expected.identity}`);
    }
    if (!conf.includes(`t.window.title = ${JSON.stringify(expected.windowTitle)}`)) {
        throw new Error(`staged conf.lua lost Project window title ${expected.windowTitle}`);
    }
}

function run(options = {}) {
    const sourceProject = path.resolve(options.sourceProject || process.env.THESTRA_PORTABILITY_PROJECT || ROOTS.projectRoot);
    const lovec = options.lovec || process.env.LOVEC || process.env.LOVEC_PATH || 'lovec';
    const work = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-second-gate-portability-'));
    let testPlayStage = null;
    try {
        const copiedProject = path.join(work, 'external-second-gate-copy');
        copyProjectOwned(sourceProject, copiedProject);

        for (const forbidden of ['engine', 'presentation', 'tools', 'main.lua', 'conf.lua']) {
            if (fs.existsSync(path.join(copiedProject, forbidden))) {
                throw new Error(`portability fixture copied checkout/runtime material: ${forbidden}`);
            }
        }

        const info = lifecycle.projectInfo(copiedProject, { installRoot: ROOTS.installRoot });
        if (info.sameAsInstall) throw new Error('external Second Gate copy collapsed back into install root');
        if (path.resolve(info.projectRoot) !== path.resolve(copiedProject)) {
            throw new Error('Project discovery did not preserve the copied external root');
        }

        const originalIdentity = projectIdentity.readProjectIdentity(copiedProject);
        testPlayStage = projectPlay.stageProject({
            installRoot: ROOTS.runtimeRoot,
            projectRoot: copiedProject,
        });
        if (!fs.existsSync(path.join(testPlayStage, 'engine', 'data', 'loader.lua'))) {
            throw new Error('external Test Play stage did not receive installed Thestra runtime');
        }
        if (!fs.existsSync(path.join(testPlayStage, 'data', 'runtime_data_manifest.json'))) {
            throw new Error('external Test Play stage did not compile copied Project semantic data');
        }
        assertMaterializedIdentity(testPlayStage, originalIdentity);
        validateStage(lovec, testPlayStage);

        // Exercise the ordinary exporter CLI against the external copy. No
        // checkout-relative Project argument is allowed after this point.
        const firstOut = path.join(work, 'export-original');
        runCommand(process.execPath, [
            path.join(ROOTS.installRoot, 'tools', 'export', 'export-game.js'),
            '--project', copiedProject,
            '--output', firstOut,
            '--skip-preflight',
        ], { env: { LOVEC_PATH: lovec } });
        const firstLove = path.join(firstOut, `${originalIdentity.productName}.love`);
        if (!fs.existsSync(firstLove) || fs.statSync(firstLove).size === 0) {
            throw new Error(`normal export did not produce Project-named .love artifact: ${firstLove}`);
        }
        assertMaterializedIdentity(path.join(firstOut, 'stage'), originalIdentity);

        // Strong negative control for installed identity leakage: modify only
        // the copied Project's identity and export again. Installed Thestra and
        // the source checkout remain untouched, so any old Second Rite title in
        // conf/artifact naming would prove topology still leaks into semantics.
        const rewritten = {
            schemaVersion: 1,
            name: 'Portability Mirror',
            identity: 'PortabilityMirror',
            productName: 'Portability Mirror',
            executableName: 'Portability Mirror',
            buildSlug: 'portability-mirror',
            windowTitle: 'Portability Mirror',
            productVersion: '9.9.9-portability',
        };
        fs.writeFileSync(
            path.join(copiedProject, projectIdentity.PROJECT_IDENTITY_RELATIVE),
            JSON.stringify(rewritten, null, 2) + '\n',
            'utf8',
        );
        const rewrittenIdentity = projectIdentity.readProjectIdentity(copiedProject);
        const secondOut = path.join(work, 'export-rewritten');
        runCommand(process.execPath, [
            path.join(ROOTS.installRoot, 'tools', 'export', 'export-game.js'),
            '--project', copiedProject,
            '--output', secondOut,
            '--skip-preflight',
        ], { env: { LOVEC_PATH: lovec } });
        const secondLove = path.join(secondOut, 'Portability Mirror.love');
        if (!fs.existsSync(secondLove) || fs.statSync(secondLove).size === 0) {
            throw new Error('rewritten external Project did not control exported artifact naming');
        }
        if (fs.existsSync(path.join(secondOut, 'Second Rite.love'))) {
            throw new Error('installed Second Gate build identity leaked into unrelated external export');
        }
        assertMaterializedIdentity(path.join(secondOut, 'stage'), rewrittenIdentity);
        const rewrittenConf = fs.readFileSync(path.join(secondOut, 'stage', 'conf.lua'), 'utf8');
        if (rewrittenConf.includes('SecondRite') || rewrittenConf.includes('Second Rite')) {
            throw new Error('installed Second Gate release identity leaked into rewritten external Project conf.lua');
        }

        process.stdout.write(`SECOND GATE PORTABILITY OK ${JSON.stringify({
            sourceProject,
            copiedProject: path.basename(copiedProject),
            testPlayExternal: true,
            validation: 'VALIDATE OK',
            originalProduct: originalIdentity.productName,
            rewrittenProduct: rewrittenIdentity.productName,
            hermeticLove: path.basename(secondLove),
        })}\n`);
        return 0;
    } finally {
        if (testPlayStage) projectPlay.removeStage(testPlayStage);
        fs.rmSync(work, { recursive: true, force: true });
    }
}

if (require.main === module) {
    try { process.exitCode = run(); }
    catch (error) {
        console.error(error && error.stack ? error.stack : error);
        process.exitCode = 1;
    }
}

module.exports = { assertMaterializedIdentity, copyProjectOwned, run };
