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

function parseArgs(argv) {
    const options = { outputDir: path.join(PROJECT_DIR, 'dist'), campaign: '', preflight: true, pack: true };
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === '--output') options.outputDir = path.resolve(argv[++i] || '');
        else if (arg === '--campaign') options.campaign = argv[++i] || '';
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
        console.log('Usage: node tools/export/export-game.js [--campaign name] [--output dir] [--stage-only] [--skip-preflight]');
        return;
    }
    if (options.preflight) preflight({ campaign: options.campaign });
    const stageDir = path.join(options.outputDir, 'stage');
    const staged = stageGame({ outputDir: stageDir, campaign: options.campaign });
    if (options.pack) {
        const lovePath = path.join(options.outputDir, 'Second Rite.love');
        packLove(staged.stageDir, lovePath);
        console.log(`EXPORT OK: ${lovePath}`);
    } else {
        console.log(`STAGE OK: ${staged.stageDir}`);
    }
}

if (require.main === module) main();

module.exports = { campaignSource, copyCampaignJson, packLove, preflight, readManifest, stageGame };
