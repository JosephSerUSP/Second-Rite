\
'use strict';

// #391: materialize only player-facing RTP files selected by typed resolution.
// The installed RTP tree itself is never copied into a player build.
const fs = require('fs');
const path = require('path');
const rtpResources = require('./rtp-resource-resolver');

function copySelected(source, destination) {
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
}

function materialize({ stageDir, projectDir, systemValue, rtpRoot } = {}) {
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

    return { fonts };
}

module.exports = { materialize };
