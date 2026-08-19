#!/usr/bin/env node
'use strict';

// #811 step 1: render what tools/ci/time-step.js recorded.
//
// This is a report, never a gate. It has no failing exit path for slow steps --
// #811 defers budget enforcement until hosted-runner variance is known, and a
// reporter that can fail is a budget enforcer whether or not it is called one.
// It exits non-zero only for a bad invocation.
const fs = require('fs');
const timings = require('./timings');

const USAGE = `usage: node tools/ci/report-timings.js [options]

  --run <id>   report one run id (default: every run in the timings dir)
  --json       emit the raw records as JSON instead of a table
  --help       show this message

Reads out/timings/ (override with THESTRA_TIMINGS_DIR). When GITHUB_STEP_SUMMARY
is set the table is appended there as well.
`;

function main(argv) {
    const options = {};
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === '--run') options.run = argv[++i];
        else if (arg === '--json') options.json = true;
        else if (arg === '--help') { process.stdout.write(USAGE); return; }
        else { process.stderr.write(`Unknown argument: ${arg}\n\n${USAGE}`); process.exit(2); return; }
    }

    const records = options.run ? timings.loadRun(options.run) : timings.loadAll();
    if (options.json) {
        process.stdout.write(`${JSON.stringify(records, null, 2)}\n`);
        return;
    }
    if (records.length === 0) {
        process.stdout.write(`No timings recorded in ${timings.timingsDir()}.\nWrap a step with tools/ci/time-step.js to record one.\n`);
        return;
    }

    const table = timings.formatTable(timings.summarize(records));
    const heading = `### Verification latency (${records.length} timed steps)`;
    process.stdout.write(`${heading}\n\n${table}\n`);

    const summaryPath = String(process.env.GITHUB_STEP_SUMMARY || '').trim();
    if (summaryPath) {
        try {
            fs.appendFileSync(summaryPath, `\n${heading}\n\n${table}\n`, 'utf8');
        } catch (err) {
            process.stderr.write(`timings: could not write the job summary: ${err.message}\n`);
        }
    }
}

if (require.main === module) main(process.argv.slice(2));
