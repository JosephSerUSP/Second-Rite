'use strict';

// #389: first deliberately typed RTP resolution seam.
//
// This module does NOT expose a directory overlay. It resolves two named
// authored resources with different ownership policies:
//   - system: Project-required, never inherited;
//   - sounds: Project-local -> one explicit Package contribution -> pinned RTP.
//
// The RTP root is only an installation lookup root. Identity comes from the
// Project's exact `system.rtp.revision` pin, never from whichever revision is
// newest or otherwise happens to be installed.
const fs = require('fs');
const path = require('path');

const RTP_ROOT_ENV = 'THESTRA_RTP_ROOT';
const SYSTEM_RELATIVE = path.join('data', 'system.json');
const SOUNDS_RELATIVE = path.join('data', 'sounds.json');

function readJson(filePath, label) {
    try {
        return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (error) {
        throw new Error(`${label} is not readable JSON: ${filePath}: ${error.message}`);
    }
}

function projectSystem(projectDir) {
    if (!projectDir) throw new Error('projectSystem requires projectDir');
    const sourcePath = path.resolve(projectDir, SYSTEM_RELATIVE);
    if (!fs.existsSync(sourcePath) || !fs.statSync(sourcePath).isFile()) {
        throw new Error(`Project-required resource is missing: ${SYSTEM_RELATIVE} (${sourcePath})`);
    }
    return {
        resource: 'system',
        logicalPath: SYSTEM_RELATIVE,
        sourcePath,
        provider: { kind: 'project', id: 'project' },
        value: readJson(sourcePath, 'Project system resource'),
    };
}

function pinnedRevision(systemValue) {
    const rtp = systemValue && systemValue.rtp;
    if (rtp === undefined) return null;
    if (!rtp || typeof rtp !== 'object' || Array.isArray(rtp)
            || typeof rtp.revision !== 'string' || !rtp.revision.trim()) {
        throw new Error('Project system.rtp.revision must be a non-empty string when RTP inheritance is declared');
    }
    const revision = rtp.revision.trim();
    if (revision === '.' || revision === '..' || !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(revision)) {
        throw new Error(`Project system.rtp.revision is not a safe revision identifier: ${JSON.stringify(revision)}`);
    }
    return revision;
}

function packageSoundContribution(packageContributions) {
    if (packageContributions === undefined) return null;
    if (!Array.isArray(packageContributions)) throw new Error('packageContributions must be an array');
    const matches = packageContributions.filter(entry => entry && entry.resource === 'sounds');
    if (matches.length > 1) {
        throw new Error('Multiple Package contributions for sounds require an explicit collision rule; none is defined by #389');
    }
    if (!matches.length) return null;
    const contribution = matches[0];
    if (typeof contribution.packageId !== 'string' || !contribution.packageId.trim()) {
        throw new Error('Package sounds contribution requires packageId');
    }
    if (typeof contribution.file !== 'string' || !contribution.file) {
        throw new Error(`Package ${contribution.packageId} sounds contribution requires file`);
    }
    const sourcePath = path.resolve(contribution.file);
    if (!fs.existsSync(sourcePath) || !fs.statSync(sourcePath).isFile()) {
        throw new Error(`Package ${contribution.packageId} sounds contribution is missing: ${sourcePath}`);
    }
    return {
        resource: 'sounds',
        logicalPath: SOUNDS_RELATIVE,
        sourcePath,
        provider: { kind: 'package', id: contribution.packageId },
    };
}

function sounds({ projectDir, systemValue, rtpRoot = process.env[RTP_ROOT_ENV], packageContributions } = {}) {
    if (!projectDir) throw new Error('sounds resolver requires projectDir');

    const projectPath = path.resolve(projectDir, SOUNDS_RELATIVE);
    if (fs.existsSync(projectPath) && fs.statSync(projectPath).isFile()) {
        return {
            resource: 'sounds',
            logicalPath: SOUNDS_RELATIVE,
            sourcePath: projectPath,
            provider: { kind: 'project', id: 'project' },
        };
    }

    const packageResource = packageSoundContribution(packageContributions);
    if (packageResource) return packageResource;

    const revision = pinnedRevision(systemValue);
    if (!revision) return null; // Backward-compatible Project: no pin means no RTP lookup.
    if (!rtpRoot) {
        throw new Error(`Project pins RTP revision ${revision}, but no RTP installation root was provided (set ${RTP_ROOT_ENV})`);
    }

    const revisionRoot = path.resolve(rtpRoot, 'revisions', revision);
    const sourcePath = path.resolve(revisionRoot, SOUNDS_RELATIVE);
    if (sourcePath !== revisionRoot && !sourcePath.startsWith(revisionRoot + path.sep)) {
        throw new Error(`Pinned RTP resource escaped revision root: ${sourcePath}`);
    }
    if (!fs.existsSync(sourcePath) || !fs.statSync(sourcePath).isFile()) {
        throw new Error(`Pinned RTP revision ${revision} does not provide inherited sounds: ${sourcePath}`);
    }
    return {
        resource: 'sounds',
        logicalPath: SOUNDS_RELATIVE,
        sourcePath,
        provider: { kind: 'rtp', id: 'thestra-rtp', revision },
    };
}

module.exports = {
    RTP_ROOT_ENV,
    SOUNDS_RELATIVE,
    SYSTEM_RELATIVE,
    packageSoundContribution,
    pinnedRevision,
    projectSystem,
    sounds,
};
