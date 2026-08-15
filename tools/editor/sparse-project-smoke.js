#!/usr/bin/env node
'use strict';

const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const lifecycle = require('./project-lifecycle');
const projectPlay = require('./project-play');

const REPO = path.resolve(__dirname, '..', '..');

function spawnLove(lovec, stageDir, args = []) {
    const result = childProcess.spawnSync(lovec, ['.', ...args], {
        cwd: stageDir,
        env: Object.assign({}, process.env, { SDL_AUDIODRIVER: 'dummy' }),
        encoding: 'utf8',
        maxBuffer: 16 * 1024 * 1024,
        timeout: 120000,
    });
    const output = `${result.stdout || ''}\n${result.stderr || ''}`;
    process.stdout.write(output);
    if (result.error) throw result.error;
    return { result, output };
}

function run(options = {}) {
    const lovec = options.lovec || process.env.LOVEC || 'lovec';
    const work = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-sparse-smoke-'));
    let stageDir = null;
    try {
        const project = path.join(work, 'fresh-game');
        const created = lifecycle.createSparseProject({ target: project, installRoot: REPO, name: 'Fresh Game' });

        // Source-shape assertions before staging: a new Project is genuinely
        // sparse, and keyed registries use #485's explicit-empty marker rather
        // than a fake starter record. Inherited authored defaults must stay out
        // of Project/data until the author explicitly chooses Make Local.
        const localSystem = JSON.parse(fs.readFileSync(path.join(project, 'data', 'system.json'), 'utf8'));
        if (!localSystem.ui || localSystem.ui.activeFont !== 'monogram-extended-italic') {
            throw new Error('fresh sparse Project did not select vendored Monogram Extended Italic');
        }
        const localTitle = JSON.parse(fs.readFileSync(path.join(project, 'data', 'scenes', 'title.json'), 'utf8'));
        const titleWindow = localTitle.windows.find(window => window.id === 'project_title');
        if (!titleWindow || !titleWindow.content || titleWindow.content[0].text !== 'Fresh Game') {
            throw new Error('fresh sparse Project did not author its visible Project name literally');
        }
        if (localTitle.draw !== 'windows') {
            throw new Error(`fresh sparse title Scene has invalid draw mode: ${localTitle.draw}`);
        }
        const localMapScene = JSON.parse(fs.readFileSync(path.join(project, 'data', 'scenes', 'map.json'), 'utf8'));
        if (localMapScene.draw !== 'world' || localMapScene.world !== 'map') {
            throw new Error(`fresh sparse Map Scene must draw registered map world, got draw=${localMapScene.draw} world=${localMapScene.world}`);
        }
        if (fs.existsSync(path.join(project, 'data', 'scenes', 'dialogue.json'))) {
            throw new Error('fresh sparse Project must inherit house Dialogue Scene instead of copying it locally');
        }
        if (fs.existsSync(path.join(project, 'data', 'flows', 'exploration.json'))) {
            throw new Error('fresh sparse Project must inherit house exploration Flow instead of shadowing it locally');
        }
        if (fs.existsSync(path.join(project, 'data', 'progression.json'))) {
            throw new Error('fresh sparse Project must inherit progression instead of copying it locally');
        }
        const progressionProvider = lifecycle.authoredDefaultInfo({
            project,
            resource: 'progression',
            installRoot: REPO,
        });
        if (progressionProvider.provider !== 'rtp' || progressionProvider.revision !== created.rtpRevision) {
            throw new Error(`fresh sparse Project resolved wrong progression provider: ${JSON.stringify(progressionProvider)}`);
        }

        const emptyTilesets = JSON.parse(fs.readFileSync(path.join(project, 'data', 'tilesets', 'index.json'), 'utf8'));
        if (!Array.isArray(emptyTilesets.files) || emptyTilesets.files.length !== 0) {
            throw new Error('fresh sparse Project tilesets registry is not explicitly empty');
        }
        const localTilesetJson = fs.readdirSync(path.join(project, 'data', 'tilesets'))
            .filter(name => name.toLowerCase().endsWith('.json') && name.toLowerCase() !== 'index.json');
        if (localTilesetJson.length !== 0) {
            throw new Error(`fresh sparse Project fabricated local tileset records: ${localTilesetJson.join(', ')}`);
        }

        stageDir = projectPlay.stageProject({ installRoot: REPO, projectRoot: created.projectRoot });

        const engine = JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'engine.json'), 'utf8'));
        if (!Array.isArray(engine.commands) || !engine.commands.some(command => command.id === 'LOAD_MAP')) {
            throw new Error('staged sparse Project did not materialize inherited engine commands');
        }
        for (const scene of ['save_menu.json', 'items.json', 'status.json', 'controls.json', 'dialogue.json']) {
            if (!fs.existsSync(path.join(stageDir, 'data', 'scenes', scene))) {
                throw new Error(`staged sparse Project did not materialize inherited Scene ${scene}`);
            }
            if (fs.existsSync(path.join(project, 'data', 'scenes', scene))) {
                throw new Error(`staging leaked inherited Scene back into sparse Project source: ${scene}`);
            }
        }
        const dialogue = JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'scenes', 'dialogue.json'), 'utf8'));
        if (dialogue.draw !== 'windows' || dialogue.backdrop !== 'map') {
            throw new Error(`staged house Dialogue Scene has invalid presentation: draw=${dialogue.draw} backdrop=${dialogue.backdrop}`);
        }
        const dialogueWindows = new Set((dialogue.windows || []).map(window => window.id));
        for (const required of ['dialogue_message', 'dialogue_choices']) {
            if (!dialogueWindows.has(required)) {
                throw new Error(`staged house Dialogue Scene is missing visible Event Program window ${required}`);
            }
        }
        if (dialogue.config && dialogue.config.dock) {
            throw new Error('RTP Dialogue Scene must not depend on a Second Gate/root dock variant');
        }

        for (const flowName of ['quest.json', 'exploration.json', 'progression.json']) {
            if (!fs.existsSync(path.join(stageDir, 'data', 'flows', flowName))) {
                throw new Error(`staged sparse Project did not materialize inherited Flow ${flowName}`);
            }
            if (fs.existsSync(path.join(project, 'data', 'flows', flowName))) {
                throw new Error(`staging leaked inherited Flow back into sparse Project source: ${flowName}`);
            }
        }
        const explorationFlow = JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'flows', 'exploration.json'), 'utf8'));
        if (!Array.isArray(explorationFlow.step) || explorationFlow.step.length === 0) {
            throw new Error('staged sparse Project has no non-empty exploration.step host phase');
        }
        if (!Array.isArray(explorationFlow.expedition_start) || explorationFlow.expedition_start.length === 0) {
            throw new Error('staged sparse Project has no non-empty exploration.expedition_start host phase');
        }
        if (fs.existsSync(path.join(project, 'data', 'engine.json'))) {
            throw new Error('staging materialized inherited engine registry into Project source');
        }

        const stagedProgressionPath = path.join(stageDir, 'data', 'progression.json');
        if (!fs.existsSync(stagedProgressionPath)) {
            throw new Error('staged sparse Project did not materialize inherited progression');
        }
        const stagedProgression = JSON.parse(fs.readFileSync(stagedProgressionPath, 'utf8'));
        if (stagedProgression.nextLevelExp !== 'level * 15') {
            throw new Error(`staged sparse Project resolved unexpected progression: ${JSON.stringify(stagedProgression)}`);
        }
        const provenance = JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'authored_resolution.json'), 'utf8'));
        const stagedProgressionProvider = provenance.resources && provenance.resources.progression
            && provenance.resources.progression.provider;
        if (!stagedProgressionProvider || stagedProgressionProvider.kind !== 'rtp'
            || stagedProgressionProvider.revision !== created.rtpRevision) {
            throw new Error(`staged sparse Project lost progression provenance: ${JSON.stringify(stagedProgressionProvider)}`);
        }
        if (fs.existsSync(path.join(project, 'data', 'progression.json'))) {
            throw new Error('staging leaked inherited progression back into sparse Project source');
        }

        const stagedTitle = JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'scenes', 'title.json'), 'utf8'));
        const stagedTitleWindow = stagedTitle.windows.find(window => window.id === 'project_title');
        if (!stagedTitleWindow || stagedTitleWindow.content[0].text !== 'Fresh Game') {
            throw new Error('staged sparse Project lost its visible Project-owned title');
        }
        const stagedMapScene = JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'scenes', 'map.json'), 'utf8'));
        if (stagedMapScene.draw !== 'world' || stagedMapScene.world !== 'map') {
            throw new Error(`staged sparse Project lost Map presentation contract: draw=${stagedMapScene.draw} world=${stagedMapScene.world}`);
        }
        const defaultFont = path.join(stageDir, 'assets', 'fonts', 'monogram-extended-italic.ttf');
        if (!fs.existsSync(defaultFont) || fs.statSync(defaultFont).size < 1024) {
            throw new Error('staged sparse Project cannot resolve assets/fonts/monogram-extended-italic.ttf');
        }

        // First prove the ordinary staged game validates as-is.
        const validation = spawnLove(lovec, stageDir, ['validate']);
        if (validation.result.status !== 0 || !validation.output.includes('VALIDATE OK')) {
            throw new Error(`fresh sparse Project validation failed (exit ${validation.result.status})`);
        }

        // Then prove the hermetic STAGED player tree can actually cross a level
        // from its materialized progression authority. The probe replaces only
        // the disposable stage's main.lua; Project source and installed RTP stay
        // untouched. This avoids adding a test-only runtime command to Thestra.
        fs.writeFileSync(path.join(stageDir, 'main.lua'), `
local loader = require("data.loader")
local session = require("engine.session")
local progression = require("engine.progression")

function love.load()
    loader.init()
    local sess = session.GameSession.new(loader)
    local unit = {
        id = "sparse_progression_probe",
        name = "Progression Probe",
        defaultGrowthSeed = 1,
        params = { maxHp = 10, atk = 10, def = 10, mat = 10, mdf = 10, mpd = 2, mxa = 1, mxp = 1 },
    }
    local battler = session.Battler.new(unit, 1, 1, "probe")
    sess.party[1] = battler
    local needed = progression.nextLevelExp(1)
    local leveled = battler:gainExp(needed, sess)
    if not leveled or battler.level ~= 2 or battler.exp ~= 0 then
        error("sparse progression crossing failed: needed=" .. tostring(needed)
            .. " level=" .. tostring(battler.level) .. " exp=" .. tostring(battler.exp))
    end
    print("SPARSE PROGRESSION RUNTIME OK threshold=" .. tostring(needed) .. " level=" .. tostring(battler.level))
    love.event.quit(0)
end
`, 'utf8');
        const progressionRun = spawnLove(lovec, stageDir);
        if (progressionRun.result.status !== 0
            || !progressionRun.output.includes('SPARSE PROGRESSION RUNTIME OK threshold=15 level=2')) {
            throw new Error(`fresh sparse Project progression runtime proof failed (exit ${progressionRun.result.status})`);
        }

        process.stdout.write(`SPARSE PROJECT SMOKE OK ${JSON.stringify({
            mode: created.mode,
            rtpRevision: created.rtpRevision,
            progressionProvider: progressionProvider.provider,
            progressionFormula: stagedProgression.nextLevelExp,
            defaultFont: localSystem.ui.activeFont,
            mapDraw: localMapScene.draw,
            mapWorld: localMapScene.world,
            dialogueWindows: [...dialogueWindows],
            explorationStepCommands: explorationFlow.step.length,
            localSceneFiles: JSON.parse(fs.readFileSync(path.join(project, 'data', 'scenes', 'index.json'), 'utf8')).files,
        })}\n`);
        return 0;
    } finally {
        if (stageDir) projectPlay.removeStage(stageDir);
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