'use strict';

// Low-level exporter mechanics. Semantic root selection and Project identity
// belong to export-game.js; this module only performs staging, archive, native
// runtime packaging, and build-manifest operations with explicit inputs.
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');
const rtpResources = require('./rtp-resource-resolver');
const rtpPlayerFiles = require('./rtp-player-files');
const runtimeDataCompiler = require('./runtime-data-compiler');

const DEFAULT_MANIFEST = path.join(__dirname, 'runtime-manifest.json');
const DEFAULT_LOVE = path.join('C:', 'Program Files', 'LOVE', 'love.exe');
const WINDOWS_RUNTIME_FILES = ['love.dll', 'lua51.dll', 'mpg123.dll', 'msvcp120.dll', 'msvcr120.dll', 'OpenAL32.dll', 'SDL2.dll'];
const ARCHIVE_HELPER = path.join(__dirname, 'archive.js');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function requireRelativePath(value, label) {
    if (typeof value !== 'string' || !value || path.isAbsolute(value) || value.split(/[\\/]/).includes('..')) {
        throw new Error(`${label} must be a non-empty repository-relative path`);
    }
    return value;
}

function readManifest(manifestPath = DEFAULT_MANIFEST) {
    const manifest = readJson(manifestPath);
    if (manifest.version !== 1) throw new Error(`Unsupported runtime manifest version: ${manifest.version}`);
    for (const key of ['rootFiles', 'runtimeDirectories', 'authoredDataExtensions']) {
        if (!Array.isArray(manifest[key]) || manifest[key].length === 0) throw new Error(`runtime manifest ${key} must be a non-empty array`);
    }
    if (manifest.projectDirectories === undefined) manifest.projectDirectories = [];
    if (!Array.isArray(manifest.projectDirectories)) throw new Error('runtime manifest projectDirectories must be an array');
    manifest.rootFiles.forEach(value => requireRelativePath(value, 'rootFiles entry'));
    manifest.runtimeDirectories.forEach(value => requireRelativePath(value, 'runtimeDirectories entry'));
    manifest.projectDirectories.forEach(value => requireRelativePath(value, 'projectDirectories entry'));
    manifest.authoredDataExtensions.forEach(value => {
        if (typeof value !== 'string' || !value.startsWith('.')) throw new Error(`Invalid authored-data extension: ${value}`);
    });
    requireRelativePath(manifest.releaseConfig, 'releaseConfig');
    return manifest;
}

function copyFile(source, destination) {
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
}

function copyDirectory(source, destination) {
    if (!fs.statSync(source).isDirectory()) throw new Error(`Manifest source directory is missing: ${source}`);
    fs.cpSync(source, destination, { recursive: true, force: true, errorOnExist: false });
}

function copyAuthoredData(source, destination, extensions) {
    for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
        const from = path.join(source, entry.name);
        const to = path.join(destination, entry.name);
        if (entry.isDirectory()) {
            copyAuthoredData(from, to, extensions);
        } else if (entry.isFile() && extensions.includes(path.extname(entry.name).toLowerCase())) {
            copyFile(from, to);
        }
    }
}

function projectDataSource(projectDir) {
    return path.join(projectDir, 'data');
}

function stageGame({ projectDir, runtimeDir, outputDir, manifestPath = DEFAULT_MANIFEST,
        rtpRoot, packageContributions } = {}) {
    if (!projectDir || !runtimeDir || !outputDir) {
        throw new Error('stageGame requires projectDir, runtimeDir, and outputDir');
    }
    const manifest = readManifest(manifestPath);
    const stageDir = path.resolve(outputDir);
    const sourceData = projectDataSource(projectDir);
    if (!fs.existsSync(sourceData) || !fs.statSync(sourceData).isDirectory()) {
        throw new Error(`Project authored data is missing: ${sourceData}`);
    }
    const systemResource = rtpResources.projectSystem(projectDir);
    const soundsResource = rtpResources.sounds({
        projectDir,
        systemValue: systemResource.value,
        rtpRoot,
        packageContributions,
    });

    fs.rmSync(stageDir, { recursive: true, force: true });
    fs.mkdirSync(stageDir, { recursive: true });
    for (const relative of manifest.rootFiles) copyFile(path.join(runtimeDir, relative), path.join(stageDir, relative));
    for (const relative of manifest.runtimeDirectories) copyDirectory(path.join(runtimeDir, relative), path.join(stageDir, relative));
    for (const relative of manifest.projectDirectories) copyDirectory(path.join(projectDir, relative), path.join(stageDir, relative));
    copyFile(path.join(runtimeDir, manifest.releaseConfig), path.join(stageDir, 'conf.lua'));

    const stagedData = path.join(stageDir, 'data');
    copyAuthoredData(sourceData, stagedData, manifest.authoredDataExtensions);
    if (soundsResource) copyFile(soundsResource.sourcePath, path.join(stageDir, soundsResource.logicalPath));
    const inheritedPlayerFiles = rtpPlayerFiles.materialize({
        stageDir,
        projectDir,
        systemValue: systemResource.value,
        rtpRoot,
    });
    return {
        stageDir,
        manifest,
        projectDir: path.resolve(projectDir),
        runtimeDir: path.resolve(runtimeDir),
        resolvedResources: { system: systemResource, sounds: soundsResource, fonts: inheritedPlayerFiles.fonts },
    };
}

