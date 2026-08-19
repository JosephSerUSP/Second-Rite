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

function put(file, value) { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, value); }
function json(file, value) { put(file, JSON.stringify(value) + '\n'); }
function entry(id, klass, logicalPath, extra = {}) {
    return Object.assign({ id, class: klass, logicalPath, source: 'fixture', authorship: 'fixture', redistributionStatus: 'allowed', genericReason: 'neutral fixture', playerFacingReason: 'player presentation' }, extra);
}
function revision(root, rev, font, template = false) {
    const base = path.join(root, 'revisions', rev);
    const resources = [entry('font.jersey10', 'font', 'assets/fonts/Jersey10-Regular.ttf', { licensePath: 'licenses/Jersey10-OFL.txt' })];
    put(path.join(base, 'assets/fonts/Jersey10-Regular.ttf'), font);
    put(path.join(base, 'licenses/Jersey10-OFL.txt'), `${rev} LICENSE`);
    if (template) {
        resources.push(entry('tileset.template', 'tileset-template', 'assets/tilesets/template_tileset.png'));
        put(path.join(base, 'assets/tilesets/template_tileset.png'), `${rev} TEMPLATE`);
    }
    json(path.join(base, 'manifest.json'), { version: 1, revision: rev, resources });
}
function project(root) {
    json(path.join(root, 'data/system.json'), { rtp: { revision: 'A' }, ui: { activeFont: 'Jersey10-Regular' } });
    json(path.join(root, 'data/sounds.json'), {});
    fs.mkdirSync(path.join(root, 'assets/fonts'), { recursive: true });
    fs.mkdirSync(path.join(root, 'assets/tilesets'), { recursive: true });
}

test('revision 1.0 baseline has pinned Jersey provenance and exact upstream bytes', () => {
    const manifest = JSON.parse(fs.readFileSync(path.join(REPO, 'rtp/revisions/1.0/manifest.json'), 'utf8'));
    const r = manifest.resources[0];
    for (const key of ['source', 'authorship', 'redistributionStatus', 'genericReason', 'playerFacingReason']) assert.ok(r[key]);
    const bytes = fs.readFileSync(path.join(REPO, 'rtp/revisions/1.0', r.logicalPath));
    const sha = crypto.createHash('sha1').update(Buffer.from(`blob ${bytes.length}\0`)).update(bytes).digest('hex');
    assert.equal(sha, '6870bfd222d1fa0c32a20c1d348320bb9a04b9ed');
    assert.match(fs.readFileSync(path.join(REPO, 'rtp/revisions/1.0', r.licensePath), 'utf8'), /SIL OPEN FONT LICENSE Version 1\.1/);
});

test('external generic preview pins A; Project resources win; dungeon art never becomes a template', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-391-preview-'));
    try {
        const p = path.join(tmp, 'project'); const rtp = path.join(tmp, 'rtp'); project(p);
        revision(rtp, 'A', 'A FONT'); revision(rtp, 'B', 'B FONT', true);
        let fonts = resolver.fonts({ projectDir: p, systemValue: resolver.projectSystem(p).value, rtpRoot: rtp });
        assert.equal(fonts[0].provider.revision, 'A'); assert.equal(fs.readFileSync(fonts[0].sourcePath, 'utf8'), 'A FONT');
        assert.deepEqual(preview.fontNames(p, rtp), ['Lucida', 'Jersey10-Regular']);
        put(path.join(p, 'assets/tilesets/dungeon_001.png'), 'SECOND GATE');
        assert.equal(preview.tilesetTemplate(p, rtp), null);
        put(path.join(p, 'assets/tilesets/template_tileset.png'), 'PROJECT TEMPLATE');
        assert.equal(preview.tilesetTemplate(p, rtp).provider.kind, 'project');
        put(path.join(p, 'assets/fonts/Jersey10-Regular.ttf'), 'PROJECT FONT');
        fonts = resolver.fonts({ projectDir: p, systemValue: resolver.projectSystem(p).value, rtpRoot: rtp });
        assert.equal(fonts[0].provider.kind, 'project');
    } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
});

test('Project font extension matching is portable but ambiguous case variants fail loud', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-font-case-'));
    try {
        const p = path.join(tmp, 'project');
        json(path.join(p, 'data/system.json'), { ui: { activeFont: '04B_03__' } });
        put(path.join(p, 'assets/fonts/04B_03__.TTF'), 'UPPERCASE EXTENSION');
        let fonts = resolver.fonts({ projectDir: p, systemValue: resolver.projectSystem(p).value });
        assert.equal(fonts.length, 1);
        assert.equal(fonts[0].provider.kind, 'project');
        assert.equal(fonts[0].logicalPath, 'assets/fonts/04B_03__.ttf');
        assert.equal(fs.readFileSync(fonts[0].sourcePath, 'utf8'), 'UPPERCASE EXTENSION');

        if (process.platform !== 'win32') {
            assert.equal(path.basename(fonts[0].sourcePath), '04B_03__.TTF');
            put(path.join(p, 'assets/fonts/04b_03__.ttf'), 'AMBIGUOUS CASE VARIANT');
            assert.throws(
                () => resolver.fonts({ projectDir: p, systemValue: resolver.projectSystem(p).value }),
                /ambiguous under case-insensitive \.ttf matching/,
            );
        }
    } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
});

test('typed template and export staging use only pinned A and leave no installed RTP dependency', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-391-stage-'));
    try {
        const p = path.join(tmp, 'project'); const runtime = path.join(tmp, 'runtime'); const rtp = path.join(runtime, 'rtp'); const stage = path.join(tmp, 'stage');
        project(p); revision(rtp, 'A', 'A FONT', true); revision(rtp, 'B', 'B FONT', true);
        assert.equal(fs.readFileSync(preview.tilesetTemplate(p, rtp).sourcePath, 'utf8'), 'A TEMPLATE');
        put(path.join(runtime, 'main.lua'), '-- runtime'); put(path.join(runtime, 'release-conf.lua'), '-- config');
        put(path.join(runtime, 'engine/x.lua'), '-- engine'); put(path.join(runtime, 'presentation/x.lua'), '-- presentation'); json(path.join(runtime, 'data/runtime.json'), {});
        const manifest = path.join(runtime, 'runtime-manifest.json');
        json(manifest, { version: 1, rootFiles: ['main.lua'], runtimeDirectories: ['engine', 'presentation'], projectDirectories: ['assets'], authoredDataExtensions: ['.json'], releaseConfig: 'release-conf.lua' });
        const out = exporter.stageGame({ projectDir: p, runtimeDir: runtime, rtpRoot: rtp, outputDir: stage, manifestPath: manifest });
        assert.equal(out.resolvedResources.fonts[0].provider.revision, 'A');
        assert.equal(fs.readFileSync(path.join(stage, 'assets/fonts/Jersey10-Regular.ttf'), 'utf8'), 'A FONT');
        assert.equal(fs.readFileSync(path.join(stage, 'LICENSES/Jersey10-OFL.txt'), 'utf8'), 'A LICENSE');
        assert.equal(fs.existsSync(path.join(stage, 'rtp')), false); assert.equal(fs.existsSync(path.join(stage, 'tools/editor/Assets')), false);
    } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
});

test('actual tileset creator contains no Second Gate fallback', () => {
    const source = fs.readFileSync(path.join(REPO, 'tools/editor/server.js'), 'utf8');
    assert.ok(source.includes('rtpPreviewResources.tilesetTemplate(PROJECT_ROOT, rtpRoot)'));
    assert.ok(!source.includes("tmplPng = path.join(tilesetsDir, 'dungeon_001.png')"));
});
