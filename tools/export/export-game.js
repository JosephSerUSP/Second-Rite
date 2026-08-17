#!/usr/bin/env node
'use strict';

// #699 semantic facade over the established exporter mechanics. The internal
// module owns archive/shim/staging implementation; this public boundary owns
// what each root means and materializes player-facing identity from the Project.
const fs = require('fs');
const path = require('path');
const semanticRoots = require('../semantic-roots');
const projectIdentity = require('./project-identity');
const internal = require('./export-game-internal');
const { runGeometryPrebake } = require('./geometry-prebake');

const ROOTS = semanticRoots.resolveSemanticRoots();
const DEFAULT_LOVEC = path.join('C:', 'Program Files', 'LOVE', 'lovec.exe');
const DEFAULT_LOVE = path.join('C:', 'Program Files', 'LOVE', 'love.exe');
const IDENTITY_TOKEN = '__THESTRA_PROJECT_IDENTITY__';
const WINDOW_TITLE_TOKEN = '__THESTRA_PROJECT_WINDOW_TITLE__';

function resolveExportRoots(options = {}) {
    return semanticRoots.resolveSemanticRoots({
        installRoot: options.installRoot || ROOTS.installRoot,
        runtimeRoot: options.runtimeDir || ROOTS.runtimeRoot,
        rtpRoot: options.rtpRoot,
        studioRoot: options.studioRoot || ROOTS.studioRoot,
        projectRoot: options.projectDir || ROOTS.projectRoot,
        env: {},
    });
}

function normalizeStageOptions(options = {}) {
    const roots = resolveExportRoots(options);
    return {
        roots,
        options: Object.assign({}, options, {
            projectDir: roots.projectRoot,
            runtimeDir: roots.runtimeRoot,
            rtpRoot: roots.rtpRoot,
        }),
    };
}

function readBuildMetadata(projectDir = ROOTS.projectRoot) {
    return projectIdentity.readProjectIdentity(projectDir);
}

function materializeReleaseIdentity(stageDir, projectDir) {
    const confPath = path.join(stageDir, 'conf.lua');
    const metadata = readBuildMetadata(projectDir);
    let source = fs.readFileSync(confPath, 'utf8');
    if (!source.includes(IDENTITY_TOKEN) || !source.includes(WINDOW_TITLE_TOKEN)) {
        throw new Error('Installed release config is not the Project-identity template expected by #699');
    }
    source = source.replace(IDENTITY_TOKEN, JSON.stringify(metadata.identity));
    source = source.replace(WINDOW_TITLE_TOKEN, JSON.stringify(metadata.windowTitle));
    if (source.includes('__THESTRA_PROJECT_')) {
        throw new Error('Release config contains an unresolved Project identity token');
    }
    fs.writeFileSync(confPath, source, 'utf8');
    return metadata;
}

function stageGame(options = {}) {
    const normalized = normalizeStageOptions(options);
    const staged = internal.stageGame(normalized.options);
    staged.projectIdentity = materializeReleaseIdentity(staged.stageDir, normalized.roots.projectRoot);
    staged.semanticRoots = normalized.roots;
    return staged;
}

function stageRuntimeGame(options = {}) {
    const normalized = normalizeStageOptions(options);
    const staged = internal.stageRuntimeGame(normalized.options);
    staged.projectIdentity = materializeReleaseIdentity(staged.stageDir, normalized.roots.projectRoot);
    staged.semanticRoots = normalized.roots;
    return staged;
}

function preflight(options = {}) {
    return internal.preflight(Object.assign({}, options, {
        projectDir: options.projectDir || ROOTS.projectRoot,
        lovecPath: options.lovecPath || process.env.LOVEC_PATH || DEFAULT_LOVEC,
    }));
}

function declaredEffekseerSymbols(runtimeDir = ROOTS.runtimeRoot) {
    return internal.declaredEffekseerSymbols(runtimeDir);
}

function verifyShim(shimPath, runtimeDir = ROOTS.runtimeRoot) {
    return internal.verifyShim(shimPath, runtimeDir);
}

function windowsPreflight(options = {}) {
    const runtimeDir = path.resolve(options.runtimeDir || ROOTS.runtimeRoot);
    const shimPath = options.shimPath || path.join(runtimeDir, 'effekseer_shim.dll');
    return internal.windowsPreflight(Object.assign({}, options, {
        projectDir: runtimeDir,
        shimPath,
    }));
}

