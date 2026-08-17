'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { declaredEffekseerSymbols, exportWindows, projectNeedsEffekseer, readBuildMetadata, readDllExports,
    readManifest, stageGame, verifyShim, writeBuildManifest } = require('./export-game');

function write(filePath, contents = '') {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, contents);
}

const MANIFEST = {
    version: 1,
    rootFiles: ['main.lua'],
    runtimeDirectories: ['engine', 'presentation'],
    projectDirectories: ['assets'],
    authoredDataExtensions: ['.json'],
    releaseConfig: 'tools/export/release-conf.lua'
};

function makeProject(root) {
    write(path.join(root, 'main.lua'), 'return true');
    write(path.join(root, 'engine', 'runtime.lua'), 'return true');
    write(path.join(root, 'presentation', 'draw.lua'), 'return true');
    write(path.join(root, 'assets', 'sprite.png'), 'png');
    write(path.join(root, 'tools', 'export', 'release-conf.lua'), 't.console = false');
    const manifestPath = path.join(root, 'manifest.json');
    write(manifestPath, JSON.stringify(MANIFEST));
    return manifestPath;
}

function makePeWithExports(names) {
    const SECTION_RVA = 0x1000;
    const SECTION_RAW = 0x400;
    const directoryEntry = Buffer.alloc(40);
    const pointers = Buffer.alloc(names.length * 4);
    const strings = [];
    let cursor = 40 + names.length * 4;
    names.forEach((name, i) => {
        pointers.writeUInt32LE(SECTION_RVA + cursor, i * 4);
        const encoded = Buffer.from(name + '\0', 'ascii');
        strings.push(encoded);
        cursor += encoded.length;
    });
    directoryEntry.writeUInt32LE(names.length, 24);
    directoryEntry.writeUInt32LE(SECTION_RVA + 40, 32);
    const section = Buffer.concat([directoryEntry, pointers, ...strings]);

    const buffer = Buffer.alloc(SECTION_RAW + section.length);
    buffer.writeUInt16LE(0x5a4d, 0);
    const peOffset = 0x80;
    buffer.writeUInt32LE(peOffset, 0x3c);
    buffer.writeUInt32LE(0x00004550, peOffset);
    buffer.writeUInt16LE(1, peOffset + 6);
    const optionalSize = 240;
    buffer.writeUInt16LE(optionalSize, peOffset + 20);
    const optionalOffset = peOffset + 24;
    buffer.writeUInt16LE(0x20b, optionalOffset);
    buffer.writeUInt32LE(SECTION_RVA, optionalOffset + 112);
    const sectionHeader = optionalOffset + optionalSize;
    buffer.writeUInt32LE(SECTION_RVA, sectionHeader + 12);
    buffer.writeUInt32LE(section.length, sectionHeader + 16);
    buffer.writeUInt32LE(SECTION_RAW, sectionHeader + 20);
    section.copy(buffer, SECTION_RAW);
    return buffer;
}

