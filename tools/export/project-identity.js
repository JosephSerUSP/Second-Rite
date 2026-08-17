'use strict';

// #699: player-facing identity belongs to the Project, not to the installed
// Thestra runtime/exporter. Projects may author data/project.json; when they do
// not, neutral defaults derive only from that Project's directory name.
const fs = require('fs');
const path = require('path');

const PROJECT_IDENTITY_RELATIVE = path.join('data', 'project.json');
const DEFAULT_PRODUCT_VERSION = '0.0.0-dev';
const RESERVED_PATH_CHARS = /[\\/:*?"<>|]/;

function nonEmpty(value, label) {
    if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} must be a non-empty string`);
    return value.trim();
}

function authoredOr(raw, key, fallback) {
    return Object.prototype.hasOwnProperty.call(raw, key) ? raw[key] : fallback;
}

function slugify(value) {
    const slug = String(value || '')
        .trim()
        .replace(/[^A-Za-z0-9._-]+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^[-.]+|[-.]+$/g, '');
    return slug || 'project';
}

function safeArtifactName(value, label) {
    const name = nonEmpty(value, label);
    if (name === '.' || name === '..' || RESERVED_PATH_CHARS.test(name)) {
        throw new Error(`${label} must not contain path separators or reserved characters`);
    }
    return name;
}

function normalizeIdentity(raw, fallbackName) {
    const name = nonEmpty(authoredOr(raw, 'name', fallbackName), 'Project identity name');
    const identity = nonEmpty(authoredOr(raw, 'identity', slugify(name)), 'Project LÖVE identity');
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(identity)) {
        throw new Error('Project LÖVE identity must use only letters, numbers, dot, underscore, and hyphen');
    }
    const productName = safeArtifactName(authoredOr(raw, 'productName', name), 'Project productName');
    const executableName = safeArtifactName(authoredOr(raw, 'executableName', productName), 'Project executableName');
    const buildSlug = safeArtifactName(authoredOr(raw, 'buildSlug', slugify(productName)), 'Project buildSlug');
    const windowTitle = nonEmpty(authoredOr(raw, 'windowTitle', productName), 'Project windowTitle');
    const productVersion = nonEmpty(authoredOr(raw, 'productVersion', DEFAULT_PRODUCT_VERSION), 'Project productVersion');
    return Object.freeze({
        name,
        identity,
        productName,
        executableName,
        buildSlug,
        windowTitle,
        productVersion,
    });
}

function readProjectIdentity(projectDir) {
    if (!projectDir) throw new Error('readProjectIdentity requires projectDir');
    const root = path.resolve(projectDir);
    const sourcePath = path.join(root, PROJECT_IDENTITY_RELATIVE);
    const fallbackName = path.basename(root) || 'Project';
    if (!fs.existsSync(sourcePath)) return normalizeIdentity({}, fallbackName);

    let raw;
    try {
        raw = JSON.parse(fs.readFileSync(sourcePath, 'utf8'));
    } catch (error) {
        throw new Error(`Project identity is not readable JSON: ${sourcePath}: ${error.message}`);
    }
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
        throw new Error(`Project identity must be an object: ${sourcePath}`);
    }
    if (raw.schemaVersion !== 1) {
        throw new Error(`Unsupported Project identity schemaVersion: ${raw.schemaVersion}`);
    }
    return normalizeIdentity(raw, fallbackName);
}

module.exports = {
    DEFAULT_PRODUCT_VERSION,
    PROJECT_IDENTITY_RELATIVE,
    authoredOr,
    normalizeIdentity,
    readProjectIdentity,
    safeArtifactName,
    slugify,
};
