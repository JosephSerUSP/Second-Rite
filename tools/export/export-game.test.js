'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { campaignNeedsEffekseer, exportWindows, stageGame } = require('./export-game');

function write(filePath, contents = '') {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, contents);
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
