'use strict';

// Pure Project-path -> semantic invalidation classification.
//
// A future filesystem watcher owns only generic observation/coalescing. This
// module owns the Thestra question that follows: "what semantic Project thing
// changed?" It deliberately returns resource identity or asset identity, never
// parsed authored values. Renderers continue to re-read authority through the
// existing resource-commit refresh seam.

const path = require('path');
const authoredStorage = require('./authored-storage-physical');

function relativeSegments(relativePath) {
    if (typeof relativePath !== 'string' || relativePath.length === 0) return null;

    // This helper is intentionally host-independent because tests/tooling may
    // hand it either slash convention. Absolute filesystem paths go through
    // classifyProjectPath(), which uses the current host's path semantics first.
    const portable = relativePath.replace(/\\/g, '/');
    if (portable.startsWith('/') || portable.startsWith('//') || /^[A-Za-z]:\//.test(portable)) {
        return null;
    }

    const segments = [];
    for (const segment of portable.split('/')) {
        if (!segment || segment === '.') continue;
        if (segment === '..') return null;
        segments.push(segment);
    }
    return segments.length > 0 ? segments : null;
}

function resourceForDataSegments(segments, manifest) {
    if (segments.length < 2 || segments[0] !== 'data') return null;
    const resources = manifest && manifest.resources;
    if (!resources || Array.isArray(resources) || typeof resources !== 'object') return null;

    // Monolith authority is exactly data/<stem>.json. A neighboring directory
    // named after the same stem is not secretly another representation.
    if (segments.length === 2) {
        const filename = segments[1];
        if (!filename.endsWith('.json')) return null;
        const stem = filename.slice(0, -5);
        const spec = resources[stem];
        return spec && spec.representation === 'monolith' ? stem : null;
    }

    // Fragment-backed resources own only direct JSON children. Current ordered,
    // registry and semantic-config physical contracts all forbid/ignore nested
    // fragment paths, so a watcher must not manufacture authority for them.
    if (segments.length === 3) {
        const stem = segments[1];
        const filename = segments[2];
        const spec = resources[stem];
        if (!spec || spec.representation !== 'fragments') return null;
        if (!filename.toLowerCase().endsWith('.json')) return null;
        return stem;
    }

    return null;
}

function classifyProjectRelativePath(relativePath, manifest = authoredStorage.loadManifest()) {
    const segments = relativeSegments(relativePath);
    if (!segments) return null;

    const resource = resourceForDataSegments(segments, manifest);
    if (resource) {
        return {
            kind: 'resource',
            resource,
            relativePath: segments.join('/'),
        };
    }

    // Assets are a distinct invalidation class because the existing
    // resource-commit protocol only accepts semantic authored-resource names.
    // A future watcher/consumer can decide whether a changed asset requires a
    // thumbnail refresh, viewport invalidation, or runtime recompile without
    // pretending the asset itself is a database resource.
    if (segments[0] === 'assets' && segments.length >= 2) {
        return {
            kind: 'asset',
            assetPath: segments.slice(1).join('/'),
            relativePath: segments.join('/'),
        };
    }

    return null;
}

function classifyProjectPath(projectRoot, filePath, manifest = authoredStorage.loadManifest()) {
    if (typeof projectRoot !== 'string' || !projectRoot) return null;
    if (typeof filePath !== 'string' || !filePath) return null;

    const root = path.resolve(projectRoot);
    const target = path.resolve(filePath);
    const relative = path.relative(root, target);

    // Prefix-string containment is unsafe (/project vs /project-copy). A real
    // path.relative result that escapes or stays absolute is outside Project.
    if (!relative || path.isAbsolute(relative)
            || relative === '..' || relative.startsWith('..' + path.sep)) {
        return null;
    }
    return classifyProjectRelativePath(relative, manifest);
}

function resourceNamesForProjectPaths(projectRoot, filePaths, manifest = authoredStorage.loadManifest()) {
    const resources = new Set();
    for (const filePath of filePaths || []) {
        const invalidation = classifyProjectPath(projectRoot, filePath, manifest);
        if (invalidation && invalidation.kind === 'resource') resources.add(invalidation.resource);
    }
    return Array.from(resources);
}

module.exports = {
    classifyProjectPath,
    classifyProjectRelativePath,
    resourceNamesForProjectPaths,
};
