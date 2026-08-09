#!/usr/bin/env node
'use strict';

// Opt-in infrastructure assertion for SPEC §5.3. This intentionally needs an
// authenticated `gh` session and is therefore neither a local gate nor CI.
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const spec = fs.readFileSync(path.join(root, 'docs', 'SPEC.md'), 'utf8');
const workflow = fs.readFileSync(path.join(root, '.github', 'workflows', 'verify.yml'), 'utf8');
const problems = [];

function expect(condition, message) {
    if (!condition) problems.push(message);
}

function ghJson(args) {
    return JSON.parse(childProcess.execFileSync('gh', args, {
        cwd: root,
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'inherit'],
    }));
}

function workflowHas(pattern) {
    return pattern.test(workflow);
}

const repository = ghJson(['repo', 'view', '--json', 'nameWithOwner,defaultBranchRef']);
const repo = repository.nameWithOwner;
const defaultBranch = repository.defaultBranchRef.name;
const rulesets = ghJson(['api', `repos/${repo}/rulesets`]);
const active = rulesets.filter(ruleset => ruleset.target === 'branch' && ruleset.enforcement === 'active');
const names = active.map(ruleset => ruleset.name).sort();

expect(defaultBranch === 'main', `SPEC §5.3 says the protected default branch is main; GitHub reports ${defaultBranch}`);
expect(JSON.stringify(names) === JSON.stringify(['antidel', 'verify-gates']),
    `SPEC §5.3 says active branch rulesets are antidel and verify-gates; GitHub reports ${names.join(', ') || '(none)'}`);

const details = {};
for (const ruleset of active) details[ruleset.name] = ghJson(['api', `repos/${repo}/rulesets/${ruleset.id}`]);

for (const name of ['antidel', 'verify-gates']) {
    const ruleset = details[name];
    expect(ruleset && ruleset.conditions && ruleset.conditions.ref_name
        && (ruleset.conditions.ref_name.include || []).includes('~DEFAULT_BRANCH'),
    `ruleset ${name} no longer targets the default branch as §5.3 states`);
}

const verify = details['verify-gates'];
const requiredRule = verify && (verify.rules || []).find(rule => rule.type === 'required_status_checks');
const required = requiredRule && requiredRule.parameters;
const contexts = required ? (required.required_status_checks || []).map(check => check.context).sort() : [];
expect(required && required.strict_required_status_checks_policy === true,
    'ruleset verify-gates no longer requires strict status checks as §5.3 states');
expect(JSON.stringify(contexts) === JSON.stringify(['gates (Windows)']),
    `ruleset verify-gates required contexts differ from §5.3: ${contexts.join(', ') || '(none)'}`);
expect(verify && (verify.bypass_actors || []).some(actor => actor.actor_type === 'RepositoryRole'
    && actor.bypass_mode === 'always'),
'ruleset verify-gates no longer has the documented always-on repository-role bypass');

expect(workflowHas(/push:\s*\r?\n\s*branches:\s*\[main\]/),
    'verify.yml no longer triggers on pushes to main as §5.3 states');
expect(workflowHas(/\r?\n\s*pull_request:\s*(?:\r?\n|#)/),
    'verify.yml no longer triggers on pull requests as §5.3 states');

const hosted = [
    ['G1', /lovec\.exe?\s+\.\s+validate|\$env:LOVEC\s+\.\s+validate/],
    ['unit', /\$env:LOVEC\s+\.\s+unittest/],
    ['save', /\$env:LOVEC\s+\.\s+savetest/],
    ['G2', /tools\/golden\/check\.ps1/],
    ['G3', /tools\/golden\/check-ui\.ps1/],
    ['G4', /tools\/golden\/check-state\.ps1/],
];
for (const [gate, pattern] of hosted) {
    expect(workflowHas(pattern), `verify.yml no longer runs ${gate}, contrary to §5.3`);
}
expect(!workflowHas(/check-screens\.ps1|check-editor\.ps1/),
    'verify.yml now runs G5 or G6, but §5.3 says hosted CI excludes both');
expect(workflowHas(/reachability \(informational, never a gate\)[\s\S]*?continue-on-error:\s*true/),
    'verify.yml no longer runs reachability as a non-blocking report as §5.3 states');

expect(/Ruleset `antidel`/.test(spec), 'SPEC §5.3 no longer documents the antidel ruleset');
expect(/Ruleset `verify-gates` requires the `gates \(Windows\)` check, strict/.test(spec),
    'SPEC §5.3 no longer documents the strict gates (Windows) requirement');
expect(/CI covers six of the eight gates/.test(spec) && /G5 and G6 are excluded by design/.test(spec),
    'SPEC §5.3 no longer documents the six-gate hosted-CI split and G5/G6 exclusion');

if (problems.length) {
    console.error(`SPEC/CI infrastructure drift (${problems.length}):`);
    for (const problem of problems) console.error(`- ${problem}`);
    process.exitCode = 1;
} else {
    console.log(`SPEC/CI infrastructure claims match ${repo} (${defaultBranch}).`);
}
