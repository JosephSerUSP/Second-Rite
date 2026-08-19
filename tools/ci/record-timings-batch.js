#!/usr/bin/env node
'use strict';

// #815: G6 keeps per-frame observations in memory until the last capture has
// completed, then sends the whole batch here. This process never runs the
// measured command and therefore cannot perturb screenshot timing or pixels.
const timings = require('./timings');

function recordBatch(entries, defaultRunId = timings.runId()) {
    if (!Array.isArray(entries)) throw new Error('expected a JSON array of timing records');
    let written = 0;
    for (const entry of entries) {
        if (!entry || typeof entry !== 'object') continue;
        const label = String(entry.label || 'unlabelled');
        const id = entry.runId || defaultRunId;
        const phase = entry.phase === 'cold' || entry.phase === 'warm'
            ? entry.phase
            : timings.nextPhase(label, id);
        if (timings.record({ ...entry, label, runId: id, phase })) written += 1;
    }
    return written;
}

function main() {
    let input = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { input += chunk; });
    process.stdin.on('end', () => {
        try {
            const entries = JSON.parse(input || '[]');
            const written = recordBatch(entries);
            process.stdout.write(`timings: recorded ${written}/${entries.length} batched records\n`);
        } catch (err) {
            process.stderr.write(`timings: invalid batch: ${err.message}\n`);
            process.exitCode = 2;
        }
    });
}

if (require.main === module) main();

module.exports = { recordBatch };
