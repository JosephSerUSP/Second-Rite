'use strict';

function charAt(layout, x, y) {
    const row = layout[y];
    return row && row[x];
}

function zoneAt(map, x, y) {
    const zone = map.zoneGrid?.[y]?.[x] || '';
    return zone || null;
}

function paletteForZone(map, zone) {
    if (!zone) return map.palette;
    const spec = map.zones?.[zone];
    if (!spec?.palette) throw new Error(`zone ${zone} has no palette`);
    return spec.palette;
}

function paletteForCellSurface(map, x, y) {
    return paletteForZone(map, zoneAt(map, x, y));
}

function paletteForWallFace(map, wallX, wallY, facingX, facingY) {
    if (charAt(map.layout, wallX, wallY) !== '#') {
        throw new Error(`wall face owner ${wallX},${wallY} is not solid`);
    }
    const neighbor = charAt(map.layout, facingX, facingY);
    if (neighbor == null || neighbor === '#') {
        throw new Error(`wall face ${wallX},${wallY} does not face traversable authored space at ${facingX},${facingY}`);
    }
    return {
        zone: zoneAt(map, facingX, facingY),
        palette: paletteForCellSurface(map, facingX, facingY),
        logicalWall: [wallX, wallY],
        facingCell: [facingX, facingY],
    };
}

function exposedWallFaces(map) {
    const faces = [];
    const directions = [
        ['north', 0, -1], ['south', 0, 1], ['west', -1, 0], ['east', 1, 0],
    ];
    for (let y = 0; y < map.layout.length; y += 1) {
        for (let x = 0; x < map.layout[y].length; x += 1) {
            if (charAt(map.layout, x, y) !== '#') continue;
            for (const [side, dx, dy] of directions) {
                const nx = x + dx;
                const ny = y + dy;
                const neighbor = charAt(map.layout, nx, ny);
                if (neighbor != null && neighbor !== '#') {
                    faces.push({
                        side,
                        ...paletteForWallFace(map, x, y, nx, ny),
                    });
                }
            }
        }
    }
    return faces;
}

module.exports = {
    paletteForCellSurface,
    paletteForWallFace,
    exposedWallFaces,
};
