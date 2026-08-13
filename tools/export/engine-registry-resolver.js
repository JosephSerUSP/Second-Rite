'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const rtp = require('./rtp-resource-resolver');

const ENGINE_RELATIVE = path.join('data', 'engine.json');

function readJson(filePath, label) {
    try { return JSON.parse(fs.readFileSync(filePath, 'utf8')); }
    catch (error) { throw new Error(`${label} is not readable JSON: ${filePath}: ${error.message}`); }
}

function objectValue(value, label) {
    if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error(`${label} must be a JSON object`);
    return value;
}

function revisionFile(revision, rtpRoot) {
    if (!rtpRoot) throw new Error(`Project pins RTP revision ${revision}, but no RTP installation root was provided (set ${rtp.RTP_ROOT_ENV})`);
    const revisionRoot = path.resolve(rtpRoot, 'revisions', revision);
    const sourcePath = path.resolve(revisionRoot, ENGINE_RELATIVE);
    if (!sourcePath.startsWith(revisionRoot + path.sep)) throw new Error(`Pinned RTP resource escaped revision root: ${sourcePath}`);
    if (!fs.existsSync(sourcePath) || !fs.statSync(sourcePath).isFile()) {
        throw new Error(`Pinned RTP revision ${revision} does not provide inherited engineRegistry baseline: ${sourcePath}`);
    }
    return sourcePath;
}

function versionOf(sources) {
    const hash = crypto.createHash('sha256');
    for (const source of sources) { hash.update(source.logicalPath); hash.update('\0'); hash.update(fs.readFileSync(source.sourcePath)); hash.update('\0'); }
    return hash.digest('hex');
}

function resolve({ projectDir, systemValue, rtpRoot = process.env[rtp.RTP_ROOT_ENV] } = {}) {
    if (!projectDir) throw new Error('engineRegistry resolver requires projectDir');
    const projectPath = path.resolve(projectDir, ENGINE_RELATIVE);
    const revision = rtp.pinnedRevision(systemValue);
    if (!revision) {
        if (!fs.existsSync(projectPath) || !fs.statSync(projectPath).isFile()) throw new Error(`Project-required resource is missing: ${ENGINE_RELATIVE} (${projectPath})`);
        const value = objectValue(readJson(projectPath, 'Project engine resource'), 'Project engine resource');
        const sources = [{ provider: { kind: 'project', id: 'project' }, logicalPath: ENGINE_RELATIVE, sourcePath: projectPath }];
        return { resource: 'engineRegistry', logicalPath: ENGINE_RELATIVE, sourcePath: projectPath, provider: { kind: 'project', id: 'project' }, sources, value, baselineValue: null, overlayValue: value, version: versionOf(sources) };
    }
    const baselinePath = revisionFile(revision, rtpRoot);
    const baselineValue = objectValue(readJson(baselinePath, 'RTP engineRegistry baseline'), 'RTP engineRegistry baseline');
    let overlayValue = {};
    let overlaySource = null;
    if (fs.existsSync(projectPath) && fs.statSync(projectPath).isFile()) { overlayValue = objectValue(readJson(projectPath, 'Project engineRegistry policy'), 'Project engineRegistry policy'); overlaySource = projectPath; }
    for (const key of Object.keys(overlayValue)) if (Object.prototype.hasOwnProperty.call(baselineValue, key)) throw new Error(`engineRegistry ownership collision at top-level key '${key}'; RTP baseline and Project policy must be disjoint`);
    const baseProvider = { kind: 'rtp', id: 'thestra-rtp', revision };
    const sources = [{ provider: baseProvider, logicalPath: ENGINE_RELATIVE, sourcePath: baselinePath }];
    if (overlaySource) sources.push({ provider: { kind: 'project', id: 'project' }, logicalPath: ENGINE_RELATIVE, sourcePath: overlaySource });
    return { resource: 'engineRegistry', logicalPath: ENGINE_RELATIVE, sourcePath: baselinePath,
        provider: overlaySource ? { kind: 'composed', id: 'engine-registry', base: baseProvider, overlay: { kind: 'project', id: 'project' } } : baseProvider,
        sources, baselineValue, overlayValue, value: Object.assign({}, baselineValue, overlayValue), version: versionOf(sources) };
}

module.exports = { ENGINE_RELATIVE, resolve };
