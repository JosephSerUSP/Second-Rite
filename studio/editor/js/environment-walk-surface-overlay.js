(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraEnvironmentWalkSurfaceOverlay = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const MATERIALS = Object.freeze({
        regionFill: { id: '__walk_surface_region_fill', color: [0.16, 0.78, 0.98, 0.20] },
        regionEdge: { id: '__walk_surface_region_edge', color: [0.30, 0.92, 1.00, 0.88] },
        obstacleFill: { id: '__walk_surface_obstacle_fill', color: [1.00, 0.36, 0.16, 0.30] },
        obstacleEdge: { id: '__walk_surface_obstacle_edge', color: [1.00, 0.68, 0.28, 0.96] },
    });
    const INSTANCE_TRANSPORT_KIND = 'mesh-definitions-v1';
    const REGION_Z_OFFSET = 0.018;
    const OBSTACLE_Z_OFFSET = 0.032;
    const EDGE_HALF_WIDTH = 0.025;
    const EPSILON = 1e-9;

    function finite(value, label) {
        const n = Number(value);
        if (!Number.isFinite(n)) throw new Error(`${label} must be finite`);
        return n;
    }

    function normalizeLoop(raw, label) {
        if (!raw || !Array.isArray(raw.points)) throw new Error(`${label} needs points`);
        const points = raw.points.map((point, index) => {
            if (!Array.isArray(point) || point.length < 2) throw new Error(`${label} point ${index} must be XY`);
            return [finite(point[0], `${label} point ${index} X`), finite(point[1], `${label} point ${index} Y`)];
        });
        if (points.length >= 2) {
            const a = points[0], b = points[points.length - 1];
            if (Math.abs(a[0] - b[0]) <= EPSILON && Math.abs(a[1] - b[1]) <= EPSILON) points.pop();
        }
        if (points.length < 3) throw new Error(`${label} must contain at least 3 distinct points`);
        return points;
    }

    function signedArea(points) {
        let area = 0;
        for (let i = 0; i < points.length; i++) {
            const a = points[i], b = points[(i + 1) % points.length];
            area += a[0] * b[1] - b[0] * a[1];
        }
        return area * 0.5;
    }

    function cross(a, b, c) {
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    }

    function pointInTriangle(point, a, b, c) {
        const c1 = cross(a, b, point), c2 = cross(b, c, point), c3 = cross(c, a, point);
        const hasNegative = c1 < -EPSILON || c2 < -EPSILON || c3 < -EPSILON;
        const hasPositive = c1 > EPSILON || c2 > EPSILON || c3 > EPSILON;
        return !(hasNegative && hasPositive);
    }

    function triangulate(points, label) {
        const area = signedArea(points);
        if (Math.abs(area) <= EPSILON) throw new Error(`${label} has zero area`);
        const orientation = area > 0 ? 1 : -1;
        const remaining = points.map((_, index) => index);
        const triangles = [];
        let guard = points.length * points.length;

        while (remaining.length > 3 && guard-- > 0) {
            let clipped = false;
            for (let slot = 0; slot < remaining.length; slot++) {
                const prev = remaining[(slot - 1 + remaining.length) % remaining.length];
                const curr = remaining[slot];
                const next = remaining[(slot + 1) % remaining.length];
                const a = points[prev], b = points[curr], c = points[next];
                if (cross(a, b, c) * orientation <= EPSILON) continue;
                let contains = false;
                for (const index of remaining) {
                    if (index === prev || index === curr || index === next) continue;
                    if (pointInTriangle(points[index], a, b, c)) { contains = true; break; }
                }
                if (contains) continue;
                triangles.push([a, b, c]);
                remaining.splice(slot, 1);
                clipped = true;
                break;
            }
            if (!clipped) throw new Error(`${label} is not a simple triangulable polygon`);
        }
        if (remaining.length === 3) triangles.push(remaining.map(index => points[index]));
        return triangles;
    }

    function emptySurface(id, name, source, material) {
        return { id, name, source, material, positions: [], uvs: [], normals: [], colors: [] };
    }

    function pushVertex(surface, x, y, z) {
        surface.positions.push(x, y, z);
        surface.uvs.push(0, 0);
        surface.normals.push(0, 0, 1);
        surface.colors.push(1, 1, 1, 1);
    }

    function pushTriangle(surface, triangle, z) {
        for (const point of triangle) pushVertex(surface, point[0], point[1], z);
    }

    function pushBoundary(surface, points, z) {
        for (let index = 0; index < points.length; index++) {
            const a = points[index], b = points[(index + 1) % points.length];
            const dx = b[0] - a[0], dy = b[1] - a[1];
            const length = Math.hypot(dx, dy);
            if (length <= EPSILON) continue;
            const ox = (-dy / length) * EDGE_HALF_WIDTH;
            const oy = (dx / length) * EDGE_HALF_WIDTH;
            const p0 = [a[0] - ox, a[1] - oy];
            const p1 = [b[0] - ox, b[1] - oy];
            const p2 = [b[0] + ox, b[1] + oy];
            const p3 = [a[0] + ox, a[1] + oy];
            pushTriangle(surface, [p0, p1, p2], z);
            pushTriangle(surface, [p0, p2, p3], z);
        }
    }

    function surfaceSet(walkSurface, manifestPath) {
        if (!walkSurface || typeof walkSurface !== 'object') return [];
        const groundZ = finite(walkSurface.groundZ ?? 0, 'walkSurface groundZ');
        const surfaces = [];
        const groups = [
            { key: 'regions', fill: MATERIALS.regionFill.id, edge: MATERIALS.regionEdge.id,
                offset: REGION_Z_OFFSET, role: 'walk-region' },
            { key: 'obstacles', fill: MATERIALS.obstacleFill.id, edge: MATERIALS.obstacleEdge.id,
                offset: OBSTACLE_Z_OFFSET, role: 'walk-obstacle' },
        ];
        for (const group of groups) {
            (walkSurface[group.key] || []).forEach((raw, index) => {
                const label = `${group.role} ${index}`;
                const points = normalizeLoop(raw, label);
                const source = {
                    kind: 'walk-surface-inspection', surface: group.role,
                    index, manifestPath: manifestPath || null, readOnly: true,
                };
                const fill = emptySurface(`__${group.role}_fill_${index}`, `${label} fill`, source, group.fill);
                for (const triangle of triangulate(points, label)) pushTriangle(fill, triangle, groundZ + group.offset);
                surfaces.push(fill);
                const edge = emptySurface(`__${group.role}_edge_${index}`, `${label} edge`, source, group.edge);
                pushBoundary(edge, points, groundZ + group.offset + 0.003);
                surfaces.push(edge);
            });
        }
        return surfaces;
    }

    function transportAwareSurfaces(bundle, surfaces) {
        if (bundle?.encoding?.kind !== INSTANCE_TRANSPORT_KIND) return surfaces;
        const baseCount = (Array.isArray(bundle.placements) ? bundle.placements.length : 0)
            + (Array.isArray(bundle.surfaces) ? bundle.surfaces.length : 0);
        return surfaces.map((surface, index) => ({
            ...surface,
            // Direct runtime transport preserves one explicit global draw order
            // across definition placements and literal surfaces. Inspection
            // geometry is Studio-only, so append it after every authoritative
            // runtime surface rather than mutating/re-numbering runtime order.
            transportOrder: baseCount + index + 1,
        }));
    }

    function augmentBundle(bundle, manifest, manifestPath) {
        if (!bundle || !Array.isArray(bundle.surfaces) || !manifest?.walkSurface) return bundle;
        const addedSurfaces = transportAwareSurfaces(bundle, surfaceSet(manifest.walkSurface, manifestPath));
        if (!addedSurfaces.length) return bundle;
        const ids = new Set((bundle.materials || []).map(material => material && material.id));
        const addedMaterials = Object.values(MATERIALS).filter(material => !ids.has(material.id));
        return {
            ...bundle,
            materials: [...(bundle.materials || []), ...addedMaterials],
            surfaces: [...bundle.surfaces, ...addedSurfaces],
            inspection: {
                ...(bundle.inspection || {}),
                walkSurface: {
                    manifestPath: manifestPath || null,
                    regionCount: Array.isArray(manifest.walkSurface.regions) ? manifest.walkSurface.regions.length : 0,
                    obstacleCount: Array.isArray(manifest.walkSurface.obstacles) ? manifest.walkSurface.obstacles.length : 0,
                    groundZ: Number(manifest.walkSurface.groundZ || 0),
                    readOnly: true,
                }
            }
        };
    }

    function install(viewport) {
        if (!viewport || typeof viewport.setRenderableBundle !== 'function') return null;
        if (viewport.__thestraWalkSurfaceOverlay) return viewport.__thestraWalkSurfaceOverlay;
        const rawSet = viewport.setRenderableBundle.bind(viewport);
        const state = { bundle: null, manifest: null, manifestPath: null, visible: false, error: null };

        function render() {
            if (!state.bundle) return undefined;
            try {
                state.error = null;
                return rawSet(state.visible ? augmentBundle(state.bundle, state.manifest, state.manifestPath) : state.bundle);
            } catch (error) {
                state.error = error instanceof Error ? error.message : String(error);
                return rawSet(state.bundle);
            }
        }

        viewport.setRenderableBundle = function (bundle) {
            state.bundle = bundle;
            return render();
        };
        viewport.setEnvironmentWalkSurfaceManifest = function (manifest, manifestPath) {
            state.manifest = manifest || null;
            state.manifestPath = manifestPath || null;
            return render();
        };
        viewport.clearEnvironmentWalkSurfaceManifest = function () {
            state.manifest = null;
            state.manifestPath = null;
            state.error = null;
            return render();
        };
        viewport.setWalkSurfaceVisible = function (visible) {
            state.visible = !!visible;
            return render();
        };
        viewport.getWalkSurfaceVisible = () => state.visible;
        viewport.getWalkSurfaceInfo = function () {
            const surface = state.manifest?.walkSurface;
            return {
                available: !!surface,
                visible: state.visible,
                manifestPath: state.manifestPath,
                regionCount: Array.isArray(surface?.regions) ? surface.regions.length : 0,
                obstacleCount: Array.isArray(surface?.obstacles) ? surface.obstacles.length : 0,
                groundZ: surface ? Number(surface.groundZ || 0) : null,
                authority: state.manifest?.provenance?.walkSurfaceAuthority || null,
                error: state.error,
                readOnly: true,
            };
        };
        const api = { state, render };
        Object.defineProperty(viewport, '__thestraWalkSurfaceOverlay', { value: api, configurable: true });
        return api;
    }

    return { MATERIALS, normalizeLoop, triangulate, surfaceSet, transportAwareSurfaces, augmentBundle, install };
}));