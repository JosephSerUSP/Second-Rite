'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { stageGame } = require('./export-game');
const { RUNTIME_RESOURCES, materializeRuntimeData } = require('./runtime-data-snapshot');

const ROOT = path.resolve(__dirname, '..', '..');
const EXTERNAL_PROJECT = path.join(ROOT, 'projects', 'labs', 'scene-benchmarks');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeLoaderSmoke(stageDir) {
    fs.writeFileSync(path.join(stageDir, 'main.lua'), `
local loader = require("data.loader")

function love.load()
    local ok, err = pcall(loader.init)
    if not ok then
        print("RUNTIME SNAPSHOT SMOKE FAIL: " .. tostring(err))
        love.event.quit(1)
        return
    end
    local expected = "runtime_snapshot"
    if loader.unitsStorage ~= expected or loader.mapsStorage ~= expected
            or loader.flowsStorage ~= expected or loader.scenesStorage ~= expected
            or loader.tilesetsStorage ~= expected then
        print("RUNTIME SNAPSHOT SMOKE FAIL: wrong storage modes "
            .. tostring(loader.unitsStorage) .. "/" .. tostring(loader.mapsStorage) .. "/"
            .. tostring(loader.flowsStorage) .. "/" .. tostring(loader.scenesStorage) .. "/"
            .. tostring(loader.tilesetsStorage))
        love.event.quit(2)
        return
    end
    print("RUNTIME SNAPSHOT SMOKE OK")
    love.event.quit(0)
end
`, 'utf8');
}

test('resolved external Project stage loads after physical authored storage is removed', { timeout: 120000 }, () => {
    assert.ok(fs.existsSync(path.join(EXTERNAL_PROJECT, 'data', 'system.json')),
        'scene-benchmarks must remain a first-class external Project fixture');

    const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-runtime-snapshot-'));
    const stageDir = path.join(tempRoot, 'stage');
    try {
        // Use the real exporter boundary first. This materializes exact pinned
        // RTP defaults into the external Project stage before the experiment
        // flattens source storage, so the comparison is against current runtime
        // truth rather than an invented fixture-only resolver.
        stageGame({
            runtimeDir: ROOT,
            projectDir: EXTERNAL_PROJECT,
            outputDir: stageDir,
        });

        assert.ok(fs.existsSync(path.join(stageDir, 'data', 'authored_resolution.json')),
            'RTP/default materialization must happen before runtime flattening');
        assert.ok(RUNTIME_RESOURCES.some(stem => fs.existsSync(path.join(stageDir, 'data', stem))),
            'pre-snapshot stage should still contain source-oriented fragment storage');

        const result = materializeRuntimeData({ stageDir });
        const marker = readJson(result.markerPath);
        assert.equal(marker.version, 1);
        assert.equal(marker.materialized, true);

        for (const stem of RUNTIME_RESOURCES) {
            const monolith = path.join(stageDir, 'data', `${stem}.json`);
            assert.ok(fs.existsSync(monolith), `${stem} runtime monolith must exist`);
            assert.ok(!fs.existsSync(path.join(stageDir, 'data', stem)),
                `${stem} source storage directory must be absent from materialized stage`);
            assert.deepEqual(readJson(monolith), result.resources[stem],
                `${stem} runtime monolith must equal the resolved pre-removal value`);
            assert.equal(marker.resources[stem].runtimePath, `data/${stem}.json`);
            assert.ok(Array.isArray(marker.resources[stem].sources));
        }

        assert.ok(!fs.existsSync(path.join(stageDir, 'data', 'authored_storage.lua')),
            'materialized player must not retain physical Lua fragment parser');
        assert.ok(!fs.existsSync(path.join(stageDir, 'data', 'authored_storage_manifest.json')),
            'materialized player must not retain source storage schema');
        assert.ok(fs.existsSync(path.join(stageDir, 'data', 'authored_storage_resolved.lua')),
            'loader-facing resolved membrane remains as the tiny snapshot reader');

        const lovec = process.env.LOVEC;
        if (!lovec) {
            console.log('runtime snapshot loader smoke skipped: LOVEC environment variable is not set');
            return;
        }

        // Replace only the temporary stage entry point with a one-frame loader
        // harness. This deliberately avoids engine.validator, whose job is to
        // inspect authored *source* contracts; the experiment asks the narrower
        // player question: can the real LÖVE loader consume the resolved stage
        // after physical authoring storage has been deleted?
        writeLoaderSmoke(stageDir);
        const smoke = childProcess.spawnSync(lovec, ['.'], {
            cwd: stageDir,
            env: Object.assign({}, process.env, { SDL_AUDIODRIVER: 'dummy' }),
            encoding: 'utf8',
            windowsHide: true,
            timeout: 30000,
        });
        const output = `${smoke.stdout || ''}\n${smoke.stderr || ''}`;
        assert.equal(smoke.status, 0, output);
        assert.match(output, /RUNTIME SNAPSHOT SMOKE OK/, output);
    } finally {
        fs.rmSync(tempRoot, { recursive: true, force: true });
    }
});
