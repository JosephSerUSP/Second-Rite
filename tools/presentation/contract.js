'use strict';

// #967: the presentation contract, published for a non-LOVE host.
//
// The LOVE renderer reads `runtime/presentation/presentation.json` through
// `presentation/presentation_contract.lua`. This module reads the SAME file
// for the browser adapter (#968), joins it to the Project's authored UI
// configuration and to the resolved system assets, and stamps the result with
// a content identity.
//
// What this module is NOT: a place to decide anything. It publishes facts that
// already have an authored home. If a value is not in the installation
// contract or in the Project's data/system.json, it does not appear here --
// there are no defaults invented at this layer, because a default invented
// here would be a second presentation authority by another name.
//
// Ownership is resolved through the existing exporter boundary rather than
// restated: `tools/export/rtp-baseline-resources.js` already knows whether a
// font came from the Project or the pinned RTP revision, and carries its
// provenance record.

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const baseline = require('../export/rtp-baseline-resources');

const CONTRACT_RELATIVE = path.posix.join('presentation', 'presentation.json');
const SYSTEM_RELATIVE = path.posix.join('data', 'system.json');
const SYSTEM_ASSET_DIR = path.posix.join('assets', 'system');

// The Project-authored UI facts the adapter needs. Deliberately an allowlist:
// system.json also carries combat, growth and spawn policy, and publishing it
// wholesale would hand gameplay configuration to a presentation consumer.
const UI_KEYS = [
    'activeFont', 'fontSize', 'fontOffsetY', 'fontNormalize',
    'textPalette', 'textRevealDelay',
    'menuSlideDuration', 'moveTransitionDuration', 'turnTransitionDuration',
    'inputCooldown', 'autoRepeatInitial', 'autoRepeatInterval',
    'bumpDuration', 'bumpCooldown', 'bumpNudge',
];

// LOVE's built-in default face. It has no file on disk, so an adapter must
// render it as an explicit "engine default" rather than substituting a face of
// its own choosing -- a substituted font is a silently wrong answer to
// "what will this look like in the game?".
const ENGINE_DEFAULT_FONT = 'Lucida';

function readJson(file, label) {
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {
        throw new Error(`${label} is missing: ${file}`);
    }
    const raw = fs.readFileSync(file, 'utf8');
    try {
        return JSON.parse(raw);
    } catch (error) {
        throw new Error(`${label} is not valid JSON: ${file}: ${error.message}`);
    }
}

