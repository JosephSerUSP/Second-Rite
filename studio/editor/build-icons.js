'use strict';

const fs = require('fs');
const path = require('path');

const ICON_DIR = path.join(__dirname, 'Assets', 'icons', 'thestra-studio');
const ICO_SIZES = [16, 24, 32, 48, 64, 128, 256];
const ICNS_SIZES = [16, 32, 64, 128, 256];
const ICNS_TYPES = new Map([
    [16, 'icp4'],
    [32, 'icp5'],
    [64, 'icp6'],
    [128, 'ic07'],
    [256, 'ic08'],
]);
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function readPng(iconDir, size) {
    const filename = path.join(iconDir, `icon-${size}.png`);
    const data = fs.readFileSync(filename);
    if (data.length < 24 || !data.subarray(0, 8).equals(PNG_SIGNATURE)) {
        throw new Error(`${filename} is not a PNG`);
    }
    const width = data.readUInt32BE(16);
    const height = data.readUInt32BE(20);
    if (width !== size || height !== size) {
        throw new Error(`${filename} must be ${size}x${size}, got ${width}x${height}`);
    }
    return data;
}

function buildIco(iconDir = ICON_DIR) {
    const images = ICO_SIZES.map(size => ({ size, data: readPng(iconDir, size) }));
    const headerBytes = 6 + images.length * 16;
    let offset = headerBytes;

    const header = Buffer.alloc(6);
    header.writeUInt16LE(0, 0);
    header.writeUInt16LE(1, 2);
    header.writeUInt16LE(images.length, 4);

    const entries = images.map(({ size, data }) => {
        const entry = Buffer.alloc(16);
        entry.writeUInt8(size === 256 ? 0 : size, 0);
        entry.writeUInt8(size === 256 ? 0 : size, 1);
        entry.writeUInt8(0, 2); // PNG palette is internal to the PNG payload.
        entry.writeUInt8(0, 3);
        entry.writeUInt16LE(1, 4); // planes
        entry.writeUInt16LE(32, 6); // nominal bit depth for shell selection
        entry.writeUInt32LE(data.length, 8);
        entry.writeUInt32LE(offset, 12);
        offset += data.length;
        return entry;
    });

    return Buffer.concat([header, ...entries, ...images.map(image => image.data)]);
}

function buildIcns(iconDir = ICON_DIR) {
    const chunks = ICNS_SIZES.map(size => {
        const data = readPng(iconDir, size);
        const chunk = Buffer.alloc(8 + data.length);
        chunk.write(ICNS_TYPES.get(size), 0, 4, 'ascii');
        chunk.writeUInt32BE(chunk.length, 4);
        data.copy(chunk, 8);
        return chunk;
    });
    const output = Buffer.concat([Buffer.alloc(8), ...chunks]);
    output.write('icns', 0, 4, 'ascii');
    output.writeUInt32BE(output.length, 4);
    return output;
}

function assertPngPayload(data, expectedSize, label) {
    if (data.length < 24 || !data.subarray(0, 8).equals(PNG_SIGNATURE)) {
        throw new Error(`${label} does not contain a PNG payload`);
    }
    const width = data.readUInt32BE(16);
    const height = data.readUInt32BE(20);
    if (width !== expectedSize || height !== expectedSize) {
        throw new Error(`${label} contains ${width}x${height}; expected ${expectedSize}x${expectedSize}`);
    }
}

function validateIco(data) {
    if (data.length < 6 || data.readUInt16LE(0) !== 0 || data.readUInt16LE(2) !== 1) {
        throw new Error('icon.ico has an invalid ICO header');
    }
    const count = data.readUInt16LE(4);
    if (count !== ICO_SIZES.length) {
        throw new Error(`icon.ico contains ${count} entries; expected ${ICO_SIZES.length}`);
    }

    const seen = [];
    for (let index = 0; index < count; index += 1) {
        const at = 6 + index * 16;
        if (at + 16 > data.length) throw new Error('icon.ico directory is truncated');
        const widthByte = data.readUInt8(at);
        const heightByte = data.readUInt8(at + 1);
        const width = widthByte === 0 ? 256 : widthByte;
        const height = heightByte === 0 ? 256 : heightByte;
        if (width !== height) throw new Error(`icon.ico entry ${index} is not square: ${width}x${height}`);
        const size = data.readUInt32LE(at + 8);
        const offset = data.readUInt32LE(at + 12);
        if (offset < 6 + count * 16 || offset + size > data.length) {
            throw new Error(`icon.ico entry ${index} points outside the file`);
        }
        assertPngPayload(data.subarray(offset, offset + size), width, `icon.ico entry ${index}`);
        seen.push(width);
    }

    if (seen.join(',') !== ICO_SIZES.join(',')) {
        throw new Error(`icon.ico entries are ${seen.join(',')}; expected ${ICO_SIZES.join(',')}`);
    }
}

