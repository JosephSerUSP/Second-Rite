'use strict';

// #391: manifest-gated player-facing RTP assets. This is deliberately not a
// directory overlay: callers pass one exact pinned revision and request a
// typed class.
const fs = require('fs');
const path = require('path');

const MANIFEST = 'resources.json';
const FONT_DIR = 'assets/fonts';
const TILESET_TEMPLATE = 'assets/tilesets/template_tileset.png';
const PROVENANCE = ['source', 'authorship', 'redistributionStatus', 'genericReason', 'playerFacingReason'];

function safeRelative(value, label) {
    if (typeof value !== 'string' || !value || path.isAbsolute(value) || value.split(/[\\/]/).includes('..')) {
        throw new Error(`${label} must be a safe non-empty relative path`);
    }
    return value.replace(/\\/g, '/');
}

function inside(root, relative, label) {
    const logicalPath = safeRelative(relative, label);
    const sourcePath = path.resolve(root, ...logicalPath.split('/'));
    if (sourcePath !== root && !sourcePath.startsWith(root + path.sep)) {
        throw new Error(`${label} escaped pinned RTP revision root: ${sourcePath}`);
    }
    return { logicalPath, sourcePath };
}

function readManifest({ revision, rtpRoot }) {
    if (!revision) return null;
    if (!rtpRoot) throw new Error(`Project pins RTP revision ${revision}, but no RTP installation root was provided`);
    const root = path.resolve(rtpRoot, 'revisions', revision);
    const manifestPath = path.join(root, MANIFEST);
    if (!fs.existsSync(manifestPath) || !fs.statSync(manifestPath).isFile()) {
        throw new Error(`Pinned RTP revision ${revision} has no typed resource manifest: ${manifestPath}`);
    }
    let value;
    try { value = JSON.parse(fs.readFileSync(manifestPath, 'utf8')); }
    catch (error) { throw new Error(`Pinned RTP revision ${revision} resource manifest is not readable JSON: ${error.message}`); }
    if (!value || value.version !== 1 || value.revision !== revision || !Array.isArray(value.resources)) {
        throw new Error(`Pinned RTP revision ${revision} resource manifest must declare version 1, matching revision, and resources[]`);
    }
    const ids = new Set();
    const resources = value.resources.map((entry, index) => {
        if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw new Error(`RTP resources[${index}] must be an object`);
        if (typeof entry.id !== 'string' || !entry.id.trim()) throw new Error(`RTP resources[${index}] requires id`);
        if (ids.has(entry.id)) throw new Error(`Pinned RTP revision ${revision} duplicates resource id ${entry.id}`);
        ids.add(entry.id);
        if (typeof entry.class !== 'string' || !entry.class.trim()) throw new Error(`Pinned RTP resource ${entry.id} requires class`);
        for (const field of PROVENANCE) {
            if (typeof entry[field] !== 'string' || !entry[field].trim()) throw new Error(`Pinned RTP resource ${entry.id} requires provenance field ${field}`);
        }
        const file = inside(root, entry.logicalPath, `Pinned RTP resource ${entry.id} logicalPath`);
        const out = Object.assign({}, entry, file);
        if (entry.licensePath !== undefined) {
            const license = inside(root, entry.licensePath, `Pinned RTP resource ${entry.id} licensePath`);
            out.licensePath = license.logicalPath;
            out.licenseSourcePath = license.sourcePath;
        }
        return out;
    });
    return { revision, root, manifestPath, resources };
}

function requireFiles(manifest, entry) {
    if (!fs.existsSync(entry.sourcePath) || !fs.statSync(entry.sourcePath).isFile()) {
        throw new Error(`Pinned RTP revision ${manifest.revision} declares missing ${entry.class} resource ${entry.id}: ${entry.sourcePath}`);
    }
    if (entry.licenseSourcePath && (!fs.existsSync(entry.licenseSourcePath) || !fs.statSync(entry.licenseSourcePath).isFile())) {
        throw new Error(`Pinned RTP revision ${manifest.revision} declares missing license notice for ${entry.id}: ${entry.licenseSourcePath}`);
    }
    return entry;
}

