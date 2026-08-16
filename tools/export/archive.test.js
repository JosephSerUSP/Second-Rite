'use strict';

const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { collectFiles, createZipFromDirectory } = require('./archive');
const { packDirectory, packLove } = require('./export-game');

function tempDir() {
    return fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-archive-test-'));
}

function write(root, relative, contents) {
    const target = path.join(root, ...relative.split('/'));
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, contents);
}

test('collectFiles uses stable root-relative POSIX archive names', () => {
    const root = tempDir();
    try {
        write(root, 'main.lua', 'return true\n');
        write(root, 'data/maps/one.json', '{}\n');
        write(root, 'assets/águas/névoa.txt', 'mist\n');
        assert.deepEqual(
            collectFiles(root).map(file => file.relative),
            ['assets/águas/névoa.txt', 'data/maps/one.json', 'main.lua']
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('createZipFromDirectory puts staged contents at archive root and preserves unicode names', async () => {
    const root = tempDir();
    const out = tempDir();
    try {
        write(root, 'main.lua', 'print("boot")\n');
        write(root, 'data/maps/one.json', '{"id":1}\n');
        write(root, 'assets/águas/névoa.txt', 'mist\n');
        const target = path.join(out, 'fixture.love');
        const result = await createZipFromDirectory(root, target);

        assert.deepEqual(result.entries, ['assets/águas/névoa.txt', 'data/maps/one.json', 'main.lua']);
        const bytes = fs.readFileSync(target);
        assert.equal(bytes.subarray(0, 4).toString('hex'), '504b0304', 'ZIP local header');
        for (const name of result.entries) {
            assert.ok(bytes.includes(Buffer.from(name, 'utf8')), `archive contains UTF-8 entry name ${name}`);
        }
        assert.ok(bytes.includes(Buffer.from('504b0506', 'hex')), 'ZIP has end-of-central-directory record');
        assert.equal(bytes.includes(Buffer.from(path.basename(root) + '/')), false,
            'source directory itself is not wrapped around .love contents');
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
        fs.rmSync(out, { recursive: true, force: true });
    }
});

test('export packLove and packDirectory use the same Node archive contract', () => {
    const root = tempDir();
    const out = tempDir();
    try {
        write(root, 'main.lua', 'print("boot")\n');
        write(root, 'data/system.json', '{}\n');
        const lovePath = path.join(out, 'fixture.love');
        const zipPath = path.join(out, 'fixture.zip');
        packLove(root, lovePath);
        packDirectory(root, zipPath);
        for (const target of [lovePath, zipPath]) {
            assert.ok(fs.existsSync(target), `${path.basename(target)} exists`);
            assert.equal(fs.readFileSync(target).subarray(0, 4).toString('hex'), '504b0304');
        }
        const exporterSource = fs.readFileSync(path.join(__dirname, 'export-game.js'), 'utf8');
        assert.equal(exporterSource.includes('powershell.exe'), false, 'archive packing no longer spawns PowerShell');
        assert.equal(exporterSource.includes('pack-love.ps1'), false);
        assert.equal(exporterSource.includes('pack-directory.ps1'), false);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
        fs.rmSync(out, { recursive: true, force: true });
    }
});

test('archive failure leaves no successful-looking target', async () => {
    const out = tempDir();
    try {
        const target = path.join(out, 'missing.zip');
        fs.writeFileSync(target, 'stale previous artifact');
        await assert.rejects(
            createZipFromDirectory(path.join(out, 'does-not-exist'), target),
            /Archive source directory is missing/
        );
        assert.equal(fs.existsSync(target), false, 'stale target is removed before replacement begins');
        assert.equal(fs.readdirSync(out).some(name => name.endsWith('.tmp')), false);
    } finally {
        fs.rmSync(out, { recursive: true, force: true });
    }
});
