const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const DEFAULT_MANIFEST_PATH = path.resolve(__dirname, '../../data/authored_storage_manifest.json');
const VALID_KINDS = new Set(['document', 'ordered_collection', 'keyed_registry']);
const VALID_REPRESENTATIONS = new Set(['monolith', 'fragments']);

function readJson(filePath) {
    let text;
    try {
        text = fs.readFileSync(filePath, 'utf8');
    } catch (err) {
        const e = new Error(`authored JSON file does not exist: ${filePath}`);
        e.cause = err;
        throw e;
    }
    try {
        return JSON.parse(text);
    } catch (err) {
        const e = new Error(`invalid JSON in ${filePath}: ${err.message}`);
        e.cause = err;
        throw e;
    }
}

function validateSpec(stem, spec, source = '<authored storage manifest>') {
    if (!spec || Array.isArray(spec) || typeof spec !== 'object') {
        throw new Error(`authored resource '${stem}' has no storage metadata: ${source}`);
    }
    if (!VALID_KINDS.has(spec.kind)) {
        throw new Error(`authored resource '${stem}' has unknown kind '${spec.kind}': ${source}`);
    }
    if (!VALID_REPRESENTATIONS.has(spec.representation)) {
        throw new Error(`authored resource '${stem}' has unknown representation '${spec.representation}': ${source}`);
    }
    if (spec.kind === 'document' && spec.representation !== 'monolith') {
        throw new Error(`document resource '${stem}' must use monolith representation: ${source}`);
    }
    return spec;
}

function loadManifest(manifestPath = DEFAULT_MANIFEST_PATH) {
    const manifest = readJson(manifestPath);
    if (!manifest || Array.isArray(manifest) || typeof manifest !== 'object'
            || !manifest.resources || Array.isArray(manifest.resources)
            || typeof manifest.resources !== 'object') {
        throw new Error(`authored storage manifest must contain a resources object: ${manifestPath}`);
    }
    for (const [stem, spec] of Object.entries(manifest.resources)) {
        validateSpec(stem, spec, manifestPath);
    }
    return manifest;
}

function resourceSpec(stem, manifest = loadManifest()) {
    const spec = manifest.resources[stem];
    if (!spec) throw new Error(`authored resource '${stem}' is not declared in the storage manifest`);
    return validateSpec(stem, spec);
}

function bulkEditableResources(manifest = loadManifest()) {
    return Object.entries(manifest.resources)
        .filter(([, spec]) => spec.bulkEditable === true)
        .map(([stem]) => stem);
}

function validateOrderedCollection(entries, stem, source) {
    if (!Array.isArray(entries) || entries.length === 0) {
        throw new Error(`ordered collection '${stem}' must be a non-empty array: ${source}`);
    }
    const ids = new Set();
    for (let index = 0; index < entries.length; index += 1) {
        const entry = entries[index];
        if (!entry || Array.isArray(entry) || typeof entry !== 'object' || entry.id === undefined || entry.id === null) {
            throw new Error(`ordered collection '${stem}' entry ${index + 1} has no id: ${source}`);
        }
        const id = String(entry.id);
        if (ids.has(id)) throw new Error(`ordered collection '${stem}' has duplicate id '${id}': ${source}`);
        ids.add(id);
    }
    return entries;
}

function validateRegistryRecord(record, stem, source) {
    if (!record || Array.isArray(record) || typeof record !== 'object') {
        throw new Error(`registry '${stem}' record is not an object: ${source}`);
    }
    if (typeof record.id !== 'string' || record.id.length === 0) {
        throw new Error(`registry '${stem}' record must own a non-empty string id: ${source}`);
    }
    return record.id;
}

function validateRegistry(value, stem, source) {
    if (!value || Array.isArray(value) || typeof value !== 'object' || Object.keys(value).length === 0) {
        throw new Error(`registry '${stem}' must be a non-empty object: ${source}`);
    }
    const out = {};
    for (const [key, record] of Object.entries(value)) {
        const recordId = validateRegistryRecord(record, stem, source);
        if (key !== recordId) {
            throw new Error(`registry '${stem}' key '${key}' disagrees with record.id '${recordId}': ${source}`);
        }
        if (Object.prototype.hasOwnProperty.call(out, recordId)) {
            throw new Error(`registry '${stem}' has duplicate id '${recordId}': ${source}`);
        }
        out[recordId] = record;
    }
    return out;
}

