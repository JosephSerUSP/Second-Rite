'use strict';

// #968 negative control for the adapter parity gate.
//
// A gate that has never been observed to fail is a claim, not evidence. This
// runs the parity comparison once per deliberate breakage and requires every
// one of them to redden it. Each mutation is a mistake an adapter author could
// plausibly make, and each one is small enough that a lax gate would wave it
// through -- which is exactly the failure this control exists to rule out.
//
// It also asserts the honest inverse: with no mutation, the gate is green. A
// control that only ever proves "fails when broken" cannot distinguish a
// working gate from one that fails on everything.
//
//   node tools/presentation/parity/negative-control.js

const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { MUTATIONS } = require('./run-parity');
const RUNNER = path.join(__dirname, 'run-parity.js');

function run(mutation) {
    const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'sg-parity-nc-'));
    try {
        const args = [RUNNER, '--out', outDir];
        if (mutation) args.push('--mutate', mutation);
        const result = spawnSync(process.execPath, args, { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
        return { status: result.status, output: `${result.stdout || ''}${result.stderr || ''}` };
    } finally {
        fs.rmSync(outDir, { recursive: true, force: true });
    }
}

function main() {
    const failures = [];

    process.stdout.write('baseline (no mutation): ');
    const baseline = run(null);
    if (baseline.status === 0 && /PRESENTATION ADAPTER PARITY OK/.test(baseline.output)) {
        console.log('green, as required');
    } else {
        console.log('NOT GREEN');
        console.log(baseline.output);
        failures.push('baseline must pass before any mutation result means anything');
    }

    for (const mutation of Object.keys(MUTATIONS)) {
        process.stdout.write(`mutation ${mutation}: `);
        const result = run(mutation);
        if (result.status !== 0 && !/PRESENTATION ADAPTER PARITY OK/.test(result.output)) {
            const line = (result.output.match(/differences the gate does not tolerate: (\d+)/) || [])[1];
            console.log(`caught (untolerated differences: ${line === undefined ? 'n/a' : line})`);
        } else {
            console.log('NOT CAUGHT');
            failures.push(`the parity gate did not catch '${mutation}'`);
        }
    }

    if (failures.length) {
        console.error('\nPRESENTATION ADAPTER NEGATIVE CONTROL FAILED:');
        for (const failure of failures) console.error(`  ${failure}`);
        process.exitCode = 1;
        return;
    }
    console.log('\nPRESENTATION ADAPTER NEGATIVE CONTROL OK');
}

main();
