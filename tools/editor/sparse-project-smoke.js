#!/usr/bin/env node
'use strict';

const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const lifecycle = require('./project-lifecycle');
const projectPlay = require('./project-play');

const REPO = path.resolve(__dirname, '..', '..');

function run(options = {}) {
    const lovec = options.lovec || process.env.LOVEC || 'lovec';
    const work = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-sparse-smoke-'));
    try {
        const project = path.join(work, 'fresh-game');
        const created = lifecycle.createSparseProject({ target: project, installRoot: REPO, name: 'Fresh Game' });
        const stageDir = projectPlay.stageProject({ installRoot: REPO, projectRoot: created.projectRoot });

        const engine = JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'engine.json'), 'utf8'));
        if (!Array.isArray(engine.commands) || !engine.commands.some(command => command.id === 'LOAD_MAP')) {
            throw new Error('staged sparse Project did not materialize inherited engine commands');
        }
        for (const scene of ['save_menu.json', 'items.json', 'status.json', 'controls.json']) {
            if (!fs.existsSync(path.join(stageDir, 'data', 'scenes', scene))) {
                throw new Error(`staged sparse Project did not materialize inherited Scene ${scene}`);
            }
            if (fs.existsSync(path.join(project, 'data', 'scenes', scene))) {
                throw new Error(`staging leaked inherited Scene back into sparse Project source: ${scene}`);
            }
        }
        if (!fs.existsSync(path.join(stageDir, 'data', 'flows', 'quest.json'))) {
            throw new Error('staged sparse Project did not materialize inherited quest Flow');
        }
        if (fs.existsSync(path.join(project, 'data', 'engine.json'))
                || fs.existsSync(path.join(project, 'data', 'flows', 'quest.json'))) {
            throw new Error('staging materialized inherited authored defaults into Project source');
        }

        const result = childProcess.spawnSync(lovec, [stageDir, 'validate'], {
            cwd: REPO,
            env: Object.assign({}, process.env, { SDL_AUDIODRIVER: 'dummy' }),
            encoding: 'utf8',
            maxBuffer: 16 * 1024 * 1024,
        });
        const output = `${result.stdout || ''}\n${result.stderr || ''}`;
        process.stdout.write(output);
        if (result.error) throw result.error;
        if (result.status !== 0 || !output.includes('VALIDATE OK')) {
            throw new Error(`fresh sparse Project validation failed (exit ${result.status})`);
        }
        process.stdout.write(`SPARSE PROJECT SMOKE OK ${JSON.stringify({
            mode: created.mode,
            rtpRevision: created.rtpRevision,
            localSceneFiles: JSON.parse(fs.readFileSync(path.join(project, 'data', 'scenes', 'index.json'), 'utf8')).files,
        })}\n`);
        projectPlay.removeStage(stageDir);
        return 0;
    } finally {
        fs.rmSync(work, { recursive: true, force: true });
    }
}

if (require.main === module) {
    try { process.exitCode = run(); }
    catch (error) {
        console.error(error && error.stack ? error.stack : error);
        process.exitCode = 1;
    }
}

module.exports = { run };
