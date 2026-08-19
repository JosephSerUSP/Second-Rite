'use strict';

// Structured map -> .blend authoring export.
//
// LÖVE remains the geometry authority. This tool submits the authored Map JSON
// through the same compileRenderable() bridge used by Thestra Studio's Three
// viewport, writes the neutral bundle to a temporary file, and asks Blender to
// materialize one selectable object per bundle surface with source provenance.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

function safeName(value) {
    const cleaned = String(value || 'map')
        .replace(/[\x00-\x20<>:"/\\|?*]+/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '');
    return cleaned || 'map';
}

function repoServices() {
    const projectRoot = require('../../studio/editor/project-root');
    const { compileRenderable } = require('../../studio/editor/runtime-bridge-server');
    return { projectRoot, compileRenderable };
}

function resolveMapPath(value, root) {
    if (!root) root = repoServices().projectRoot.PROJECT_ROOT;
    const direct = path.resolve(root, value);
    if (fs.existsSync(direct) && fs.statSync(direct).isFile()) return direct;
    const byId = path.join(root, 'data', 'maps', `${value}.json`);
    if (fs.existsSync(byId) && fs.statSync(byId).isFile()) return byId;
    throw new Error(`map '${value}' is neither a JSON file nor data/maps/${value}.json`);
}

function readMap(value, root) {
    if (!root) root = repoServices().projectRoot.PROJECT_ROOT;
    const file = resolveMapPath(value, root);
    const map = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (!map || typeof map !== 'object' || Array.isArray(map)) {
        throw new Error(`map file did not contain an object: ${file}`);
    }
    if (map.id === undefined || map.id === null || map.id === '') {
        throw new Error(`map file needs an id: ${file}`);
    }
    return { file, map };
}

function defaultOutput(map, root) {
    if (!root) root = repoServices().projectRoot.PROJECT_ROOT;
    const id = safeName(map.id);
    const name = safeName(map.name || map.title || `map_${id}`);
    return path.join(root, 'exports', 'maps', `${id}-${name}.blend`);
}

function blenderExecutable(env = process.env) {
    return env.BLENDER_PATH || 'blender';
}

async function exportMapBlend(options) {
    const services = options.services || repoServices();
    const root = path.resolve(options.projectRoot || services.projectRoot.PROJECT_ROOT);
    const { map } = readMap(options.map, root);
    const output = options.output
        ? (path.isAbsolute(options.output) ? options.output : path.resolve(root, options.output))
        : defaultOutput(map, root);
    const seed = options.seed === undefined ? 1735689600 : Number(options.seed);
    if (!Number.isFinite(seed)) throw new Error('seed must be numeric');

    const bundle = await (options.compileRenderable || services.compileRenderable)(
        { map, seed },
        { projectRoot: root, installRoot: options.installRoot || services.projectRoot.INSTALL_ROOT }
    );

    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-map-blend-'));
    const bundlePath = path.join(tempDir, 'renderable-bundle.json');
    fs.writeFileSync(bundlePath, JSON.stringify(bundle));
    fs.mkdirSync(path.dirname(output), { recursive: true });

    const blender = options.blender || blenderExecutable();
    const importer = path.join(__dirname, 'import_map_bundle.py');
    const run = options.execFileSync || execFileSync;
    try {
        run(blender, [
            '--background',
            '--factory-startup',
            '--python', importer,
            '--', bundlePath, output, root,
        ], { stdio: 'inherit', cwd: root });
    } catch (error) {
        if (error && error.code === 'ENOENT') {
            throw new Error(`Blender executable not found (${blender}); set BLENDER_PATH to blender.exe`);
        }
        throw error;
    } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
    }
    return output;
}

function parseArgs(argv) {
    const args = argv.slice();
    const result = { map: null, output: null, seed: undefined, projectRoot: undefined };
    while (args.length) {
        const arg = args.shift();
        if (arg === '--output') result.output = args.shift();
        else if (arg === '--seed') result.seed = args.shift();
        else if (arg === '--project-root') result.projectRoot = args.shift();
        else if (!result.map) result.map = arg;
        else throw new Error(`unexpected argument: ${arg}`);
    }
    if (!result.map) {
        throw new Error(
            'usage: node tools/blender/export_map_blend.js <map-id-or-json> '
            + '[--output file.blend] [--seed N] [--project-root DIR]'
        );
    }
    return result;
}

if (require.main === module) {
    exportMapBlend(parseArgs(process.argv.slice(2)))
        .then(output => console.log(`Wrote ${output}`))
        .catch(error => {
            console.error(error.message || error);
            process.exitCode = 1;
        });
}

module.exports = {
    safeName,
    repoServices,
    resolveMapPath,
    readMap,
    defaultOutput,
    blenderExecutable,
    parseArgs,
    exportMapBlend,
};
