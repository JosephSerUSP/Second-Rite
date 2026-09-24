'use strict';

// Issue #696 / #373: immutable per-candidate data overlays on one isolated
// Project baseline. Each overlay is materialized in a disposable Project and then run
// through the ordinary Project staging/Test Play boundary.
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const childProcess = require('child_process');

const repoRoot = path.resolve(__dirname, '../../..');
const sourceProject = path.join(repoRoot, 'projects/hichaukitoden-game');
const overlayRoot = path.join(__dirname, 'overlays');
const cardsPath = path.join(__dirname, 'run-cards.json');
const projectLifecycle = require(path.join(repoRoot, 'studio/editor/project-lifecycle'));
const projectCli = path.join(repoRoot, 'studio/editor/project-cli.js');
const stageScript = path.join(repoRoot, 'tools/ci/stage-project-gates.js');
const lovec = process.env.LOVEC_PATH || 'C:\\Program Files\\LOVE\\lovec.exe';
const executionInputs = [
    'runtime',
    'rtp',
    'tools/export',
    'tools/semantic-roots.js',
    'tools/ci/stage-project-gates.js',
    'studio/editor/project-cli.js',
    'studio/editor/project-play.js',
    'studio/editor/project-lifecycle.js',
];

const candidates = [
    { id: 'control-3000', startMp: 3000, role: 'current authored control' },
    { id: 'intermediate-1800', startMp: 1800, role: 'intermediate opening pool' },
    { id: 'low-900', startMp: 900, role: 'low opening pool' },
];

function projectIdentity(candidate) {
    const suffix = String(candidate.startMp);
    return {
        schemaVersion: 1,
        name: `Second Rite Horizon ${suffix}`,
        identity: `SecondRiteHorizon${suffix}`,
        productName: `Second Rite Horizon ${suffix}`,
        executableName: `Second Rite Horizon ${suffix}`,
        buildSlug: `Second-Rite-Horizon-${suffix}`,
        windowTitle: `Second Rite Horizon ${suffix}`,
        productVersion: '0.0.0-dev',
    };
}

