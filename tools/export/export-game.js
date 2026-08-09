#!/usr/bin/env node
'use strict';

// Runtime-only game staging. This script intentionally knows nothing about
// the editor's server or its dependencies: the manifest is the complete
// allowlist of source runtime code, assets, and authored campaign data.
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const PROJECT_DIR = path.resolve(__dirname, '..', '..');
const DEFAULT_MANIFEST = path.join(__dirname, 'runtime-manifest.json');
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
    for (const key of ['rootFiles', 'runtimeDirectories', 'dataRuntimeFiles', 'campaignExtensions']) {
        if (!Array.isArray(manifest[key]) || manifest[key].length === 0) throw new Error(`runtime manifest ${key} must be a non-empty array`);
    }
    manifest.rootFiles.forEach(value => requireRelativePath(value, 'rootFiles entry'));
    manifest.runtimeDirectories.forEach(value => requireRelativePath(value, 'runtimeDirectories entry'));
    manifest.dataRuntimeFiles.forEach(value => requireRelativePath(value, 'dataRuntimeFiles entry'));
    manifest.campaignExtensions.forEach(value => {
        if (typeof value !== 'string' || !value.startsWith('.')) throw new Error(`Invalid campaign extension: ${value}`);
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

function copyCampaignJson(source, destination, extensions) {
    for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
        const from = path.join(source, entry.name);
        const to = path.join(destination, entry.name);
        if (entry.isDirectory()) {
            copyCampaignJson(from, to, extensions);
        } else if (entry.isFile() && extensions.includes(path.extname(entry.name).toLowerCase())) {
            copyFile(from, to);
        }
    }
}

function campaignSource(projectDir, campaign) {
    if (!campaign) return path.join(projectDir, 'data');
    if (!/^[a-z0-9_]+$/.test(campaign)) throw new Error(`Invalid campaign name '${campaign}'`);
    return path.join(projectDir, 'campaigns', campaign);
}

function stageGame({ projectDir = PROJECT_DIR, outputDir, campaign = '', manifestPath = DEFAULT_MANIFEST }) {
    if (!outputDir) throw new Error('stageGame requires outputDir');
    const manifest = readManifest(manifestPath);
    const stageDir = path.resolve(outputDir);
    const sourceCampaign = campaignSource(projectDir, campaign);
    if (!fs.existsSync(sourceCampaign)) throw new Error(`Campaign source is missing: ${sourceCampaign}`);

    fs.rmSync(stageDir, { recursive: true, force: true });
    fs.mkdirSync(stageDir, { recursive: true });
    for (const relative of manifest.rootFiles) copyFile(path.join(projectDir, relative), path.join(stageDir, relative));
    for (const relative of manifest.runtimeDirectories) copyDirectory(path.join(projectDir, relative), path.join(stageDir, relative));
    copyFile(path.join(projectDir, manifest.releaseConfig), path.join(stageDir, 'conf.lua'));

    const stagedData = path.join(stageDir, 'data');
    for (const relative of manifest.dataRuntimeFiles) copyFile(path.join(projectDir, 'data', relative), path.join(stagedData, relative));
    copyCampaignJson(sourceCampaign, stagedData, manifest.campaignExtensions);
    return { stageDir, manifest, campaign: campaign || '(default)' };
}

function preflight({ projectDir = PROJECT_DIR, campaign = '', lovecPath = process.env.LOVEC_PATH || DEFAULT_LOVEC }) {
    if (!fs.existsSync(lovecPath)) throw new Error(`lovec.exe not found at ${lovecPath} (set LOVEC_PATH)`);
    const args = ['.', 'validate'];
    if (campaign) args.push(`campaign=${campaign}`);
    const result = childProcess.spawnSync(lovecPath, args, { cwd: projectDir, encoding: 'utf8', windowsHide: true });
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

// Same question asked of an unstaged campaign root, so the editor's export
// dialog can report the shim requirement before anything is copied. A
// campaign without an animations document simply authors no effects.
function campaignNeedsEffekseer(projectDir, campaign) {
    const file = path.join(campaignSource(projectDir, campaign), 'animations.json');
    if (!fs.existsSync(file)) return false;
    return JSON.stringify(readJson(file)).includes('"effekseer"');
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

function windowsPreflight({ stageDir, loveExe = process.env.LOVE_PATH || DEFAULT_LOVE, shimPath = path.join(PROJECT_DIR, 'effekseer_shim.dll') }) {
    const runtime = requiredWindowsRuntime(loveExe);
    const needsShim = effekseerRequired(stageDir);
    if (needsShim && !fs.existsSync(shimPath)) {
        throw new Error(`effekseer_shim.dll is required by authored animations but is missing at ${shimPath}. Build it with tools/effekseer/build.ps1.`);
    }
    return { runtime, needsShim };
}

function exportWindows({ projectDir = PROJECT_DIR, stageDir, outputDir, lovePath, loveExe = process.env.LOVE_PATH || DEFAULT_LOVE, shimPath = path.join(projectDir, 'effekseer_shim.dll'), productName = 'Second Rite', smoke = true }) {
    if (!stageDir || !outputDir || !lovePath) throw new Error('exportWindows requires stageDir, outputDir, and lovePath');
    if (!fs.existsSync(path.join(stageDir, 'main.lua'))) throw new Error(`Staged game is missing main.lua: ${stageDir}`);
    if (!fs.existsSync(lovePath)) throw new Error(`Staged .love archive is missing: ${lovePath}`);
    const { runtime, needsShim } = windowsPreflight({ stageDir, loveExe, shimPath });

    const playerDir = path.resolve(outputDir);
    fs.rmSync(playerDir, { recursive: true, force: true });
    fs.mkdirSync(playerDir, { recursive: true });
    const executableName = `${productName}.exe`;
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

function parseArgs(argv) {
    const options = { outputDir: path.join(PROJECT_DIR, 'dist'), campaign: '', preflight: true, pack: true, target: 'love' };
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === '--output') options.outputDir = path.resolve(argv[++i] || '');
        else if (arg === '--campaign') options.campaign = argv[++i] || '';
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
        console.log('Usage: node tools/export/export-game.js [--target love|windows-x64] [--campaign name] [--output dir] [--stage-only] [--skip-preflight]');
        return;
    }
    if (!['love', 'windows-x64'].includes(options.target)) throw new Error(`Unsupported export target: ${options.target}`);
    if (options.preflight) preflight({ campaign: options.campaign });
    const stageDir = path.join(options.outputDir, 'stage');
    const staged = stageGame({ outputDir: stageDir, campaign: options.campaign });
    if (options.target === 'windows-x64') windowsPreflight({ stageDir: staged.stageDir });
    if (options.pack) {
        const lovePath = path.join(options.outputDir, 'Second Rite.love');
        packLove(staged.stageDir, lovePath);
        if (options.target === 'love') {
            console.log(`EXPORT OK: ${lovePath}`);
        } else if (options.target === 'windows-x64') {
            const playerDir = path.join(options.outputDir, 'Second-Rite-windows-x64');
            const player = exportWindows({ stageDir: staged.stageDir, outputDir: playerDir, lovePath });
            const zipPath = path.join(options.outputDir, 'Second-Rite-windows-x64.zip');
            packDirectory(player.playerDir, zipPath);
            console.log(`EXPORT OK: ${zipPath}`);
        }
    } else {
        console.log(`STAGE OK: ${staged.stageDir}`);
    }
}

if (require.main === module) main();

module.exports = { campaignNeedsEffekseer, campaignSource, copyCampaignJson, effekseerRequired, exportWindows, packDirectory, packLove, preflight, readManifest, requiredWindowsRuntime, stageGame, windowsPreflight };
