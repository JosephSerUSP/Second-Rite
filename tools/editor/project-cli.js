#!/usr/bin/env node
'use strict';

// Agent/human shell surface for the same Project lifecycle used by Studio.
// Keep output compact and deterministic so goal-mode agents can establish an
// isolated root before doing any content work.

const path = require('path');
const lifecycle = require('./project-lifecycle');

function usage() {
    return [
        'Usage:',
        '  node tools/editor/project-cli.js info <project> [--json]',
        '  node tools/editor/project-cli.js fork <source-project> <target-project> [--json]',
        '  node tools/editor/project-cli.js create <target-project> [--json]',
        '',
        'Notes:',
        '  create materializes a neutral sparse Project pinned to the installed RTP baseline.',
        '  fork   explicitly copies only Project-owned data/ and assets/ from a named source Project.',
        '  launch/open a Project with: npm start -- --project <project>',
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

function run(argv = process.argv.slice(2)) {
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

module.exports = { output, parse, run, usage };
