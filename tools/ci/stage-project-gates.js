#!/usr/bin/env node
'use strict';

// #700: repository verification still owns tests/goldens, while the runnable
// game is now an ordinary Project. Build exactly one canonical runtime stage
// through the exporter, then add repository-only test fixtures for `unittest`.
// No production data/assets are copied by this helper outside stageRuntimeGame.
const fs = require('fs');
const os = require('os');
const path = require('path');
const semanticRoots = require('../semantic-roots');
const exporter = require('../export/export-game');

function parseArgs(argv) {
    const options = {};
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === '--output') options.outputDir = path.resolve(argv[++i] || '');
        else if (arg === '--project') options.projectDir = path.resolve(argv[++i] || '');
        else if (arg === '--help') return null;
        else throw new Error(`Unknown argument: ${arg}`);
    }
    return options;
}

function stageProjectGates(options = {}) {
    const roots = semanticRoots.resolveSemanticRoots({
        projectRoot: options.projectDir || semanticRoots.DEFAULT_PROJECT_ROOT,
    });
    const outputDir = path.resolve(options.outputDir || path.join(os.tmpdir(), 'thestra-project-gates'));
    const staged = exporter.stageRuntimeGame({
        installRoot: roots.installRoot,
        runtimeDir: roots.runtimeRoot,
        rtpRoot: roots.rtpRoot,
        projectDir: roots.projectRoot,
        outputDir,
    });

    // `unittest` is a repository verification command, not a player capability.
    // Keep tests out of the runtime manifest/exported game while making the
    // temporary verification stage able to run the same registered Lua suite.
    const sourceTests = path.join(roots.installRoot, 'tests');
    const stageTests = path.join(staged.stageDir, 'tests');
    fs.cpSync(sourceTests, stageTests, { recursive: true, force: true });

    return {
        stageDir: staged.stageDir,
        projectDir: roots.projectRoot,
        runtimeDir: roots.runtimeRoot,
        rtpRoot: roots.rtpRoot,
    };
}

function main() {
    const options = parseArgs(process.argv.slice(2));
    if (!options) {
        console.log('Usage: node tools/ci/stage-project-gates.js [--project dir] [--output dir]');
        return;
    }
    const result = stageProjectGates(options);
    process.stdout.write(`PROJECT GATE STAGE OK ${JSON.stringify(result)}\n`);
}

if (require.main === module) {
    try { main(); }
    catch (error) {
        console.error(error && error.stack ? error.stack : error);
        process.exitCode = 1;
    }
}

module.exports = { parseArgs, stageProjectGates };
