\
'use strict';

const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');

const exporter = require('./export-game');
const resolver = require('./rtp-resource-resolver');
const preview = require('../editor/rtp-preview-resources');

const REPO = path.resolve(__dirname, '..', '..');

function mkdir(file) { fs.mkdirSync(path.dirname(file), { recursive: true }); }
function write(file, content) { mkdir(file); fs.writeFileSync(file, content); }
function writeJson(file, value) { write(file, JSON.stringify(value, null, 2) + '\n'); }
function blobSha(buffer) {
    return crypto.createHash('sha1')
        .update(Buffer.from(`blob ${buffer.length}\0`))
        .update(buffer)
        .digest('hex');
}

const provenance = {
    source: 'fixture source',
    authorship: 'fixture author',
    redistributionStatus: 'fixture redistribution allowed',
    genericReason: 'fixture has no Project content',
    playerFacingReason: 'fixture is player presentation data',
};

function resource(id, klass, logicalPath, extra = {}) {
    return Object.assign({ id, class: klass, logicalPath }, provenance, extra);
}

function makeRevision(rtpRoot, revision, fontBytes, includeTemplate) {
    const root = path.join(rtpRoot, 'revisions', revision);
    const resources = [resource('font.jersey10', 'font', 'assets/fonts/Jersey10-Regular.ttf', {
        licensePath: 'licenses/Jersey10-OFL.txt',
    })];
    if (includeTemplate) {
        resources.push(resource('tileset.template', 'tileset-template', 'assets/tilesets/template_tileset.png'));
        write(path.join(root, 'assets', 'tilesets', 'template_tileset.png'), `${revision} TEMPLATE`);
    }
    write(path.join(root, 'assets', 'fonts', 'Jersey10-Regular.ttf'), fontBytes);
    write(path.join(root, 'licenses', 'Jersey10-OFL.txt'), `${revision} LICENSE`);
    writeJson(path.join(root, 'resources.json'), { version: 1, revision, resources });
}

function makeProject(root) {
    writeJson(path.join(root, 'data', 'system.json'), {
        rtp: { revision: 'A' },
        ui: { activeFont: 'Jersey10-Regular' },
    });
    // Keep sounds Project-local so this fixture isolates #391's new classes.
    writeJson(path.join(root, 'data', 'sounds.json'), {});
    fs.mkdirSync(path.join(root, 'assets', 'fonts'), { recursive: true });
    fs.mkdirSync(path.join(root, 'assets', 'tilesets'), { recursive: true });
}

test('checked-in revision A font has independently pinned upstream identity and provenance', () => {
    const manifest = JSON.parse(fs.readFileSync(path.join(REPO, 'rtp', 'revisions', 'A', 'resources.json'), 'utf8'));
    assert.equal(manifest.revision, 'A');
    assert.equal(manifest.resources.length, 1);
    const entry = manifest.resources[0];
    for (const field of ['source', 'authorship', 'redistributionStatus', 'genericReason', 'playerFacingReason']) {
        assert.equal(typeof entry[field], 'string');
        assert.ok(entry[field].trim(), field);
    }
    const font = fs.readFileSync(path.join(REPO, 'rtp', 'revisions', 'A', entry.logicalPath));
    assert.equal(blobSha(font), '6870bfd222d1fa0c32a20c1d348320bb9a04b9ed');
    const notice = fs.readFileSync(path.join(REPO, 'rtp', 'revisions', 'A', entry.licensePath), 'utf8');
    assert.match(notice, /Copyright 2023 The Soft Type Project Authors/);
    assert.match(notice, /SIL OPEN FONT LICENSE Version 1\.1/);
});

test('generic preview resolves only pinned A while Project-specific resources still win', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-rtp-preview-'));
    try {
        const project = path.join(tmp, 'external-project');
        const rtpRoot = path.join(tmp, 'installed-rtp');
        makeProject(project);
        makeRevision(rtpRoot, 'A', 'A FONT', false);
        makeRevision(rtpRoot, 'B', 'B FONT', true);

        // A neighboring/newer B is not an implicit overlay.
        let fonts = resolver.fonts({
            projectDir: project,
            systemValue: resolver.projectSystem(project).value,
            rtpRoot,
        });
        assert.equal(fonts.length, 1);
        assert.equal(fonts[0].provider.kind, 'rtp');
        assert.equal(fonts[0].provider.revision, 'A');
        assert.equal(fs.readFileSync(fonts[0].sourcePath, 'utf8'), 'A FONT');
        assert.deepEqual(preview.fontNames(project, rtpRoot), ['Lucida', 'Jersey10-Regular']);

        // A Second Gate-shaped texture name cannot satisfy generic creation.
        write(path.join(project, 'assets', 'tilesets', 'dungeon_001.png'), 'PROJECT DUNGEON');
        assert.equal(preview.tilesetTemplate(project, rtpRoot), null);

        // Project-local resources remain intentional Project-specific truth.
        write(path.join(project, 'assets', 'tilesets', 'template_tileset.png'), 'PROJECT TEMPLATE');
        let template = preview.tilesetTemplate(project, rtpRoot);
        assert.equal(template.provider.kind, 'project');
        assert.equal(fs.readFileSync(template.sourcePath, 'utf8'), 'PROJECT TEMPLATE');

        write(path.join(project, 'assets', 'fonts', 'Jersey10-Regular.ttf'), 'PROJECT FONT');
        fonts = resolver.fonts({
            projectDir: project,
            systemValue: resolver.projectSystem(project).value,
            rtpRoot,
        });
        assert.equal(fonts[0].provider.kind, 'project');
        assert.equal(fs.readFileSync(fonts[0].sourcePath, 'utf8'), 'PROJECT FONT');
    } finally {
        fs.rmSync(tmp, { recursive: true, force: true });
    }
});

