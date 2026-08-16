#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const SCHEMA_PATH = path.join(__dirname, 'schema.json');
const CENSUS_PATH = path.join(__dirname, 'census.json');
const OUTPUT_PATH = path.join(REPO_ROOT, 'docs', 'AUTHORING-STATE.md');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function unique(values) {
  return new Set(values).size === values.length;
}

function schemaContract(schema) {
  const defs = schema && schema.$defs;
  if (!defs || !defs.domain || !defs.dimensionState || !defs.dimensionName || !defs.surface) {
    throw new Error('schema.json is missing the finite census definitions');
  }

  const domains = defs.domain.enum;
  const states = defs.dimensionState.enum;
  const dimensions = defs.dimensionName.enum;
  const required = defs.surface.required;
  const allowed = Object.keys(defs.surface.properties || {});

  if (![domains, states, dimensions, required, allowed].every(Array.isArray)) {
    throw new Error('schema.json census definitions must be finite arrays');
  }
  if (![domains, states, dimensions, required, allowed].every(unique)) {
    throw new Error('schema.json census definitions must not contain duplicate values');
  }

  const expectedStates = ['covered', 'missing', 'not-applicable'];
  if (states.length !== expectedStates.length || expectedStates.some(v => !states.includes(v))) {
    throw new Error(`dimensionState must be exactly: ${expectedStates.join(', ')}`);
  }

  return { domains, states, dimensions, required, allowed };
}

function validateCensus(census, schema) {
  const errors = [];
  const contract = schemaContract(schema);

  if (!census || typeof census !== 'object' || Array.isArray(census)) {
    return ['census root must be an object'];
  }
  const rootKeys = Object.keys(census);
  for (const key of rootKeys) {
    if (!['schemaVersion', 'surfaces'].includes(key)) errors.push(`root: unexpected property '${key}'`);
  }
  if (census.schemaVersion !== 1) errors.push('root: schemaVersion must be 1');
  if (!Array.isArray(census.surfaces) || census.surfaces.length === 0) {
    errors.push('root: surfaces must be a non-empty array');
    return errors;
  }

  const seenIds = new Set();
  const seenDomains = new Set();

  census.surfaces.forEach((surface, index) => {
    const at = `surfaces[${index}]`;
    if (!surface || typeof surface !== 'object' || Array.isArray(surface)) {
      errors.push(`${at}: must be an object`);
      return;
    }

    for (const key of contract.required) {
      if (!(key in surface)) errors.push(`${at}: missing required property '${key}'`);
    }
    for (const key of Object.keys(surface)) {
      if (!contract.allowed.includes(key)) errors.push(`${at}: unexpected property '${key}'`);
    }

    if (typeof surface.id !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(surface.id)) {
      errors.push(`${at}: id must be lower-kebab-case`);
    } else if (seenIds.has(surface.id)) {
      errors.push(`${at}: duplicate id '${surface.id}'`);
    } else {
      seenIds.add(surface.id);
    }

    if (typeof surface.name !== 'string' || surface.name.trim() === '') {
      errors.push(`${at}: name must be a non-empty string`);
    }
    if (!contract.domains.includes(surface.domain)) {
      errors.push(`${at}: domain '${surface.domain}' is not in schema.json`);
    } else {
      seenDomains.add(surface.domain);
    }

    const missing = [];
    for (const dimension of contract.dimensions) {
      const value = surface[dimension];
      if (!contract.states.includes(value)) {
        errors.push(`${at}.${dimension}: expected one of ${contract.states.join(', ')}`);
      }
      if (value === 'missing') missing.push(dimension);
    }

    if (!Array.isArray(surface.deferredDebt)) {
      errors.push(`${at}.deferredDebt: must be an array`);
    } else {
      if (!unique(surface.deferredDebt)) errors.push(`${at}.deferredDebt: duplicate dimensions are not allowed`);
      for (const dimension of surface.deferredDebt) {
        if (!contract.dimensions.includes(dimension)) {
          errors.push(`${at}.deferredDebt: unknown dimension '${dimension}'`);
        }
      }

      const registered = new Set(surface.deferredDebt);
      for (const dimension of missing) {
        if (!registered.has(dimension)) {
          errors.push(`${at}.${dimension}: missing coverage is unregistered debt`);
        }
      }
      for (const dimension of registered) {
        if (surface[dimension] !== 'missing') {
          errors.push(`${at}.deferredDebt: '${dimension}' is registered but the dimension is '${surface[dimension]}'`);
        }
      }
    }

    if (typeof surface.notes !== 'string' || surface.notes.trim() === '') {
      errors.push(`${at}: notes must be a non-empty string`);
    }
  });

  for (const domain of contract.domains) {
    if (!seenDomains.has(domain)) {
      errors.push(`domain '${domain}' has no census surface; every finite schema domain must be represented`);
    }
  }

  return errors;
}

function statusMark(value) {
  if (value === 'covered') return '✅';
  if (value === 'missing') return '⚠️';
  return '—';
}

function escapeCell(value) {
  return String(value).replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');
}