function validateIcns(data) {
    if (data.length < 8 || data.toString('ascii', 0, 4) !== 'icns') {
        throw new Error('icon.icns has an invalid ICNS header');
    }
    if (data.readUInt32BE(4) !== data.length) {
        throw new Error('icon.icns length header does not match file size');
    }

    const expectedByType = new Map(ICNS_SIZES.map(size => [ICNS_TYPES.get(size), size]));
    const seen = [];
    let at = 8;
    while (at < data.length) {
        if (at + 8 > data.length) throw new Error('icon.icns chunk header is truncated');
        const type = data.toString('ascii', at, at + 4);
        const length = data.readUInt32BE(at + 4);
        if (length < 8 || at + length > data.length) {
            throw new Error(`icon.icns chunk ${type} has an invalid length`);
        }
        if (!expectedByType.has(type)) throw new Error(`icon.icns contains unexpected chunk ${type}`);
        const size = expectedByType.get(type);
        assertPngPayload(data.subarray(at + 8, at + length), size, `icon.icns chunk ${type}`);
        seen.push(size);
        at += length;
    }
    if (at !== data.length) throw new Error('icon.icns has trailing/truncated data');
    if (seen.join(',') !== ICNS_SIZES.join(',')) {
        throw new Error(`icon.icns entries are ${seen.join(',')}; expected ${ICNS_SIZES.join(',')}`);
    }
}

function writeIfChanged(filename, data) {
    if (fs.existsSync(filename) && fs.readFileSync(filename).equals(data)) return false;
    fs.writeFileSync(filename, data);
    return true;
}

function buildContainers(iconDir = ICON_DIR) {
    const ico = buildIco(iconDir);
    const icns = buildIcns(iconDir);
    validateIco(ico);
    validateIcns(icns);
    return { ico, icns };
}

function checkCurrent(iconDir = ICON_DIR) {
    const expected = buildContainers(iconDir);
    const targets = [
        ['icon.ico', expected.ico, validateIco],
        ['icon.icns', expected.icns, validateIcns],
    ];
    for (const [name, generated, validate] of targets) {
        const filename = path.join(iconDir, name);
        if (!fs.existsSync(filename)) throw new Error(`${name} is missing; run npm run icons`);
        const current = fs.readFileSync(filename);
        validate(current);
        if (!current.equals(generated)) {
            throw new Error(`${name} is stale relative to the optical PNGs; run npm run icons`);
        }
    }
}

function main(argv = process.argv.slice(2)) {
    if (argv.length > 1 || (argv.length === 1 && argv[0] !== '--check')) {
        throw new Error('usage: node tools/editor/build-icons.js [--check]');
    }
    if (argv[0] === '--check') {
        checkCurrent();
        console.log('Thestra Studio icon containers are current and valid.');
        return;
    }

    const { ico, icns } = buildContainers();
    const icoChanged = writeIfChanged(path.join(ICON_DIR, 'icon.ico'), ico);
    const icnsChanged = writeIfChanged(path.join(ICON_DIR, 'icon.icns'), icns);
    checkCurrent();
    console.log(`icon.ico ${icoChanged ? 'rebuilt' : 'already current'}; icon.icns ${icnsChanged ? 'rebuilt' : 'already current'}.`);
}

if (require.main === module) {
    try {
        main();
    } catch (error) {
        console.error(error && error.message ? error.message : error);
        process.exitCode = 1;
    }
}

module.exports = {
    ICO_SIZES,
    ICNS_SIZES,
    buildIco,
    buildIcns,
    buildContainers,
    checkCurrent,
    validateIco,
    validateIcns,
};
