'use strict';

function roleField(role) {
    if (role === 'walls') return 'walls';
    if (role === 'floors') return 'floors';
    if (role === 'ceilings') return 'ceilings';
    if (role === 'doors') return 'doors';
    throw new Error(`unsupported role ${role}`);
}

function compileEntry(role, entry, surface) {
    const out = { id: entry.id, weight: entry.weight };
    const source = surface.source || {};
    if (source.kind === 'atlasRegion') {
        const region = source.region;
        if (!region) throw new Error(`${entry.id}: atlasRegion has no region`);
        if (role === 'walls') {
            out.middle = [region.row, region.column];
            out.leftEdge = [region.row, region.column, 0];
            out.rightEdge = [region.row, region.column, Math.floor(region.width / 2)];
        } else {
            out.atlas = [region.row, region.column];
        }
    } else if (source.kind === 'geometry') {
        out.geometry = source.asset;
    } else if (source.kind === 'standalone') {
        out.__normalizationRequired = 'standalone-image';
    } else {
        throw new Error(`${entry.id}: unsupported Surface source kind ${source.kind}`);
    }
    return out;
}

function unique(values) {
    return Array.from(new Set(values.filter(value => value != null)));
}

function compilePalette(model, paletteId) {
    const palette = model.palettes && model.palettes[paletteId];
    if (!palette) throw new Error(`missing palette ${paletteId}`);

    const sourceImages = [];
    const heightImages = [];
    const emissionImages = [];
    const roleHeightScales = {};
    const base = {};
    const normalization = [];

    for (const role of ['walls', 'floors', 'ceilings']) {
        const entries = palette[role] || [];
        if (!entries.length) continue;
        base[roleField(role)] = [];
        const scales = [];
        for (const entry of entries) {
            const surface = model.surfaces && model.surfaces[entry.surface];
            if (!surface) throw new Error(`${paletteId}/${entry.id}: missing Surface ${entry.surface}`);
            if (surface.source?.kind === 'atlasRegion') sourceImages.push(surface.source.image);
            if (surface.height?.image) {
                heightImages.push(surface.height.image);
                if (surface.height.scale != null) scales.push(Number(surface.height.scale));
            }
            if (surface.emission?.image) emissionImages.push(surface.emission.image);
            const compiled = compileEntry(role, entry, surface);
            if (compiled.__normalizationRequired) {
                normalization.push({ entry: entry.id, reason: compiled.__normalizationRequired });
                delete compiled.__normalizationRequired;
            }
            base[role].push(compiled);
        }
        const distinctScales = unique(scales);
        if (distinctScales.length === 1) roleHeightScales[role.slice(0, -1)] = distinctScales[0];
        else if (distinctScales.length > 1) {
            normalization.push({ role, reason: 'per-surface-height-scale', values: distinctScales });
        }
    }

    const textures = unique(sourceImages);
    const heights = unique(heightImages);
    const emissions = unique(emissionImages);
    if (textures.length > 1) normalization.push({ reason: 'multiple-albedo-sources', values: textures });
    if (heights.length > 1) normalization.push({ reason: 'multiple-height-sources', values: heights });
    if (emissions.length > 1) normalization.push({ reason: 'multiple-emission-sources', values: emissions });

    const legacy = { id: paletteId, base };
    if (textures.length === 1) legacy.texture = textures[0];
    if (heights.length === 1) legacy.heightMap = heights[0];
    if (emissions.length === 1) legacy.glowMap = emissions[0];
    if (Object.keys(roleHeightScales).length) legacy.heightMapScale = roleHeightScales;

    return {
        paletteId,
        legacy,
        normalization,
        directlyRepresentable: normalization.length === 0,
        sourceCounts: { albedo: textures.length, height: heights.length, emission: emissions.length },
    };
}

module.exports = { compilePalette, compileEntry };