test('stageGame copies only manifest runtime files plus Project-owned assets/data', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        const runtime = path.join(root, 'install');
        const project = path.join(root, 'project');
        write(path.join(runtime, 'main.lua'), 'runtime-main');
        write(path.join(runtime, 'engine', 'runtime.lua'), 'runtime-engine');
        write(path.join(runtime, 'presentation', 'draw.lua'), 'runtime-presentation');
        write(path.join(runtime, 'assets', 'sprite.png'), 'wrong-install-asset');
        write(path.join(runtime, 'data', 'json.lua'), 'return {}');
        write(path.join(runtime, 'data', 'loader.lua'), 'return {}');
        write(path.join(runtime, 'data', 'authored_storage.lua'), 'return {}');
        write(path.join(runtime, 'data', 'authored_storage_manifest.json'), '{}');
        write(path.join(runtime, 'tools', 'export', 'release-conf.lua'), 't.console = false');
        write(path.join(project, 'main.lua'), 'wrong-project-main');
        write(path.join(project, 'engine', 'runtime.lua'), 'wrong-project-engine');
        write(path.join(project, 'assets', 'sprite.png'), 'project-asset');
        write(path.join(project, 'data', 'system.json'), '{"id":"project"}');
        write(path.join(project, 'data', 'scenes', 'index.json'), '[]');
        write(path.join(project, 'data', 'notes.txt'), 'do not ship');
        write(path.join(project, 'campaign.json'), '{"active":"stale"}');
        write(path.join(project, 'campaigns', 'stale', 'system.json'), '{"id":"wrong"}');
        const manifestPath = path.join(root, 'manifest.json');
        write(manifestPath, JSON.stringify(MANIFEST));
        const outputDir = path.join(root, 'output');
        stageGame({ runtimeDir: runtime, projectDir: project, outputDir, manifestPath });
        assert.equal(fs.readFileSync(path.join(outputDir, 'main.lua'), 'utf8'), 'runtime-main');
        assert.equal(fs.readFileSync(path.join(outputDir, 'engine', 'runtime.lua'), 'utf8'), 'runtime-engine');
        assert.equal(fs.readFileSync(path.join(outputDir, 'assets', 'sprite.png'), 'utf8'), 'project-asset');
        assert.equal(JSON.parse(fs.readFileSync(path.join(outputDir, 'data', 'system.json'), 'utf8')).id, 'project');
        assert.ok(fs.existsSync(path.join(outputDir, 'data', 'scenes', 'index.json')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'data', 'notes.txt')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'campaign.json')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'campaigns')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'tools')));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('a new unrelated repository file is not exported', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        const manifestPath = makeProject(root);
        write(path.join(root, 'data', 'system.json'), '{}');
        write(path.join(root, 'SECRETS.md'), 'do not ship');
        write(path.join(root, 'analysis', 'notes.json'), '{"internal":true}');
        const outputDir = path.join(root, 'output');
        stageGame({ projectDir: root, outputDir, manifestPath });
        assert.ok(!fs.existsSync(path.join(outputDir, 'SECRETS.md')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'analysis')));
        assert.ok(fs.existsSync(path.join(outputDir, 'data', 'system.json')));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('a manifest entry that escapes the project root is refused', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        for (const bad of [{ rootFiles: ['../outside.lua'] }, { runtimeDirectories: ['engine', '..'] },
                           { projectDirectories: ['../../etc/passwd'] }, { releaseConfig: '/absolute/conf.lua' }]) {
            const manifestPath = path.join(root, 'bad.json');
            write(manifestPath, JSON.stringify(Object.assign({}, MANIFEST, bad)));
            assert.throws(() => readManifest(manifestPath), /repository-relative path/);
        }
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('the retired campaignExtensions manifest key is not accepted as an internal synonym', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        const manifestPath = path.join(root, 'old.json');
        const old = Object.assign({}, MANIFEST);
        delete old.authoredDataExtensions;
        old.campaignExtensions = ['.json'];
        write(manifestPath, JSON.stringify(old));
        assert.throws(() => readManifest(manifestPath), /authoredDataExtensions/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('staging removes files left by a previous build', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        const manifestPath = makeProject(root);
        write(path.join(root, 'data', 'system.json'), '{}');
        const outputDir = path.join(root, 'output');
        write(path.join(outputDir, 'data', 'stale.json'), '{"stale":true}');
        write(path.join(outputDir, 'engine', 'deleted.lua'), 'return {}');
        stageGame({ projectDir: root, outputDir, manifestPath });
        assert.ok(!fs.existsSync(path.join(outputDir, 'data', 'stale.json')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'engine', 'deleted.lua')));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('stale Campaign pointer/root state cannot redirect staged Project data', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        const manifestPath = makeProject(root);
        write(path.join(root, 'data', 'system.json'), '{"root":"project"}');
        write(path.join(root, 'data', 'scenes', 'index.json'), '["project-scene"]');
        write(path.join(root, 'campaigns', 'demo', 'system.json'), '{"root":"stale-campaign"}');
        write(path.join(root, 'campaign.json'), '{"active":"demo"}');
        const outputDir = path.join(root, 'output');
        stageGame({ projectDir: root, outputDir, manifestPath });
        assert.equal(JSON.parse(fs.readFileSync(path.join(outputDir, 'data', 'system.json'), 'utf8')).root, 'project');
        assert.ok(fs.existsSync(path.join(outputDir, 'data', 'scenes', 'index.json')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'campaigns')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'campaign.json')));
        assert.equal(JSON.parse(fs.readFileSync(path.join(root, 'campaigns', 'demo', 'system.json'), 'utf8')).root, 'stale-campaign');
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('build metadata refuses names that could escape the output root', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        const good = path.join(root, 'good.json');
        write(good, JSON.stringify({ version: 1, productName: 'X', executableName: 'X', buildSlug: 'x', productVersion: '1.0' }));
        assert.equal(readBuildMetadata(good).buildSlug, 'x');
        for (const bad of [{ buildSlug: '../escape' }, { executableName: 'a/b' }, { productName: '' }, { version: 2 }]) {
            const file = path.join(root, 'bad.json');
            write(file, JSON.stringify(Object.assign({ version: 1, productName: 'X', executableName: 'X', buildSlug: 'x', productVersion: '1.0' }, bad)));
            assert.throws(() => readBuildMetadata(file));
        }
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('the build manifest records provenance without leaking local paths or Campaign vocabulary', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        const stageDir = path.join(root, 'stage');
        write(path.join(stageDir, 'main.lua'), 'return true');
        write(path.join(stageDir, 'data', 'system.json'), '{}');
        const outputDir = path.join(root, 'out');
        const metadata = { productName: 'Second Rite', productVersion: '0.0.0-dev', executableName: 'Second Rite', buildSlug: 'Second-Rite' };
        const { manifestPath, manifest } = writeBuildManifest({
            outputDir, metadata, target: 'love', stageDir,
            loveExe: path.join(root, 'nonexistent-love.exe'), projectDir: root,
        });
        assert.ok(fs.existsSync(manifestPath));
        assert.equal(manifest.product, 'Second Rite');
        assert.ok(!Object.prototype.hasOwnProperty.call(manifest, 'campaign'));
        assert.equal(manifest.files, 2);
        assert.equal(manifest.loveRuntime, null);
        assert.ok('sourceCommit' in manifest);
        const text = fs.readFileSync(manifestPath, 'utf8');
        assert.ok(!text.includes(root), 'build manifest must not embed local absolute paths');
        assert.ok(!text.includes(os.homedir()), 'build manifest must not embed the home directory');
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('the shim is verified against the symbols the runtime declares', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        write(path.join(root, 'presentation', 'effekseer.lua'),
            'local CDEF = [[\nint efk_init(int a);\nvoid efk_draw_group(int g);\nvoid efk_set_effect_flip(int h);\n]]\n'
            + 'for name in CDEF:gmatch("(efk_[%w_]+)%s*%(") do end\n');
        const symbols = declaredEffekseerSymbols(root);
        assert.deepEqual(symbols.sort(), ['efk_draw_group', 'efk_init', 'efk_set_effect_flip']);

        const current = path.join(root, 'current.dll');
        fs.writeFileSync(current, makePeWithExports(['efk_init', 'efk_draw_group', 'efk_set_effect_flip', 'unrelated']));
        assert.deepEqual(readDllExports(current).sort(),
            ['efk_draw_group', 'efk_init', 'efk_set_effect_flip', 'unrelated']);
        assert.equal(verifyShim(current, root), 4);

        const stale = path.join(root, 'stale.dll');
        fs.writeFileSync(stale, makePeWithExports(['efk_init', 'efk_draw_group']));
        assert.throws(() => verifyShim(stale, root),
            /out of date: it does not export efk_set_effect_flip.*build\.ps1/s);

        const garbage = path.join(root, 'garbage.dll');
        fs.writeFileSync(garbage, Buffer.from('not a dll at all'));
        assert.throws(() => readDllExports(garbage), /not a readable DLL/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('the real shim satisfies the runtime contract when present', { skip: !fs.existsSync(path.join(__dirname, '..', '..', 'effekseer_shim.dll')) }, () => {
    const projectDir = path.join(__dirname, '..', '..');
    const exports = readDllExports(path.join(projectDir, 'effekseer_shim.dll'));
    assert.ok(exports.length > 0, 'real DLL exported no symbols — parser is wrong');
    assert.ok(verifyShim(path.join(projectDir, 'effekseer_shim.dll'), projectDir) > 0);
});

test('projectNeedsEffekseer reads only the Project data root', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        write(path.join(root, 'data', 'animations.json'), '{"a":{"type":"effekseer"}}');
        write(path.join(root, 'campaigns', 'plain', 'animations.json'), '{"a":{"type":"sprite"}}');
        assert.strictEqual(projectNeedsEffekseer(root), true);
        write(path.join(root, 'data', 'animations.json'), '{"a":{"type":"sprite"}}');
        assert.strictEqual(projectNeedsEffekseer(root), false);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('Windows export fails loud when authored Effekseer content has no shim', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        write(path.join(root, 'stage', 'data', 'animations.json'), '{"a":{"type":"effekseer"}}');
        write(path.join(root, 'stage', 'main.lua'), 'return true');
        write(path.join(root, 'game.love'), 'love');
        const runtime = path.join(root, 'love-runtime');
        ['love.exe', 'love.dll', 'lua51.dll', 'mpg123.dll', 'msvcp120.dll', 'msvcr120.dll', 'OpenAL32.dll', 'SDL2.dll', 'license.txt']
            .forEach(name => write(path.join(runtime, name), 'runtime'));
        assert.throws(() => exportWindows({
            projectDir: root,
            stageDir: path.join(root, 'stage'),
            outputDir: path.join(root, 'player'),
            lovePath: path.join(root, 'game.love'),
            loveExe: path.join(runtime, 'love.exe'),
            smoke: false
        }), /effekseer_shim\.dll is required/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('Windows export fuses the archive and copies only declared runtime sidecars', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        write(path.join(root, 'stage', 'main.lua'), 'return true');
        write(path.join(root, 'stage', 'data', 'animations.json'), '{}');
        write(path.join(root, 'game.love'), 'archive-payload');
        const runtime = path.join(root, 'love-runtime');
        ['love.exe', 'love.dll', 'lua51.dll', 'mpg123.dll', 'msvcp120.dll', 'msvcr120.dll', 'OpenAL32.dll', 'SDL2.dll', 'license.txt']
            .forEach(name => write(path.join(runtime, name), name));
        const playerDir = path.join(root, 'player');
        write(path.join(playerDir, 'stale-file.txt'), 'must be removed');
        const result = exportWindows({
            stageDir: path.join(root, 'stage'),
            outputDir: playerDir,
            lovePath: path.join(root, 'game.love'),
            loveExe: path.join(runtime, 'love.exe'),
            smoke: false
        });
        assert.ok(fs.existsSync(result.executable));
        assert.equal(fs.readFileSync(result.executable, 'utf8'), 'love.exearchive-payload');
        assert.ok(fs.existsSync(path.join(playerDir, 'SDL2.dll')));
        assert.ok(fs.existsSync(path.join(playerDir, 'LICENSES', 'LOVE-license.txt')));
        assert.ok(fs.existsSync(path.join(playerDir, 'THIRD_PARTY_NOTICES.txt')));
        assert.ok(!fs.existsSync(path.join(playerDir, 'stale-file.txt')));
        assert.ok(!fs.existsSync(path.join(playerDir, 'lovec.exe')));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
