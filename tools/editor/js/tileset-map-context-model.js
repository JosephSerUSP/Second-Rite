// ============================================================================
// #547 EXPERIMENT C — MAP-CONTEXTUAL TILESET AUTHORING · PURE MODEL
// ----------------------------------------------------------------------------
// DISPOSABLE PROTOTYPE. Not a production module, not a winner recommendation.
//
// This file holds the parts of the experiment that can be reasoned about
// without a browser: translating a runtime surface's semantic provenance into
// the authored owner it came from, and translating the small human-facing
// vocabulary (main face / join halves, chance, "beside floor") to and from the
// exact persisted schema.
//
// TRUTH BOUNDARY, stated once and enforced everywhere below:
//   * Which variant a cell resolved to is ENGINE TRUTH. It arrives as
//     `source.variantId` on the authoritative Map Renderable Bundle. This file
//     never re-derives a weighted choice, never hashes a cell, and never packs
//     an atlas. If provenance is missing, the answer is "unknown", not a guess.
//   * Which variants EXIST, and their weights/rules, is AUTHORED TRUTH read
//     from the Project's own tileset record.
// ============================================================================
(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraTilesetMapContext = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    // Human-facing role vocabulary <-> persisted pool location. `surface` is
    // the runtime provenance role emitted by map_renderable_bundle.lua.
    const ROLES = Object.freeze({
        wall: {
            key: 'wall', label: 'Wall', poolPath: ['base', 'walls'],
            weighted: true, visualKind: 'wall-triptych', featureRole: null,
        },
        wall_top: {
            key: 'wall_top', label: 'Wall top', poolPath: ['base', 'wallTops'],
            weighted: true, visualKind: 'single-cell', featureRole: null,
        },
        floor: {
            key: 'floor', label: 'Floor', poolPath: ['base', 'floors'],
            weighted: true, visualKind: 'single-cell', featureRole: null,
        },
        ceiling: {
            key: 'ceiling', label: 'Ceiling', poolPath: ['base', 'ceilings'],
            weighted: true, visualKind: 'single-cell', featureRole: null,
        },
        door: {
            key: 'door', label: 'Door / opening', poolPath: ['doors'],
            weighted: true, visualKind: 'single-cell', featureRole: null,
        },
        wall_feature: {
            key: 'wall_feature', label: 'Wall fixture', poolPath: ['features'],
            weighted: false, visualKind: 'single-cell', featureRole: 'wall_feature',
        },
        floor_feature: {
            key: 'floor_feature', label: 'Floor fixture', poolPath: ['features'],
            weighted: false, visualKind: 'single-cell', featureRole: 'floor_feature',
        },
    });

    const SURFACE_ROLE_LABELS = Object.freeze({
        'north-wall': 'Wall face (north side)',
        'south-wall': 'Wall face (south side)',
        'east-wall': 'Wall face (east side)',
        'west-wall': 'Wall face (west side)',
        'wall-top': 'Wall top',
        floor: 'Floor',
        ceiling: 'Ceiling',
        opening: 'Opening / door',
        'floor-feature': 'Floor fixture',
    });

    // Which authored pool owns a clicked runtime surface. A fixture wins over
    // the structural surface it stands on, because that is what the author sees.
    function roleFromProvenance(source) {
        if (!source || typeof source !== 'object' || source.kind !== 'cell') return null;
        const surface = String(source.surface || '');
        if (source.featureId) {
            return surface === 'floor-feature' ? ROLES.floor_feature : ROLES.wall_feature;
        }
        if (surface === 'floor-feature') return ROLES.floor_feature;
        if (surface === 'floor') return ROLES.floor;
        if (surface === 'ceiling') return ROLES.ceiling;
        if (surface === 'wall-top') return ROLES.wall_top;
        if (surface === 'opening') return ROLES.door;
        if (/-wall$/.test(surface)) return source.doorFace ? ROLES.door : ROLES.wall;
        return null;
    }

    function describeSurface(source) {
        if (!source || source.kind !== 'cell') return 'No runtime surface';
        const base = SURFACE_ROLE_LABELS[source.surface] || String(source.surface || 'Surface');
        if (source.featureId) return `${base} · fixture`;
        if (source.doorFace) return `${base} · doorway`;
        return base;
    }

    // The authored variant that owns a clicked surface. Which field carries it
    // depends on the surface: a doorway is a wall CELL whose visible presentation
    // comes from the door pool, so `variantId` there names the wall it was cut
    // into and `doorVariantId` names the actual owner. Reading `variantId`
    // blindly attributes doorways to the wrong pool.
    function ownerVariantId(source) {
        if (!source || typeof source !== 'object') return null;
        if (source.featureId) return source.featureId;
        if (source.doorFace) return source.doorVariantId || null;
        return source.variantId || null;
    }

    function poolFor(record, roleKey) {
        const role = ROLES[roleKey];
        if (!role || !record) return [];
        let node = record;
        for (const step of role.poolPath) {
            node = node && node[step];
        }
        if (!Array.isArray(node)) return [];
        if (!role.featureRole) return node;
        return node.filter(entry => entry && entry.role === role.featureRole);
    }

    function backingArray(record, roleKey) {
        const role = ROLES[roleKey];
        if (!role || !record) return null;
        let node = record;
        for (let index = 0; index < role.poolPath.length - 1; index++) {
            node = node && node[role.poolPath[index]];
        }
        const last = role.poolPath[role.poolPath.length - 1];
        if (!node) return null;
        if (!Array.isArray(node[last])) node[last] = [];
        return node[last];
    }

    function findVariant(record, roleKey, variantId) {
        if (!variantId) return null;
        return poolFor(record, roleKey).find(entry => entry && entry.id === variantId) || null;
    }

    // Authored weight and the share of the pool it actually claims. Both are
    // shown together so an author never has to guess what "60" means.
    function poolShares(pool) {
        const entries = (pool || []).map(entry => ({
            id: entry && entry.id,
            weight: Number(entry && entry.weight !== undefined ? entry.weight : 100),
        }));
        const total = entries.reduce((sum, entry) =>
            sum + (Number.isFinite(entry.weight) && entry.weight > 0 ? entry.weight : 0), 0);
        return entries.map(entry => ({
            id: entry.id,
            weight: entry.weight,
            share: total > 0 && entry.weight > 0 ? entry.weight / total : 0,
        }));
    }

    // What the ENGINE actually chose, counted off the compiled bundle. This is
    // the deterministic-variant-inspection answer: not a simulation of the
    // weighted draw, but a census of the real resolved map.
    function realizedCensus(provenanceList) {
        const census = {};
        for (const source of provenanceList || []) {
            const role = roleFromProvenance(source);
            if (!role) continue;
            const id = ownerVariantId(source);
            if (!id) continue;
            const bucket = census[role.key] || (census[role.key] = { total: 0, byVariant: {}, cells: {} });
            // One cell can emit several surfaces (base quad plus a height mesh,
            // or four faces of one wall cell). Count CELLS, so a census reads as
            // "places in this map", not "triangle batches".
            const cellKey = `${id}|${source.x},${source.y}`;
            if (bucket.cells[cellKey]) continue;
            bucket.cells[cellKey] = true;
            bucket.byVariant[id] = (bucket.byVariant[id] || 0) + 1;
            bucket.total += 1;
        }
        for (const bucket of Object.values(census)) delete bucket.cells;
        return census;
    }

    function realizedShare(census, roleKey, variantId) {
        const bucket = census && census[roleKey];
        if (!bucket || !bucket.total || !variantId) return null;
        return {
            cells: bucket.byVariant[variantId] || 0,
            share: (bucket.byVariant[variantId] || 0) / bucket.total,
            total: bucket.total,
        };
    }

    // --- Visual assignment ---------------------------------------------------
    // The author points at a source region. Coordinates are a consequence, not
    // an input. A wall additionally needs its join halves; the current schema
    // stores those as two half-cell offsets into a neighbouring region, so this
    // derives them rather than asking the author for three coordinate pairs.
    function assignVisual(variant, roleKey, cell) {
        if (!variant || !cell) return { ok: false, reason: 'no-target' };
        const row = Number(cell.row);
        const col = Number(cell.col);
        if (!Number.isInteger(row) || !Number.isInteger(col) || row < 0 || col < 0) {
            return { ok: false, reason: 'bad-cell' };
        }
        if (ROLES[roleKey] && ROLES[roleKey].visualKind === 'wall-triptych') {
            if (cell.columns !== undefined && col + 1 >= Number(cell.columns)) {
                return { ok: false, reason: 'wall-needs-join-column' };
            }
            variant.middle = [row, col];
            variant.leftEdge = [row, col + 1, 0];
            variant.rightEdge = [row, col + 1, 32];
            return { ok: true, assigned: 'wall-triptych' };
        }
        variant.atlas = [row, col];
        return { ok: true, assigned: 'single-cell' };
    }

    function visualCells(variant, roleKey) {
        if (!variant) return [];
        if (ROLES[roleKey] && ROLES[roleKey].visualKind === 'wall-triptych') {
            const cells = [];
            if (variant.middle) cells.push({ row: variant.middle[0], col: variant.middle[1], part: 'main face' });
            if (variant.leftEdge) cells.push({ row: variant.leftEdge[0], col: variant.leftEdge[1], part: 'join halves' });
            return cells;
        }
        if (variant.atlas) return [{ row: variant.atlas[0], col: variant.atlas[1], part: 'visual' }];
        return [];
    }

    function newVariant(roleKey, id) {
        const role = ROLES[roleKey];
        if (!role) throw new Error(`unknown role '${roleKey}'`);
        if (roleKey === 'wall') {
            return { id, role: 'base_wall', middle: [0, 0], leftEdge: [0, 0, 0], rightEdge: [0, 0, 32], weight: 100 };
        }
        if (roleKey === 'wall_top') return { id, role: 'base_wall_top', atlas: [0, 0], weight: 100 };
        if (roleKey === 'floor') return { id, role: 'base_floor', atlas: [0, 0], weight: 100, heightOffset: 0 };
        if (roleKey === 'ceiling') return { id, role: 'base_ceiling', atlas: [0, 0], weight: 100 };
        if (roleKey === 'door') return { id, role: 'door', atlas: [0, 0], weight: 100 };
        return { id, role: role.featureRole, atlas: [0, 0], injectProbability: 0.12 };
    }

    function suggestVariantId(record, roleKey, hint) {
        const base = String(hint || roleKey).toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '')
            || roleKey;
        const taken = new Set();
        for (const key of Object.keys(ROLES)) {
            for (const entry of poolFor(record, key)) if (entry && entry.id) taken.add(entry.id);
        }
        if (!taken.has(base)) return base;
        let index = 2;
        while (taken.has(`${base}_${index}`)) index += 1;
        return `${base}_${index}`;
    }

    // --- Placement rules ----------------------------------------------------
    // A tiny set of presets over the REAL predicate vocabulary in
    // engine/fixture_predicates.lua. Anything outside the presets stays
    // authorable as exact JSON; nothing here invents an editor-only operator.
    const PLACEMENT_PRESETS = Object.freeze([
        { key: 'anywhere', label: 'Anywhere eligible', where: null },
        { key: 'beside_floor', label: 'Beside open floor', where: { adjacent: 'floor' } },
        { key: 'beside_wall', label: 'Beside a wall', where: { adjacent: 'wall' } },
        { key: 'beside_opening', label: 'Beside an opening', where: { adjacent: 'opening' } },
        { key: 'corner', label: 'In a corner (wall on two sides)', where: { all: [{ adjacent: 'wall' }, { adjacent: { tile: 'wall', diagonal: true } }] } },
    ]);

    function canonicalJson(value) {
        if (value === null || value === undefined) return 'null';
        if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
        if (typeof value === 'object') {
            return `{${Object.keys(value).sort().map(key =>
                `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
        }
        return JSON.stringify(value);
    }

    function placementPresetOf(where) {
        const target = canonicalJson(where === undefined ? null : where);
        const hit = PLACEMENT_PRESETS.find(preset => canonicalJson(preset.where) === target);
        return hit ? hit.key : 'custom';
    }

    function applyPlacementPreset(variant, presetKey) {
        const preset = PLACEMENT_PRESETS.find(entry => entry.key === presetKey);
        if (!variant || !preset) return { ok: false, reason: 'unknown-preset' };
        // A prefab and an inline predicate are mutually exclusive in the
        // runtime; choosing a preset means authoring the predicate here.
        delete variant.prefab;
        if (preset.where === null) delete variant.where;
        else variant.where = JSON.parse(JSON.stringify(preset.where));
        return { ok: true, preset: preset.key };
    }

    function setChancePercent(variant, percent) {
        const value = Number(percent);
        if (!Number.isFinite(value) || value < 0 || value > 100) return { ok: false, reason: 'out-of-range' };
        variant.injectProbability = value / 100;
        return { ok: true, injectProbability: variant.injectProbability };
    }

    function chancePercent(variant) {
        const value = Number(variant && variant.injectProbability);
        return Math.round((Number.isFinite(value) ? value : 0.12) * 100);
    }

    // --- Emission -----------------------------------------------------------
    const WARM_EMISSION = Object.freeze({ color: [1, 0.58, 0.22], radius: 4, falloff: 2 });
    const COOL_EMISSION = Object.freeze({ color: [0.42, 0.66, 1], radius: 4, falloff: 2 });

    function setEmission(variant, preset) {
        if (!variant) return { ok: false, reason: 'no-variant' };
        if (preset === null || preset === 'none') {
            delete variant.emitsLight;
            return { ok: true, emits: false };
        }
        const template = preset === 'cool' ? COOL_EMISSION : WARM_EMISSION;
        variant.emitsLight = { color: template.color.slice(), radius: template.radius, falloff: template.falloff };
        return { ok: true, emits: true };
    }

    // --- Transaction --------------------------------------------------------
    function recordIsDirty(working, baselineJson) {
        if (!working || baselineJson == null) return false;
        return JSON.stringify(working) !== baselineJson;
    }

    // Only the visible edit's own record travels. A save carries the storage
    // version token it was loaded with so a stale write is refused rather than
    // silently clobbering another surface's commit.
    function savePayload(working) {
        if (!working) return null;
        const payload = JSON.parse(JSON.stringify(working));
        for (const legacy of ['wallRows', 'doorRow', 'floorRow', 'ceilingRow', 'skyRow', 'tiles']) {
            delete payload[legacy];
        }
        return payload;
    }

    return {
        ROLES,
        PLACEMENT_PRESETS,
        WARM_EMISSION,
        COOL_EMISSION,
        roleFromProvenance,
        ownerVariantId,
        describeSurface,
        poolFor,
        backingArray,
        findVariant,
        poolShares,
        realizedCensus,
        realizedShare,
        assignVisual,
        visualCells,
        newVariant,
        suggestVariantId,
        placementPresetOf,
        applyPlacementPreset,
        setChancePercent,
        chancePercent,
        setEmission,
        recordIsDirty,
        savePayload,
        canonicalJson,
    };
}));
