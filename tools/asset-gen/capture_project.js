#!/usr/bin/env node
'use strict';

// Capture exact Project Map frames through the real headless engine preview.
// This is evidence tooling, not a second renderer: preview-map owns the
// camera, raycaster, sprites and presentation composition.

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const childProcess = require('child_process');
const lifecycle = require('../../studio/editor/project-lifecycle');
const projectPlay = require('../../studio/editor/project-play');

function usage() {
    return [
        'Usage:',
        '  node tools/asset-gen/capture_project.js --project <root> \\',
        '    --capture <id>=<mapId>,<x>,<y>,<dir> [--capture ...]',
        '',
        'Captures are written beneath <root>/art/review/captures by default.',
        'Set LOVEC_PATH when lovec.exe is not at the Windows default.',
    ].join('\n');
}

function parse(argv) {
    let project = null;
    let out = 'art/review/captures';
    const captures = [];
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === '--project') project = argv[++i];
        else if (arg === '--out') out = argv[++i];
        else if (arg === '--capture') captures.push(argv[++i]);
        else if (arg === '--help' || arg === '-h') return { help: true };
        else throw new Error(`unknown argument: ${arg}`);
    }
    if (!project) throw new Error('--project is required');
    if (!captures.length) throw new Error('at least one --capture is required');
    return { project: path.resolve(project), out, captures };
}

function inside(root, candidate, label) {
    const base = path.resolve(root);
    const target = path.resolve(candidate);
    if (target !== base && !target.startsWith(base + path.sep)) {
        throw new Error(`${label} must stay inside Project root: ${target}`);
    }
    return target;
}

function parseCapture(value) {
    const [id, coordinates] = String(value).split('=', 2);
    const fields = String(coordinates || '').split(',');
    if (!id || fields.length !== 4) throw new Error(`invalid --capture: ${value}`);
    const [mapId, x, y, dir] = fields;
    if (!/^\d+$/.test(mapId) || !/^\d+$/.test(x) || !/^\d+$/.test(y) || !/^[NESW]$/.test(dir)) {
        throw new Error(`--capture wants id=mapId,x,y,dir: ${value}`);
    }
    return { id, mapId, x, y, dir };
}

function sha256(data) {
    return crypto.createHash('sha256').update(data).digest('hex');
}

function decodePreview(stdout) {
    const begin = stdout.lastIndexOf('PREVIEW BEGIN');
    const end = stdout.lastIndexOf('PREVIEW END');
    if (begin < 0 || end < begin) throw new Error('lovec preview did not return PREVIEW markers');
    const json = stdout.slice(begin + 'PREVIEW BEGIN'.length, end).trim();
    const payload = JSON.parse(json);
    if (payload.error) throw new Error(payload.error);
    if (!payload.image) throw new Error('lovec preview returned no image');
    return Buffer.from(payload.image, 'base64');
}

function captureOne(stage, request, executable) {
    const result = childProcess.spawnSync(executable, [
        '.', 'preview-map', request.mapId, request.x, request.y, request.dir,
    ], {
        cwd: stage,
        encoding: 'utf8',
        maxBuffer: 64 * 1024 * 1024,
        windowsHide: true,
    });
    if (result.error) throw result.error;
    if (result.status !== 0) {
        throw new Error(`lovec preview failed for ${request.id} (${result.status}): ${result.stderr || result.stdout}`);
    }
    return decodePreview(result.stdout || '');
}

function run(argv = process.argv.slice(2)) {
    const args = parse(argv);
    if (args.help) {
        process.stdout.write(usage() + '\n');
        return 0;
    }
    const info = lifecycle.projectInfo(args.project);
    const projectRoot = info.projectRoot;
    const outputRoot = inside(projectRoot, path.join(projectRoot, args.out), 'capture output');
    const requests = args.captures.map(parseCapture);
    const executable = process.env.LOVEC_PATH || 'C:\\Program Files\\LOVE\\lovec.exe';
    if (path.isAbsolute(executable) && !fs.existsSync(executable)) {
        throw new Error(`lovec not found at ${executable} (set LOVEC_PATH)`);
    }

    const rows = [];
    let stage = null;
    try {
        stage = projectPlay.stageProject({ installRoot: info.installRoot, projectRoot });
        for (const request of requests) {
            const bytes = captureOne(stage, request, executable);
            const output = inside(outputRoot, path.join(outputRoot, `${request.id}.png`), 'capture path');
            fs.mkdirSync(path.dirname(output), { recursive: true });
            fs.writeFileSync(output, bytes);
            rows.push({
                id: request.id,
                mapId: Number(request.mapId),
                camera: { x: Number(request.x), y: Number(request.y), dir: request.dir },
                path: path.relative(projectRoot, output).replace(/\\/g, '/'),
                sha256: sha256(bytes),
            });
        }
    } finally {
        projectPlay.removeStage(stage);
    }

    const manifestPath = inside(projectRoot, path.join(projectRoot, 'art/review/in-engine-captures.json'), 'capture manifest');
    const manifest = {
        manifestKind: 'project_engine_capture',
        manifestVersion: 1,
        command: 'node tools/asset-gen/capture_project.js --project <project-root> --capture <id>=<mapId>,<x>,<y>,<dir>',
        renderer: 'lovec . preview-map (real Project staging/runtime/raycaster path)',
        projectRoot: '.',
        captures: rows,
    };
    fs.mkdirSync(path.dirname(manifestPath), { recursive: true });
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n', 'utf8');
    for (const row of rows) process.stdout.write(`wrote ${row.path} (${row.sha256})\n`);
    process.stdout.write(`wrote ${path.relative(projectRoot, manifestPath).replace(/\\/g, '/')}\n`);
    return 0;
}

if (require.main === module) {
    try {
        process.exitCode = run();
    } catch (error) {
        process.stderr.write(`${error.message}\n${usage()}\n`);
        process.exitCode = 1;
    }
}

module.exports = { decodePreview, parse, parseCapture, run };
