'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const androidPackage = require('./android-dev-package');

function fixture() {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-android-package-'));
    const projectDir = path.join(root, 'project');
    const loveAndroidDir = path.join(root, 'love-android');
    const lovePath = path.join(root, 'Second Gate.love');
    fs.mkdirSync(path.join(projectDir, 'data'), { recursive: true });
    fs.mkdirSync(loveAndroidDir, { recursive: true });
    fs.writeFileSync(path.join(projectDir, 'data', 'project.json'), JSON.stringify({
        schemaVersion: 1,
        name: 'Second Gate',
        identity: 'SecondGate',
        productName: 'Second Gate',
        executableName: 'Second Gate',
        buildSlug: 'second-gate',
        windowTitle: 'Second Gate',
        productVersion: '0.0.0-dev',
        android: {
            applicationId: 'io.github.josephserusp.secondgate',
            displayName: 'Second Gate',
            orientation: 'landscape',
        },
    }, null, 2));
    fs.writeFileSync(path.join(loveAndroidDir, 'gradle.properties'), [
        '#app.name=LÖVE for Android',
        'app.name_byte_array=76,195,150,86,69',
        '',
        'app.application_id=org.love2d.android',
        'app.orientation=landscape',
        'app.version_code=32',
        'app.version_name=11.5a',
        '',
        'android.useAndroidX=true',
        '',
    ].join('\n'));
    fs.writeFileSync(lovePath, Buffer.from([0x50, 0x4b, 0x03, 0x04, 1, 2, 3]));
    return { root, projectDir, loveAndroidDir, lovePath };
}

test('prepares one dev app around the canonical .love export', () => {
    const f = fixture();
    const manifestPath = path.join(f.root, 'android-build.json');
    const result = androidPackage.prepareAndroidDevPackage({
        projectDir: f.projectDir,
        loveAndroidDir: f.loveAndroidDir,
        lovePath: f.lovePath,
        versionCode: '1790870400',
        sourceSha: '3acc8c1eae5dce07815554373ceba22a946d17a8',
        loveAndroidRef: '55feb38fa144f4734c26742389f279fb07d955c0',
        manifestPath,
    });

    assert.equal(result.manifest.applicationId, 'io.github.josephserusp.secondgate.dev');
    assert.equal(result.manifest.displayName, 'Second Gate Dev');
    assert.equal(result.manifest.versionCode, 1790870400);
    assert.equal(result.manifest.versionName, '0.0.0-dev+android.1790870400.3acc8c1');
    assert.equal(result.manifest.orientation, 'landscape');

    const properties = fs.readFileSync(path.join(f.loveAndroidDir, 'gradle.properties'), 'utf8');
    assert.match(properties, /^app\.name=Second Gate Dev$/m);
    assert.match(properties, /^app\.application_id=io\.github\.josephserusp\.secondgate\.dev$/m);
    assert.match(properties, /^app\.version_code=1790870400$/m);
    assert.match(properties, /^app\.version_name=0\.0\.0-dev\+android\.1790870400\.3acc8c1$/m);
    assert.doesNotMatch(properties, /^app\.name_byte_array=/m);

    const embedded = fs.readFileSync(result.embedPath);
    assert.deepEqual(embedded, fs.readFileSync(f.lovePath));
    assert.deepEqual(JSON.parse(fs.readFileSync(manifestPath, 'utf8')), result.manifest);
});

test('rejects package ids that would make Android identity ambiguous', () => {
    const f = fixture();
    const file = path.join(f.projectDir, 'data', 'project.json');
    const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
    raw.android.applicationId = 'Second Gate';
    fs.writeFileSync(file, JSON.stringify(raw));
    assert.throws(() => androidPackage.readAndroidMetadata(f.projectDir), /lowercase dotted Android package id/);
});

test('rejects invalid or exhausted Android version codes', () => {
    assert.throws(() => androidPackage.normalizeVersionCode('0'), /between 1/);
    assert.throws(() => androidPackage.normalizeVersionCode('2100000001'), /between 1/);
    assert.throws(() => androidPackage.normalizeVersionCode('12.5'), /positive integer/);
    assert.equal(androidPackage.normalizeVersionCode('42'), 42);
});