function validateResource(value, stem, spec, source = `<write ${stem}>`) {
    validateSpec(stem, spec);
    if (spec.kind === 'ordered_collection') return validateOrderedCollection(value, stem, source);
    if (spec.kind === 'keyed_registry') return validateRegistry(value, stem, source);
    if (value === undefined) throw new Error(`document resource '${stem}' cannot be undefined: ${source}`);
    return value;
}

function validateFragmentPath(stem, entry, seen) {
    if (typeof entry !== 'string' || entry.length === 0) {
        throw new Error(`${stem}/index.json entries must be non-empty filenames`);
    }
    if (entry.includes('..') || entry.startsWith('/') || entry.startsWith('\\') || path.basename(entry) !== entry) {
        throw new Error(`${stem}/index.json contains an unsafe fragment path: ${entry}`);
    }
    if (!entry.toLowerCase().endsWith('.json')) {
        throw new Error(`${stem}/index.json fragment must end in .json: ${entry}`);
    }
    const folded = entry.toLowerCase();
    if (seen.has(folded)) throw new Error(`${stem}/index.json lists the same fragment twice: ${entry}`);
    seen.add(folded);
}

function orderedFragmentFiles(directory, stem) {
    const indexPath = path.join(directory, 'index.json');
    const manifest = readJson(indexPath);
    const files = manifest && Array.isArray(manifest.files) ? manifest.files : manifest;
    if (!Array.isArray(files) || files.length === 0) {
        throw new Error(`${stem}/index.json must be an array or { files = [...] }`);
    }
    const seen = new Set();
    return files.map(entry => {
        validateFragmentPath(stem, entry, seen);
        const filePath = path.join(directory, entry);
        if (!fs.existsSync(filePath)) throw new Error(`${stem}/index.json references a missing fragment: ${filePath}`);
        return { name: entry, path: filePath };
    });
}

function registryFiles(directory, stem) {
    if (!fs.existsSync(directory) || !fs.statSync(directory).isDirectory()) {
        throw new Error(`registry directory does not exist: ${directory}`);
    }
    if (fs.existsSync(path.join(directory, 'index.json'))) {
        throw new Error(`registry '${stem}' must not use a shared index.json`);
    }
    const files = fs.readdirSync(directory)
        .filter(name => name.toLowerCase().endsWith('.json'))
        .sort((a, b) => a.localeCompare(b, 'en'));
    if (files.length === 0) throw new Error(`registry '${stem}' has no JSON fragments: ${directory}`);
    return files;
}

function loadOrderedFragments(directory, stem) {
    const out = [];
    for (const fragment of orderedFragmentFiles(directory, stem)) {
        const value = readJson(fragment.path);
        if (Array.isArray(value)) out.push(...value);
        else out.push(value);
    }
    return validateOrderedCollection(out, stem, path.join(directory, 'index.json'));
}

function loadRegistryFragments(directory, stem = path.basename(directory)) {
    const out = {};
    const sourceById = {};
    for (const name of registryFiles(directory, stem)) {
        const filePath = path.join(directory, name);
        const record = readJson(filePath);
        const recordId = validateRegistryRecord(record, stem, filePath);
        if (Object.prototype.hasOwnProperty.call(out, recordId)) {
            throw new Error(`registry '${stem}' has duplicate id '${recordId}': ${filePath}`);
        }
        out[recordId] = record;
        sourceById[recordId] = filePath;
    }
    return { records: out, sourceById };
}

function authoritativeFiles(root, stem, spec = resourceSpec(stem)) {
    validateSpec(stem, spec);
    if (spec.representation === 'monolith') {
        const filePath = path.join(root, `${stem}.json`);
        if (!fs.existsSync(filePath)) throw new Error(`authored JSON file does not exist: ${filePath}`);
        return [filePath];
    }
    const directory = path.join(root, stem);
    if (spec.kind === 'ordered_collection') {
        return [path.join(directory, 'index.json'), ...orderedFragmentFiles(directory, stem).map(entry => entry.path)];
    }
    if (spec.kind === 'keyed_registry') {
        return registryFiles(directory, stem).map(name => path.join(directory, name));
    }
    throw new Error(`resource '${stem}' cannot use fragmented document storage`);
}

