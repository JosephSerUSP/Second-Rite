'use strict';

const SOURCE_FIELDS = [
    'texture', 'tileWidth', 'tileHeight',
    'heightMap', 'heightMapScale', 'heightMapMeshColumns', 'heightMapMeshRows',
    'heightMapTriangleBudget', 'heightMapSampleColumns', 'heightMapSampleRows',
    'heightMapOperation', 'heightMapOffset',
    'glowMap', 'glowStrength',
];
const ENVIRONMENT_FIELDS = ['skyPanorama'];
const REPRESENTATION_FIELDS = ['atlas', 'middle', 'leftEdge', 'rightEdge', 'geometry', 'model'];
const BASE_ROLES = ['walls', 'floors', 'ceilings', 'skies'];
const KNOWN_TOP_LEVEL = new Set([
    'id', 'name', 'base', 'doors', 'features', 'fixturePrefabs',
    ...SOURCE_FIELDS,
    ...ENVIRONMENT_FIELDS,
]);

function clone(value) {
    return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

function own(object, key) {
    return Object.prototype.hasOwnProperty.call(object, key);
}

function splitVariant(record) {
    const representation = {};
    const properties = {};
    for (const [key, value] of Object.entries(record)) {
        if (REPRESENTATION_FIELDS.includes(key)) representation[key] = clone(value);
        else if (key !== 'id' && key !== 'weight') properties[key] = clone(value);
    }
    return {
        identity: {
            hasId: own(record, 'id'),
            id: clone(record.id),
            hasWeight: own(record, 'weight'),
            weight: clone(record.weight),
        },
        representation,
        properties,
    };
}

function joinVariant(surface, assignment) {
    const record = {};
    if (assignment.identity.hasId) record.id = clone(assignment.identity.id);
    if (assignment.identity.hasWeight) record.weight = clone(assignment.identity.weight);
    Object.assign(record, clone(surface.representation));
    Object.assign(record, clone(assignment.properties));
    return record;
}

function migrateLegacyTileset(legacy) {
    const unknown = Object.keys(legacy).filter(key => !KNOWN_TOP_LEVEL.has(key)).sort();
    if (unknown.length) {
        throw new Error(`${legacy.id || '(unnamed)'}: unclassified top-level fields: ${unknown.join(', ')}`);
    }

    const source = { kind: 'legacyAtlasCompatibility' };
    const sourcePresence = {};
    for (const field of SOURCE_FIELDS) {
        sourcePresence[field] = own(legacy, field);
        if (sourcePresence[field]) source[field] = clone(legacy[field]);
    }

    const environment = {};
    const environmentPresence = {};
    for (const field of ENVIRONMENT_FIELDS) {
        environmentPresence[field] = own(legacy, field);
        if (environmentPresence[field]) environment[field] = clone(legacy[field]);
    }

    const surfaces = {};
    const base = {};
    const basePresence = {};
    const originalBase = legacy.base || {};
    for (const role of BASE_ROLES) {
        basePresence[role] = own(originalBase, role);
        if (!basePresence[role]) continue;
        base[role] = [];
        (originalBase[role] || []).forEach((record, index) => {
            const split = splitVariant(record);
            const surfaceId = `${legacy.id}:${role}:${record.id ?? index}`;
            surfaces[surfaceId] = {
                source: 'legacyAtlas',
                representation: split.representation,
            };
            base[role].push({
                surface: surfaceId,
                identity: split.identity,
                properties: split.properties,
            });
        });
    }

    const doors = [];
    const doorPresence = own(legacy, 'doors');
    (legacy.doors || []).forEach((record, index) => {
        const split = splitVariant(record);
        const surfaceId = `${legacy.id}:doors:${record.id ?? index}`;
        surfaces[surfaceId] = {
            source: 'legacyAtlas',
            representation: split.representation,
        };
        doors.push({
            surface: surfaceId,
            identity: split.identity,
            properties: split.properties,
        });
    });

    return {
        _experimental: '#558 lossless compatibility migration shape; not canonical schema',
        id: clone(legacy.id),
        name: clone(legacy.name),
        sources: { legacyAtlas: source },
        surfaces,
        palette: {
            base,
            doors,
            // Feature/fixture behavior deliberately remains palette-owned in this
            // migration proof. We are testing lossless Surface extraction, not
            // forcing models/predicates into the Surface abstraction.
            features: clone(legacy.features || []),
            fixturePrefabs: clone(legacy.fixturePrefabs || []),
            environment,
        },
        _presence: {
            id: own(legacy, 'id'),
            name: own(legacy, 'name'),
            base: own(legacy, 'base'),
            baseRoles: basePresence,
            doors: doorPresence,
            features: own(legacy, 'features'),
            fixturePrefabs: own(legacy, 'fixturePrefabs'),
            sourceFields: sourcePresence,
            environmentFields: environmentPresence,
        },
    };
}

function compileLegacyTileset(migrated) {
    const presence = migrated._presence;
    const legacy = {};
    if (presence.id) legacy.id = clone(migrated.id);
    if (presence.name) legacy.name = clone(migrated.name);

    const source = migrated.sources.legacyAtlas;
    for (const field of SOURCE_FIELDS) {
        if (presence.sourceFields[field]) legacy[field] = clone(source[field]);
    }

    if (presence.base) {
        legacy.base = {};
        for (const role of BASE_ROLES) {
            if (!presence.baseRoles[role]) continue;
            legacy.base[role] = (migrated.palette.base[role] || []).map(assignment => {
                const surface = migrated.surfaces[assignment.surface];
                if (!surface) throw new Error(`missing Surface ${assignment.surface}`);
                return joinVariant(surface, assignment);
            });
        }
    }

    if (presence.doors) {
        legacy.doors = migrated.palette.doors.map(assignment => {
            const surface = migrated.surfaces[assignment.surface];
            if (!surface) throw new Error(`missing door Surface ${assignment.surface}`);
            return joinVariant(surface, assignment);
        });
    }
    if (presence.features) legacy.features = clone(migrated.palette.features);
    if (presence.fixturePrefabs) legacy.fixturePrefabs = clone(migrated.palette.fixturePrefabs);

    for (const field of ENVIRONMENT_FIELDS) {
        if (presence.environmentFields[field]) legacy[field] = clone(migrated.palette.environment[field]);
    }
    return legacy;
}

module.exports = {
    SOURCE_FIELDS,
    REPRESENTATION_FIELDS,
    migrateLegacyTileset,
    compileLegacyTileset,
};
