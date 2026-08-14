#!/usr/bin/env node
'use strict';

// Agent-facing location wrapper for the existing staged Project generator.
// Generation semantics stay in gen.js; this command only chooses an explicit
// Project destination so reviewable games can live under projects/labs/ (or
// anywhere else) without changing Second Gate.

const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');
const fixtures = require('./fixture-project');

const VALUE_OPTIONS = new Set(['--stage', '--provider', '--model']);

function usage() {
    return [
        'Usage:',
        '  node tools/campaign-gen/generate-project.js --project <target> [gen options] "<pitch>"',
        '',
        'Example:',
        '  node tools/campaign-gen/generate-project.js --project projects/labs/mist-isle "A drowned-bell island RPG"',
        '',
        'The target must not already exist. Generation edits only that Project root.',
        'The current compatibility bootstrap is an explicit fork of the source Project;',
        'it becomes sparse/neutral when #390 provides the neutral authored baseline.',
    ].join('\n');
}

function normalizeGeneratorArgs(args) {
    const options = [];
    const pitch = [];
    for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        if (VALUE_OPTIONS.has(arg)) {
            if (i + 1 >= args.length) throw new Error(`${arg} requires a value`);
            options.push(arg, args[++i]);
            continue;
        }
        if (arg.startsWith('--stage=') || arg.startsWith('--provider=') || arg.startsWith('--model=')) {
            options.push(arg);
            continue;
        }
        if (arg === '--resume' || arg === '--dry-run') {
            options.push(arg);
            continue;
        }
        if (arg.startsWith('--')) {
            // Preserve unknown flags so gen.js remains the authority that
            // accepts/rejects generation options instead of this wrapper
            // silently creating a second option registry.
            options.push(arg);
            continue;
        }
        pitch.push(arg);
    }
    if (pitch.length) options.push(pitch.join(' '));
    return options;
}

function parse(argv) {
    const args = argv.slice();
    let project = null;
    const forwarded = [];
    for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        if (arg === '--project') {
            if (i + 1 >= args.length) throw new Error('--project requires a path');
            project = args[++i];
            continue;
        }
        if (arg.startsWith('--project=')) {
            project = arg.slice('--project='.length);
            if (!project) throw new Error('--project requires a path');
            continue;
        }
        if (arg === '--name' || arg.startsWith('--name=')) {
            throw new Error('Do not pass --name with --project; the Project folder name is the generator name');
        }
        if (arg === '--clean') {
            throw new Error('Explicit Project targets are never auto-deleted; remove the target deliberately instead of using --clean');
        }
        forwarded.push(arg);
    }
    if (!project) throw new Error('--project is required');
    return { project: path.resolve(project), forwarded: normalizeGeneratorArgs(forwarded) };
}

function run(argv = process.argv.slice(2), options = {}) {
    const parsed = parse(argv);
    if (fs.existsSync(parsed.project)) {
        throw new Error(`Project target already exists; refusing to overwrite it: ${parsed.project}`);
    }
    const parent = path.dirname(parsed.project);
    fs.mkdirSync(parent, { recursive: true });
    const name = path.basename(parsed.project);
    fixtures.assertSafeName(name);

    const gen = path.join(__dirname, 'gen.js');
    const env = Object.assign({}, process.env, options.env || {});
    env[fixtures.PROJECTS_ROOT_ENV] = parent;
    const childArgs = [gen, '--name', name, ...parsed.forwarded];
    const result = childProcess.spawnSync(process.execPath, childArgs, {
        cwd: options.cwd || path.resolve(__dirname, '..', '..'),
        env,
        stdio: options.stdio || 'inherit',
        encoding: options.stdio ? 'utf8' : undefined,
    });
    if (result.error) throw result.error;
    if (result.status !== 0) return result.status === null ? 1 : result.status;
    process.stdout.write(`\nGenerated Thestra Project: ${parsed.project}\n`);
    process.stdout.write(`Open in Studio: npm start -- --project ${JSON.stringify(parsed.project)}\n`);
    return 0;
}

if (require.main === module) {
    try {
        process.exitCode = run();
    } catch (error) {
        process.stderr.write(`Project generation failed: ${error.message}\n\n${usage()}\n`);
        process.exitCode = 1;
    }
}

module.exports = { normalizeGeneratorArgs, parse, run, usage };
