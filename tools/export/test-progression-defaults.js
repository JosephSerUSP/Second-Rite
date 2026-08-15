'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const rtp = require('./rtp-resource-resolver');
const defaults = require('./authored-default-resolver');
const materializer = require('./authored-default-materializer');

function write(file, value) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n');
}

function fixture() {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-progression-defaults-'));
    const project = path.join(root, 'project');
    const rtpRoot = path.join(root, 'rtp');
    const revisionRoot = path.join(rtpRoot, 'revisions', 'A');
    const stage = path.join(root, 'stage');

    write(path.join(project, 'data', 'system.json'), { rtp: { revision: 'A' } });
    write(path.join(revisionRoot, 'manifest.json'), {
        version: 1,
        revision: 'A',
        resources: [],
        authored: { progression: 'data/progression.json' },
    });
    write(path.join(revisionRoot, 'data', 'progression.json'), { nextLevelExp: 'level * 15' });
    write(path.join(stage, 'data', 'system.json'), { rtp: { revision: 'A' } });

    return { root, project, rtpRoot, revisionRoot, stage };
}

test('progression resolves from the exact pinned RTP when Project-local policy is absent', () => {
    const f = fixture();
    try {
        const system = rtp.projectSystem(f.project);
        const resolved = defaults.progression({
            projectDir: f.project,
            systemValue: system.value,
            rtpRoot: f.rtpRoot,
        });
        assert.equal(resolved.resource, 'progression');
        assert.equal(resolved.logicalPath.replace(/\\/g, '/'), 'data/progression.json');
        assert.equal(resolved.provider.kind, 'rtp');
        assert.equal(resolved.provider.revision, 'A');
        assert.deepEqual(resolved.value, { nextLevelExp: 'level * 15' });
    } finally { fs.rmSync(f.root, { recursive: true, force: true }); }
});

test('installing a newer RTP revision does not silently move an older Project off its pin', () => {
    const f = fixture();
    try {
        const newer = path.join(f.rtpRoot, 'revisions', 'B');
        write(path.join(newer, 'manifest.json'), {
            version: 1,
            revision: 'B',
            resources: [],
            authored: { progression: 'data/progression.json' },
        });
        write(path.join(newer, 'data', 'progression.json'), { nextLevelExp: 'level * level + 99' });

        const system = rtp.projectSystem(f.project);
        assert.equal(system.value.rtp.revision, 'A');
        const resolved = defaults.progression({
            projectDir: f.project,
            systemValue: system.value,
            rtpRoot: f.rtpRoot,
        });
        assert.equal(resolved.provider.revision, 'A');
        assert.deepEqual(resolved.value, { nextLevelExp: 'level * 15' });
    } finally { fs.rmSync(f.root, { recursive: true, force: true }); }
});

test('Project-local progression explicitly overrides the pinned house baseline', () => {
    const f = fixture();
    try {
        write(path.join(f.project, 'data', 'progression.json'), { nextLevelExp: 'level * level' });
        const system = rtp.projectSystem(f.project);
        const resolved = defaults.progression({
            projectDir: f.project,
            systemValue: system.value,
            rtpRoot: f.rtpRoot,
        });
        assert.equal(resolved.provider.kind, 'project');
        assert.deepEqual(resolved.value, { nextLevelExp: 'level * level' });
    } finally { fs.rmSync(f.root, { recursive: true, force: true }); }
});

test('materialization writes the resolved progression and provider provenance', () => {
    const f = fixture();
    try {
        const result = materializer.resolveAndMaterialize({
            projectDir: f.project,
            runtimeDir: f.root,
            stageDir: f.stage,
            rtpRoot: f.rtpRoot,
            includeSounds: false,
        });
        const staged = JSON.parse(fs.readFileSync(path.join(f.stage, 'data', 'progression.json'), 'utf8'));
        assert.deepEqual(staged, { nextLevelExp: 'level * 15' });
        assert.equal(result.progression.provider.kind, 'rtp');

        const provenance = JSON.parse(fs.readFileSync(path.join(f.stage, 'data', 'authored_resolution.json'), 'utf8'));
        assert.equal(provenance.rtpRevision, 'A');
        assert.equal(provenance.resources.progression.provider.kind, 'rtp');
        assert.equal(provenance.resources.progression.provider.revision, 'A');
        assert.ok(!JSON.stringify(provenance).includes(f.root), 'provenance must not embed development checkout paths');
    } finally { fs.rmSync(f.root, { recursive: true, force: true }); }
});

test('a manifest-declared progression default fails visibly when its file is missing', () => {
    const f = fixture();
    try {
        fs.rmSync(path.join(f.revisionRoot, 'data', 'progression.json'));
        const system = rtp.projectSystem(f.project);
        assert.throws(() => defaults.progression({
            projectDir: f.project,
            systemValue: system.value,
            rtpRoot: f.rtpRoot,
        }), /declares missing progression default/);
    } finally { fs.rmSync(f.root, { recursive: true, force: true }); }
});