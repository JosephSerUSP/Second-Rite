'use strict';

function normalizeVisualProperty(value, semantic) {
    if (value == null) return null;
    if (typeof value === 'string') {
        return { semantic, animated: false, frames: [value], fps: null, clock: null };
    }
    if (typeof value !== 'object') throw new Error(`${semantic} must be a path or property object`);
    if (Array.isArray(value.frames)) {
        if (value.frames.length === 0) throw new Error(`${semantic} animation has no frames`);
        if (!value.frames.every(frame => typeof frame === 'string' && frame)) {
            throw new Error(`${semantic} animation contains an invalid frame path`);
        }
        return {
            semantic,
            animated: true,
            frames: value.frames.slice(),
            fps: Number(value.fps) || 0,
            clock: value.clock || null,
        };
    }
    if (typeof value.image === 'string' && value.image) {
        return { semantic, animated: false, frames: [value.image], fps: null, clock: null };
    }
    throw new Error(`${semantic} object has no image or frames`);
}

function addProvenance(target, property) {
    if (!property) return;
    for (const path of property.frames) target.push({ semantic: property.semantic, path });
}

function normalizeSurface(id, surface) {
    if (!surface || typeof surface !== 'object') throw new Error(`${id}: Surface must be an object`);

    const albedo = normalizeVisualProperty(surface.albedo, 'albedo');
    const emission = normalizeVisualProperty(surface.emission, 'emission');
    const height = surface.height ? normalizeVisualProperty(surface.height, 'height') : null;
    if (height && height.animated) {
        throw new Error(`${id}: animated height is animated geometry and is outside the ordinary material normalizer`);
    }

    const passes = (surface.layers || []).map((layer, index) => {
        if (!layer || typeof layer.image !== 'string' || !layer.image) {
            throw new Error(`${id}: layer ${index} has no semantic image source`);
        }
        return {
            index,
            image: layer.image,
            blend: layer.blend,
            uvSource: layer.uvSource,
            strength: layer.strength == null ? 1 : Number(layer.strength),
            meaning: layer.meaning || null,
        };
    });

    const provenance = [];
    addProvenance(provenance, albedo);
    addProvenance(provenance, emission);
    addProvenance(provenance, height);
    for (const pass of passes) provenance.push({ semantic: `layer:${pass.meaning || pass.index}`, path: pass.image });

    return {
        id,
        properties: { albedo, emission, height },
        geometryBuilds: height ? [{ source: height.frames[0], semantic: 'height' }] : [],
        passes,
        provenance,
        runtimePlan: {
            staticGeometryBuildCount: height ? 1 : 0,
            animatedSamplerFrames: {
                albedo: albedo ? albedo.frames.length : 0,
                emission: emission ? emission.frames.length : 0,
            },
            sourcePacking: 'unspecified-runtime-optimization',
        },
    };
}

function normalizeFixture(fixture) {
    const surfaces = {};
    for (const [id, surface] of Object.entries(fixture.surfaces || {})) {
        surfaces[id] = normalizeSurface(id, surface);
    }
    return { surfaces };
}

module.exports = { normalizeVisualProperty, normalizeSurface, normalizeFixture };
