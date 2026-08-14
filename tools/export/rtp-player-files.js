'use strict';

// #391/#390: materialize only typed RTP resources selected by exact resolution.
// The installed RTP tree itself is never copied wholesale into a player build.
const fs = require('fs');
const path = require('path');
const rtpResources = require('./rtp-resource-resolver');
const authoredDefaults = require('./authored-default-materializer');

function copySelected(source, destination) {
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
}

function materialize({ stageDir, projectDir, systemValue, rtpRoot, runtimeDir } = {}) {
    if (!stageDir || !projectDir) throw new Error('RTP materialization requires stageDir and projectDir');
    const fonts = rtpResources.fonts({ projectDir, systemValue, rtpRoot });
    const notices = new Map();

    for (const resource of fonts) {
        // Project assets were already copied by the normal Project overlay.
        if (resource.provider.kind !== 'rtp') continue;
        copySelected(resource.sourcePath, path.join(stageDir, resource.logicalPath));
        if (!resource.notice) continue;

        const previous = notices.get(resource.notice.logicalPath);
        if (previous && previous !== resource.notice.sourcePath) {
            throw new Error(`RTP license notice collision at ${resource.notice.logicalPath}`);
        }
        notices.set(resource.notice.logicalPath, resource.notice.sourcePath);
        copySelected(resource.notice.sourcePath, path.join(stageDir, resource.notice.logicalPath));
    }

    // Sounds are already materialized by the existing exporter path. Keep that
    // proven precedence untouched here; this hook adds #390's authored classes
    // at the same player-stage boundary.
    const authored = authoredDefaults.resolveAndMaterialize({
        stageDir,
        projectDir,
        runtimeDir: runtimeDir || path.resolve(__dirname, '..', '..'),
        rtpRoot,
        includeSounds: false,
    });

    return { fonts, authored };
}

module.exports = { materialize };
