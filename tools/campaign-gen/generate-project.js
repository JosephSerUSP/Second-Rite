#!/usr/bin/env node
'use strict';

// Agent-facing location wrapper for the staged goal -> Project generator.
// Generation semantics stay in gen.js; this command only chooses an explicit
// ordinary Project destination so reviewable games can live under projects/labs/
// (or anywhere else) without changing Second Gate.

const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');
const fixtures = require('./fixture-project');

const VALUE_OPTIONS = new Set(['--stage', '--provider', '--model', '--responses']);

function usage() {
    return [
        'Usage:',
        '  node tools/campaign-gen/generate-project.js --project <target> [gen options] "<goal>"',
        '',
        'Example:',
        '  node tools/campaign-gen/generate-project.js --project projects/labs/mist-isle "A drowned-bell island adventure"',
        '',
        'The target must not already exist. Generation edits only that Project root.',
        'The target starts from the neutral sparse RTP-backed New Project lifecycle;',
        'the generator authors that Project\'s own game grammar instead of forking Second Gate.',
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
        if (arg.startsWith('--stage=') || arg.startsWith('--provider=') || arg.startsWith('--model=') || arg.startsWith('--responses=')) {
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
            throw new Error('Do not pass --name with --project; the wrapper owns the generator run id');
        }
        if (arg === '--clean') {
            throw new Error('Explicit Project targets are never auto-deleted; remove the target deliberately instead of using --clean');
        }
        forwarded.push(arg);
    }
    if (!project) throw new Error('--project is required');
    return { project: path.resolve(project), forwarded: normalizeGeneratorArgs(forwarded) };
}

function generatorRunName(projectPath) {
    // The historical gen.js CLI accepts snake_case run ids. Project folder
    // names have a broader slug contract (hyphens are normal), so keep these
    // implementation/run identities separate from Project identity.
    const base = path.basename(projectPath);
    fixtures.assertSafeName(base);
    const normalized = base.replace(/-/g, '_');
    if (!/^[a-z0-9_]+$/.test(normalized)) {
        throw new Error(`Project folder cannot be represented as a generator run id: ${base}`);
    }
    return normalized;
}

function run(argv = process.argv.slice(2), options = {}) {
    const parsed = parse(argv);
    if (fs.existsSync(parsed.project)) {
        throw new Error(`Project target already exists; refusing to overwrite it: ${parsed.project}`);
    }
    const parent = path.dirname(parsed.project);
    fs.mkdirSync(parent, { recursive: true });
    const runName = generatorRunName(parsed.project);

    const gen = path.join(__dirname, 'gen.js');
    const env = Object.assign({}, process.env, options.env || {});
    env[fixtures.PROJECTS_ROOT_ENV] = parent;
    env[fixtures.PROJECT_TARGET_ENV] = parsed.project;
    const childArgs = [gen, '--name', runName, ...parsed.forwarded];
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

module.exports = { generatorRunName, normalizeGeneratorArgs, parse, run, usage };
