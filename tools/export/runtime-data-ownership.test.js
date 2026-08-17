'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '..', '..');
const manifest = require('./runtime-manifest.json');
const oldRuntimeSupport = [
  "data/authored_storage.lua",
  "data/authored_storage_resolved.lua",
  "data/authored_storage_manifest.json",
  "data/semantic_resources.lua",
  "data/json.lua",
  "data/loader.lua",
  "data/rtp_authored_defaults.lua",
  "data/vendor/lunajson/decoder.lua",
  "data/vendor/lunajson/encoder.lua",
  "data/vendor/lunajson/LICENSE",
  "data/vendor/lunajson/README.md"
];
const newRuntimeSupport = [
  "engine/data/authored_storage.lua",
  "engine/data/authored_storage_resolved.lua",
  "engine/data/authored_storage_manifest.json",
  "engine/data/semantic_resources.lua",
  "engine/data/json.lua",
  "engine/data/loader.lua",
  "engine/data/rtp_authored_defaults.lua",
  "engine/data/vendor/lunajson/decoder.lua",
  "engine/data/vendor/lunajson/encoder.lua",
  "engine/data/vendor/lunajson/LICENSE",
  "engine/data/vendor/lunajson/README.md"
];
function walk(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const p = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(p) : [p];
  });
}
test('Project data contains semantic data only; runtime support is engine-owned', () => {
  assert.equal(Object.prototype.hasOwnProperty.call(manifest, 'dataRuntimeFiles'), false);
  assert.ok(manifest.runtimeDirectories.includes('engine'));
  for (const p of oldRuntimeSupport) assert.equal(fs.existsSync(path.join(ROOT, p)), false, p);
  for (const p of newRuntimeSupport) assert.equal(fs.existsSync(path.join(ROOT, p)), true, p);
  const projectData = walk(path.join(ROOT, 'data')).map(p => path.relative(path.join(ROOT, 'data'), p).replaceAll('\\', '/'));
  assert.deepEqual(projectData.filter(p => p.endsWith('.lua')), []);
  assert.equal(projectData.includes('authored_storage_manifest.json'), false);
  assert.equal(projectData.some(p => p.startsWith('vendor/')), false);
});