function sha256File(file) {
    return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

// `_comment` keys carry the authoring rationale for a human reading the
// contract. They are not facts, and shipping them would make the published
// identity churn on a comment edit.
function stripComments(value) {
    if (Array.isArray(value)) return value.map(stripComments);
    if (!value || typeof value !== 'object') return value;
    const out = {};
    for (const key of Object.keys(value)) {
        if (key === '_comment') continue;
        out[key] = stripComments(value[key]);
    }
    return out;
}

// Deterministic serialization for hashing: key order must not depend on
// insertion order, or the same facts would produce two identities.
function canonical(value) {
    if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
}

function requireRect(rect, label) {
    for (const key of ['x', 'y', 'w', 'h']) {
        const component = rect && rect[key];
        if (!Number.isInteger(component) || component < 0) {
            throw new Error(`${label}.${key} must be a non-negative integer`);
        }
    }
    if (rect.w === 0 || rect.h === 0) throw new Error(`${label} has zero area`);
}

function validateInstallation(value, file) {
    if (!value || typeof value !== 'object') throw new Error(`presentation contract is not an object: ${file}`);
    if (value.version !== 1) throw new Error(`presentation contract declares unsupported version ${value.version}: ${file}`);
    for (const group of ['metrics', 'atlas', 'palettes']) {
        if (!value[group] || typeof value[group] !== 'object') {
            throw new Error(`presentation contract is missing '${group}': ${file}`);
        }
    }
    for (const [atlasName, atlas] of Object.entries(value.atlas)) {
        if (!atlas.parts || typeof atlas.parts !== 'object') {
            throw new Error(`presentation contract atlas '${atlasName}' declares no parts: ${file}`);
        }
        for (const [partName, rect] of Object.entries(atlas.parts)) {
            requireRect(rect, `atlas.${atlasName}.parts.${partName}`);
        }
    }
    return value;
}

// A system asset the renderer looks for by name. Presence is REPORTED, never
// papered over: `ui.init` deliberately degrades from a missing windowskin
// (a panel wearing the wrong skin beats a panel that draws nothing), and the
// adapter has to be able to make the same honest choice, and to show the
// viewer that it did. An asset that is absent is `available: false` with a
// reason -- it is never quietly dropped from the list.
function systemAsset(projectDir, name, role) {
    const logicalPath = `${SYSTEM_ASSET_DIR}/${name}.png`;
    const sourcePath = path.resolve(projectDir, ...logicalPath.split('/'));
    const present = fs.existsSync(sourcePath) && fs.statSync(sourcePath).isFile();
    return {
        resource: 'system-image',
        role,
        name,
        logicalPath,
        available: present,
        sha256: present ? sha256File(sourcePath) : null,
        provider: { kind: 'project', id: 'project' },
        ...(present ? {} : { unavailableReason: `Project does not provide ${logicalPath}` }),
    };
}

/**
 * Build the published presentation contract for one Project.
 *
 * @param {string} projectDir  Project root (the directory holding data/ and assets/).
 * @param {string} runtimeDir  Thestra installation runtime root (holds presentation/).
 * @param {string} [rtpRoot]   Installed RTP root; defaults to <runtimeDir>/rtp.
 */
function build({ projectDir, runtimeDir, rtpRoot }) {
    if (!projectDir) throw new Error('presentation contract requires projectDir');
    if (!runtimeDir) throw new Error('presentation contract requires runtimeDir');

    const installationPath = path.resolve(runtimeDir, ...CONTRACT_RELATIVE.split('/'));
    const installation = stripComments(
        validateInstallation(readJson(installationPath, 'installation presentation contract'), installationPath));

    const systemPath = path.resolve(projectDir, ...SYSTEM_RELATIVE.split('/'));
    const system = readJson(systemPath, 'Project system.json');
    const ui = (system && system.ui) || {};

    const revision = system && system.rtp && system.rtp.revision;
    const resolvedRtpRoot = rtpRoot || path.join(runtimeDir, 'rtp');

    // Fonts resolve through the exporter's ownership authority, which throws
    // when a configured font exists in neither the Project nor the pinned RTP
    // revision. That throw is the fail-visible behaviour the audit asks for:
    // an adapter must not start up quietly against a font it cannot load.
    const fonts = baseline.fonts({ projectDir, systemValue: system, revision, rtpRoot: resolvedRtpRoot })
        .map(entry => ({
            resource: 'font',
            name: entry.name,
            logicalPath: entry.logicalPath,
            available: true,
            sha256: sha256File(entry.sourcePath),
            provider: entry.provider,
            ...(entry.provenance ? { provenance: entry.provenance } : {}),
        }));

    const roles = installation.atlas.windowskin.roles || {};
    const assets = [
        ...Object.entries(roles).map(([role, name]) => systemAsset(projectDir, name, `windowskin.${role}`)),
        systemAsset(projectDir, installation.atlas.target.image, 'target'),
        systemAsset(projectDir, 'iconset', 'iconset'),
        systemAsset(projectDir, 'Cursor', 'cursor'),
        ...fonts,
    ];

    const project = {};
    for (const key of UI_KEYS) {
        if (ui[key] !== undefined) project[key] = ui[key];
    }
    // The active font names a face; say which resolved file (if any) carries
    // it, so the adapter never has to guess the mapping itself.
    const activeFont = project.activeFont || ENGINE_DEFAULT_FONT;
    const activeEntry = fonts.find(entry => entry.name === activeFont) || null;

    const published = {
        version: 1,
        metrics: installation.metrics,
        atlas: installation.atlas,
        palettes: installation.palettes,
        project,
        font: {
            active: activeFont,
            engineDefault: activeFont === ENGINE_DEFAULT_FONT,
            logicalPath: activeEntry ? activeEntry.logicalPath : null,
            provider: activeEntry ? activeEntry.provider : null,
        },
        rtp: revision ? { revision } : null,
        assets,
    };

    // Identity covers every contributing input by construction: the
    // installation facts, the Project's authored UI values, the RTP revision,
    // and each asset's own content digest are all inside the object being
    // hashed. A browser cache keyed on this cannot serve a stale theme.
    const identity = crypto.createHash('sha256').update(canonical(published)).digest('hex');
    return { ...published, identity };
}

module.exports = {
    CONTRACT_RELATIVE,
    ENGINE_DEFAULT_FONT,
    SYSTEM_ASSET_DIR,
    UI_KEYS,
    build,
    canonical,
};
