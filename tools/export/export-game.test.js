'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { campaignNeedsEffekseer, declaredEffekseerSymbols, exportWindows, readBuildMetadata, readDllExports,
    readManifest, stageGame, verifyShim, writeBuildManifest } = require('./export-game');

function write(filePath, contents = '') {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, contents);
}

const MANIFEST = {
    version: 1,
    rootFiles: ['main.lua'],
    runtimeDirectories: ['engine', 'presentation', 'assets'],
    dataRuntimeFiles: ['authored_storage.lua', 'authored_storage_manifest.json', 'json.lua', 'loader.lua'],
    campaignExtensions: ['.json'],
    releaseConfig: 'tools/export/release-conf.lua'
};

// A project laid out the way the real one is, so staging tests exercise the
// shipped manifest's shape rather than a bespoke fixture.
function makeProject(root) {
    write(path.join(root, 'main.lua'), 'return true');
    write(path.join(root, 'engine', 'runtime.lua'), 'return true');
    write(path.join(root, 'presentation', 'draw.lua'), 'return true');
    write(path.join(root, 'assets', 'sprite.png'), 'png');
    for (const name of MANIFEST.dataRuntimeFiles) write(path.join(root, 'data', name), '{}');
    write(path.join(root, 'tools', 'export', 'release-conf.lua'), 't.console = false');
    const manifestPath = path.join(root, 'manifest.json');
    write(manifestPath, JSON.stringify(MANIFEST));
    return manifestPath;
}

// A minimal PE32+ DLL carrying an export name table, so the export-table reader
// is tested deterministically rather than only against a locally built shim.
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
    directoryEntry.writeUInt32LE(names.length, 24);          // NumberOfNames
    directoryEntry.writeUInt32LE(SECTION_RVA + 40, 32);      // AddressOfNames
    const section = Buffer.concat([directoryEntry, pointers, ...strings]);

    const buffer = Buffer.alloc(SECTION_RAW + section.length);
    buffer.writeUInt16LE(0x5a4d, 0);                         // MZ
    const peOffset = 0x80;
    buffer.writeUInt32LE(peOffset, 0x3c);
    buffer.writeUInt32LE(0x00004550, peOffset);              // PE\0\0
    buffer.writeUInt16LE(1, peOffset + 6);                   // one section
    const optionalSize = 240;
    buffer.writeUInt16LE(optionalSize, peOffset + 20);
    const optionalOffset = peOffset + 24;
    buffer.writeUInt16LE(0x20b, optionalOffset);             // PE32+
    buffer.writeUInt32LE(SECTION_RVA, optionalOffset + 112); // data directory 0
    const sectionHeader = optionalOffset + optionalSize;
    buffer.writeUInt32LE(SECTION_RVA, sectionHeader + 12);
    buffer.writeUInt32LE(section.length, sectionHeader + 16);
    buffer.writeUInt32LE(SECTION_RAW, sectionHeader + 20);
    section.copy(buffer, SECTION_RAW);
    return buffer;
}