function stageRuntimeGame(options = {}) {
    const staged = stageGame(options);
    staged.runtimeData = runtimeDataCompiler.compileRuntimeStage({ stageDir: staged.stageDir });
    return staged;
}

function preflight({ projectDir, lovecPath } = {}) {
    if (!projectDir || !lovecPath) throw new Error('preflight requires projectDir and lovecPath');
    if (!fs.existsSync(lovecPath)) throw new Error(`lovec.exe not found at ${lovecPath} (set LOVEC_PATH)`);
    const result = childProcess.spawnSync(lovecPath, ['.', 'validate'], { cwd: projectDir, encoding: 'utf8', windowsHide: true });
    const output = `${result.stdout || ''}${result.stderr || ''}`;
    if (result.status !== 0 || !output.includes('VALIDATE OK')) throw new Error(`Export preflight failed:\n${output.trim()}`);
}

function runArchive(sourceDir, targetPath, label) {
    const result = childProcess.spawnSync(process.execPath, [ARCHIVE_HELPER, sourceDir, targetPath], {
        encoding: 'utf8',
        windowsHide: true,
    });
    if (result.status !== 0 || !fs.existsSync(targetPath)) {
        throw new Error(`Could not create ${label}:\n${result.stderr || result.stdout || ''}`);
    }
}

function packLove(stageDir, lovePath) {
    runArchive(stageDir, lovePath, '.love archive');
}

function packDirectory(sourceDir, zipPath) {
    runArchive(sourceDir, zipPath, 'distribution ZIP');
}

function effekseerRequired(runtimeRoot) {
    const animations = readJson(path.join(runtimeRoot, 'data', 'animations.json'));
    return JSON.stringify(animations).includes('"effekseer"');
}

function projectNeedsEffekseer(projectDir) {
    const file = path.join(projectDataSource(projectDir), 'animations.json');
    if (!fs.existsSync(file)) return false;
    return JSON.stringify(readJson(file)).includes('"effekseer"');
}

