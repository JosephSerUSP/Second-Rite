#!/usr/bin/env node
'use strict';

// Agent/human shell surface for the same Project lifecycle used by Studio.
// Keep output compact and deterministic so goal-mode agents can establish an
// isolated root before doing any content work.

const fs = require('fs');
const path = require('path');
const lifecycle = require('./project-lifecycle');
const projectPlay = require('./project-play');

function usage() {
    return [
        'Usage:',
        '  node tools/editor/project-cli.js info <project> [--json]',
        '  node tools/editor/project-cli.js authored <project> <resource> [--json]',
        '  node tools/editor/project-cli.js make-local <project> <resource> [--json]',
        '  node tools/editor/project-cli.js play <project>',
        '  node tools/editor/project-cli.js fork <source-project> <target-project> [--json]',
        '  node tools/editor/project-cli.js create <target-project> [--json]',
        '',
        'Notes:',
        '  create      materializes a sparse Project pinned to the installed Thestra house baseline.',
        '  authored    reports which provider currently supplies one inherited authored resource.',
        '  make-local  copies that resolved authored resource into the Project so it can diverge explicitly.',
        '  play        stages an external Project through the ordinary Test Play boundary and launches LÖVE.',
        '  fork        explicitly copies only Project-owned data/ and assets/ from a named source Project.',
        '  edit/open a Project in Studio with: npm start -- --project <project>',
        '  set LOVE_PATH when LÖVE is not installed at the platform default.',
    ].join('\n');
}

function parse(argv) {
    const args = argv.slice();
    const jsonAt = args.indexOf('--json');
    const json = jsonAt !== -1;
    if (json) args.splice(jsonAt, 1);
    return { command: args.shift(), args, json };
}

function output(value, json) {
    if (json) {
        process.stdout.write(JSON.stringify(value) + '\n');
        return;
    }
    for (const [key, item] of Object.entries(value)) {
        if (item !== null && item !== undefined) process.stdout.write(`${key}: ${item}\n`);
    }
}

function resolveLoveExecutable(env = process.env, platform = process.platform) {
    if (env.LOVE_PATH) return env.LOVE_PATH;
    return platform === 'win32' ? 'C:\\Program Files\\LOVE\\love.exe' : 'love';
}

function playProject(projectPath, options = {}) {
    const info = lifecycle.projectInfo(path.resolve(projectPath));
    const executable = options.executable || resolveLoveExecutable(options.env, options.platform);
    if (path.isAbsolute(executable) && !fs.existsSync(executable)) {
        throw new Error(`LOVE not found at ${executable} (set LOVE_PATH)`);
    }

    const callback = options.callback || ((error, _stdout, stderr) => {
        if (!error) return;
        const detail = String(stderr || '').trim();
        process.stderr.write(`Project Test Play failed: ${error.message}${detail ? `\n${detail}` : ''}\n`);
        process.exitCode = 1;
    });

    return projectPlay.execStaged({
        executable,
        installRoot: info.installRoot,
        projectRoot: info.projectRoot,
        args: options.args || [],
        windowsHide: false,
    }, callback);
}

function run(argv = process.argv.slice(2), dependencies = {}) {
    const parsed = parse(argv);
    const command = parsed.command;
    if (!command || command === '-h' || command === '--help' || command === 'help') {
        process.stdout.write(usage() + '\n');
        return 0;
    }

    if (command === 'info') {
        if (parsed.args.length !== 1) throw new Error('info requires exactly one Project path');
        output(lifecycle.projectInfo(path.resolve(parsed.args[0])), parsed.json);
        return 0;
    }

    if (command === 'authored') {
        if (parsed.args.length !== 2) throw new Error('authored requires <project> <resource>');
        output(lifecycle.authoredDefaultInfo({
            project: path.resolve(parsed.args[0]),
            resource: parsed.args[1],
        }), parsed.json);
        return 0;
    }

    if (command === 'make-local') {
        if (parsed.args.length !== 2) throw new Error('make-local requires <project> <resource>');
        output(lifecycle.makeAuthoredDefaultLocal({
            project: path.resolve(parsed.args[0]),
            resource: parsed.args[1],
        }), parsed.json);
        return 0;
    }

    if (command === 'play') {
        if (parsed.json) throw new Error('play does not support --json');
        if (parsed.args.length !== 1) throw new Error('play requires exactly one Project path');
        const player = dependencies.playProject || playProject;
        player(path.resolve(parsed.args[0]));
        return 0;
    }

    if (command === 'fork') {
        if (parsed.args.length !== 2) throw new Error('fork requires <source-project> <target-project>');
        output(lifecycle.forkProject({
            source: path.resolve(parsed.args[0]),
            target: path.resolve(parsed.args[1]),
        }), parsed.json);
        return 0;
    }

    if (command === 'create') {
        if (parsed.args.length !== 1) throw new Error('create requires <target-project>');
        output(lifecycle.createProject({
            mode: 'sparse',
            target: path.resolve(parsed.args[0]),
        }), parsed.json);
        return 0;
    }

    throw new Error(`Unknown Project command '${command}'\n${usage()}`);
}

if (require.main === module) {
    try {
        process.exitCode = run();
    } catch (error) {
        const payload = { success: false, code: error.code || 'PROJECT_COMMAND_FAILED', message: error.message };
        if (process.argv.includes('--json')) process.stderr.write(JSON.stringify(payload) + '\n');
        else process.stderr.write(`Project command failed: ${error.message}\n`);
        process.exitCode = 1;
    }
}

module.exports = { output, parse, playProject, resolveLoveExecutable, run, usage };