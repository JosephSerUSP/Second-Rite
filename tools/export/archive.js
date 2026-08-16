'use strict';

const fs = require('fs');
const path = require('path');
const yazl = require('yazl');

function collectFiles(root) {
    const absoluteRoot = path.resolve(root);
    if (!fs.existsSync(absoluteRoot) || !fs.statSync(absoluteRoot).isDirectory()) {
        throw new Error(`Archive source directory is missing: ${absoluteRoot}`);
    }
    const out = [];
    const visit = (dir) => {
        const entries = fs.readdirSync(dir, { withFileTypes: true })
            .sort((a, b) => Buffer.compare(Buffer.from(a.name), Buffer.from(b.name)));
        for (const entry of entries) {
            const absolute = path.join(dir, entry.name);
            if (entry.isDirectory()) visit(absolute);
            else if (entry.isFile()) {
                const relative = path.relative(absoluteRoot, absolute).split(path.sep).join('/');
                out.push({ absolute, relative });
            }
        }
    };
    visit(absoluteRoot);
    return out;
}

function createZipFromDirectory(sourceDir, targetPath) {
    const files = collectFiles(sourceDir);
    const target = path.resolve(targetPath);
    const parent = path.dirname(target);
    fs.mkdirSync(parent, { recursive: true });
    const temp = path.join(parent, `.${path.basename(target)}.${process.pid}.${Date.now()}.tmp`);
    fs.rmSync(temp, { force: true });

    return new Promise((resolve, reject) => {
        const zip = new yazl.ZipFile();
        const output = fs.createWriteStream(temp, { flags: 'wx' });
        let settled = false;

        const fail = (error) => {
            if (settled) return;
            settled = true;
            try { output.destroy(); } catch (_) {}
            try { fs.rmSync(temp, { force: true }); } catch (_) {}
            reject(error);
        };

        output.on('error', fail);
        zip.on('error', fail);
        output.on('close', () => {
            if (settled) return;
            try {
                fs.rmSync(target, { force: true });
                fs.renameSync(temp, target);
                settled = true;
                resolve({ target, entries: files.map(file => file.relative) });
            } catch (error) {
                fail(error);
            }
        });

        zip.outputStream.on('error', fail);
        zip.outputStream.pipe(output);
        for (const file of files) {
            zip.addFile(file.absolute, file.relative, {
                // Stable archive metadata keeps identical source bytes from
                // acquiring arbitrary wall-clock timestamps at pack time.
                mtime: new Date(0),
                mode: 0o100644,
            });
        }
        zip.end();
    });
}

async function main(argv = process.argv.slice(2)) {
    if (argv.length !== 2) {
        throw new Error('Usage: node tools/export/archive.js <source-directory> <target.zip|target.love>');
    }
    const result = await createZipFromDirectory(argv[0], argv[1]);
    console.log(`ARCHIVE OK: ${result.target} (${result.entries.length} files)`);
}

if (require.main === module) {
    main().catch(error => {
        console.error(error.stack || error.message || String(error));
        process.exitCode = 1;
    });
}

module.exports = { collectFiles, createZipFromDirectory };
