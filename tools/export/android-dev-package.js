'use strict';

// #1305: explicit Android packaging adapter over the canonical .love export.
// This module does not stage or compile a Project. It consumes the .love that
// tools/export/export-game.js already produced and configures a pinned
// love-android checkout around it. Gradle/application identity therefore stays
// outside runtime/gameplay code while Project-owned Android metadata remains
// beside the rest of the Project identity.
const fs = require('fs');
const path = require('path');
const projectIdentity = require('./project-identity');

const PROJECT_IDENTITY_RELATIVE = path.join('data', 'project.json');
const MAX_ANDROID_VERSION_CODE = 2100000000;
const APPLICATION_ID_RE = /^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$/;
const RECORD_AUDIO_PERMISSION = 'android.permission.RECORD_AUDIO';

function nonEmpty(value, label) {
    if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} must be a non-empty string`);
    return value.trim();
}

function readAndroidMetadata(projectDir) {
    if (!projectDir) throw new Error('readAndroidMetadata requires projectDir');
    const sourcePath = path.join(path.resolve(projectDir), PROJECT_IDENTITY_RELATIVE);
    const raw = JSON.parse(fs.readFileSync(sourcePath, 'utf8'));
    const android = raw && raw.android;
    if (!android || typeof android !== 'object' || Array.isArray(android)) {
        throw new Error(`Project Android metadata is missing from ${sourcePath}`);
    }

    const applicationId = nonEmpty(android.applicationId, 'Project android.applicationId');
    if (!APPLICATION_ID_RE.test(applicationId)) {
        throw new Error('Project android.applicationId must be a lowercase dotted Android package id');
    }
    const displayName = nonEmpty(android.displayName, 'Project android.displayName');
    const orientation = nonEmpty(android.orientation || 'landscape', 'Project android.orientation');
    return Object.freeze({ applicationId, displayName, orientation });
}

function normalizeVersionCode(value) {
    const text = String(value == null ? '' : value).trim();
    if (!/^\d+$/.test(text)) throw new Error('Android versionCode must be a positive integer');
    const versionCode = Number(text);
    if (!Number.isSafeInteger(versionCode) || versionCode < 1 || versionCode > MAX_ANDROID_VERSION_CODE) {
        throw new Error(`Android versionCode must be between 1 and ${MAX_ANDROID_VERSION_CODE}`);
    }
    return versionCode;
}

function normalizeSourceSha(value) {
    const sourceSha = nonEmpty(value, 'source SHA').toLowerCase();
    if (!/^[0-9a-f]{7,40}$/.test(sourceSha)) throw new Error('source SHA must be a 7-40 digit hexadecimal Git SHA');
    return sourceSha;
}

function setGradleProperty(lines, key, value) {
    const prefix = `${key}=`;
    const matches = [];
    for (let i = 0; i < lines.length; i += 1) {
        if (lines[i].startsWith(prefix)) matches.push(i);
    }
    if (matches.length > 1) throw new Error(`love-android gradle.properties repeats ${key}`);
    const line = `${key}=${value}`;
    if (matches.length === 1) {
        lines[matches[0]] = line;
        return;
    }
    lines.push(line);
}

function configureGradleProperties(filePath, values) {
    const original = fs.readFileSync(filePath, 'utf8');
    const lines = original.replace(/\r\n/g, '\n').split('\n');

    // Upstream 11.5a enables app.name_byte_array and comments app.name. Android
    // rejects defining both, so the adapter owns exactly one display-name form.
    for (let i = 0; i < lines.length; i += 1) {
        if (lines[i].startsWith('app.name_byte_array=')) {
            lines[i] = '# app.name_byte_array disabled by Thestra Android packaging adapter';
        }
    }

    setGradleProperty(lines, 'app.name', values.displayName);
    setGradleProperty(lines, 'app.application_id', values.applicationId);
    setGradleProperty(lines, 'app.orientation', values.orientation);
    setGradleProperty(lines, 'app.version_code', String(values.versionCode));
    setGradleProperty(lines, 'app.version_name', values.versionName);
    fs.writeFileSync(filePath, `${lines.join('\n').replace(/\n+$/, '')}\n`, 'utf8');
}

function stripManifestPermission(filePath, permission) {
    const original = fs.readFileSync(filePath, 'utf8');
    const escaped = permission.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`^[ \\t]*<uses-permission\\s+android:name=["']${escaped}["']\\s*/>[ \\t]*(?:\\r?\\n|$)`, 'gm');
    const matches = original.match(pattern) || [];
    if (matches.length !== 1) {
        throw new Error(`Expected exactly one ${permission} declaration in pinned love-android manifest; found ${matches.length}`);
    }
    fs.writeFileSync(filePath, original.replace(pattern, ''), 'utf8');
}

