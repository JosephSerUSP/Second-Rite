#!/usr/bin/env node
'use strict';

// #811 step 1: record the wall time of a gate or suite.
//
// Two modes, and the difference matters:
//
//   --record  the caller already ran the command and hands over the numbers:
//               node tools/ci/time-step.js --record --label "G2 battle" \
//                 --ms 41230 --exit 0
//             This is the mode CI uses. Re-spawning is NOT free of
//             consequences: wrapping tools/golden/check.ps1 in a node spawn
//             made New-TemporaryFile unresolvable on the hosted runner and
//             turned G2 red -- the one thing an instrument must never do.
//             Recording after the fact leaves the measured command
//             byte-identical to what it was before instrumentation.
//
//   wrapper   run the command and time it:
//               node tools/ci/time-step.js --label "unit" -- npm test
//             Convenient for local and agent use. The wrapper is transparent
//             (stdio inherited, child's exit code propagated), but it is still
//             a new process boundary, so prefer --record for anything whose
//             environment is load-bearing -- PowerShell scripts especially.
//
// Set THESTRA_TIMINGS=0 to run with no recording at all.
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
const timings = require('./timings');

const USAGE = `usage:
  node tools/ci/time-step.js --label <name> [options] -- <command> [args...]
  node tools/ci/time-step.js --record --label <name> --ms <n> [--exit <n>]

  --label <name>     step name the timing is recorded under (required)
  --record           record a timing for a command the caller already ran
  --ms <n>           elapsed milliseconds (required with --record)
  --exit <n>         exit code of the command (with --record; default 0)
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
        else if (arg === '--record') options.record = true;
        else if (arg === '--ms') options.ms = Number(argv[++i]);
        else if (arg === '--exit') options.exitCode = Number(argv[++i]);
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

function fail(message) {
    process.stderr.write(`${message}\n\n${USAGE}`);
    process.exit(2);
}

function main(argv) {
    let options;
    try {
        options = parseArgs(argv);
    } catch (err) {
        return fail(err.message);
    }
    if (!options) {
        process.stdout.write(USAGE);
        return undefined;
    }
    if (!options.label) return fail('--label is required');

    const phase = options.phase === 'cold' || options.phase === 'warm'
        ? options.phase
        : timings.nextPhase(options.label);

    if (options.record) {
        if (!Number.isFinite(options.ms)) return fail('--record requires --ms <milliseconds>');
        const exitCode = Number.isFinite(options.exitCode) ? options.exitCode : 0;
        timings.record({
            label: options.label,
            phase,
            ms: options.ms,
            exitCode,
            ok: exitCode === 0,
            command: options.command.length ? options.command.join(' ') : null,
            tags: options.tags,
        });
        process.stdout.write(`timings: ${options.label} [${phase}] ${timings.formatMs(Math.round(options.ms))} (exit ${exitCode})\n`);
        return undefined;
    }

    if (options.command.length === 0) return fail('no command given after --');

    const [file, ...args] = options.command;
    // .cmd/.bat shims (npm.cmd) are not executable images on Windows; they need
    // the shell. Everything else is spawned directly so no quoting is involved.
    const needsShell = process.platform === 'win32' && /\.(cmd|bat)$/i.test(path.extname(file) || file);
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
        if (signal) process.exit(128 + (os.constants.signals[signal] || 0));
        process.exit(exitCode === null ? 1 : exitCode);
    };

    child.on('error', (err) => {
        process.stderr.write(`timings: failed to start "${file}": ${err.message}\n`);
        finish(127, null);
    });
    child.on('close', (code, signal) => finish(code, signal));
    return undefined;
}

if (require.main === module) main(process.argv.slice(2));

module.exports = { parseArgs };
