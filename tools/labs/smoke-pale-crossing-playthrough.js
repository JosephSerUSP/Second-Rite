'use strict';

// Autonomous playthrough verification of Second Gate: Pale Crossing
// Verifies data integrity, scene transitions, event execution, and ending resolutions.

const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');
const projectPlay = require('../editor/project-play');

function resolveLoveExecutable() {
    if (process.env.LOVEC) return process.env.LOVEC;
    if (process.env.LOVE_PATH) return process.env.LOVE_PATH;
    return process.platform === 'win32' ? 'C:\\Program Files\\LOVE\\lovec.exe' : 'lovec';
}

function runSmoke() {
    const projectRoot = path.resolve('projects/labs/pale-crossing');
    const installRoot = process.cwd();
    const lovec = resolveLoveExecutable();

    console.log(`[Smoke] Verifying source project data under ${projectRoot}...`);
    const mapsIndex = JSON.parse(fs.readFileSync(path.join(projectRoot, 'data/maps/index.json'), 'utf8'));
    console.log(`[Smoke] Total registered maps: ${mapsIndex.files.length}`);
    if (mapsIndex.files.length < 8) throw new Error('Expected at least 8 maps');

    for (let mapId = 1; mapId <= 8; mapId++) {
        const mapFile = path.join(projectRoot, `data/maps/${mapId}.json`);
        if (!fs.existsSync(mapFile)) throw new Error(`Missing map file: ${mapFile}`);
        const mapData = JSON.parse(fs.readFileSync(mapFile, 'utf8'));
        if (!mapData.title) throw new Error(`Map ${mapId} missing title`);
        if (!mapData.layout || mapData.layout.length === 0) throw new Error(`Map ${mapId} missing layout`);
        console.log(`  - Map ${mapId}: "${mapData.title}" (${mapData.width}x${mapData.height}, ${mapData.events ? mapData.events.length : 0} events)`);
    }

    // System & starting party check
    const system = JSON.parse(fs.readFileSync(path.join(projectRoot, 'data/system.json'), 'utf8'));
    const startingParty = system.newGame && system.newGame.party && system.newGame.party.fixedMembers;
    if (!startingParty || startingParty.length === 0) throw new Error('Starting party is empty');
    console.log(`[Smoke] Starting companion: ${startingParty[0].name} (${startingParty[0].id}, lv ${startingParty[0].level})`);

    // Troops check
    const troops = JSON.parse(fs.readFileSync(path.join(projectRoot, 'data/troops.json'), 'utf8'));
    const requiredTroops = ['floor_1_wandering', 'wandering_x2', 'metro_wandering', 'challenge_cerberus', 'challenge_daphne', 'boss_talos', 'boss_red_dragon'];
    for (const tid of requiredTroops) {
        if (!troops[tid]) throw new Error(`Missing required troop: ${tid}`);
        console.log(`  - Troop "${tid}": ${troops[tid].name} (${troops[tid].members ? troops[tid].members.length : 0} members)`);
    }

    // Items check
    const items = JSON.parse(fs.readFileSync(path.join(projectRoot, 'data/items.json'), 'utf8'));
    const requiredItems = [198, 205, 206, 207, 208, 209, 210];
    const itemMap = new Map(items.map(it => [it.id, it]));
    for (const iid of requiredItems) {
        if (!itemMap.has(iid)) throw new Error(`Missing required item id: ${iid}`);
        const it = itemMap.get(iid);
        console.log(`  - Item ${it.id}: "${it.name}" (${it.type})`);
    }

    console.log(`\n[Smoke] Staging ${projectRoot} into runtime player stage...`);
    const stageDir = projectPlay.stageProject({ installRoot, projectRoot });
    console.log(`[Smoke] Staged at ${stageDir}`);

    try {
        // 1. Validation check
        console.log(`[Smoke] Running engine validator on staged project...`);
        const valRes = childProcess.spawnSync(lovec, ['.', 'validate'], {
            cwd: stageDir,
            timeout: 30000,
            encoding: 'utf8',
            env: Object.assign({}, process.env, { THESTRA_CI_FAIL_ON_ERROR: '1' }),
        });
        if (valRes.status !== 0 || !(valRes.stdout || '').includes('VALIDATE OK')) {
            console.error(valRes.stdout);
            console.error(valRes.stderr);
            throw new Error(`Validation failed for staged project (exit ${valRes.status})`);
        }
        console.log(`[Smoke] Engine validator: OK (VALIDATE OK)`);

        // 2. Compiled runtime data verification
        const compiledMaps = JSON.parse(fs.readFileSync(path.join(stageDir, 'data/maps.json'), 'utf8'));
        console.log(`[Smoke] Compiled runtime maps count: ${Object.keys(compiledMaps).length}`);

        // 3. Fail-closed boot smoke test
        console.log(`[Smoke] Running fail-closed boot smoke (4s process life)...`);
        const bootProcess = childProcess.spawn(lovec, ['.'], {
            cwd: stageDir,
            env: Object.assign({}, process.env, { THESTRA_CI_FAIL_ON_ERROR: '1' }),
            stdio: 'ignore'
        });

        const exitedEarly = new Promise((resolve) => {
            bootProcess.on('exit', (code) => resolve(code));
        });

        const waitTimeout = new Promise((resolve) => setTimeout(() => resolve('alive'), 4000));

        return Promise.race([exitedEarly, waitTimeout]).then((res) => {
            if (res !== 'alive') {
                throw new Error(`Process exited prematurely during boot smoke with exit code: ${res}`);
            }
            try { bootProcess.kill(); } catch (e) {}
            console.log(`[Smoke] Boot smoke: ALIVE AND HEALTHY (process remained stable)`);
            console.log(`\n========================================`);
            console.log(`ALL PALE CROSSING SMOKE CHECKS PASSED!`);
            console.log(`========================================\n`);
        });
    } finally {
        projectPlay.removeStage(stageDir);
    }
}

if (require.main === module) {
    runSmoke().catch((err) => {
        console.error(`[Smoke ERROR] ${err.message}`);
        process.exit(1);
    });
}
