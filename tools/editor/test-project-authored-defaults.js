'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const lifecycle = require('./project-lifecycle');

const REPO = path.resolve(__dirname, '..', '..');

function read(file) {
    return fs.readFileSync(file, 'utf8');
}

test('sparse Project progression is inherited, inspectable, and can Make Local without editing RTP', () => {
    const work = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-authored-local-'));
    try {
        const project = path.join(work, 'game');
        lifecycle.createSparseProject({ target: project, installRoot: REPO, name: 'Make Local Proof' });
        const localFile = path.join(project, 'data', 'progression.json');
        assert.equal(fs.existsSync(localFile), false, 'fresh Project remains locally sparse');

        const inherited = lifecycle.authoredDefaultInfo({
            project,
            resource: 'progression',
            installRoot: REPO,
        });
        assert.equal(inherited.provider, 'rtp');
        assert.equal(inherited.providerId, 'thestra-rtp');
        assert.equal(inherited.revision, '1.0');
        assert.equal(inherited.logicalPath, 'data/progression.json');

        const rtpFile = path.join(REPO, 'rtp', 'revisions', '1.0', 'data', 'progression.json');
        const rtpBefore = read(rtpFile);
        const made = lifecycle.makeAuthoredDefaultLocal({
            project,
            resource: 'progression',
            installRoot: REPO,
        });
        assert.equal(made.madeLocal, true);
        assert.equal(made.provider, 'project');
        assert.equal(made.inheritedRevision, '1.0');
        assert.equal(fs.existsSync(localFile), true);
        assert.deepEqual(JSON.parse(read(localFile)), JSON.parse(rtpBefore),
            'Make Local starts from the exact resolved inherited value');

        fs.writeFileSync(localFile, JSON.stringify({ nextLevelExp: 'level * level + 7' }, null, 2) + '\n');
        const local = lifecycle.resolveAuthoredDefault({
            project,
            resource: 'progression',
            installRoot: REPO,
        });
        assert.equal(local.provider.kind, 'project');
        assert.deepEqual(local.value, { nextLevelExp: 'level * level + 7' });
        assert.equal(read(rtpFile), rtpBefore, 'Project divergence never edits shared RTP source');

        const again = lifecycle.makeAuthoredDefaultLocal({
            project,
            resource: 'progression',
            installRoot: REPO,
        });
        assert.equal(again.madeLocal, false, 'Make Local is idempotent once Project-owned');
        assert.deepEqual(JSON.parse(read(localFile)), { nextLevelExp: 'level * level + 7' });
    } finally {
        fs.rmSync(work, { recursive: true, force: true });
    }
});

test('sparse Project creation refuses a house baseline that omits progression', () => {
    const work = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-incomplete-baseline-'));
    try {
        const revision = path.join(work, 'rtp', 'revisions', '1.0');
        fs.mkdirSync(revision, { recursive: true });
        fs.writeFileSync(path.join(revision, 'manifest.json'), JSON.stringify({
            version: 1,
            revision: '1.0',
            resources: [],
            authored: {
                engineRegistry: 'data/engine.json',
                sceneDefaults: { dialogue: 'data/scenes/dialogue.json' },
                flowDefaults: { exploration: 'data/flows/exploration.json' },
            },
        }, null, 2) + '\n');

        const availability = lifecycle.sparseProjectAvailability({ installRoot: work });
        assert.equal(availability.available, false);
        assert.equal(availability.code, 'SPARSE_RTP_BASELINE_INCOMPLETE');
        assert.match(availability.reason, /engine\/progression\/Scene\/Flow baseline/);
    } finally {
        fs.rmSync(work, { recursive: true, force: true });
    }
});