function loadResource(root, stem, spec = resourceSpec(stem)) {
    validateSpec(stem, spec);
    if (spec.representation === 'monolith') {
        const source = path.join(root, `${stem}.json`);
        const value = validateResource(readJson(source), stem, spec, source);
        return { value, storage: 'monolith', sourceById: {} };
    }
    const directory = path.join(root, stem);
    if (spec.kind === 'ordered_collection') {
        return { value: loadOrderedFragments(directory, stem), storage: 'fragments', sourceById: {} };
    }
    const loaded = loadRegistryFragments(directory, stem);
    return { value: loaded.records, storage: 'fragments', sourceById: loaded.sourceById };
}

function hashFile(hasher, root, filePath) {
    const relative = path.relative(root, filePath).split(path.sep).join('/');
    const relativeBytes = Buffer.from(relative, 'utf8');
    const payload = fs.readFileSync(filePath);
    const size = Buffer.alloc(8);
    size.writeBigUInt64BE(BigInt(relativeBytes.length));
    hasher.update(size);
    hasher.update(relativeBytes);
    size.writeBigUInt64BE(BigInt(payload.length));
    hasher.update(size);
    hasher.update(payload);
}

function versionToken(root, stem, spec = resourceSpec(stem)) {
    const hasher = crypto.createHash('sha256');
    hasher.update(`authored-resource\0${stem}\0${spec.kind}\0${spec.representation}\0`);
    for (const filePath of authoritativeFiles(root, stem, spec)) hashFile(hasher, root, filePath);
    return hasher.digest('hex');
}

function atomicWriteJson(filePath, value, indent = 2) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    const temp = path.join(path.dirname(filePath), `.${path.basename(filePath)}.${process.pid}.${Date.now()}.tmp`);
    fs.writeFileSync(temp, JSON.stringify(value, null, indent) + '\n', 'utf8');
    try {
        fs.renameSync(temp, filePath);
    } catch (err) {
        try { fs.unlinkSync(temp); } catch (_) {}
        throw err;
    }
}

function encodedSuffix(id) {
    return Buffer.from(String(id), 'utf8').toString('hex');
}

function safeFragmentCandidate(recordId, existingNames = []) {
    const id = String(recordId);
    const folded = new Set(existingNames.map(name => name.toLowerCase()));
    let candidate = /^[A-Za-z0-9._-]+$/.test(id) && id !== '.' && id !== '..' && id.toLowerCase() !== 'index'
        ? `${id}.json`
        : null;
    if (candidate && !folded.has(candidate.toLowerCase())) return candidate;
    const slug = id.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'record';
    candidate = `${slug}--${encodedSuffix(id)}.json`;
    if (folded.has(candidate.toLowerCase())) throw new Error(`fragment filename collision for id '${id}': ${candidate}`);
    return candidate;
}

function removeStaleJson(directory, keepNames, allowIndex) {
    if (!fs.existsSync(directory)) return;
    const keep = new Set(keepNames.map(name => name.toLowerCase()));
    for (const name of fs.readdirSync(directory)) {
        if (!name.toLowerCase().endsWith('.json')) continue;
        if (!allowIndex && name.toLowerCase() === 'index.json') {
            throw new Error(`registry directory must not contain index.json: ${directory}`);
        }
        if (!keep.has(name.toLowerCase())) fs.unlinkSync(path.join(directory, name));
    }
}

