'use strict';

// Compile the existing native material binding, not a new Surface ontology.
// Both consumers receive the same facts from the retained Lua source adapter.
// Its pure grammar executes locally; no LOVE boot or second handwritten parser.
const fs = require('node:fs');
const path = require('node:path');
const contract = require('./model-contract');

function compileAppearance(projectRoot, recipe, sourceText, runtimeRoot = path.resolve(__dirname, '../../runtime')) {
    const library = sourceText.match(/(?:^|\n)\s*mtllib\s+([^\r\n]+)/);
    if (!library) throw new Error(`Model '${recipe.id}' obj-mtl appearance requires mtllib`);
    const root = path.resolve(projectRoot);
    const relative = path.posix.normalize(path.posix.join(path.posix.dirname(recipe.source.path), library[1].trim()));
    function sourceFile(relativePath) {
        const absolute = path.resolve(root, relativePath);
        if (!absolute.startsWith(root + path.sep)) throw new Error(`Material path escaped Project root: ${relativePath}`);
        return fs.readFileSync(absolute);
    }
    const bytes = sourceFile(relative);
    const materials = require('./mtl-host').parseMtl(runtimeRoot, bytes.toString('utf8'));
    const dependencies = new Map([[relative, contract.sha256(bytes)]]);
    const appearances = {};
    function texturePath(value) {
        const resolved = value.startsWith('assets/') ? value
            : path.posix.normalize(path.posix.join(path.posix.dirname(recipe.source.path), value));
        dependencies.set(resolved, contract.sha256(sourceFile(resolved)));
        return resolved;
    }
    for (const [slotId, slot] of Object.entries(recipe.materialSlots)) {
        let appearance;
        for (const name of slot.sourceMaterials) {
            const original = materials[name];
            if (!original) throw new Error(`Model '${recipe.id}' MTL has no source material '${name}'`);
            const material = JSON.parse(JSON.stringify(original));
            if (material.texture) material.texture = texturePath(material.texture);
            if (material.passes) material.passes.forEach(pass => { pass.texture = texturePath(pass.texture); });
            if (appearance && contract.serialize(appearance) !== contract.serialize(material)) {
                throw new Error(`Model '${recipe.id}' slot '${slotId}' merges different MTL appearances`);
            }
            appearance = material;
        }
        if (!appearance) throw new Error(`Model '${recipe.id}' obj-mtl slot '${slotId}' has no source material`);
        appearances[slotId] = appearance;
    }
    return { appearances, dependencies: Array.from(dependencies, ([path, sha256]) => ({ path, sha256 })).sort((a,b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0) };

}

module.exports = { compileAppearance };