function exportWindows(options = {}) {
    const projectDir = path.resolve(options.projectDir || ROOTS.projectRoot);
    const runtimeDir = path.resolve(options.runtimeDir || ROOTS.runtimeRoot);
    const shimPath = options.shimPath || path.join(runtimeDir, 'effekseer_shim.dll');
    const metadata = options.metadata || readBuildMetadata(projectDir);
    return internal.exportWindows(Object.assign({}, options, {
        projectDir: runtimeDir,
        shimPath,
        metadata,
    }));
}

function writeBuildManifest(options = {}) {
    return internal.writeBuildManifest(Object.assign({}, options, {
        projectDir: options.projectDir || ROOTS.projectRoot,
    }));
}

function parseArgs(argv) {
    const options = {
        outputDir: path.join(ROOTS.projectRoot, 'dist'),
        projectDir: ROOTS.projectRoot,
        preflight: true,
        pack: true,
        target: 'love',
    };
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === '--output') options.outputDir = path.resolve(argv[++i] || '');
        else if (arg === '--project') options.projectDir = path.resolve(argv[++i] || '');
        else if (arg === '--target') options.target = argv[++i] || '';
        else if (arg === '--skip-preflight') options.preflight = false;
        else if (arg === '--stage-only') options.pack = false;
        else if (arg === '--help') return null;
        else throw new Error(`Unknown argument: ${arg}`);
    }
    return options;
}

function main() {
    const options = parseArgs(process.argv.slice(2));
    if (!options) {
        console.log('Usage: node tools/export/export-game.js [--target love|windows-x64] [--project dir] [--output dir] [--stage-only] [--skip-preflight]');
        return;
    }
    if (!['love', 'windows-x64'].includes(options.target)) throw new Error(`Unsupported export target: ${options.target}`);

    const metadata = readBuildMetadata(options.projectDir);
    const stageDir = path.join(options.outputDir, 'stage');
    const staged = stageRuntimeGame({
        installRoot: ROOTS.installRoot,
        runtimeDir: ROOTS.runtimeRoot,
        rtpRoot: ROOTS.rtpRoot,
        projectDir: options.projectDir,
        outputDir: stageDir,
    });

    if (options.preflight) preflight({ projectDir: staged.stageDir });
    runGeometryPrebake({ stageDir: staged.stageDir });

    if (options.target === 'windows-x64') windowsPreflight({
        stageDir: staged.stageDir,
        runtimeDir: ROOTS.runtimeRoot,
    });

    if (options.pack) {
        const loveExe = process.env.LOVE_PATH || DEFAULT_LOVE;
        const lovePath = path.join(options.outputDir, `${metadata.productName}.love`);
        internal.packLove(staged.stageDir, lovePath);
        writeBuildManifest({
            outputDir: options.outputDir,
            metadata,
            target: options.target,
            stageDir: staged.stageDir,
            loveExe,
            projectDir: options.projectDir,
        });
        if (options.target === 'love') {
            console.log(`EXPORT OK: ${lovePath}`);
        } else {
            const playerDir = path.join(options.outputDir, `${metadata.buildSlug}-windows-x64`);
            const player = exportWindows({
                projectDir: options.projectDir,
                runtimeDir: ROOTS.runtimeRoot,
                stageDir: staged.stageDir,
                outputDir: playerDir,
                lovePath,
                metadata,
            });
            const zipPath = path.join(options.outputDir, `${metadata.buildSlug}-windows-x64.zip`);
            internal.packDirectory(player.playerDir, zipPath);
            console.log(`EXPORT OK: ${zipPath}`);
        }
    } else {
        console.log(`STAGE OK: ${staged.stageDir}`);
    }
}

if (require.main === module) main();

module.exports = {
    ROOTS,
    copyAuthoredData: internal.copyAuthoredData,
    declaredEffekseerSymbols,
    effekseerRequired: internal.effekseerRequired,
    exportWindows,
    geometryPrebakeSummary: internal.geometryPrebakeSummary,
    materializeReleaseIdentity,
    packDirectory: internal.packDirectory,
    packLove: internal.packLove,
    parseArgs,
    preflight,
    projectDataSource: internal.projectDataSource,
    projectNeedsEffekseer: internal.projectNeedsEffekseer,
    readBuildMetadata,
    readDllExports: internal.readDllExports,
    readManifest: internal.readManifest,
    requiredWindowsRuntime: internal.requiredWindowsRuntime,
    resolveExportRoots,
    stageGame,
    stageRuntimeGame,
    verifyShim,
    windowsPreflight,
    writeBuildManifest,
};