function writeResource(root, stem, value, spec = resourceSpec(stem)) {
    const validated = validateResource(value, stem, spec);
    if (spec.representation === 'monolith') {
        atomicWriteJson(path.join(root, `${stem}.json`), validated, 2);
        return { storage: 'monolith', version: versionToken(root, stem, spec) };
    }

    const directory = path.join(root, stem);
    fs.mkdirSync(directory, { recursive: true });
    if (spec.kind === 'ordered_collection') {
        const planned = [];
        const reserved = [];
        for (const entry of validated) {
            const name = safeFragmentCandidate(entry.id, reserved);
            reserved.push(name);
            planned.push({ name, value: entry });
        }
        for (const fragment of planned) atomicWriteJson(path.join(directory, fragment.name), fragment.value, 2);
        atomicWriteJson(path.join(directory, 'index.json'), { files: planned.map(fragment => fragment.name) }, 2);
        removeStaleJson(directory, ['index.json', ...planned.map(fragment => fragment.name)], true);
    } else if (spec.kind === 'keyed_registry') {
        const loaded = fs.existsSync(directory) && fs.readdirSync(directory).some(name => name.toLowerCase().endsWith('.json'))
            ? loadRegistryFragments(directory, stem)
            : { sourceById: {} };
        const existingNames = fs.existsSync(directory) ? fs.readdirSync(directory) : [];
        const keep = [];
        const reserved = existingNames.slice();
        for (const id of Object.keys(validated).sort()) {
            const existingPath = loaded.sourceById[id];
            const name = existingPath ? path.basename(existingPath) : safeFragmentCandidate(id, reserved);
            if (!existingPath) reserved.push(name);
            keep.push(name);
            atomicWriteJson(path.join(directory, name), validated[id], 2);
        }
        removeStaleJson(directory, keep, false);
    } else {
        throw new Error(`resource '${stem}' cannot use fragmented document storage`);
    }
    return { storage: 'fragments', version: versionToken(root, stem, spec) };
}

function snapshotResource(root, stem, destinationRoot, spec = resourceSpec(stem)) {
    const loaded = loadResource(root, stem, spec);
    const target = path.join(destinationRoot, `${stem}.json`);
    atomicWriteJson(target, loaded.value, 2);
    return target;
}

function loadRegistry(root, stem, spec = resourceSpec(stem)) {
    if (spec.kind !== 'keyed_registry') throw new Error(`authored resource '${stem}' is not a keyed registry`);
    const loaded = loadResource(root, stem, spec);
    return { records: loaded.value, storage: loaded.storage, sourceById: loaded.sourceById };
}

function loadOrderedCollection(root, stem, spec = resourceSpec(stem)) {
    if (spec.kind !== 'ordered_collection') throw new Error(`authored resource '${stem}' is not an ordered collection`);
    const loaded = loadResource(root, stem, spec);
    return { entries: loaded.value, storage: loaded.storage };
}

function writeRegistryRecord(root, stem, record, expectedVersion = null, spec = resourceSpec(stem)) {
    if (spec.kind !== 'keyed_registry') throw new Error(`authored resource '${stem}' is not a keyed registry`);
    const recordId = validateRegistryRecord(record, stem, `<write ${stem}>`);
    const loaded = loadRegistry(root, stem, spec);
    const currentVersion = versionToken(root, stem, spec);
    const exists = Object.prototype.hasOwnProperty.call(loaded.records, recordId);
    if (exists && expectedVersion !== currentVersion) {
        const err = new Error(`registry '${stem}' changed on disk after the record was loaded`);
        err.code = 'STALE_AUTHORED_DATA';
        err.currentVersion = currentVersion;
        throw err;
    }

    const next = Object.assign({}, loaded.records, { [recordId]: record });
    validateRegistry(next, stem, `<write ${stem}>`);
    if (spec.representation === 'monolith') {
        atomicWriteJson(path.join(root, `${stem}.json`), next, 2);
    } else {
        const directory = path.join(root, stem);
        const existingPath = loaded.sourceById[recordId];
        const target = existingPath || path.join(directory, safeFragmentCandidate(recordId, fs.readdirSync(directory)));
        atomicWriteJson(target, record, 2);
    }
    return { id: recordId, version: versionToken(root, stem, spec), storage: spec.representation };
}

module.exports = {
    DEFAULT_MANIFEST_PATH,
    authoritativeFiles,
    bulkEditableResources,
    loadManifest,
    loadOrderedCollection,
    loadRegistry,
    loadRegistryFragments,
    loadResource,
    resourceSpec,
    snapshotResource,
    validateOrderedCollection,
    validateRegistryMonolith: validateRegistry,
    validateRegistryRecord,
    validateResource,
    versionToken,
    writeRegistryRecord,
    writeResource,
};
