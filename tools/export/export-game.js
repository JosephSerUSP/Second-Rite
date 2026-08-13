#!/usr/bin/env node
'use strict';

// Runtime-only game staging. This script intentionally knows nothing about
// the editor's server or its dependencies: the manifest is the complete
// allowlist of installed runtime code plus Project-owned assets/authored data.
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { runGeometryPrebake } = require('./geometry-prebake');

const PROJECT_DIR = path.resolve(__dirname, '..', '..');
const DEFAULT_MANIFEST = path.join(__dirname, 'runtime-manifest.json');
const DEFAULT_BUILD_METADATA = path.join(__dirname, 'build-metadata.json');
const DEFAULT_LOVEC = path.join('C:', 'Program Files', 'LOVE', 'lovec.exe');
const DEFAULT_LOVE = path.join('C:', 'Program Files', 'LOVE', 'love.exe');
const WINDOWS_RUNTIME_FILES = ['love.dll', 'lua51.dll', 'mpg123.dll', 'msvcp120.dll', 'msvcr120.dll', 'OpenAL32.dll', 'SDL2.dll'];

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
    for (const key of ['rootFiles', 'runtimeDirectories', 'dataRuntimeFiles', 'authoredDataExtensions']) {
        if (!Array.isArray(manifest[key]) || manifest[key].length === 0) throw new Error(`runtime manifest ${key} must be a non-empty array`);
    }
    if (manifest.projectDirectories === undefined) manifest.projectDirectories = [];
    if (!Array.isArray(manifest.projectDirectories)) throw new Error('runtime manifest projectDirectories must be an array');
    manifest.rootFiles.forEach(value => requireRelativePath(value, 'rootFiles entry'));
    manifest.runtimeDirectories.forEach(value => requireRelativePath(value, 'runtimeDirectories entry'));
    manifest.projectDirectories.forEach(value => requireRelativePath(value, 'projectDirectories entry'));
    manifest.dataRuntimeFiles.forEach(value => requireRelativePath(value, 'dataRuntimeFiles entry'));
    manifest.authoredDataExtensions.forEach(value => {
        if (typeof value !== 'string' || !value.startsWith('.')) throw new Error(`Invalid authored-data extension: ${value}`);
    });
    requireRelativePath(manifest.releaseConfig, 'releaseConfig');
    return manifest;
}

