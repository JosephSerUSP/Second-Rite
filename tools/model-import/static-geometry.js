'use strict';

const EPSILON = 1e-10;

function canonical(value) {
    return value === 0 ? 0 : value;
}

function vec(values) {
    return Array.from(values, canonical);
}

function sourceVectorToWorld(value, scale = 1) {
    return vec([value[0] * scale, -value[2] * scale, value[1] * scale]);
}

function normalize3(value, label = 'vector') {
    const length = Math.hypot(value[0], value[1], value[2]);
    if (!Number.isFinite(length) || length <= EPSILON) throw new Error(`${label} has zero or invalid length`);
    return vec([value[0] / length, value[1] / length, value[2] / length]);
}

function faceNormal(a, b, c) {
    const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
    const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
    return normalize3([
        uy * vz - uz * vy,
        uz * vx - ux * vz,
        ux * vy - uy * vx,
    ], 'triangle normal');
}

function emptyBounds() {
    return {
        minX: Infinity, minY: Infinity, minZ: Infinity,
        maxX: -Infinity, maxY: -Infinity, maxZ: -Infinity,
    };
}

function include(bounds, position) {
    bounds.minX = Math.min(bounds.minX, position[0]);
    bounds.minY = Math.min(bounds.minY, position[1]);
    bounds.minZ = Math.min(bounds.minZ, position[2]);
    bounds.maxX = Math.max(bounds.maxX, position[0]);
    bounds.maxY = Math.max(bounds.maxY, position[1]);
    bounds.maxZ = Math.max(bounds.maxZ, position[2]);
}

function finalBounds(bounds) {
    const out = {};
    for (const key of ['minX', 'minY', 'minZ', 'maxX', 'maxY', 'maxZ']) {
        if (!Number.isFinite(bounds[key])) throw new Error('static Model produced no finite bounds');
        out[key] = canonical(bounds[key]);
    }
    return out;
}

function collector() {
    const bySlot = new Map();
    const order = [];
    const bounds = emptyBounds();
    let vertexCount = 0;

    function group(slot) {
        if (bySlot.has(slot)) return bySlot.get(slot);
        const value = { materialSlot: slot, vertices: [] };
        bySlot.set(slot, value);
        order.push(value);
        return value;
    }

    function appendTriangle(slot, corners) {
        if (!Array.isArray(corners) || corners.length !== 3) throw new Error('appendTriangle requires three corners');
        const generated = faceNormal(corners[0].position, corners[1].position, corners[2].position);
        const target = group(slot);
        for (const corner of corners) {
            const p = vec(corner.position);
            const uv = vec(corner.uv || [0, 0]);
            const n = normalize3(corner.normal || generated, 'vertex normal');
            const color = vec(corner.color || [1, 1, 1, 1]);
            include(bounds, p);
            target.vertices.push([
                p[0], p[1], p[2],
                uv[0], uv[1],
                n[0], n[1], n[2],
                color[0], color[1], color[2], color.length > 3 ? color[3] : 1,
            ]);
            vertexCount += 1;
        }
    }

    function finish() {
        if (vertexCount === 0) throw new Error('static Model produced no triangle geometry');
        return { groups: order, vertexCount, bounds: finalBounds(bounds) };
    }

    return { appendTriangle, finish };
}

function transformPosition(matrix, position) {
    const x = position[0], y = position[1], z = position[2];
    return vec([
        matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
        matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
        matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14],
    ]);
}

function determinant3(matrix) {
    const a00 = matrix[0], a01 = matrix[4], a02 = matrix[8];
    const a10 = matrix[1], a11 = matrix[5], a12 = matrix[9];
    const a20 = matrix[2], a21 = matrix[6], a22 = matrix[10];
    return a00 * (a11 * a22 - a12 * a21)
        - a01 * (a10 * a22 - a12 * a20)
        + a02 * (a10 * a21 - a11 * a20);
}

function transformNormal(matrix, normal) {
    const a00 = matrix[0], a01 = matrix[4], a02 = matrix[8];
    const a10 = matrix[1], a11 = matrix[5], a12 = matrix[9];
    const a20 = matrix[2], a21 = matrix[6], a22 = matrix[10];
    const c00 = a11 * a22 - a12 * a21;
    const c01 = -(a10 * a22 - a12 * a20);
    const c02 = a10 * a21 - a11 * a20;
    const c10 = -(a01 * a22 - a02 * a21);
    const c11 = a00 * a22 - a02 * a20;
    const c12 = -(a00 * a21 - a01 * a20);
    const c20 = a01 * a12 - a02 * a11;
    const c21 = -(a00 * a12 - a02 * a10);
    const c22 = a00 * a11 - a01 * a10;
    const det = a00 * c00 + a01 * c01 + a02 * c02;
    if (!Number.isFinite(det) || Math.abs(det) <= EPSILON) throw new Error('source node transform is non-invertible');
    return normalize3([
        (c00 * normal[0] + c01 * normal[1] + c02 * normal[2]) / det,
        (c10 * normal[0] + c11 * normal[1] + c12 * normal[2]) / det,
        (c20 * normal[0] + c21 * normal[1] + c22 * normal[2]) / det,
    ], 'transformed normal');
}

module.exports = {
    EPSILON,
    collector,
    determinant3,
    normalize3,
    sourceVectorToWorld,
    transformNormal,
    transformPosition,
};