function fontName(logicalPath) {
    const value = safeRelative(logicalPath, 'RTP font logicalPath');
    if (!value.startsWith(FONT_DIR + '/') || !/\.ttf$/i.test(value)) {
        throw new Error(`RTP font must live under ${FONT_DIR}/ and be a .ttf: ${value}`);
    }
    return path.posix.basename(value).replace(/\.ttf$/i, '');
}

function fontLibrary({ revision, rtpRoot }) {
    if (!revision) return [];
    const manifest = readManifest({ revision, rtpRoot });
    return manifest.resources.filter(entry => entry.class === 'font').map(entry => {
        requireFiles(manifest, entry);
        return {
            resource: 'font', name: fontName(entry.logicalPath), logicalPath: entry.logicalPath,
            sourcePath: entry.sourcePath, provider: { kind: 'rtp', id: 'thestra-rtp', revision },
            provenance: Object.fromEntries(['id', ...PROVENANCE].map(key => [key, entry[key]])),
            notice: entry.licenseSourcePath ? {
                sourcePath: entry.licenseSourcePath,
                logicalPath: path.posix.join('LICENSES', path.posix.basename(entry.licensePath)),
            } : null,
        };
    });
}

function configuredFontNames(systemValue) {
    const ui = systemValue && systemValue.ui;
    const popup = systemValue && systemValue.battle_screen && systemValue.battle_screen.popup;
    const names = []; const seen = new Set();
    for (const value of [ui && ui.activeFont, popup && popup.font, popup && popup.numberFont, popup && popup.textFont]) {
        if (value === undefined || value === null || value === '' || value === 'Lucida') continue;
        if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(value)) {
            throw new Error(`Configured font name is not a safe font basename: ${JSON.stringify(value)}`);
        }
        if (!seen.has(value)) { seen.add(value); names.push(value); }
    }
    return names;
}

function fonts({ projectDir, systemValue, revision, rtpRoot }) {
    if (!projectDir) throw new Error('fonts resolver requires projectDir');
    const inherited = revision ? new Map(fontLibrary({ revision, rtpRoot }).map(entry => [entry.name, entry])) : new Map();
    return configuredFontNames(systemValue).flatMap(name => {
        const logicalPath = `${FONT_DIR}/${name}.ttf`;
        const sourcePath = path.resolve(projectDir, ...logicalPath.split('/'));
        if (fs.existsSync(sourcePath) && fs.statSync(sourcePath).isFile()) {
            return [{ resource: 'font', name, logicalPath, sourcePath, provider: { kind: 'project', id: 'project' }, notice: null }];
        }
        if (!revision) return [];
        const entry = inherited.get(name);
        if (!entry) throw new Error(`Configured font ${name} is missing from the Project and pinned RTP revision ${revision}`);
        return [entry];
    });
}

function tilesetTemplate({ projectDir, revision, rtpRoot }) {
    if (!projectDir) throw new Error('tilesetTemplate resolver requires projectDir');
    const projectPath = path.resolve(projectDir, ...TILESET_TEMPLATE.split('/'));
    if (fs.existsSync(projectPath) && fs.statSync(projectPath).isFile()) {
        return { resource: 'tileset-template', logicalPath: TILESET_TEMPLATE, sourcePath: projectPath, provider: { kind: 'project', id: 'project' } };
    }
    if (!revision) return null;
    const manifest = readManifest({ revision, rtpRoot });
    const candidates = manifest.resources.filter(entry => entry.class === 'tileset-template');
    if (candidates.length > 1) throw new Error(`Pinned RTP revision ${revision} declares multiple tileset-template resources; no collision rule exists`);
    if (!candidates.length) return null;
    const entry = requireFiles(manifest, candidates[0]);
    if (entry.logicalPath !== TILESET_TEMPLATE) throw new Error(`Pinned RTP tileset-template must use ${TILESET_TEMPLATE}, got ${entry.logicalPath}`);
    return {
        resource: 'tileset-template', logicalPath: entry.logicalPath, sourcePath: entry.sourcePath,
        provider: { kind: 'rtp', id: 'thestra-rtp', revision },
        provenance: Object.fromEntries(['id', ...PROVENANCE].map(key => [key, entry[key]])),
    };
}

module.exports = { FONT_DIR, MANIFEST, TILESET_TEMPLATE, configuredFontNames, fontLibrary, fonts, readManifest, tilesetTemplate };
