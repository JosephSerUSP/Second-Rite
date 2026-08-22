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

function numberTag(record, name) {
    const value = record && record.tags && Number(record.tags[name]);
    return Number.isFinite(value) ? Math.max(0, Math.round(value)) : 0;
}

function percentile(values, fraction) {
    if (!values.length) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const index = Math.min(sorted.length - 1, Math.max(0, Math.floor((sorted.length - 1) * fraction)));
    return sorted[index];
}

function formatG6CaptureReport(records) {
    const frames = records.filter((entry) => entry && entry.tags && entry.tags.kind === 'g6-frame');
    const legs = records.filter((entry) => entry && entry.tags && entry.tags.kind === 'g6-leg');
    if (frames.length === 0 && legs.length === 0) return null;

    const groups = new Map();
    for (const entry of frames) {
        const leg = String(entry.tags.leg || entry.runId || 'g6');
        if (!groups.has(leg)) groups.set(leg, { frames: [], leg: null });
        groups.get(leg).frames.push(entry);
    }
    for (const entry of legs) {
        const leg = String(entry.tags.leg || entry.runId || 'g6');
        if (!groups.has(leg)) groups.set(leg, { frames: [], leg: null });
        groups.get(leg).leg = entry;
    }

    const sections = ['### G6 capture timing'];
    for (const [legName, group] of groups) {
        const ranked = [...group.frames].sort((a, b) => b.ms - a.ms);
        const readiness = ranked.reduce((sum, row) => sum + numberTag(row, 'readinessMs'), 0)
            + numberTag(group.leg, 'setupReadinessMs');
        const settling = ranked.reduce((sum, row) => sum + numberTag(row, 'settlingMs'), 0);
        const screenshots = ranked.reduce((sum, row) => sum + numberTag(row, 'screenshotMs'), 0);
        const frameWall = ranked.reduce((sum, row) => sum + Math.max(0, Math.round(Number(row.ms) || 0)), 0);
        const legWall = group.leg ? Math.max(0, Math.round(Number(group.leg.ms) || 0)) : frameWall;
        const other = Math.max(0, legWall - readiness - settling - screenshots);
        const stableWalls = ranked.map((row) => numberTag(row, 'stableScreenshotMs'));
        const stableMean = stableWalls.length
            ? Math.round(stableWalls.reduce((sum, ms) => sum + ms, 0) / stableWalls.length)
            : null;
        const stableMedian = percentile(stableWalls, 0.5);
        const stableMax = stableWalls.length ? Math.max(...stableWalls) : null;
        const targetSha = (group.leg && group.leg.tags && group.leg.tags.targetSha)
            || (ranked[0] && ranked[0].tags.targetSha)
            || null;

        sections.push('');
        sections.push(`#### ${legName}${targetSha ? ` (${String(targetSha).slice(0, 12)})` : ''}`);
        sections.push('');
        sections.push(`Leg wall **${timings.formatMs(legWall)}** = readiness **${timings.formatMs(readiness)}** + settling **${timings.formatMs(settling)}** + screenshot round trips **${timings.formatMs(screenshots)}** + other/setup **${timings.formatMs(other)}**.`);
        if (stableMean !== null) {
            sections.push(`stable_screenshot wall: mean **${timings.formatMs(stableMean)}**, median **${timings.formatMs(stableMedian)}**, max **${timings.formatMs(stableMax)}** across ${stableWalls.length} frames.`);
        }
        sections.push('');
        sections.push('| rank | frame | wall | readiness | settling | screenshots | shot mean / max | iterations | binding | other |');
        sections.push('| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |');
        ranked.forEach((row, index) => {
            const rounds = Array.isArray(row.tags.screenshotRoundTripsMs)
                ? row.tags.screenshotRoundTripsMs.map(Number).filter(Number.isFinite)
                : [];
            const mean = rounds.length ? Math.round(rounds.reduce((sum, ms) => sum + ms, 0) / rounds.length) : null;
            const max = rounds.length ? Math.max(...rounds) : null;
            const shot = rounds.length ? `${timings.formatMs(mean)} / ${timings.formatMs(max)}` : '-';
            sections.push(`| ${index + 1} | ${row.tags.frame || '?'} | ${timings.formatMs(row.ms)} | ${timings.formatMs(numberTag(row, 'readinessMs'))} | ${timings.formatMs(numberTag(row, 'settlingMs'))} | ${timings.formatMs(numberTag(row, 'screenshotMs'))} | ${shot} | ${row.tags.iterations ?? '?'} | ${row.tags.binding || '?'} | ${timings.formatMs(numberTag(row, 'otherMs'))} |`);
        });
    }
    return sections.join('\n');
}

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

    // G6 frame/leg records overlap by construction: summing them in the generic
    // table would double-count the leg. Keep them in their dedicated accounting
    // report and leave the #811 step table for non-overlapping command timings.
    const generic = records.filter((entry) => !(entry && entry.tags && (entry.tags.kind === 'g6-frame' || entry.tags.kind === 'g6-leg')));
    const sections = [];
    if (generic.length) {
        const table = timings.formatTable(timings.summarize(generic));
        sections.push(`### Verification latency (${generic.length} timed steps)\n\n${table}`);
    }
    const g6 = formatG6CaptureReport(records);
    if (g6) sections.push(g6);
    const output = sections.join('\n\n');
    process.stdout.write(`${output}\n`);

    const summaryPath = String(process.env.GITHUB_STEP_SUMMARY || '').trim();
    if (summaryPath) {
        try {
            fs.appendFileSync(summaryPath, `\n${output}\n`, 'utf8');
        } catch (err) {
            process.stderr.write(`timings: could not write the job summary: ${err.message}\n`);
        }
    }
}

if (require.main === module) main(process.argv.slice(2));

module.exports = { formatG6CaptureReport };
