#!/usr/bin/env node
'use strict';

// #811 step 1: verification latency is a first-class property, so every gate
// and suite records its own wall time. This module is the shared store.
//
// Two rules govern everything here, and both are deliberate:
//
//   1. Recording NEVER fails a build. A timing store that can turn a green
//      gate red has made verification slower and more fragile, which is the
//      opposite of the point. Every write path swallows its own errors.
//   2. Nothing in here enforces a budget. #811 explicitly defers enforcement
//      until the natural variance on a hosted runner is known; today this
//      records and reports drift, nothing more.
//
// Cold vs warm is not a property of a command, it is a property of an
// occurrence: the first run of a label in a given run id paid the cold cost
// (staging, process start, caches empty), later ones did not. `nextPhase`
// derives that from what is already on disk so callers do not have to track it.
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const DEFAULT_DIR = path.join(REPO_ROOT, 'out', 'timings');

function isDisabled() {
    return String(process.env.THESTRA_TIMINGS || '').trim() === '0';
}

function timingsDir() {
    const override = String(process.env.THESTRA_TIMINGS_DIR || '').trim();
    return override ? path.resolve(override) : DEFAULT_DIR;
}

// One file per run keeps concurrent shards from interleaving writes into the
// same file, and keeps "first occurrence of this label" scoped to one run.
function runId() {
    const override = String(process.env.THESTRA_TIMINGS_RUN_ID || '').trim();
    if (override) return override;
    const github = String(process.env.GITHUB_RUN_ID || '').trim();
    const attempt = String(process.env.GITHUB_RUN_ATTEMPT || '').trim();
    if (github) return attempt ? `gh-${github}-${attempt}` : `gh-${github}`;
    return `local-${new Date().toISOString().replace(/[:.]/g, '-')}-${process.pid}`;
}

function timingsFile(id = runId()) {
    return path.join(timingsDir(), `${String(id).replace(/[^A-Za-z0-9._-]/g, '_')}.jsonl`);
}

function readRecords(file) {
    let text;
    try {
        text = fs.readFileSync(file, 'utf8');
    } catch (err) {
        return [];
    }
    const records = [];
    for (const line of text.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
            const record = JSON.parse(trimmed);
            if (record && typeof record === 'object') records.push(record);
        } catch (err) {
            // A truncated final line (interrupted run) must not poison a report.
        }
    }
    return records;
}

function loadRun(id = runId()) {
    return readRecords(timingsFile(id));
}

function loadAll(dir = timingsDir()) {
    let names;
    try {
        names = fs.readdirSync(dir);
    } catch (err) {
        return [];
    }
    const records = [];
    for (const name of names.sort()) {
        if (!name.endsWith('.jsonl')) continue;
        for (const record of readRecords(path.join(dir, name))) records.push(record);
    }
    return records;
}

// First occurrence of a label within a run is cold; every later one is warm.
function nextPhase(label, id = runId()) {
    const seen = loadRun(id).some((record) => record && record.label === label);
    return seen ? 'warm' : 'cold';
}

function record(entry) {
    if (isDisabled()) return false;
    const id = entry.runId || runId();
    const full = {
        schema: 1,
        runId: id,
        label: String(entry.label || 'unlabelled'),
        phase: entry.phase === 'warm' ? 'warm' : 'cold',
        ms: Math.max(0, Math.round(Number(entry.ms) || 0)),
        exitCode: Number.isInteger(entry.exitCode) ? entry.exitCode : null,
        ok: entry.ok === true,
        command: entry.command == null ? null : String(entry.command),
        startedAt: entry.startedAt || new Date().toISOString(),
        host: entry.host || os.hostname(),
        platform: process.platform,
        ci: Boolean(String(process.env.CI || '').trim()),
        commit: String(process.env.GITHUB_SHA || '').trim() || null,
        tags: entry.tags && typeof entry.tags === 'object' ? entry.tags : {},
    };
    try {
        const file = timingsFile(id);
        fs.mkdirSync(path.dirname(file), { recursive: true });
        fs.appendFileSync(file, `${JSON.stringify(full)}\n`, 'utf8');
        return true;
    } catch (err) {
        // Rule 1: instrumentation never fails the thing it is measuring.
        process.stderr.write(`timings: could not record "${full.label}": ${err.message}\n`);
        return false;
    }
}

function summarize(records) {
    const byLabel = new Map();
    for (const entry of records) {
        if (!entry || typeof entry.label !== 'string') continue;
        if (!byLabel.has(entry.label)) {
            byLabel.set(entry.label, {
                label: entry.label,
                runs: 0,
                failures: 0,
                totalMs: 0,
                coldMs: null,
                warmMs: [],
            });
        }
        const row = byLabel.get(entry.label);
        const ms = Math.max(0, Math.round(Number(entry.ms) || 0));
        row.runs += 1;
        if (entry.ok !== true) row.failures += 1;
        row.totalMs += ms;
        if (entry.phase === 'warm') row.warmMs.push(ms);
        else if (row.coldMs === null) row.coldMs = ms;
    }
    const rows = [];
    for (const row of byLabel.values()) {
        const warmRuns = row.warmMs.length;
        const warmTotal = row.warmMs.reduce((sum, ms) => sum + ms, 0);
        rows.push({
            label: row.label,
            runs: row.runs,
            failures: row.failures,
            totalMs: row.totalMs,
            coldMs: row.coldMs,
            warmMeanMs: warmRuns ? Math.round(warmTotal / warmRuns) : null,
            warmRuns,
        });
    }
    rows.sort((a, b) => b.totalMs - a.totalMs);
    return rows;
}

function formatMs(ms) {
    if (ms === null || ms === undefined) return '-';
    if (ms < 1000) return `${ms} ms`;
    return `${(ms / 1000).toFixed(1)} s`;
}

function formatTable(rows) {
    const total = rows.reduce((sum, row) => sum + row.totalMs, 0);
    const lines = [];
    lines.push('| step | runs | cold | warm (mean) | total | share |');
    lines.push('| --- | ---: | ---: | ---: | ---: | ---: |');
    for (const row of rows) {
        const share = total > 0 ? `${((row.totalMs / total) * 100).toFixed(1)}%` : '-';
        const label = row.failures > 0 ? `${row.label} (${row.failures} failed)` : row.label;
        lines.push(`| ${label} | ${row.runs} | ${formatMs(row.coldMs)} | ${formatMs(row.warmMeanMs)} | ${formatMs(row.totalMs)} | ${share} |`);
    }
    lines.push(`| **total** | | | | **${formatMs(total)}** | |`);
    return lines.join('\n');
}

module.exports = {
    DEFAULT_DIR,
    formatMs,
    formatTable,
    isDisabled,
    loadAll,
    loadRun,
    nextPhase,
    readRecords,
    record,
    runId,
    summarize,
    timingsDir,
    timingsFile,
};