function declaredEffekseerSymbols(runtimeDir) {
    if (!runtimeDir) throw new Error('declaredEffekseerSymbols requires runtimeDir');
    const source = fs.readFileSync(path.join(runtimeDir, 'presentation', 'effekseer.lua'), 'utf8');
    const names = [...source.matchAll(/\b(efk_[A-Za-z0-9_]+)\s*\(/g)].map(m => m[1]);
    const unique = [...new Set(names)];
    if (!unique.length) throw new Error('Could not read any efk_* symbols from presentation/effekseer.lua');
    return unique;
}

function readDllExports(dllPath) {
    const buffer = fs.readFileSync(dllPath);
    const fail = (why) => { throw new Error(`${path.basename(dllPath)} is not a readable DLL: ${why}`); };
    if (buffer.length < 0x40 || buffer.readUInt16LE(0) !== 0x5a4d) fail('missing MZ header');
    const peOffset = buffer.readUInt32LE(0x3c);
    if (peOffset + 24 > buffer.length || buffer.readUInt32LE(peOffset) !== 0x00004550) fail('missing PE signature');

    const sectionCount = buffer.readUInt16LE(peOffset + 6);
    const optionalSize = buffer.readUInt16LE(peOffset + 20);
    const optionalOffset = peOffset + 24;
    const magic = buffer.readUInt16LE(optionalOffset);
    const directoryOffset = optionalOffset + (magic === 0x20b ? 112 : 96);
    if (directoryOffset + 8 > buffer.length) fail('truncated optional header');
    const exportRva = buffer.readUInt32LE(directoryOffset);
    if (!exportRva) return [];

    const sections = [];
    const sectionBase = optionalOffset + optionalSize;
    for (let i = 0; i < sectionCount; i += 1) {
        const entry = sectionBase + i * 40;
        if (entry + 40 > buffer.length) fail('truncated section table');
        sections.push({
            virtualAddress: buffer.readUInt32LE(entry + 12),
            rawSize: buffer.readUInt32LE(entry + 16),
            rawOffset: buffer.readUInt32LE(entry + 20),
        });
    }
    const toOffset = (rva) => {
        for (const s of sections) {
            if (rva >= s.virtualAddress && rva < s.virtualAddress + s.rawSize) return s.rawOffset + (rva - s.virtualAddress);
        }
        return -1;
    };

    const table = toOffset(exportRva);
    if (table < 0 || table + 40 > buffer.length) fail('export directory outside every section');
    const nameCount = buffer.readUInt32LE(table + 24);
    const namePointers = toOffset(buffer.readUInt32LE(table + 32));
    if (namePointers < 0) fail('export name table outside every section');

    const names = [];
    for (let i = 0; i < nameCount; i += 1) {
        const pointer = namePointers + i * 4;
        if (pointer + 4 > buffer.length) fail('truncated export name table');
        const start = toOffset(buffer.readUInt32LE(pointer));
        if (start < 0) continue;
        let end = start;
        while (end < buffer.length && buffer[end] !== 0) end += 1;
        names.push(buffer.toString('ascii', start, end));
    }
    return names;
}

function verifyShim(shimPath, runtimeDir) {
    if (!runtimeDir) throw new Error('verifyShim requires runtimeDir');
    const exported = new Set(readDllExports(shimPath));
    const missing = declaredEffekseerSymbols(runtimeDir).filter(name => !exported.has(name));
    if (missing.length) {
        throw new Error(`${path.basename(shimPath)} is out of date: it does not export ${missing.join(', ')}. `
            + 'Rebuild it with tools/effekseer/build.ps1.');
    }
    return exported.size;
}

function requiredWindowsRuntime(loveExe) {
    const root = path.dirname(loveExe);
    const files = [loveExe, ...WINDOWS_RUNTIME_FILES.map(name => path.join(root, name)), path.join(root, 'license.txt')];
    const missing = files.filter(filePath => !fs.existsSync(filePath));
    if (missing.length) throw new Error(`LÖVE runtime is incomplete; missing: ${missing.join(', ')}`);
    return files;
}

function appendFile(source, destination) {
    fs.appendFileSync(destination, fs.readFileSync(source));
}

function windowsPreflight({ stageDir, runtimeDir, loveExe = process.env.LOVE_PATH || DEFAULT_LOVE, shimPath } = {}) {
    if (!stageDir || !runtimeDir) throw new Error('windowsPreflight requires stageDir and runtimeDir');
    const effectiveShimPath = shimPath || path.join(runtimeDir, 'effekseer_shim.dll');
    const runtime = requiredWindowsRuntime(loveExe);
    const needsShim = effekseerRequired(stageDir);
    if (needsShim) {
        if (!fs.existsSync(effectiveShimPath)) {
            throw new Error(`effekseer_shim.dll is required by authored animations but is missing at ${effectiveShimPath}. Build it with tools/effekseer/build.ps1.`);
        }
        verifyShim(effectiveShimPath, runtimeDir);
    }
    return { runtime, needsShim, shimPath: effectiveShimPath };
}

function exportWindows({ runtimeDir, stageDir, outputDir, lovePath,
        loveExe = process.env.LOVE_PATH || DEFAULT_LOVE, shimPath, metadata, smoke = true } = {}) {
    if (!runtimeDir || !stageDir || !outputDir || !lovePath || !metadata) {
        throw new Error('exportWindows requires runtimeDir, stageDir, outputDir, lovePath, and metadata');
    }
    if (!fs.existsSync(path.join(stageDir, 'main.lua'))) throw new Error(`Staged game is missing main.lua: ${stageDir}`);
    if (!fs.existsSync(lovePath)) throw new Error(`Staged .love archive is missing: ${lovePath}`);
    const preflightResult = windowsPreflight({ stageDir, runtimeDir, loveExe, shimPath });

    const playerDir = path.resolve(outputDir);
    fs.rmSync(playerDir, { recursive: true, force: true });
    fs.mkdirSync(playerDir, { recursive: true });
    const executableName = `${metadata.executableName}.exe`;
    const executable = path.join(playerDir, executableName);
    copyFile(loveExe, executable);
    appendFile(lovePath, executable);
    for (const filePath of preflightResult.runtime.slice(1, -1)) copyFile(filePath, path.join(playerDir, path.basename(filePath)));
    if (preflightResult.needsShim) copyFile(preflightResult.shimPath, path.join(playerDir, 'effekseer_shim.dll'));
    copyFile(preflightResult.runtime[preflightResult.runtime.length - 1], path.join(playerDir, 'LICENSES', 'LOVE-license.txt'));
    fs.writeFileSync(path.join(playerDir, 'THIRD_PARTY_NOTICES.txt'),
        'This distribution bundles the LÖVE runtime. Its license is included in LICENSES/LOVE-license.txt.\n' +
        (preflightResult.needsShim ? 'It also bundles the project Effekseer shim; see tools/effekseer/README.md in the source project for its build provenance.\n' : ''), 'utf8');
    if (smoke) {
        const result = childProcess.spawnSync(executable, ['validate'], { cwd: playerDir, encoding: 'utf8', windowsHide: true, timeout: 60000 });
        if (result.status !== 0) throw new Error(`Exported executable smoke test failed:\n${result.stderr || result.stdout || ''}`);
    }
    return { playerDir, executable, needsShim: preflightResult.needsShim };
}

function countFiles(dir) {
    let total = 0;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (entry.isDirectory()) total += countFiles(path.join(dir, entry.name));
        else if (entry.isFile()) total += 1;
    }
    return total;
}