function renderMarkdown(census, schema) {
  const { dimensions } = schemaContract(schema);
  const unhealthy = census.surfaces.filter(surface => surface.deferredDebt.length > 0);
  const debtCount = census.surfaces.reduce((sum, surface) => sum + surface.deferredDebt.length, 0);

  const labels = {
    runtimeExists: 'Runtime',
    persisted: 'Persisted',
    authorable: 'Authorable',
    livePreview: 'Live preview',
    goldenFixture: 'Golden',
    parityCovered: 'Parity',
    roundTripCovered: 'Round-trip',
    hardeningCovered: 'Hardening'
  };

  const lines = [
    '# Authoring State',
    '',
    '<!-- GENERATED by tools/authoring-census/generate.js. Do not edit by hand. -->',
    '',
    'This is the generated accounting view of authoring-visible engine/editor surfaces. It does **not** replace `docs/ENGINE-STATE.md`: runtime truth remains owned by the live engine and its existing generated status. This document records closure around that truth — persistence, authoring, preview, fixtures, parity, round-trip, and hardening.',
    '',
    `**Status:** ${census.surfaces.length} surfaces across ${schema.$defs.domain.enum.length} finite domains; ${unhealthy.length} unhealthy surfaces; ${debtCount} explicitly registered missing dimensions.`,
    '',
    'Legend: ✅ covered · ⚠️ missing but explicitly registered as debt · — not applicable.',
    '',
    '## Surface census',
    '',
    `| Domain | Surface | ${dimensions.map(d => labels[d]).join(' | ')} |`,
    `|---|---|${dimensions.map(() => '---').join('|')}|`,
  ];

  for (const surface of census.surfaces) {
    lines.push(`| ${escapeCell(surface.domain)} | ${escapeCell(surface.name)} | ${dimensions.map(d => statusMark(surface[d])).join(' | ')} |`);
  }

  lines.push('', '## Unhealthy surfaces', '');
  if (unhealthy.length === 0) {
    lines.push('No missing dimensions are registered.');
  } else {
    for (const surface of unhealthy) {
      lines.push(`### ${surface.name}`);
      lines.push('');
      lines.push(`- **Domain:** ${surface.domain}`);
      lines.push(`- **Missing:** ${surface.deferredDebt.map(d => `\`${d}\``).join(', ')}`);
      lines.push(`- **Notes:** ${surface.notes}`);
      lines.push('');
    }
  }

  lines.push(
    '## Review and verification contract',
    '',
    '- `tools/authoring-census/census.json` is the machine-readable source. `schema.json` is the finite vocabulary.',
    '- A `missing` dimension is legal only when that exact dimension is also present in `deferredDebt`. Unknown or unregistered gaps fail verification.',
    '- When a registered gap is closed, change the dimension to `covered` **and remove it from `deferredDebt`**; stale debt also fails verification.',
    '- A PR that adds an authoring-visible feature or an authoring-facing persistence field must review this census and add/update the relevant surface. Do not infer editor closure from runtime existence.',
    '- Do not copy runtime implementation truth into this census. Notes should identify the closure claim or point at the owning surface; engine/runtime behavior remains authoritative in engine/data code and `docs/ENGINE-STATE.md`.',
    '',
    'Exact local commands:',
    '',
    '```text',
    'npm run authoring-state:generate',
    'npm run authoring-state:check',
    'npm run test:authoring-state',
    '```',
    '',
    '`authoring-state:check` is read-only and fails when the source is invalid or this generated document has drifted.',
    ''
  );

  return lines.join('\n');
}

function loadAndValidate() {
  const schema = readJson(SCHEMA_PATH);
  const census = readJson(CENSUS_PATH);
  const errors = validateCensus(census, schema);
  if (errors.length > 0) {
    const message = ['AUTHORING CENSUS INVALID', ...errors.map(error => `- ${error}`)].join('\n');
    throw new Error(message);
  }
  return { schema, census };
}

function main(argv = process.argv.slice(2)) {
  const check = argv.includes('--check');
  const unexpected = argv.filter(arg => arg !== '--check');
  if (unexpected.length > 0) {
    throw new Error(`unknown argument(s): ${unexpected.join(', ')}`);
  }

  const { schema, census } = loadAndValidate();
  const expected = renderMarkdown(census, schema);

  if (check) {
    if (!fs.existsSync(OUTPUT_PATH)) {
      throw new Error('docs/AUTHORING-STATE.md is missing; run npm run authoring-state:generate');
    }
    const actual = fs.readFileSync(OUTPUT_PATH, 'utf8');
    if (actual !== expected) {
      throw new Error('docs/AUTHORING-STATE.md is stale; run npm run authoring-state:generate and commit the result');
    }
    const debtCount = census.surfaces.reduce((sum, surface) => sum + surface.deferredDebt.length, 0);
    console.log(`AUTHORING STATE OK (${census.surfaces.length} surfaces; ${debtCount} registered debt dimensions)`);
    return;
  }

  fs.writeFileSync(OUTPUT_PATH, expected, 'utf8');
  console.log(`wrote ${path.relative(REPO_ROOT, OUTPUT_PATH)}`);
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
  schemaContract,
  validateCensus,
  renderMarkdown,
  statusMark
};
