'use strict';

// #521: semantic EditorSurface identity/policy belongs above any one hosting
// mechanism. WindowManager owns native BrowserWindow lifecycle; renderer DOM
// adapters own browser/docked composition. This registry states what the
// first-class surfaces ARE and their multiplicity/hosting policy without making
// BrowserWindow the definition of a surface.
const SURFACES = Object.freeze({
    main: Object.freeze({
        id: 'main',
        displayName: 'Thestra Studio',
        category: 'workspace',
        multiplicity: 'singleton',
        secondary: false,
        productionHost: 'native',
        browserTestHost: 'root-workspace',
        closePolicy: 'studio-shutdown',
    }),
    database: Object.freeze({
        id: 'database',
        displayName: 'Database',
        category: 'editor',
        multiplicity: 'singleton',
        secondary: true,
        productionHost: 'native',
        browserTestHost: 'dom-modal',
        closePolicy: 'resource-transaction',
    }),
    engine: Object.freeze({
        id: 'engine',
        displayName: 'Engine Editor',
        category: 'editor',
        multiplicity: 'singleton',
        secondary: true,
        productionHost: 'native',
        browserTestHost: 'dom-modal',
        closePolicy: 'resource-transaction',
    }),
});

const SURFACE_IDS = Object.freeze(Object.keys(SURFACES));
const SECONDARY_NATIVE_SURFACE_IDS = Object.freeze(
    SURFACE_IDS.filter(id => SURFACES[id].secondary && SURFACES[id].productionHost === 'native')
);

function getSurfacePolicy(surfaceId) {
    return SURFACES[surfaceId] || null;
}

function requireSurfacePolicy(surfaceId) {
    const policy = getSurfacePolicy(surfaceId);
    if (!policy) throw new Error(`Unknown EditorSurface: ${surfaceId}`);
    return policy;
}

module.exports = {
    SURFACES,
    SURFACE_IDS,
    SECONDARY_NATIVE_SURFACE_IDS,
    getSurfacePolicy,
    requireSurfacePolicy,
};
