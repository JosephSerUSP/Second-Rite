'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const contract = require('./model-contract');
const { importRecipe } = require('./import-model');
const OUTPUT = 'assets/generated/models';

async function compileModels(projectRoot, runtimeRoot) {
    if (!fs.existsSync(path.join(projectRoot, 'data/models.json'))) return null;
    const { models } = contract.loadRegistry(projectRoot);
    const manifest = { version: 1, models: {}, sourcePaths: {} };
    const products = [];
    for (const [id, recipe] of Object.entries(models)) {
        const bundle = await importRecipe({ projectRoot, recipe, runtimeRoot });
        const text = contract.serialize(bundle);
        const relative = `${OUTPUT}/${contract.sha256(Buffer.from(text))}.json`;
        if (recipe.appearance && manifest.sourcePaths[recipe.source.path]) throw new Error(`Model source '${recipe.source.path}' has two bound recipes`);
        manifest.models[id] = relative;
        // Geometry-only recipes are not promoted over an existing visual
        // source until their visible material slots have a compiled binding.
        if (recipe.appearance) manifest.sourcePaths[recipe.source.path] = id;
        products.push([relative, text]);
    }
    for (const [relative, text] of products) {
        fs.mkdirSync(path.dirname(path.join(projectRoot, relative)), { recursive: true });
        fs.writeFileSync(path.join(projectRoot, relative), text);
    }
    fs.mkdirSync(path.join(projectRoot, OUTPUT), { recursive: true });
    fs.writeFileSync(path.join(projectRoot, OUTPUT, 'manifest.json'), contract.serialize(manifest));
    return manifest;
}

function compileStagedModels(stageDir) {
    if (!fs.existsSync(path.join(stageDir, 'data/models.json'))) return null;
    const result = spawnSync(process.execPath, [__filename, stageDir, stageDir], {
        windowsHide: true, encoding: 'utf8', timeout: 120000,
    });
    if (result.error || result.status !== 0) throw new Error(`Model compilation failed: ${result.error || result.stderr || result.stdout}`);
    return JSON.parse(fs.readFileSync(path.join(stageDir, OUTPUT, 'manifest.json'), 'utf8'));
}

if (require.main === module) compileModels(path.resolve(process.argv[2]), process.argv[3]).then(() => {
    process.stdout.write('MODEL COMPILATION OK\n');
}).catch(error => { console.error(error); process.exitCode = 1; });

module.exports = { compileModels, compileStagedModels, OUTPUT };
