'use strict';

function cornerPolyline(profile) {
    if (!profile || profile.kind !== 'procedural') throw new Error('procedural profile required');
    const radius = Number(profile.radius || 0.12);
    if (!(radius > 0 && radius <= 0.5)) throw new Error('radius out of range');

    if (profile.corner === 'square') {
        return [{ x: 1 - radius, y: 1 }, { x: 1, y: 1 }, { x: 1, y: 1 - radius }];
    }
    if (profile.corner === 'chamfer') {
        return [{ x: 1 - radius, y: 1 }, { x: 1, y: 1 - radius }];
    }
    if (profile.corner === 'round') {
        const segments = Number(profile.segments);
        if (!Number.isInteger(segments) || segments < 2) throw new Error('round requires at least 2 segments');
        const cx = 1 - radius;
        const cy = 1 - radius;
        const points = [];
        for (let i = 0; i <= segments; i += 1) {
            const angle = (Math.PI / 2) * (1 - i / segments);
            points.push({ x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius });
        }
        return points;
    }
    throw new Error(`unsupported corner ${profile.corner}`);
}

function extrude(polyline) {
    const vertices = [];
    const triangles = [];
    for (const p of polyline) {
        vertices.push({ x: p.x, y: p.y, z: 0 }, { x: p.x, y: p.y, z: 1 });
    }
    for (let i = 0; i < polyline.length - 1; i += 1) {
        const a = i * 2;
        triangles.push([a, a + 2, a + 3], [a, a + 3, a + 1]);
    }
    return { vertices, triangles };
}

function contained(vertices) {
    return vertices.every(v => v.x >= -1e-9 && v.x <= 1 + 1e-9 && v.y >= -1e-9 && v.y <= 1 + 1e-9);
}

function metrics(profile) {
    const polyline = cornerPolyline(profile);
    const mesh = extrude(polyline);
    return {
        points: polyline.length,
        segments: polyline.length - 1,
        triangles: mesh.triangles.length,
        contained: contained(mesh.vertices),
    };
}

module.exports = { cornerPolyline, extrude, contained, metrics };