function geometryPrebakeSummary(stageDir) {
    const manifestPath = path.join(stageDir, 'assets', 'generated', 'geometry', 'manifest.json');
    if (!fs.existsSync(manifestPath)) return null;
    const manifest = readJson(manifestPath);
    return {
        entries: Array.isArray(manifest.entries) ? manifest.entries.length : 0,
        formatVersion: manifest.formatVersion,
        compilerVersion: manifest.compilerVersion,
        quality: manifest.quality,
        geometryClass: manifest.geometryClass,
    };
}

function gitProvenance(projectDir) {
    const run = (args) => {
        const result = childProcess.spawnSync('git', args, { cwd: projectDir, encoding: 'utf8', windowsHide: true });
        if (result.status !== 0) return null;
        return (result.stdout || '').trim();
    };
    const commit = run(['rev-parse', 'HEAD']);
    if (commit === null) return { sourceCommit: null, dirty: null, note: 'git metadata unavailable' };
    const status = run(['status', '--porcelain']);
    return { sourceCommit: commit, dirty: status === null ? null : status.length > 0 };
}

function loveRuntimeVersion(loveExe) {
    const candidates = [path.join(path.dirname(loveExe), 'lovec.exe'), loveExe];
    for (const exe of candidates) {
        if (!fs.existsSync(exe)) continue;
        const result = childProcess.spawnSync(exe, ['--version'], { encoding: 'utf8', windowsHide: true, timeout: 15000 });
        const text = `${result.stdout || ''}${result.stderr || ''}`.trim();
        const match = /LOVE\s+([0-9][^\s(]*)/i.exec(text);
        if (match) return match[1];
    }
    return null;
}

function writeBuildManifest({ outputDir, metadata, target, stageDir, loveExe, projectDir } = {}) {
    if (!outputDir || !metadata || !target || !stageDir || !projectDir) {
        throw new Error('writeBuildManifest requires outputDir, metadata, target, stageDir, and projectDir');
    }
    const provenance = gitProvenance(projectDir);
    const manifest = Object.assign({
        product: metadata.productName,
        productVersion: metadata.productVersion,
        target,
        loveRuntime: loveRuntimeVersion(loveExe),
        createdAt: new Date().toISOString(),
        files: countFiles(stageDir),
        geometryPrebake: geometryPrebakeSummary(stageDir),
    }, provenance);
    const manifestPath = path.join(outputDir, 'build-manifest.json');
    fs.mkdirSync(outputDir, { recursive: true });
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n', 'utf8');
    return { manifestPath, manifest };
}

module.exports = {
    copyAuthoredData,
    declaredEffekseerSymbols,
    effekseerRequired,
    exportWindows,
    geometryPrebakeSummary,
    packDirectory,
    packLove,
    preflight,
    projectDataSource,
    projectNeedsEffekseer,
    readDllExports,
    readManifest,
    requiredWindowsRuntime,
    stageGame,
    stageRuntimeGame,
    verifyShim,
    windowsPreflight,
    writeBuildManifest,
};
