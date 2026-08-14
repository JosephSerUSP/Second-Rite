'use strict';

const fs = require('fs');
const path = require('path');
const rtp = require('./rtp-resource-resolver');
const baseline = require('./rtp-baseline-resources');

function readJson(filePath, label) {
    try { return JSON.parse(fs.readFileSync(filePath, 'utf8')); }
    catch (error) { throw new Error(`${label} is not readable JSON: ${filePath}: ${error.message}`); }
}

function manifestFor(options) {
    const revision = rtp.pinnedRevision(options.systemValue);
    if (!revision) return null;
    const manifest = rtp.revisionManifest({ systemValue: options.systemValue, rtpRoot: options.rtpRoot });
    if (!manifest || !manifest.authored) return null;
    return manifest;
}

function localScenes(projectDir) {
    const indexPath = path.resolve(projectDir, 'data', 'scenes', 'index.json');
    if (!fs.existsSync(indexPath)) return { fragmented: false, byId: new Map() };
    const index = readJson(indexPath, 'Project Scene index');
    const files = Array.isArray(index) ? index : index && index.files;
    if (!Array.isArray(files)) throw new Error(`Project Scene index must be an array or { files: [...] }: ${indexPath}`);
    const byId = new Map();
    let fragmented = false;
    for (const file of files) {
        if (typeof file !== 'string') continue;
        if (path.basename(file) !== file || !file.toLowerCase().endsWith('.json')) {
            throw new Error(`Project Scene index contains unsafe entry: ${JSON.stringify(file)}`);
        }
        fragmented = true;
        const sourcePath = path.resolve(path.dirname(indexPath), file);
        const value = readJson(sourcePath, `Project Scene ${file}`);
        const id = String(value.id);
        if (byId.has(id)) throw new Error(`Project Scene index contains duplicate Scene id ${id}`);
        byId.set(id, { file, sourcePath, value });
    }
    return { fragmented, byId };
}

function sceneResource(id, entry, provider, value) {
    return {
        resource: `sceneDefault:${id}`,
        logicalPath: entry.logicalPath,
        sourcePath: entry.sourcePath,
        file: path.posix.basename(entry.logicalPath.replace(/\\/g, '/')),
        value,
        provider,
    };
}

function scenes({ projectDir, systemValue, rtpRoot = process.env[rtp.RTP_ROOT_ENV] } = {}) {
    if (!projectDir) throw new Error('scene default resolver requires projectDir');
    // #390 is opt-in through one exact pinned manifest. Projects without that
    // declaration retain their existing storage semantics, including legacy or
    // deliberately odd fixture indexes used by boundary tests.
    const manifest = manifestFor({ systemValue, rtpRoot });
    if (!manifest || !Object.keys(manifest.authored.sceneDefaults || {}).length) return [];
    const local = localScenes(projectDir);
    if (!local.fragmented) return [];
    const out = [];
    for (const [id, inheritedEntry] of Object.entries(manifest.authored.sceneDefaults || {})) {
        const project = local.byId.get(id);
        if (project) {
            out.push(sceneResource(id, {
                logicalPath: path.join('data', 'scenes', project.file),
                sourcePath: project.sourcePath,
            }, { kind: 'project', id: 'project' }, project.value));
            continue;
        }
        baseline.requireAuthoredFile(manifest, inheritedEntry, `Scene default '${id}'`);
        const value = readJson(inheritedEntry.sourcePath, `RTP Scene default '${id}'`);
        if (String(value.id) !== id) {
            throw new Error(`RTP Scene default '${id}' has mismatched id ${JSON.stringify(value.id)}: ${inheritedEntry.sourcePath}`);
        }
        out.push(sceneResource(id, inheritedEntry, { kind: 'rtp', id: 'thestra-rtp', revision: manifest.revision }, value));
    }
    return out;
}

function flows({ projectDir, systemValue, rtpRoot = process.env[rtp.RTP_ROOT_ENV] } = {}) {
    if (!projectDir) throw new Error('flow default resolver requires projectDir');
    const manifest = manifestFor({ systemValue, rtpRoot });
    if (!manifest) return [];
    const out = [];
    for (const [id, inheritedEntry] of Object.entries(manifest.authored.flowDefaults || {})) {
        const logicalPath = inheritedEntry.logicalPath;
        const projectPath = path.resolve(projectDir, ...logicalPath.split('/'));
        if (fs.existsSync(projectPath) && fs.statSync(projectPath).isFile()) {
            out.push({
                resource: `flowDefault:${id}`, logicalPath, sourcePath: projectPath,
                file: path.posix.basename(logicalPath), value: readJson(projectPath, `Project Flow default '${id}'`),
                provider: { kind: 'project', id: 'project' },
            });
            continue;
        }
        baseline.requireAuthoredFile(manifest, inheritedEntry, `Flow default '${id}'`);
        out.push({
            resource: `flowDefault:${id}`, logicalPath, sourcePath: inheritedEntry.sourcePath,
            file: path.posix.basename(logicalPath), value: readJson(inheritedEntry.sourcePath, `RTP Flow default '${id}'`),
            provider: { kind: 'rtp', id: 'thestra-rtp', revision: manifest.revision },
        });
    }
    return out;
}

module.exports = { flows, localScenes, scenes };