test('typed A tileset template works when explicitly declared and never comes from B', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-rtp-template-'));
    try {
        const project = path.join(tmp, 'external-project');
        const rtpRoot = path.join(tmp, 'installed-rtp');
        makeProject(project);
        makeRevision(rtpRoot, 'A', 'A FONT', true);
        makeRevision(rtpRoot, 'B', 'B FONT', true);
        const template = preview.tilesetTemplate(project, rtpRoot);
        assert.equal(template.provider.kind, 'rtp');
        assert.equal(template.provider.revision, 'A');
        assert.equal(fs.readFileSync(template.sourcePath, 'utf8'), 'A TEMPLATE');
    } finally {
        fs.rmSync(tmp, { recursive: true, force: true });
    }
});

test('stageGame materializes depended RTP font and notice into a hermetic external Project tree', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-rtp-stage-'));
    const project = path.join(tmp, 'external-project');
    const runtime = path.join(tmp, 'runtime');
    const stage = path.join(tmp, 'stage');
    try {
        makeProject(project);
        makeRevision(path.join(runtime, 'rtp'), 'A', 'A FONT', false);
        makeRevision(path.join(runtime, 'rtp'), 'B', 'B FONT', false);

        write(path.join(runtime, 'main.lua'), '-- fixture runtime');
        write(path.join(runtime, 'release-conf.lua'), '-- fixture release config');
        write(path.join(runtime, 'engine', 'fixture.lua'), '-- engine');
        write(path.join(runtime, 'presentation', 'fixture.lua'), '-- presentation');
        writeJson(path.join(runtime, 'data', 'runtime.json'), {});
        const manifestPath = path.join(runtime, 'runtime-manifest.json');
        writeJson(manifestPath, {
            version: 1,
            rootFiles: ['main.lua'],
            runtimeDirectories: ['engine', 'presentation'],
            projectDirectories: ['assets'],
            dataRuntimeFiles: ['runtime.json'],
            authoredDataExtensions: ['.json'],
            releaseConfig: 'release-conf.lua',
        });

        const staged = exporter.stageGame({ projectDir: project, runtimeDir: runtime, outputDir: stage, manifestPath });
        assert.equal(staged.resolvedResources.fonts.length, 1);
        assert.equal(staged.resolvedResources.fonts[0].provider.revision, 'A');
        assert.equal(fs.readFileSync(path.join(stage, 'assets', 'fonts', 'Jersey10-Regular.ttf'), 'utf8'), 'A FONT');
        assert.equal(fs.readFileSync(path.join(stage, 'LICENSES', 'Jersey10-OFL.txt'), 'utf8'), 'A LICENSE');
        assert.equal(fs.existsSync(path.join(stage, 'rtp')), false);
        assert.equal(fs.existsSync(path.join(stage, 'tools', 'editor', 'Assets')), false);

        // The player tree survives after authoring-time Project/RTP sources go away.
        fs.rmSync(project, { recursive: true, force: true });
        fs.rmSync(runtime, { recursive: true, force: true });
        assert.equal(fs.readFileSync(path.join(stage, 'assets', 'fonts', 'Jersey10-Regular.ttf'), 'utf8'), 'A FONT');
    } finally {
        fs.rmSync(tmp, { recursive: true, force: true });
    }
});

test('actual Studio creator contains no dungeon fallback and uses the typed preview helper', () => {
    const source = fs.readFileSync(path.join(REPO, 'tools', 'editor', 'server.js'), 'utf8');
    assert.ok(source.includes('rtpPreviewResources.tilesetTemplate(PROJECT_ROOT, rtpRoot)'));
    assert.ok(!source.includes("tmplPng = path.join(tilesetsDir, 'dungeon_001.png')"));
});
