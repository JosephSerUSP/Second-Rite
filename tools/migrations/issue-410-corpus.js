'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..');
const SKIP_DIRS = new Set(['.git', 'node_modules']);
const stats = {
  files: 0,
  sceneCommands: 0,
  localCommands: 0,
  guardCommands: 0,
  splitCommands: 0,
  deadWrites: 0,
  sceneSeeds: 0,
  engineRegistry: 0,
  template: 0,
};

function rel(file) {
  return path.relative(ROOT, file).replaceAll('\\', '/');
}

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    const r = rel(full);
    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name) || r === 'docs/archive' || r.startsWith('docs/archive/')) continue;
      walk(full, out);
    } else {
      out.push(full);
    }
  }
  return out;
}

function isAuthoredDataJson(r) {
  if (r.startsWith('inspiration/')) return false;
  return r.endsWith('.json') && (r.includes('/data/') || r.startsWith('data/'));
}

function isEngineRegistry(r) {
  return r.endsWith('/data/engine.json') || r === 'data/engine.json';
}

function isSceneResource(r) {
  return r.includes('/data/scenes/')
    || r.startsWith('data/scenes/')
    || r.endsWith('/data/scene_overrides.json')
    || r === 'data/scene_overrides.json';
}

function stringifyLike(raw, value) {
  if (!raw.includes('\n')) return JSON.stringify(value);
  const match = raw.match(/\n( +)"/);
  const indent = match ? match[1].length : 2;
  const hadFinalNewline = raw.endsWith('\n');
  return JSON.stringify(value, null, indent) + (hadFinalNewline ? '\n' : '');
}

function isDeadSetVar(r, cmd) {
  if (!cmd || cmd.cmd !== 'SET_VAR') return false;
  if (r === 'projects/hichaukitoden-game/data/maps/8.json' && cmd.name === 'return_count') return true;
  if (r.endsWith('/data/flows/progression.json')
      && (cmd.name === 'reachedLevel' || cmd.name === 'levelsGained')) return true;
  return false;
}

function rewriteStateString(value, sceneOwned) {
  if (typeof value !== 'string') return value;
  let out = value;
  if (sceneOwned) {
    out = out.replace(/\bv\._guard\b/g, 'locals._guard');
    out = out.replace(/\bctx\.v\b/g, 'ctx.sceneState');
    out = out.replace(/\bv\./g, 'sceneState.');
    out = out.replace(/\bv:/g, 'sceneState:');
    out = out.replace(/\blocal\s+v\s*=\s*ctx\.sceneState\b/g, 'local sceneState = ctx.sceneState');
  } else {
    out = out.replace(/\bctx\.v\b/g, 'ctx.locals');
    out = out.replace(/\bv\./g, 'locals.');
    out = out.replace(/\blocal\s+v\s*=\s*ctx\.locals\b/g, 'local locals = ctx.locals');
  }
  return out;
}

function rewriteEngineLegacySceneStrings(node) {
  if (typeof node === 'string') {
    return node
      .replace(/\bctx\.v\b/g, 'ctx.sceneState')
      .replace(/\bv\./g, 'sceneState.')
      .replace(/\bv:/g, 'sceneState:');
  }
  if (Array.isArray(node)) return node.map(rewriteEngineLegacySceneStrings);
  if (node && typeof node === 'object') {
    for (const [key, value] of Object.entries(node)) {
      node[key] = rewriteEngineLegacySceneStrings(value);
    }
  }
  return node;
}

function assignmentOwner(row) {
  return row && row.name === '_guard' ? 'local' : 'scene';
}

function splitMixedSceneSetVar(item) {
  if (!item || item.cmd !== 'SET_VAR' || !Array.isArray(item.assignments)) return null;
  const rows = item.assignments.filter(row => row && row.name);
  if (!rows.some(row => assignmentOwner(row) === 'local')
      || !rows.some(row => assignmentOwner(row) === 'scene')) return null;

  const commands = [];
  let current = null;
  for (const row of item.assignments) {
    const owner = assignmentOwner(row);
    if (!current || current.owner !== owner) {
      const cmd = { ...item, assignments: [] };
      delete cmd.name;
      delete cmd.value;
      current = { owner, cmd };
      commands.push(current);
    }
    current.cmd.assignments.push(row);
  }
  stats.splitCommands += 1;
  return commands.map(entry => entry.cmd);
}

function transformNode(node, sceneOwned, r) {
  if (Array.isArray(node)) {
    const next = [];
    for (const item of node) {
      const split = sceneOwned ? splitMixedSceneSetVar(item) : null;
      if (split) {
        for (const part of split) {
          const mappedPart = transformNode(part, sceneOwned, r);
          if (mappedPart !== null) next.push(mappedPart);
        }
        continue;
      }
      const mapped = transformNode(item, sceneOwned, r);
      if (mapped !== null) next.push(mapped);
    }
    return next;
  }
  if (!node || typeof node !== 'object') {
    return rewriteStateString(node, sceneOwned);
  }

  if (isDeadSetVar(r, node)) {
    stats.deadWrites += 1;
    return null;
  }

  if (node.cmd === 'SET_VAR') {
    const assignments = Array.isArray(node.assignments) ? node.assignments : [];
    const assignmentNames = assignments.map(row => row && row.name).filter(Boolean);
    const hasGuard = node.name === '_guard' || assignmentNames.includes('_guard');
    const hasNonGuard = (node.name && node.name !== '_guard')
      || assignmentNames.some(name => name !== '_guard');
    if (sceneOwned && hasGuard && hasNonGuard) {
      throw new Error(`${r}: mixed _guard + Scene-state SET_VAR escaped ordered split`);
    }
    if (sceneOwned && hasGuard) {
      node.cmd = 'SET_LOCAL';
      stats.guardCommands += 1;
    } else if (sceneOwned) {
      node.cmd = 'SET_SCENE_STATE';
      stats.sceneCommands += 1;
    } else {
      node.cmd = 'SET_LOCAL';
      stats.localCommands += 1;
    }
  }

  if (node.cmd === 'SCENE_EVENT' && Object.hasOwn(node, 'vars')) {
    if (Object.hasOwn(node, 'sceneState')) {
      throw new Error(`${r}: SCENE_EVENT contains both vars and sceneState`);
    }
    node.sceneState = node.vars;
    delete node.vars;
    stats.sceneSeeds += 1;
  }

  for (const [key, value] of Object.entries(node)) {
    node[key] = transformNode(value, sceneOwned, r);
  }
  return node;
}

function migrateEngineJson(file) {
  const raw = fs.readFileSync(file, 'utf8');
  const data = JSON.parse(raw);
  const beforeCommands = (data.commands || []).length;
  data.formulaHelp = (data.formulaHelp || [])
    .filter(entry => entry.token !== 'v')
    .map(entry => ({
      ...entry,
      description: typeof entry.description === 'string'
        ? entry.description.replace(/\bv\./g, 'sceneState.')
        : entry.description,
    }));
  data.scriptingHelp = (data.scriptingHelp || []).filter(entry => entry.token !== 'ctx.v');
  data.commands = (data.commands || []).filter(entry => entry.id !== 'SET_VAR');
  const removed = beforeCommands - data.commands.length;
  if (removed > 1) throw new Error(`${rel(file)}: retired ${removed} SET_VAR registry entries`);
  const sceneEvent = data.commands.find(entry => entry.id === 'SCENE_EVENT');
  if (sceneEvent) {
    for (const param of sceneEvent.params || []) {
      if (param.key === 'vars') param.key = 'sceneState';
    }
    if (typeof sceneEvent.description === 'string') {
      sceneEvent.description = sceneEvent.description
        .replace(/\bvars\b/g, 'sceneState')
        .replace(/\bv\b/g, 'Scene State');
    }
  }
  rewriteEngineLegacySceneStrings(data);
  const next = stringifyLike(raw, data);
  if (next !== raw) {
    fs.writeFileSync(file, next);
    stats.files += 1;
  }
  stats.engineRegistry += removed;
}

function migrateAuthoredJson(file) {
  const r = rel(file);
  if (isEngineRegistry(r)) return migrateEngineJson(file);
  const raw = fs.readFileSync(file, 'utf8');
  if (!raw.includes('SET_VAR') && !raw.includes('v.') && !raw.includes('ctx.v')
      && !raw.includes('"vars"') && !raw.includes('v:')) return;
  const data = JSON.parse(raw);
  const sceneOwned = isSceneResource(r);
  const migrated = transformNode(data, sceneOwned, r);
  const next = stringifyLike(raw, migrated);
  if (next !== raw) {
    fs.writeFileSync(file, next);
    stats.files += 1;
  }
}

function migrateMinimalTemplate(file) {
  let text = fs.readFileSync(file, 'utf8');
  const before = text;
  text = text.replace(/cmd: 'SET_VAR'/g, "cmd: 'SET_SCENE_STATE'");
  text = text.replace(/\bv\./g, 'sceneState.');
  text = text.replace(/\bv:/g, 'sceneState:');
  if (text !== before) {
    fs.writeFileSync(file, text);
    stats.template += 1;
  }
}

function collectLegacyStateStrings(node, currentPath = '$', hits = []) {
  if (typeof node === 'string') {
    if (/\bv\.[A-Za-z_]/.test(node) || /\bctx\.v\b/.test(node) || /\bv:[A-Za-z_]/.test(node)) {
      hits.push(`${currentPath} = ${JSON.stringify(node)}`);
    }
    return hits;
  }
  if (Array.isArray(node)) {
    node.forEach((value, index) => collectLegacyStateStrings(value, `${currentPath}[${index}]`, hits));
    return hits;
  }
  if (node && typeof node === 'object') {
    for (const [key, value] of Object.entries(node)) {
      collectLegacyStateStrings(value, `${currentPath}.${key}`, hits);
    }
  }
  return hits;
}

function assertAuthoredPostconditions(files) {
  const errors = [];
  for (const file of files) {
    const r = rel(file);
    if (!isAuthoredDataJson(r)) continue;
    const text = fs.readFileSync(file, 'utf8');
    let data;
    try { data = JSON.parse(text); } catch { continue; }
    const scan = JSON.stringify(data);
    if (scan.includes('"cmd":"SET_VAR"')) errors.push(`${r}: SET_VAR remains`);
    const legacyStrings = collectLegacyStateStrings(data);
    if (legacyStrings.length) {
      for (const hit of legacyStrings) errors.push(`${r}: legacy state string remains at ${hit}`);
    }
    if (/"cmd":"SCENE_EVENT"[^}]*"vars":/.test(scan)) errors.push(`${r}: SCENE_EVENT.vars remains`);
    if (isEngineRegistry(r)) {
      if ((data.commands || []).some(entry => entry.id === 'SET_VAR')) errors.push(`${r}: SET_VAR remains registered`);
      if ((data.formulaHelp || []).some(entry => entry.token === 'v')) errors.push(`${r}: v remains in Formula help`);
      if ((data.scriptingHelp || []).some(entry => entry.token === 'ctx.v')) errors.push(`${r}: ctx.v remains in SCRIPT help`);
    }
  }
  if (errors.length) throw new Error(`\n#410 authored migration postcondition failed:\n- ${errors.join('\n- ')}`);
}

const files = walk(ROOT);
for (const file of files) {
  const r = rel(file);
  if (isAuthoredDataJson(r)) migrateAuthoredJson(file);
}
migrateMinimalTemplate(path.join(ROOT, 'studio/editor/minimal-project-template.js'));
assertAuthoredPostconditions(files);

console.log('issue #410 authored corpus migration complete');
console.log(JSON.stringify(stats, null, 2));