test('stageGame copies only manifest runtime files and selected campaign JSON', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        write(path.join(root, 'main.lua'), 'return true');
        write(path.join(root, 'engine', 'runtime.lua'), 'return true');
        write(path.join(root, 'presentation', 'draw.lua'), 'return true');
        write(path.join(root, 'assets', 'sprite.png'), 'png');
        write(path.join(root, 'data', 'json.lua'), 'return {}');
        write(path.join(root, 'data', 'loader.lua'), 'return {}');
        write(path.join(root, 'data', 'authored_storage.lua'), 'return {}');
        write(path.join(root, 'data', 'authored_storage_manifest.json'), '{}');
        write(path.join(root, 'campaigns', 'demo', 'system.json'), '{"id":"demo"}');
        write(path.join(root, 'campaigns', 'demo', 'scenes', 'index.json'), '[]');
        write(path.join(root, 'campaigns', 'demo', 'notes.txt'), 'do not ship');
        write(path.join(root, 'tools', 'export', 'release-conf.lua'), 't.console = false');
        const manifest = {
            version: 1,
            rootFiles: ['main.lua'],
            runtimeDirectories: ['engine', 'presentation', 'assets'],
            dataRuntimeFiles: ['authored_storage.lua', 'authored_storage_manifest.json', 'json.lua', 'loader.lua'],
            campaignExtensions: ['.json'],
            releaseConfig: 'tools/export/release-conf.lua'
        };
        const manifestPath = path.join(root, 'manifest.json');
        write(manifestPath, JSON.stringify(manifest));
        const outputDir = path.join(root, 'output');
        stageGame({ projectDir: root, outputDir, campaign: 'demo', manifestPath });
        assert.ok(fs.existsSync(path.join(outputDir, 'main.lua')));
        assert.ok(fs.existsSync(path.join(outputDir, 'conf.lua')));
        assert.ok(fs.existsSync(path.join(outputDir, 'data', 'system.json')));
        assert.ok(fs.existsSync(path.join(outputDir, 'data', 'scenes', 'index.json')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'data', 'notes.txt')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'tools')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'campaigns')));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

// The allowlist's whole point: a file appearing in the repository is not a
// reason for it to appear in a build. This is the regression that a
// blacklist-shaped exporter fails silently.
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
                           { dataRuntimeFiles: ['../../etc/passwd'] }, { releaseConfig: 'C:/absolute/conf.lua' }]) {
            const manifestPath = path.join(root, 'bad.json');
            write(manifestPath, JSON.stringify(Object.assign({}, MANIFEST, bad)));
            assert.throws(() => readManifest(manifestPath), /repository-relative path/);
        }
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
        write(path.join(outputDir, 'data', 'removed-campaign.json'), '{"stale":true}');
        write(path.join(outputDir, 'engine', 'deleted.lua'), 'return {}');
        stageGame({ projectDir: root, outputDir, manifestPath });
        assert.ok(!fs.existsSync(path.join(outputDir, 'data', 'removed-campaign.json')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'engine', 'deleted.lua')));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