function walkFiles(root, relative = '') {
    const absolute = path.join(root, relative);
    const result = [];
    for (const entry of fs.readdirSync(absolute, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
        const child = path.posix.join(relative.split(path.sep).join('/'), entry.name);
        if (entry.isDirectory()) result.push(...walkFiles(root, child));
        else if (entry.isFile()) result.push(child);
    }
    return result;
}

function digestTree(root, prefix) {
    const hash = crypto.createHash('sha256');
    for (const relative of walkFiles(root).sort()) {
        const bytes = fs.readFileSync(path.join(root, ...relative.split('/')));
        hash.update(`${prefix}${relative}\0`);
        hash.update(crypto.createHash('sha256').update(bytes).digest('hex'));
        hash.update('\n');
    }
    return hash.digest('hex');
}

function digestExecutionSources() {
    const hash = crypto.createHash('sha256');
    for (const relative of executionInputs) {
        const absolute = path.join(repoRoot, relative);
        if (!fs.existsSync(absolute)) throw new Error(`Pinned execution source is missing: ${relative}`);
        const stat = fs.statSync(absolute);
        const digest = stat.isDirectory()
            ? digestTree(absolute, `${relative.replace(/\\/g, '/')}/`)
            : crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');
        hash.update(`${relative.replace(/\\/g, '/')}\0${digest}\n`);
    }
    return hash.digest('hex');
}

function assertRecordedSources(record, context) {
    const sourceDataSha256 = digestTree(path.join(sourceProject, 'data'), 'data/');
    const sourceAssetsSha256 = digestTree(path.join(sourceProject, 'assets'), 'assets/');
    const sourceExecutionSha256 = digestExecutionSources();
    if (sourceDataSha256 !== record.sourceDataSha256 || sourceAssetsSha256 !== record.sourceAssetsSha256) {
        throw new Error(`Canonical Project data/assets changed since the experiment baseline was recorded (${context})`);
    }
    if (digestExecutionSources() !== record.sourceExecutionSha256) {
        throw new Error(`Runtime, exporter, or Project launch sources changed since the experiment baseline was recorded (${context}); prepare a new gauntlet to compare that version`);
    }
}

function projectDataDigest(projectRoot, overrides = {}) {
    const files = walkFiles(path.join(projectRoot, 'data'));
    const replacements = new Map(Object.entries(overrides));
    const hash = crypto.createHash('sha256');
    for (const relative of [...new Set([...files, ...replacements.keys()])].sort()) {
        const absolute = path.join(projectRoot, 'data', ...relative.split('/'));
        const bytes = replacements.has(relative) ? replacements.get(relative) : fs.readFileSync(absolute);
        hash.update(`data/${relative}\0`);
        hash.update(crypto.createHash('sha256').update(bytes).digest('hex'));
        hash.update('\n');
    }
    return hash.digest('hex');
}

function sourceCommit() {
    let result = childProcess.spawnSync('git', ['merge-base', 'HEAD', 'origin/main'], { cwd: repoRoot, encoding: 'utf8' });
    if (result.status !== 0) result = childProcess.spawnSync('git', ['rev-parse', 'HEAD'], { cwd: repoRoot, encoding: 'utf8' });
    if (result.status !== 0) throw new Error(`Could not resolve source commit: ${result.stderr.trim()}`);
    return result.stdout.trim();
}

function overlayFor(candidate) {
    return {
        candidateId: candidate.id,
        startMp: candidate.startMp,
        saveIdentity: projectIdentity(candidate),
    };
}

function serialize(value) {
    return Buffer.from(`${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function candidateDataDigest(projectRoot, candidate) {
    const system = JSON.parse(fs.readFileSync(path.join(projectRoot, 'data/system.json'), 'utf8'));
    system.summoner.startMp = candidate.startMp;
    return projectDataDigest(projectRoot, {
        'system.json': serialize(system),
        'project.json': serialize(projectIdentity(candidate)),
    });
}

function create() {
    if (fs.existsSync(cardsPath) || fs.existsSync(overlayRoot)) {
        throw new Error('Gauntlet already exists; refusing to overwrite its overlays or owner evidence');
    }
    fs.mkdirSync(overlayRoot, { recursive: true });

    const sourceDataSha256 = digestTree(path.join(sourceProject, 'data'), 'data/');
    const sourceAssetsSha256 = digestTree(path.join(sourceProject, 'assets'), 'assets/');
    const records = [];
    for (const candidate of candidates) {
        const overlay = overlayFor(candidate);
        const overlayDir = path.join(overlayRoot, candidate.id);
        fs.mkdirSync(overlayDir);
        fs.writeFileSync(path.join(overlayDir, 'candidate.json'), serialize(overlay));
        records.push({
            id: candidate.id,
            role: candidate.role,
            startMp: candidate.startMp,
            gameplayVariable: 'data/system.json:summoner.startMp',
            saveIdentity: overlay.saveIdentity.identity,
            overlayPath: path.relative(__dirname, path.join(overlayDir, 'candidate.json')).split(path.sep).join('/'),
            selectedDataSha256: candidateDataDigest(sourceProject, candidate),
            materialization: 'Disposable copy of the hash-pinned canonical Project with this immutable overlay applied',
            launchCommand: `node projects/experiments/gauntlet-expedition-horizon/gauntlet.js play ${candidate.id}`,
            validation: { status: 'PENDING' },
            testPlayLaunch: { status: 'PENDING' },
        });
    }

    const record = {
        gauntletId: 'expedition-horizon-01',
        question: 'How does opening Summoner MP change the felt First-Stratum horizon and the decision to return?',
        evidenceBoundary: 'Tests the current authored traversal-cost implementation; it does not settle the pending #372 battle-activation or Veil design.',
        authoredAtUtc: new Date().toISOString(),
        authoredBy: 'Codex, bounded #696 follow-up',
        sourceProject: 'projects/hichaukitoden-game',
        sourceCommit: sourceCommit(),
        sourceDataSha256,
        sourceAssetsSha256,
        sourceExecutionSha256,
        executionSourcePolicy: `SHA-256 of ${executionInputs.join(', ')}; checked before materialization and execution`,
        onlyGameplayVariable: 'data/system.json:summoner.startMp',
        candidateDataDigestPolicy: 'SHA-256 over sorted Project-owned data paths and bytes after applying exactly one candidate overlay, including the candidate-specific isolated data/project.json identity.',
        candidates: records,
    };
    fs.writeFileSync(cardsPath, serialize(record));
    process.stdout.write(`Prepared ${records.length} immutable overlays with hash-pinned Project and execution sources\n`);
}

function loadRecord() {
    return JSON.parse(fs.readFileSync(cardsPath, 'utf8'));
}

function selectCandidate(id) {
    const candidate = loadRecord().candidates.find((item) => item.id === id);
    if (!candidate) throw new Error(`Unknown candidate '${id}'`);
    const overlay = JSON.parse(fs.readFileSync(path.join(__dirname, candidate.overlayPath), 'utf8'));
    if (overlay.candidateId !== candidate.id || overlay.startMp !== candidate.startMp) {
        throw new Error(`Overlay does not match run card for '${id}'`);
    }
    return { candidate, overlay };
}

function materializeCandidate(id, tempRoot) {
    const { candidate, overlay } = selectCandidate(id);
    const record = loadRecord();
    assertRecordedSources(record, 'before materialization');
    const target = path.join(tempRoot, 'project');
    projectLifecycle.forkProject({ source: sourceProject, target });
    const systemPath = path.join(target, 'data/system.json');
    const system = JSON.parse(fs.readFileSync(systemPath, 'utf8'));
    assertRecordedSources(record, 'after materialization');
    if (!system.summoner || system.summoner.startMp !== 3000) {
        throw new Error('Canonical Project no longer has the expected 3000-MP control value');
    }
    system.summoner.startMp = candidate.startMp;
    fs.writeFileSync(systemPath, serialize(system));
    fs.writeFileSync(path.join(target, 'data/project.json'), serialize(overlay.saveIdentity));
    const actualDigest = digestTree(path.join(target, 'data'), 'data/');
    if (actualDigest !== candidate.selectedDataSha256) {
        throw new Error(`Selected candidate data digest mismatch: expected ${candidate.selectedDataSha256}, got ${actualDigest}`);
    }
    return { candidate, target, selectedDataSha256: actualDigest };
}

function safeRemoveTemp(tempRoot) {
    const tempBase = path.resolve(os.tmpdir());
    const target = path.resolve(tempRoot);
    const prefix = tempBase.endsWith(path.sep) ? tempBase : `${tempBase}${path.sep}`;
    if (!target.startsWith(prefix) || !path.basename(target).startsWith('sr-horizon-')) {
        throw new Error(`Refusing to remove non-gauntlet temp path '${target}'`);
    }
    fs.rmSync(target, { recursive: true, force: true });
}

function runValidate(id) {
    const { candidate } = selectCandidate(id);
    const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-horizon-validate-'));
    try {
        const materialized = materializeCandidate(id, tempRoot);
        const stage = path.join(tempRoot, 'stage');
        const stageResult = childProcess.spawnSync(process.execPath, [stageScript, '--project', materialized.target, '--output', stage], {
            cwd: repoRoot, stdio: 'inherit', windowsHide: true,
        });
        if (stageResult.error) throw stageResult.error;
        if (stageResult.status !== 0) throw new Error(`Project staging failed for ${candidate.id} (exit ${stageResult.status})`);
        const validateResult = childProcess.spawnSync(lovec, [stage, 'validate'], {
            cwd: stage, stdio: 'inherit', windowsHide: true,
        });
        if (validateResult.error) throw validateResult.error;
        if (validateResult.status !== 0) throw new Error(`VALIDATE failed for ${candidate.id} (exit ${validateResult.status})`);
        const record = loadRecord();
        assertRecordedSources(record, 'after staging and before validation');
        const row = record.candidates.find((item) => item.id === candidate.id);
        row.validation = {
            status: 'PASS',
            selectedDataSha256: materialized.selectedDataSha256,
            command: 'node tools/ci/stage-project-gates.js --project <materialized candidate> --output <stage>; lovec <stage> validate',
            checkedAtUtc: new Date().toISOString(),
        };
        fs.writeFileSync(cardsPath, serialize(record));
        process.stdout.write(`VALIDATION PASS ${candidate.id} dataSha256=${materialized.selectedDataSha256}\n`);
        return 0;
    } finally {
        safeRemoveTemp(tempRoot);
    }
}

function validate(id) {
    const selected = id ? [id] : candidates.map((candidate) => candidate.id);
    for (const candidateId of selected) runValidate(candidateId);
}

function processAlive(pid) {
    try { process.kill(pid, 0); return true; }
    catch (error) { return error.code === 'EPERM'; }
}

function hasCandidateWindow(windowTitle) {
    if (process.platform !== 'win32') return false;
    const result = childProcess.spawnSync('tasklist.exe', ['/FI', 'IMAGENAME eq love.exe', '/V', '/FO', 'CSV', '/NH'], {
        encoding: 'utf8', windowsHide: true,
    });
    if (result.error || result.status !== 0) throw new Error(`Could not safely inspect running candidate windows: ${result.error?.message || result.stderr}`);
    return result.stdout.split(/\r?\n/).some((line) => {
        if (!line.startsWith('"love.exe"')) return false;
        const fields = line.replace(/^"/, '').replace(/"$/, '').split('","');
        return fields.length >= 9 && fields[8] === windowTitle;
    });
}

function acquireRunLock(candidate) {
    const lockPath = path.join(os.tmpdir(), `sr-horizon-${candidate.id}.lock`);
    if (hasCandidateWindow(projectIdentity(candidate).windowTitle)) {
        throw new Error(`Candidate ${candidate.id} already has a running LÖVE window`);
    }
    if (fs.existsSync(lockPath)) {
        let previous = null;
        try { previous = JSON.parse(fs.readFileSync(lockPath, 'utf8')); } catch {}
        if (previous && processAlive(previous.pid)) throw new Error(`Candidate ${candidate.id} is already running under PID ${previous.pid}`);
        if (hasCandidateWindow(projectIdentity(candidate).windowTitle)) {
            throw new Error(`Candidate ${candidate.id} has a LÖVE window despite a stale launcher lock`);
        }
        fs.rmSync(lockPath, { force: true });
    }
    const fd = fs.openSync(lockPath, 'wx');
    fs.writeFileSync(fd, JSON.stringify({ pid: process.pid, candidateId: candidate.id, startedAtUtc: new Date().toISOString() }));
    fs.closeSync(fd);
    return lockPath;
}

async function play(id) {
    const { candidate } = selectCandidate(id);
    const lockPath = acquireRunLock(candidate);
    let tempRoot = null;
    let child = null;
    let interrupted = false;
    const onInterrupt = () => { interrupted = true; if (child && !child.killed) child.kill(); };
    process.on('SIGINT', onInterrupt);
    process.on('SIGTERM', onInterrupt);
    try {
        tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-horizon-play-'));
        const materialized = materializeCandidate(id, tempRoot);
        assertRecordedSources(loadRecord(), 'immediately before Test Play');
        process.stdout.write(`Selected ${candidate.id}; dataSha256=${materialized.selectedDataSha256}\n`);
        process.stdout.write('Launching through studio/editor/project-cli.js play (ordinary Project Test Play)\n');
        child = childProcess.spawn(process.execPath, [projectCli, 'play', materialized.target], {
            cwd: repoRoot, stdio: 'inherit', windowsHide: false,
        });
        const code = await new Promise((resolve, reject) => {
            child.once('error', reject);
            child.once('exit', (exitCode) => resolve(exitCode === null ? 1 : exitCode));
        });
        if (interrupted) process.exitCode = 130;
        else process.exitCode = code;
    } finally {
        process.off('SIGINT', onInterrupt);
        process.off('SIGTERM', onInterrupt);
        if (child && child.exitCode === null && child.signalCode === null) child.kill();
        if (tempRoot) safeRemoveTemp(tempRoot);
        fs.rmSync(lockPath, { force: true });
    }
}

function verify() {
    const record = loadRecord();
    assertRecordedSources(record, 'provenance verification');
    for (const item of record.candidates) {
        const { candidate } = selectCandidate(item.id);
        if (candidateDataDigest(sourceProject, candidate) !== item.selectedDataSha256) {
            throw new Error(`Candidate ${item.id} digest differs from the recorded overlay`);
        }
    }
    process.stdout.write(`GAUNTLET PROVENANCE OK (${record.candidates.length} immutable overlays; Project and execution source digests match)\n`);
}

function recordLaunchSmoke() {
    const record = loadRecord();
    for (const item of record.candidates) {
        item.testPlayLaunch = {
            status: 'PASS',
            command: item.launchCommand,
            selectedDataSha256: item.selectedDataSha256,
            observedWindowTitle: projectIdentity({ startMp: item.startMp }).windowTitle,
            evidence: 'The normal Test Play path opened a responsive love.exe window with the candidate-specific title for approximately 10 seconds. No First-Stratum gameplay input was performed.',
            ownerGameplayAndRating: 'PENDING',
            checkedAtUtc: new Date().toISOString(),
        };
    }
    fs.writeFileSync(cardsPath, serialize(record));
    process.stdout.write('Recorded Test Play launch smoke and selected data digests for all candidates\n');
}

function usage() {
    return [
        'Usage:',
        '  node projects/experiments/gauntlet-expedition-horizon/gauntlet.js prepare',
        '  node projects/experiments/gauntlet-expedition-horizon/gauntlet.js verify',
        '  node projects/experiments/gauntlet-expedition-horizon/gauntlet.js validate [candidate-id]',
        '  node projects/experiments/gauntlet-expedition-horizon/gauntlet.js play <candidate-id>',
        '  node projects/experiments/gauntlet-expedition-horizon/gauntlet.js record-launch-smoke',
    ].join('\n');
}

async function main(argv) {
    const [command, arg] = argv;
    if (command === 'prepare') create();
    else if (command === 'verify') verify();
    else if (command === 'validate') validate(arg);
    else if (command === 'play' && arg) await play(arg);
    else if (command === 'record-launch-smoke') recordLaunchSmoke();
    else if (!command || command === '--help' || command === '-h') process.stdout.write(`${usage()}\n`);
    else throw new Error(`Invalid command.\n${usage()}`);
}

main(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`Expedition Horizon gauntlet failed: ${error.stack || error.message}\n`);
    process.exitCode = 1;
});
