'use strict';

const fs = require('fs');
const path = require('path');
const rtp = require('./rtp-resource-resolver');
const engine = require('./engine-registry-resolver');
const defaults = require('./authored-default-resolver');

function copy(source, destination) {
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
}

function put(filePath, value) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + '\n');
}

function publicResolution(resource) {
    if (!resource) return null;
    return {
        resource: resource.resource,
        provider: resource.provider,
        ...(resource.sources ? {
            sources: resource.sources.map(source => ({ provider: source.provider, logicalPath: source.logicalPath })),
        } : {}),
    };
}

function hasEngineResource(projectDir, systemValue, rtpRoot) {
    const projectPath = path.resolve(projectDir, 'data', 'engine.json');
    if (fs.existsSync(projectPath)) return true;
    const revision = rtp.pinnedRevision(systemValue);
    if (!revision) return false;
    const manifest = rtp.revisionManifest({ systemValue, rtpRoot });
    return Boolean(manifest && manifest.authored && manifest.authored.engineRegistry);
}

function resolveAndMaterialize({ projectDir, runtimeDir, stageDir, rtpRoot, packageContributions }) {
    const system = rtp.projectSystem(projectDir);
    const root = rtpRoot || process.env[rtp.RTP_ROOT_ENV] || path.join(runtimeDir, 'rtp');
    const engineRegistry = hasEngineResource(projectDir, system.value, root)
        ? engine.resolve({ projectDir, systemValue: system.value, rtpRoot: root })
        : null;
    const sounds = rtp.sounds({ projectDir, systemValue: system.value, rtpRoot: root, packageContributions });
    const scenes = defaults.scenes({ projectDir, systemValue: system.value, rtpRoot: root });
    const flows = defaults.flows({ projectDir, systemValue: system.value, rtpRoot: root });

    if (engineRegistry) put(path.join(stageDir, 'data', 'engine.json'), engineRegistry.value);
    if (sounds) copy(sounds.sourcePath, path.join(stageDir, sounds.logicalPath));

    const indexPath = path.join(stageDir, 'data', 'scenes', 'index.json');
    if (scenes.length && fs.existsSync(indexPath)) {
        const parsed = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
        const sourceFiles = Array.isArray(parsed) ? parsed : parsed && parsed.files;
        if (!Array.isArray(sourceFiles)) throw new Error(`Staged Scene index must be an array or { files: [...] }: ${indexPath}`);
        const files = sourceFiles.slice();
        for (const resource of scenes) {
            if (resource.provider.kind !== 'rtp') continue;
            const filename = path.posix.basename(resource.logicalPath.replace(/\\/g, '/'));
            copy(resource.sourcePath, path.join(stageDir, ...resource.logicalPath.replace(/\\/g, '/').split('/')));
            if (!files.includes(filename)) files.push(filename);
        }
        put(indexPath, Array.isArray(parsed) ? files : { ...parsed, files });
    }

    for (const resource of flows) {
        if (resource.provider.kind === 'rtp') {
            copy(resource.sourcePath, path.join(stageDir, ...resource.logicalPath.replace(/\\/g, '/').split('/')));
        }
    }

    const provenance = {
        version: 1,
        materialized: true,
        rtpRevision: rtp.pinnedRevision(system.value),
        resources: {
            engineRegistry: publicResolution(engineRegistry),
            sounds: publicResolution(sounds),
            sceneDefaults: Object.fromEntries(scenes.map(resource => [resource.resource.split(':')[1], publicResolution(resource)])),
            flowDefaults: Object.fromEntries(flows.map(resource => [resource.resource.split(':')[1], publicResolution(resource)])),
        },
    };
    put(path.join(stageDir, 'data', 'authored_resolution.json'), provenance);
    return { system, engineRegistry, sounds, sceneDefaults: scenes, flowDefaults: flows, provenance };
}

module.exports = { publicResolution, resolveAndMaterialize };
