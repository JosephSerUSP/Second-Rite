#!/usr/bin/env node
'use strict';

// #811 step 1: wrap any gate or suite invocation so its wall time is recorded.
//
//   node tools/ci/time-step.js --label "G1 validate" -- lovec <root> validate
//
// The wrapper is transparent: the child's stdio is inherited and the wrapper
// exits with the child's exit code (or 128+signal when it was killed), so
// dropping it in front of an existing command changes nothing a caller can
// observe except that a timing lands in out/timings/. Set THESTRA_TIMINGS=0 to
// run the command with no recording at all.
const path = require('path');
const { spawn } = require('child_process');
const timings = require('./timings');

const USAGE = `usage: node tools/ci/time-step.js --label <name> [options] -- <command> [args...]

  --label <name>     step name the timing is recorded under (required)
  --phase cold|warm  override the derived phase (default: first run of this
                     label in the current run id is cold, later ones warm)
  --tag k=v          extra context recorded with the timing (repeatable)
  --help             show this message
`;

function parseArgs(argv) {
    const options = { tags: {}, command: [] };
    let i = 0;
    for (; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === '--') { i += 1; break; }
        else if (arg === '--label') options.label = argv[++i];
        else if (arg === '--phase') options.phase = argv[++i];
        else if (arg === '--tag') {
            const raw = String(argv[++i] || '');
            const eq = raw.indexOf('=');
            if (eq <= 0) throw new Error(`--tag expects k=v, got: ${raw}`);
            options.tags[raw.slice(0, eq)] = raw.slice(eq + 1);
        } else if (arg === '--help') return null;
        else throw new Error(`Unknown argument: ${arg}`);
    }
    options.command = argv.slice(i);
    return options;
}

function main(argv) {
    let options;
    try {
        options = parseArgs(argv);
    } catch (err) {
        process.stderr.write(`${err.message}\n\n${USAGE}`);
        process.exit(2);
        return;
    }
    if (!options) {
        process.stdout.write(USAGE);
        return;
    }
    if (!options.label) {
        process.stderr.write(`--label is required\n\n${USAGE}`);
        process.exit(2);
        return;
    }
    if (options.command.length === 0) {
        process.stderr.write(`no command given after --\n\n${USAGE}`);
        process.exit(2);
        return;
    }

    const [file, ...args] = options.command;
    // .cmd/.bat shims (npm.cmd) are not executable images on Windows; they need
    // the shell. Everything else is spawned directly so no quoting is involved.
    const needsShell = process.platform === 'win32' && /\.(cmd|bat)$/i.test(path.extname(file) || file);
    const phase = options.phase === 'cold' || options.phase === 'warm'
        ? options.phase
        : timings.nextPhase(options.label);
    const startedAt = new Date().toISOString();
    const started = process.hrtime.bigint();

    const child = spawn(file, args, { stdio: 'inherit', shell: needsShell });

    const finish = (exitCode, signal) => {
        const ms = Number(process.hrtime.bigint() - started) / 1e6;
        timings.record({
            label: options.label,
            phase,
            ms,
            exitCode: Number.isInteger(exitCode) ? exitCode : null,
            ok: exitCode === 0,
            command: options.command.join(' '),
            startedAt,
            tags: options.tags,
        });
        process.stdout.write(`timings: ${options.label} [${phase}] ${timings.formatMs(Math.round(ms))} (exit ${exitCode === null ? signal : exitCode})\n`);
        if (signal) process.exit(128 + (require('os').constants.signals[signal] || 0));
        process.exit(exitCode === null ? 1 : exitCode);
    };

    child.on('error', (err) => {
        process.stderr.write(`timings: failed to start "${file}": ${err.message}\n`);
        finish(127, null);
    });
    child.on('close', (code, signal) => finish(code, signal));
}

if (require.main === module) main(process.argv.slice(2));

module.exports = { parseArgs };
