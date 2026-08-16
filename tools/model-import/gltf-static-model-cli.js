#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { hashBundle, normalizeFile, serializeBundle } = require('./gltf-static-model');

function usage() {
    return [
        'Usage:',
        '  node tools/model-import/gltf-static-model-cli.js <input.glb|input.gltf>',
        '    --out <bundle.json>',
        '    --meters-to-map-cells <positive-number>',
        '    [--source-path <portable/project-relative-source-path>]',
        '',
        'This is an authoring spike. It writes a standalone normalized bundle only;',
        'it does not mutate Project data, model fields, or runtime asset authority.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = argv.slice();
    if (args.includes('--help') || args.includes('-h')) return { help: true };
    const input = args.shift();
    if (!input || input.startsWith('-')) throw new Error('input glTF/GLB path is required');

    const options = { input };
    while (args.length) {
        const flag = args.shift();
        const value = args.shift();
        if (!value || value.startsWith('--')) throw new Error(`${flag} requires a value`);
        if (flag === '--out') options.out = value;
        else if (flag === '--meters-to-map-cells') options.metersToMapCells = Number(value);
        else if (flag === '--source-path') options.sourcePath = value;
        else throw new Error(`unknown option: ${flag}`);
    }

    if (!options.out) throw new Error('--out is required');
    if (!Number.isFinite(options.metersToMapCells) || options.metersToMapCells <= 0) {
        throw new Error('--meters-to-map-cells must be a finite positive number');
    }
    return options;
}

function writeAtomic(target, contents) {
    const resolved = path.resolve(target);
    const dir = path.dirname(resolved);
    fs.mkdirSync(dir, { recursive: true });
    const temporary = `${resolved}.tmp-${process.pid}`;
    try {
        fs.writeFileSync(temporary, contents, 'utf8');
        fs.renameSync(temporary, resolved);
    } catch (error) {
        fs.rmSync(temporary, { force: true });
        throw error;
    }
    return resolved;
}

async function main(argv = process.argv.slice(2)) {
    const options = parseArgs(argv);
    if (options.help) {
        console.log(usage());
        return 0;
    }

    const bundle = await normalizeFile(path.resolve(options.input), {
        metersToMapCells: options.metersToMapCells,
        sourcePath: options.sourcePath === undefined
            ? path.basename(options.input)
            : options.sourcePath,
    });
    const output = writeAtomic(options.out, serializeBundle(bundle));
    const summary = {
        output,
        bundleHash: hashBundle(bundle),
        vertices: bundle.model.vertexCount,
        groups: bundle.model.groups.length,
        materials: bundle.materials.length,
        degradedDiagnostics: bundle.diagnostics.length,
    };
    console.log(JSON.stringify(summary, null, 2));
    return 0;
}

if (require.main === module) {
    main().then(code => {
        process.exitCode = code;
    }).catch(error => {
        console.error(`glTF static spike failed: ${error.message}`);
        process.exitCode = 1;
    });
}

module.exports = { main, parseArgs, usage, writeAtomic };
