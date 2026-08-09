'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { stageGame } = require('./export-game');

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
