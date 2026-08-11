'use strict';

// Deterministic release geometry transform (#161B).
//
// This runs against an ALREADY MATERIALIZED staging tree. The LÖVE compiler
// therefore sees exactly the campaign/runtime files that will ship, while the
// target packager remains completely geometry-unaware. The staged main.lua is
// replaced only for the duration of the compiler invocation and restored byte
// for byte in a finally block.
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const DEFAULT_LOVEC = path.join('C:', 'Program Files', 'LOVE', 'lovec.exe');
const PREBAKE_RELATIVE = path.join('assets', 'generated', 'geometry');
const ENV_OUTPUT = 'SECOND_RITE_GEOMETRY_PREBAKE_OUTPUT';

const PREBAKE_MAIN = `function love.load()
    local loader = require("data.loader")
    loader.init("data")
    local output = os.getenv("${ENV_OUTPUT}")
    if not output or output == "" then error("${ENV_OUTPUT} is required", 0) end
    local manifest = require("engine.geometry.prebake").run(output, loader)
    print(string.format("GEOMETRY PREBAKE OK entries=%d", #(manifest.entries or {})))
    love.event.quit(0)
end
`;

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function validateGeneratedPrebakes(outputDir) {
    const manifestPath = path.join(outputDir, 'manifest.json');
    if (!fs.existsSync(manifestPath)) throw new Error(`Geometry prebake did not produce ${manifestPath}`);
    const manifest = readJson(manifestPath);
    if (manifest.version !== 1 || !Number.isInteger(manifest.formatVersion)
            || !Number.isInteger(manifest.compilerVersion) || typeof manifest.quality !== 'string'
            || !Array.isArray(manifest.sourceFiles) || !Array.isArray(manifest.entries)) {
        throw new Error('Geometry prebake produced an incompatible manifest');
    }
    const seen = new Set();
    for (const entry of manifest.entries) {
        if (!entry || typeof entry.key !== 'string' || !entry.key
                || typeof entry.file !== 'string' || !/^[a-f0-9]+\.geo$/i.test(entry.file)) {
            throw new Error('Geometry prebake manifest contains an invalid entry');
        }
        if (seen.has(entry.file)) throw new Error(`Geometry prebake manifest repeats ${entry.file}`);
        seen.add(entry.file);
        if (!fs.existsSync(path.join(outputDir, entry.file))) {
            throw new Error(`Geometry prebake artifact is missing: ${entry.file}`);
        }
    }
    return { manifestPath, manifest };
}

function runGeometryPrebake({ stageDir, lovecPath = process.env.LOVEC_PATH || DEFAULT_LOVEC,
        spawnSync = childProcess.spawnSync } = {}) {
    if (!stageDir) throw new Error('runGeometryPrebake requires stageDir');
    const root = path.resolve(stageDir);
    const mainPath = path.join(root, 'main.lua');
    const compilerPath = path.join(root, 'engine', 'geometry', 'prebake.lua');
    if (!fs.existsSync(mainPath)) throw new Error(`Staged game is missing main.lua: ${root}`);
    if (!fs.existsSync(compilerPath)) throw new Error(`Staged game is missing geometry prebaker: ${compilerPath}`);
    if (!fs.existsSync(lovecPath) && spawnSync === childProcess.spawnSync) {
        throw new Error(`lovec.exe not found at ${lovecPath} (set LOVEC_PATH)`);
    }

    const outputDir = path.join(root, PREBAKE_RELATIVE);
    fs.rmSync(outputDir, { recursive: true, force: true });
    fs.mkdirSync(outputDir, { recursive: true });

    const runtimeMain = fs.readFileSync(mainPath);
    let result;
    try {
        fs.writeFileSync(mainPath, PREBAKE_MAIN, 'utf8');
        result = spawnSync(lovecPath, [root], {
            cwd: root,
            encoding: 'utf8',
            windowsHide: true,
            env: Object.assign({}, process.env, {
                // Forward slashes are accepted by Windows io.open and avoid
                // backslash escaping becoming part of a Lua/CLI concern.
                [ENV_OUTPUT]: outputDir.replace(/\\/g, '/'),
            }),
        });
    } finally {
        fs.writeFileSync(mainPath, runtimeMain);
    }

    const output = `${(result && result.stdout) || ''}${(result && result.stderr) || ''}`;
    if (!result || result.status !== 0 || !output.includes('GEOMETRY PREBAKE OK')) {
        throw new Error(`Geometry prebake failed:\n${output.trim() || '(no compiler output)'}`);
    }
    const generated = validateGeneratedPrebakes(outputDir);
    return Object.assign({ outputDir, compilerOutput: output }, generated);
}

function parseArgs(argv) {
    const options = { stageDir: '', lovecPath: process.env.LOVEC_PATH || DEFAULT_LOVEC };
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === '--stage') options.stageDir = argv[++i] || '';
        else if (arg === '--lovec') options.lovecPath = argv[++i] || '';
        else if (arg === '--help' || arg === '-h') return null;
        else throw new Error(`Unknown argument: ${arg}`);
    }
    return options;
}

function main() {
    const options = parseArgs(process.argv.slice(2));
    if (!options) {
        console.log('Usage: node tools/export/geometry-prebake.js --stage <staged-game-root> [--lovec <lovec.exe>]');
        return;
    }
    if (!options.stageDir) throw new Error('--stage is required');
    const result = runGeometryPrebake(options);
    console.log(`Geometry prebake: ${result.manifest.entries.length} artifact(s) -> ${result.outputDir}`);
}

if (require.main === module) {
    try { main(); }
    catch (err) {
        console.error(err && err.stack ? err.stack : String(err));
        process.exitCode = 1;
    }
}

module.exports = {
    ENV_OUTPUT,
    PREBAKE_MAIN,
    PREBAKE_RELATIVE,
    runGeometryPrebake,
    validateGeneratedPrebakes,
};
