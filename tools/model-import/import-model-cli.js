#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const contract = require('./model-contract');
const importer = require('./import-model');

async function main(argv = process.argv.slice(2)) {
    const [projectArg, modelId, outputArg] = argv;
    if (!projectArg || !modelId || !outputArg) {
        throw new Error('Usage: node tools/model-import/import-model-cli.js <project-root> <model-id> <output.json>');
    }
    const projectRoot = path.resolve(projectArg);
    const outputPath = path.resolve(outputArg);
    const bundle = await importer.importModel({ projectRoot, modelId });
    const text = contract.serialize(bundle);
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    const temp = `${outputPath}.${process.pid}.tmp`;
    fs.writeFileSync(temp, text, 'utf8');
    try {
        fs.renameSync(temp, outputPath);
    } catch (error) {
        try { fs.unlinkSync(temp); } catch (_) {}
        throw error;
    }
    process.stdout.write(`MODEL IMPORT OK ${modelId} ${contract.sha256(Buffer.from(text, 'utf8'))}\n`);
    return bundle;
}

if (require.main === module) {
    main().catch(error => {
        console.error(error && error.stack ? error.stack : error);
        process.exitCode = 1;
    });
}

module.exports = { main };