// Alternate-campaign materialization: the campaign becomes the build's ordinary
// data/ root, keeping split storage, and the SOURCE is left untouched.
test('an alternate campaign materializes as data/ without mutating the source', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        const manifestPath = makeProject(root);
        write(path.join(root, 'data', 'system.json'), '{"root":"default"}');
        write(path.join(root, 'campaigns', 'demo', 'system.json'), '{"root":"demo"}');
        write(path.join(root, 'campaigns', 'demo', 'scenes', 'index.json'), '["a"]');
        write(path.join(root, 'campaigns', 'demo', 'tilesets', 'cave', 'atlas.json'), '{"id":"cave"}');
        write(path.join(root, 'campaigns', 'other', 'system.json'), '{"root":"other"}');
        write(path.join(root, 'campaign.json'), '{"active":"demo"}');
        const outputDir = path.join(root, 'output');
        stageGame({ projectDir: root, outputDir, campaign: 'demo', manifestPath });

        assert.equal(JSON.parse(fs.readFileSync(path.join(outputDir, 'data', 'system.json'), 'utf8')).root, 'demo');
        // Split collections and keyed registries survive as directories.
        assert.ok(fs.existsSync(path.join(outputDir, 'data', 'scenes', 'index.json')));
        assert.ok(fs.existsSync(path.join(outputDir, 'data', 'tilesets', 'cave', 'atlas.json')));
        // The development campaign-selection structure does not ship.
        assert.ok(!fs.existsSync(path.join(outputDir, 'campaigns')));
        assert.ok(!fs.existsSync(path.join(outputDir, 'campaign.json')));
        // ...and the source campaign is untouched by having been exported.
        assert.equal(JSON.parse(fs.readFileSync(path.join(root, 'campaigns', 'demo', 'system.json'), 'utf8')).root, 'demo');
        assert.equal(JSON.parse(fs.readFileSync(path.join(root, 'data', 'system.json'), 'utf8')).root, 'default');
        assert.equal(JSON.parse(fs.readFileSync(path.join(root, 'campaign.json'), 'utf8')).active, 'demo');
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('build metadata refuses names that could escape the output root', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        const good = path.join(root, 'good.json');
        write(good, JSON.stringify({ version: 1, productName: 'X', executableName: 'X', buildSlug: 'x', productVersion: '1.0', defaultCampaign: '' }));
        assert.equal(readBuildMetadata(good).buildSlug, 'x');
        for (const bad of [{ buildSlug: '../escape' }, { executableName: 'a/b' }, { productName: '' }, { version: 2 }]) {
            const file = path.join(root, 'bad.json');
            write(file, JSON.stringify(Object.assign({ version: 1, productName: 'X', executableName: 'X', buildSlug: 'x', productVersion: '1.0', defaultCampaign: '' }, bad)));
            assert.throws(() => readBuildMetadata(file));
        }
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('the build manifest records provenance without leaking local paths', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        const stageDir = path.join(root, 'stage');
        write(path.join(stageDir, 'main.lua'), 'return true');
        write(path.join(stageDir, 'data', 'system.json'), '{}');
        const outputDir = path.join(root, 'out');
        const metadata = { productName: 'Second Rite', productVersion: '0.0.0-dev', executableName: 'Second Rite', buildSlug: 'Second-Rite' };
        const { manifestPath, manifest } = writeBuildManifest({
            outputDir, metadata, target: 'love', campaign: '', stageDir,
            loveExe: path.join(root, 'nonexistent-love.exe'), projectDir: root,
        });
        assert.ok(fs.existsSync(manifestPath));
        assert.equal(manifest.product, 'Second Rite');
        assert.equal(manifest.campaign, '(default)');
        assert.equal(manifest.files, 2);
        // A missing runtime is reported, not fatal -- same for git metadata,
        // which a temp dir outside any repository cannot supply.
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
        // A stand-in for presentation/effekseer.lua's ffi.cdef block.
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

        // The failure this exists for: loads fine, missing the newest export.
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

// The real shim, when this checkout has one built. Guards the parser against a
// synthetic fixture that agrees with itself but not with a linker.
test('the real shim satisfies the runtime contract when present', { skip: !fs.existsSync(path.join(__dirname, '..', '..', 'effekseer_shim.dll')) }, () => {
    const projectDir = path.join(__dirname, '..', '..');
    const exports = readDllExports(path.join(projectDir, 'effekseer_shim.dll'));
    assert.ok(exports.length > 0, 'real DLL exported no symbols — parser is wrong');
    assert.ok(verifyShim(path.join(projectDir, 'effekseer_shim.dll'), projectDir) > 0);
});

// The editor's export dialog reports the shim requirement before anything is
// staged, so the same question has to be answerable from an unstaged campaign
// root -- including the default data/ one, which is not under campaigns/.
test('campaignNeedsEffekseer reads the unstaged campaign root', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-export-'));
    try {
        write(path.join(root, 'data', 'animations.json'), '{"a":{"type":"effekseer"}}');
        write(path.join(root, 'campaigns', 'plain', 'animations.json'), '{"a":{"type":"sprite"}}');
        fs.mkdirSync(path.join(root, 'campaigns', 'silent'), { recursive: true });
        assert.strictEqual(campaignNeedsEffekseer(root, ''), true);
        assert.strictEqual(campaignNeedsEffekseer(root, 'plain'), false);
        assert.strictEqual(campaignNeedsEffekseer(root, 'silent'), false);
        assert.throws(() => campaignNeedsEffekseer(root, '../escape'), /Invalid campaign name/);
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
