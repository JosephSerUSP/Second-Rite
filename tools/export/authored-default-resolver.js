'use strict';

const fs = require('fs');
const path = require('path');
const rtp = require('./rtp-resource-resolver');

const SCENES = Object.freeze([
    Object.freeze({ id: 'save_menu', file: 'save_menu.json' }),
    Object.freeze({ id: 'items', file: 'items.json' }),
    Object.freeze({ id: 'status', file: 'status.json' }),
    Object.freeze({ id: 'controls', file: 'controls.json' }),
]);
const FLOWS = Object.freeze([Object.freeze({ id: 'quest', file: 'quest.json' })]);

function readJson(filePath, label) {
    try { return JSON.parse(fs.readFileSync(filePath, 'utf8')); }
    catch (error) { throw new Error(`${label} is not readable JSON: ${filePath}: ${error.message}`); }
}

function inheritedFile(revision, rtpRoot, relative, label) {
    if (!rtpRoot) throw new Error(`Project pins RTP revision ${revision}, but no RTP installation root was provided (set ${rtp.RTP_ROOT_ENV})`);
    const revisionRoot = path.resolve(rtpRoot, 'revisions', revision);
    const sourcePath = path.resolve(revisionRoot, relative);
    if (!sourcePath.startsWith(revisionRoot + path.sep)) throw new Error(`Pinned RTP resource escaped revision root: ${sourcePath}`);
    if (!fs.existsSync(sourcePath) || !fs.statSync(sourcePath).isFile()) throw new Error(`Pinned RTP revision ${revision} does not provide inherited ${label}: ${sourcePath}`);
    return sourcePath;
}

function localScene(projectDir, id) {
    const indexPath = path.resolve(projectDir, 'data', 'scenes', 'index.json');
    if (!fs.existsSync(indexPath)) return null;
    const index = readJson(indexPath, 'Project Scene index');
    const files = Array.isArray(index) ? index : index && index.files;
    if (!Array.isArray(files)) throw new Error(`Project Scene index must be an array or { files = [...] }: ${indexPath}`);
    for (const file of files) {
        if (typeof file !== 'string' || path.basename(file) !== file || !file.toLowerCase().endsWith('.json')) throw new Error(`Project Scene index contains unsafe entry: ${JSON.stringify(file)}`);
        const sourcePath = path.resolve(path.dirname(indexPath), file);
        const value = readJson(sourcePath, `Project Scene ${file}`);
        if (String(value.id) === id) return { resource: `sceneDefault:${id}`, logicalPath: path.join('data', 'scenes', file), sourcePath, file, value, provider: { kind: 'project', id: 'project' } };
    }
    return null;
}

function scene({ id, projectDir, systemValue, rtpRoot = process.env[rtp.RTP_ROOT_ENV] } = {}) {
    const spec = SCENES.find(row => row.id === id);
    if (!spec) throw new Error(`Scene '${id}' is not an inherited Scene default`);
    const local = localScene(projectDir, id);
    if (local) return local;
    const revision = rtp.pinnedRevision(systemValue);
    if (!revision) return null;
    const relative = path.join('data', 'scenes', spec.file);
    const sourcePath = inheritedFile(revision, rtpRoot, relative, `Scene default '${id}'`);
    const value = readJson(sourcePath, `RTP Scene default '${id}'`);
    if (String(value.id) !== id) throw new Error(`RTP Scene default '${id}' has mismatched id ${JSON.stringify(value.id)}: ${sourcePath}`);
    return { resource: `sceneDefault:${id}`, logicalPath: relative, sourcePath, file: spec.file, value, provider: { kind: 'rtp', id: 'thestra-rtp', revision } };
}

function scenes(options = {}) {
    if (!options.projectDir || !fs.existsSync(path.resolve(options.projectDir, 'data', 'scenes', 'index.json'))) return [];
    return SCENES.map(spec => scene(Object.assign({}, options, { id: spec.id }))).filter(Boolean);
}

function flow({ id, projectDir, systemValue, rtpRoot = process.env[rtp.RTP_ROOT_ENV] } = {}) {
    const spec = FLOWS.find(row => row.id === id);
    if (!spec) throw new Error(`Flow '${id}' is not an inherited Flow default`);
    const relative = path.join('data', 'flows', spec.file);
    const projectPath = path.resolve(projectDir, relative);
    if (fs.existsSync(projectPath) && fs.statSync(projectPath).isFile()) return { resource: `flowDefault:${id}`, logicalPath: relative, sourcePath: projectPath, file: spec.file, value: readJson(projectPath, `Project Flow default '${id}'`), provider: { kind: 'project', id: 'project' } };
    const revision = rtp.pinnedRevision(systemValue);
    if (!revision) return null;
    const sourcePath = inheritedFile(revision, rtpRoot, relative, `Flow default '${id}'`);
    return { resource: `flowDefault:${id}`, logicalPath: relative, sourcePath, file: spec.file, value: readJson(sourcePath, `RTP Flow default '${id}'`), provider: { kind: 'rtp', id: 'thestra-rtp', revision } };
}

function flows(options = {}) {
    if (!options.projectDir || !fs.existsSync(path.resolve(options.projectDir, 'data', 'flows'))) return [];
    return FLOWS.map(spec => flow(Object.assign({}, options, { id: spec.id }))).filter(Boolean);
}

module.exports = { FLOWS, SCENES, flow, flows, scene, scenes };
