'use strict';

// #391: one explicit resource boundary for generic Studio authoring previews.
// Project-local resources remain first-class. Only after that do we consult the
// exact RTP revision pinned by the opened Project; there is no campaign or
// development-Project fallback here.
const fs = require('fs');
const path = require('path');
const rtpResources = require('../export/rtp-resource-resolver');

function tilesetTemplate(projectRoot, rtpRoot) {
    const system = rtpResources.projectSystem(projectRoot).value;
    return rtpResources.tilesetTemplate({
        projectDir: projectRoot,
        systemValue: system,
        rtpRoot,
    });
}

function fontNames(projectRoot, rtpRoot) {
    const projectFonts = path.join(projectRoot, 'assets', 'fonts');
    let local = [];
    try {
        local = fs.readdirSync(projectFonts)
            .filter(name => /\.(ttf|otf)$/i.test(name))
            .map(name => name.replace(/\.(ttf|otf)$/i, ''));
    } catch (error) {}

    const system = rtpResources.projectSystem(projectRoot).value;
    const names = new Set(local);
    for (const resource of rtpResources.fontLibrary({ systemValue: system, rtpRoot })) {
        names.add(resource.name);
    }
    return ['Lucida', ...Array.from(names).sort((a, b) => a.localeCompare(b))];
}

module.exports = { fontNames, tilesetTemplate };