// The few strings the EXPORTER owns: what the player-facing artifacts are
// called. Deliberately not the window title -- conf.lua already owns that, and
// this file must not become a second place to change the game's name in.
function readBuildMetadata(metadataPath = DEFAULT_BUILD_METADATA) {
    const metadata = readJson(metadataPath);
    if (metadata.version !== 1) throw new Error(`Unsupported build metadata version: ${metadata.version}`);
    for (const key of ['productName', 'executableName', 'buildSlug', 'productVersion']) {
        if (typeof metadata[key] !== 'string' || !metadata[key]) throw new Error(`build metadata ${key} must be a non-empty string`);
    }
    for (const key of ['executableName', 'buildSlug']) {
        if (/[\\/:*?"<>|]/.test(metadata[key])) throw new Error(`build metadata ${key} must not contain path separators or reserved characters`);
    }
    return metadata;
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

// #221/#358/#299: one staging contract. Runtime implementation comes from the
// Studio/runtime installation; assets and authored JSON come from the opened
// Project. A Project has exactly one authored data root: Project/data/.
function stageGame({ projectDir = PROJECT_DIR, runtimeDir = projectDir, outputDir, manifestPath = DEFAULT_MANIFEST }) {
    if (!outputDir) throw new Error('stageGame requires outputDir');
    const manifest = readManifest(manifestPath);
    const stageDir = path.resolve(outputDir);
    const sourceData = projectDataSource(projectDir);
    if (!fs.existsSync(sourceData) || !fs.statSync(sourceData).isDirectory()) {
        throw new Error(`Project authored data is missing: ${sourceData}`);
    }

    fs.rmSync(stageDir, { recursive: true, force: true });
    fs.mkdirSync(stageDir, { recursive: true });
    for (const relative of manifest.rootFiles) copyFile(path.join(runtimeDir, relative), path.join(stageDir, relative));
    for (const relative of manifest.runtimeDirectories) copyDirectory(path.join(runtimeDir, relative), path.join(stageDir, relative));
    for (const relative of manifest.projectDirectories) copyDirectory(path.join(projectDir, relative), path.join(stageDir, relative));
    copyFile(path.join(runtimeDir, manifest.releaseConfig), path.join(stageDir, 'conf.lua'));

    const stagedData = path.join(stageDir, 'data');
    for (const relative of manifest.dataRuntimeFiles) copyFile(path.join(runtimeDir, 'data', relative), path.join(stagedData, relative));
    copyAuthoredData(sourceData, stagedData, manifest.authoredDataExtensions);
    return { stageDir, manifest, projectDir: path.resolve(projectDir) };
}

function preflight({ projectDir = PROJECT_DIR, lovecPath = process.env.LOVEC_PATH || DEFAULT_LOVEC }) {
    if (!fs.existsSync(lovecPath)) throw new Error(`lovec.exe not found at ${lovecPath} (set LOVEC_PATH)`);
    const result = childProcess.spawnSync(lovecPath, ['.', 'validate'], { cwd: projectDir, encoding: 'utf8', windowsHide: true });
    const output = `${result.stdout || ''}${result.stderr || ''}`;
    if (result.status !== 0 || !output.includes('VALIDATE OK')) throw new Error(`Export preflight failed:\n${output.trim()}`);
}

function packLove(stageDir, lovePath) {
    fs.mkdirSync(path.dirname(lovePath), { recursive: true });
    fs.rmSync(lovePath, { force: true });
    const script = path.join(__dirname, 'pack-love.ps1');
    const result = childProcess.spawnSync('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, stageDir, lovePath], { encoding: 'utf8', windowsHide: true });
    if (result.status !== 0 || !fs.existsSync(lovePath)) throw new Error(`Could not create .love archive:\n${result.stderr || result.stdout || ''}`);
}

function packDirectory(sourceDir, zipPath) {
    fs.mkdirSync(path.dirname(zipPath), { recursive: true });
    fs.rmSync(zipPath, { force: true });
    const script = path.join(__dirname, 'pack-directory.ps1');
    const result = childProcess.spawnSync('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, sourceDir, zipPath], { encoding: 'utf8', windowsHide: true });
    if (result.status !== 0 || !fs.existsSync(zipPath)) throw new Error(`Could not create distribution ZIP:\n${result.stderr || result.stdout || ''}`);
}

function effekseerRequired(runtimeRoot) {
    const animations = readJson(path.join(runtimeRoot, 'data', 'animations.json'));
    return JSON.stringify(animations).includes('"effekseer"');
}

// Same question asked of an unstaged Project, so Studio can report the shim
// requirement before anything is copied. A Project without an animations
// document simply authors no effects.
function projectNeedsEffekseer(projectDir) {
    const file = path.join(projectDataSource(projectDir), 'animations.json');
    if (!fs.existsSync(file)) return false;
    return JSON.stringify(readJson(file)).includes('"effekseer"');
}

function declaredEffekseerSymbols(projectDir = PROJECT_DIR) {
    const source = fs.readFileSync(path.join(projectDir, 'presentation', 'effekseer.lua'), 'utf8');
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

function verifyShim(shimPath, projectDir = PROJECT_DIR) {
    const exported = new Set(readDllExports(shimPath));
    const missing = declaredEffekseerSymbols(projectDir).filter(name => !exported.has(name));
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

function windowsPreflight({ stageDir, projectDir = PROJECT_DIR, loveExe = process.env.LOVE_PATH || DEFAULT_LOVE, shimPath = path.join(PROJECT_DIR, 'effekseer_shim.dll') }) {
    const runtime = requiredWindowsRuntime(loveExe);
    const needsShim = effekseerRequired(stageDir);
    if (needsShim) {
        if (!fs.existsSync(shimPath)) {
            throw new Error(`effekseer_shim.dll is required by authored animations but is missing at ${shimPath}. Build it with tools/effekseer/build.ps1.`);
        }
        verifyShim(shimPath, projectDir);
    }
    return { runtime, needsShim };
}

function exportWindows({ projectDir = PROJECT_DIR, stageDir, outputDir, lovePath, loveExe = process.env.LOVE_PATH || DEFAULT_LOVE, shimPath = path.join(projectDir, 'effekseer_shim.dll'), metadata, smoke = true }) {
    if (!stageDir || !outputDir || !lovePath) throw new Error('exportWindows requires stageDir, outputDir, and lovePath');
    if (!fs.existsSync(path.join(stageDir, 'main.lua'))) throw new Error(`Staged game is missing main.lua: ${stageDir}`);
    if (!fs.existsSync(lovePath)) throw new Error(`Staged .love archive is missing: ${lovePath}`);
    const build = metadata || readBuildMetadata();
    const { runtime, needsShim } = windowsPreflight({ stageDir, projectDir, loveExe, shimPath });

    const playerDir = path.resolve(outputDir);
    fs.rmSync(playerDir, { recursive: true, force: true });
    fs.mkdirSync(playerDir, { recursive: true });
    const executableName = `${build.executableName}.exe`;
    const executable = path.join(playerDir, executableName);
    copyFile(loveExe, executable);
    appendFile(lovePath, executable);
    for (const filePath of runtime.slice(1, -1)) copyFile(filePath, path.join(playerDir, path.basename(filePath)));
    if (needsShim) copyFile(shimPath, path.join(playerDir, 'effekseer_shim.dll'));
    copyFile(runtime[runtime.length - 1], path.join(playerDir, 'LICENSES', 'LOVE-license.txt'));
    fs.writeFileSync(path.join(playerDir, 'THIRD_PARTY_NOTICES.txt'),
        'This distribution bundles the LÖVE runtime. Its license is included in LICENSES/LOVE-license.txt.\n' +
        (needsShim ? 'It also bundles the project Effekseer shim; see tools/effekseer/README.md in the source project for its build provenance.\n' : ''), 'utf8');
    if (smoke) {
        const result = childProcess.spawnSync(executable, ['validate'], { cwd: playerDir, encoding: 'utf8', windowsHide: true, timeout: 60000 });
        if (result.status !== 0) throw new Error(`Exported executable smoke test failed:\n${result.stderr || result.stdout || ''}`);
    }
    return { playerDir, executable, needsShim };
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

function writeBuildManifest({ outputDir, metadata, target, stageDir, loveExe, projectDir = PROJECT_DIR }) {
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

function parseArgs(argv) {
    const options = { outputDir: path.join(PROJECT_DIR, 'dist'), projectDir: PROJECT_DIR, preflight: true, pack: true, target: 'love' };
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
    const metadata = readBuildMetadata();
    const stageDir = path.join(options.outputDir, 'stage');
    const staged = stageGame({ projectDir: options.projectDir, runtimeDir: PROJECT_DIR, outputDir: stageDir });

    // Validate the exact runnable tree that will be packaged. This also makes
    // external Project export obey the same installed-runtime/Project-data
    // ownership boundary as #358 Test Play.
    if (options.preflight) preflight({ projectDir: staged.stageDir });

    // #221 staging is the build-transform boundary. Geometry compilation owns
    // this step; neither the .love packer nor the Windows packager does.
    runGeometryPrebake({ stageDir: staged.stageDir });

    if (options.target === 'windows-x64') windowsPreflight({ stageDir: staged.stageDir, projectDir: PROJECT_DIR });
    if (options.pack) {
        const loveExe = process.env.LOVE_PATH || DEFAULT_LOVE;
        const lovePath = path.join(options.outputDir, `${metadata.productName}.love`);
        packLove(staged.stageDir, lovePath);
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
        } else if (options.target === 'windows-x64') {
            const playerDir = path.join(options.outputDir, `${metadata.buildSlug}-windows-x64`);
            const player = exportWindows({ stageDir: staged.stageDir, outputDir: playerDir, lovePath, metadata, projectDir: PROJECT_DIR });
            const zipPath = path.join(options.outputDir, `${metadata.buildSlug}-windows-x64.zip`);
            packDirectory(player.playerDir, zipPath);
            console.log(`EXPORT OK: ${zipPath}`);
        }
    } else {
        console.log(`STAGE OK: ${staged.stageDir}`);
    }
}

if (require.main === module) main();

module.exports = { copyAuthoredData, declaredEffekseerSymbols, effekseerRequired, exportWindows, geometryPrebakeSummary,
    packDirectory, packLove, preflight, projectDataSource, projectNeedsEffekseer, readBuildMetadata, readDllExports, readManifest,
    requiredWindowsRuntime, stageGame, verifyShim, windowsPreflight, writeBuildManifest };
