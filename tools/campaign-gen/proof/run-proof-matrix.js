#!/usr/bin/env node
'use strict';

// Offline, repeatable acceptance matrix for #486. Recorded responses make the
// Project pipeline deterministic while every generated result still crosses the
// real sparse lifecycle, staged validator, boot proof, and exporter boundary.
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const repo = path.resolve(__dirname, '..', '..', '..');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-486-proof-'));
const generate = path.join(repo, 'tools', 'campaign-gen', 'generate-project.js');
const assertGrammar = path.join(repo, 'tools', 'campaign-gen', 'proof', 'assert-generated-projects.js');
const exporter = path.join(repo, 'tools', 'export', 'export-game.js');
const cases = [
    ['botanists', 'make a tiny dungeon RPG about three botanists exploring a greenhouse'],
    ['occult', 'make a tiny occult detective adventure with a different role skill and state vocabulary'],
    ['relay', 'make a deliberately small Scene and Event routing adventure with no combat'],
];
// The production generator defaults to a four-second smoke. The offline
// matrix's three independent stages need only one second each because it runs
// on the same local process and its purpose is boundary regression coverage.
process.env.THESTRA_GENERATOR_BOOT_MS = '1000';

function run(args) {
    const result = childProcess.spawnSync(process.execPath, args, {
        cwd: repo, encoding: 'utf8', windowsHide: true,
    });
    process.stdout.write(result.stdout || '');
    process.stderr.write(result.stderr || '');
    if (result.status !== 0) throw new Error(`proof command failed (${result.status}): node ${args.join(' ')}`);
}

try {
    const generated = [];
    for (const [name, goal] of cases) {
        const project = path.join(root, name);
        generated.push(project);
        run([generate, '--project', project, '--responses', path.join(repo, 'tools', 'campaign-gen', 'proof', name), goal]);
    }
    run([assertGrammar, ...generated]);
    for (const project of generated) {
        const output = path.join(project, 'export-proof');
        run([exporter, '--project', project, '--output', output, '--target', 'love']);
        if (!fs.existsSync(path.join(output, 'Second Rite.love'))) {
            throw new Error(`missing hermetic .love export for ${path.basename(project)}`);
        }
    }
    console.log('ISSUE 486 SPARSE PROJECT PROOF MATRIX OK');
} finally {
    fs.rmSync(root, { recursive: true, force: true });
}