function prepareAndroidDevPackage({ projectDir, loveAndroidDir, lovePath, versionCode,
        sourceSha, loveAndroidRef, manifestPath } = {}) {
    if (!projectDir || !loveAndroidDir || !lovePath) {
        throw new Error('prepareAndroidDevPackage requires projectDir, loveAndroidDir, and lovePath');
    }
    const projectRoot = path.resolve(projectDir);
    const wrapperRoot = path.resolve(loveAndroidDir);
    const gameLove = path.resolve(lovePath);
    if (!fs.existsSync(gameLove) || !fs.statSync(gameLove).isFile()) {
        throw new Error(`Canonical .love export is missing: ${gameLove}`);
    }

    const identity = projectIdentity.readProjectIdentity(projectRoot);
    const android = readAndroidMetadata(projectRoot);
    const resolvedVersionCode = normalizeVersionCode(versionCode);
    const resolvedSourceSha = normalizeSourceSha(sourceSha);
    const resolvedLoveAndroidRef = nonEmpty(loveAndroidRef, 'love-android ref');
    const applicationId = `${android.applicationId}.dev`;
    const displayName = `${android.displayName} Dev`;
    const versionName = `${identity.productVersion}+android.${resolvedVersionCode}.${resolvedSourceSha.slice(0, 7)}`;

    const propertiesPath = path.join(wrapperRoot, 'gradle.properties');
    if (!fs.existsSync(propertiesPath)) throw new Error(`love-android gradle.properties is missing: ${propertiesPath}`);
    configureGradleProperties(propertiesPath, {
        applicationId,
        displayName,
        orientation: android.orientation,
        versionCode: resolvedVersionCode,
        versionName,
    });

    // Upstream 11.5a's noRecord flavor disables microphone support in the
    // native runtime but leaves RECORD_AUDIO in the common application
    // manifest. Second Gate has no microphone feature, so do not ask Android
    // for a capability the game cannot use. Keep this as an explicit pinned-
    // wrapper patch and fail loudly if the upstream manifest shape changes.
    const androidManifestPath = path.join(wrapperRoot, 'app', 'src', 'main', 'AndroidManifest.xml');
    if (!fs.existsSync(androidManifestPath)) {
        throw new Error(`love-android application manifest is missing: ${androidManifestPath}`);
    }
    stripManifestPermission(androidManifestPath, RECORD_AUDIO_PERMISSION);

    const embedPath = path.join(wrapperRoot, 'app', 'src', 'embed', 'assets', 'game.love');
    fs.mkdirSync(path.dirname(embedPath), { recursive: true });
    fs.copyFileSync(gameLove, embedPath);

    const manifest = {
        schemaVersion: 1,
        channel: 'dev',
        applicationId,
        displayName,
        orientation: android.orientation,
        versionCode: resolvedVersionCode,
        versionName,
        microphonePermission: false,
        projectIdentity: identity.identity,
        projectVersion: identity.productVersion,
        sourceSha: resolvedSourceSha,
        loveAndroidRef: resolvedLoveAndroidRef,
        loveArtifact: path.basename(gameLove),
    };
    if (manifestPath) {
        const output = path.resolve(manifestPath);
        fs.mkdirSync(path.dirname(output), { recursive: true });
        fs.writeFileSync(output, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
    }
    return { manifest, embedPath, propertiesPath, androidManifestPath };
}

function parseArgs(argv) {
    const options = {};
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === '--project') options.projectDir = argv[++i] || '';
        else if (arg === '--love-android') options.loveAndroidDir = argv[++i] || '';
        else if (arg === '--love') options.lovePath = argv[++i] || '';
        else if (arg === '--version-code') options.versionCode = argv[++i] || '';
        else if (arg === '--source-sha') options.sourceSha = argv[++i] || '';
        else if (arg === '--love-android-ref') options.loveAndroidRef = argv[++i] || '';
        else if (arg === '--manifest') options.manifestPath = argv[++i] || '';
        else if (arg === '--help' || arg === '-h') return null;
        else throw new Error(`Unknown argument: ${arg}`);
    }
    return options;
}

function main() {
    const options = parseArgs(process.argv.slice(2));
    if (!options) {
        console.log('Usage: node tools/export/android-dev-package.js --project dir --love-android dir --love game.love --version-code N --source-sha SHA --love-android-ref REF [--manifest file]');
        return;
    }
    const result = prepareAndroidDevPackage(options);
    console.log(`ANDROID PACKAGE CONFIG OK: ${result.manifest.applicationId} ${result.manifest.versionName}`);
}

if (require.main === module) {
    try { main(); }
    catch (error) {
        console.error(error && error.stack ? error.stack : String(error));
        process.exitCode = 1;
    }
}

module.exports = {
    APPLICATION_ID_RE,
    MAX_ANDROID_VERSION_CODE,
    RECORD_AUDIO_PERMISSION,
    configureGradleProperties,
    normalizeSourceSha,
    normalizeVersionCode,
    parseArgs,
    prepareAndroidDevPackage,
    readAndroidMetadata,
    stripManifestPermission,
};
