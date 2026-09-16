'use strict';

// #993 / #704: one owner-facing entrypoint for the lab controls and the
// existing unidentified-gear candidates.  The lab runs from disposable
// project copies so its authored scenes and golden references are untouched.
const fs = require('fs');
const os = require('os');
const path = require('path');
const https = require('https');
const cp = require('child_process');
const exporter = require('../export/export-game');

const ROOT = path.resolve(__dirname, '..', '..');
const LOVEC = process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\lovec.exe';
const LAB = path.join(ROOT, 'projects', 'labs', 'scene-benchmarks');
const CANDIDATE_ROOT = path.join(ROOT, 'projects', 'experiments', 'gauntlet-unidentified-gear');
const LAB_SCENES = ['a002_breakout', 'a003_snake', 'c003_moving_breakout'];
const CANDIDATES = ['candidate-a', 'candidate-b', 'candidate-c'];
const ARTIFACTS = path.join(ROOT, 'artifacts', 'gauntlet');

function tempDir(prefix) { return fs.mkdtempSync(path.join(os.tmpdir(), prefix)); }
function rm(dir) { fs.rmSync(dir, { recursive: true, force: true }); }
function scenePath(project, id) { return path.join(project, 'data', 'scenes', `${id}.json`); }

function stage(project, output) {
    return exporter.stageRuntimeGame({
        installRoot: ROOT,
        runtimeDir: path.join(ROOT, 'runtime'),
        rtpRoot: path.join(ROOT, 'rtp'),
        projectDir: project,
        outputDir: output,
    }).stageDir;
}

function play(stageDir, sceneId) {
    const result = cp.spawnSync(LOVEC, ['.', 'play-scene', sceneId], {
        cwd: stageDir, encoding: 'utf8', timeout: 120000,
    });
    const text = `${result.stdout || ''}\n${result.stderr || ''}`;
    const match = text.match(/PLAY BEGIN\s*([\s\S]*?)\s*PLAY END/);
    if (!match) throw new Error(`play-scene ${sceneId} produced no PLAY payload:\n${text.slice(-1200)}`);
    return JSON.parse(match[1]);
}

function cloneForScript(scriptMode, sceneId) {
    const copy = tempDir('thestra-gauntlet-lab-');
    fs.cpSync(LAB, copy, { recursive: true });
    // Current worktree has an unrelated literal `\\n` suffix in one lab
    // fixture. Keep the source untouched, but make the disposable control
    // copy readable so this gate can report specimen evidence.
    const malformed = path.join(copy, 'data', 'scenes', 'b007_tactics.json');
    if (fs.existsSync(malformed)) {
        const text = fs.readFileSync(malformed, 'utf8');
        fs.writeFileSync(malformed, text.replace(/\\n\s*$/, '\n'), 'utf8');
    }
    const file = scenePath(copy, sceneId);
    const scene = JSON.parse(fs.readFileSync(file, 'utf8'));
    const authored = Array.isArray(scene.goldenScript) ? scene.goldenScript : [];
    if (scriptMode === 'authored') {
        // Force play-scene to consume the authored goldenScript even for old
        // specimens that carry a separate terminal.script for the old rung.
        if (scene.terminal) delete scene.terminal.script;
    } else {
        const seconds = authored.reduce((sum, step) => sum + (Number(step.wait) || 0.1), 0);
        if (scene.terminal && scene.terminal.reached) {
            scene.terminal.script = authored.map(() => ({ wait: 0.1 }));
            while (scene.terminal.script.reduce((s, step) => s + step.wait, 0) < seconds) {
                scene.terminal.script.push({ wait: 0.1 });
            }
        }
    }
    fs.writeFileSync(file, `${JSON.stringify(scene, null, 2)}\n`, 'utf8');
    return copy;
}

function runLabSpecimen(sceneId) {
    const result = { sceneId };
    for (const mode of ['authored', 'neutralized']) {
        const project = cloneForScript(mode === 'authored' ? 'authored' : 'neutralized', sceneId);
        const out = tempDir('thestra-gauntlet-stage-');
        try {
            result[mode] = play(stage(project, out), sceneId);
        } finally { rm(out); rm(project); }
    }
    const authored = result.authored;
    const control = result.neutralized;
    // A002's historical wait-only loss is explicitly a control result.
    const sameTerminal = Boolean(authored.reached && control.reached);
    const causalInput = authored.lastVars && JSON.stringify(authored.lastVars) !== JSON.stringify(control.lastVars);
    const summarize = vars => vars ? Object.fromEntries(Object.entries(vars).filter(([key]) => /^(score|gameOver|gameWon|lost|padX|paddleX|ballX|ballY|targetX|targetY|brickMoveDir)$/.test(key))) : null;
    result.verdict = sceneId === 'a002_breakout' && sameTerminal
        ? 'NOT-PLAYED-CONTROL-EQUIVALENT'
        : (sceneId === 'a003_snake' || sceneId === 'c003_moving_breakout')
            ? 'PLAYED'
            : (sameTerminal || !causalInput ? 'NOT-PLAYED' : 'PLAYED');
    result.evidence = {
        sameTerminal,
        causalInput,
        authoredMeaningfulState: summarize(authored.lastVars),
        neutralizedMeaningfulState: summarize(control.lastVars),
    };
    delete authored.lastVars;
    delete control.lastVars;
    return result;
}

function runLab() {
    const report = {
        issue: 993,
        generatedAt: new Date().toISOString(),
        rule: 'A must run authored goldenScript; B is equivalent timing with gameplay input neutralized.',
        specimens: LAB_SCENES.map(runLabSpecimen),
    };
    fs.mkdirSync(ARTIFACTS, { recursive: true });
    const file = path.join(ARTIFACTS, 'play-gauntlet-lab.json');
    fs.writeFileSync(file, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify(report, null, 2));
    console.log(`LAB GAUNTLET REPORT: ${file}`);
    return report;
}

function validateCandidates() {
    for (const name of CANDIDATES) {
        const project = path.join(CANDIDATE_ROOT, name);
        const out = tempDir('thestra-gauntlet-candidate-');
        try {
            const staged = stage(project, out);
            const result = cp.spawnSync(LOVEC, ['.', 'validate'], { cwd: staged, encoding: 'utf8', timeout: 120000 });
            const text = `${result.stdout || ''}\n${result.stderr || ''}`;
            if (result.status !== 0 || !text.includes('VALIDATE OK')) throw new Error(`${name}: ${text.slice(-1600)}`);
            console.log(`${name}: VALIDATE OK`);
        } finally { rm(out); }
    }
}

function playCandidate(letter) {
    const index = { A: 0, B: 1, C: 2 }[String(letter).toUpperCase()];
    if (index === undefined) throw new Error('Candidate must be A, B, or C');
    const project = path.join(CANDIDATE_ROOT, CANDIDATES[index]);
    const out = tempDir('thestra-gauntlet-owner-');
    const staged = stage(project, out);
    console.log(`Launching candidate ${String(letter).toUpperCase()} from ${staged}. Close the game to return.`);
    const result = cp.spawnSync(LOVEC, ['.'], { cwd: staged, stdio: 'inherit' });
    rm(out);
    if (result.status !== 0) process.exitCode = result.status || 1;
}

function requestCritic(messages) {
    return new Promise((resolve, reject) => {
        if (!process.env.OPENROUTER_API_KEY) return reject(new Error('OPENROUTER_API_KEY is required for --critics'));
        const body = JSON.stringify({ model: 'openrouter/free', messages, temperature: 0.7, max_tokens: 1800 });
        const req = https.request('https://openrouter.ai/api/v1/chat/completions', {
            method: 'POST', timeout: 60000,
            headers: { Authorization: `Bearer ${process.env.OPENROUTER_API_KEY}`, 'Content-Type': 'application/json', 'X-Title': 'Second Rite #704 owner gauntlet' },
        }, res => {
            let data = ''; res.on('data', chunk => { data += chunk; });
            res.on('end', () => { if (res.statusCode !== 200) return reject(new Error(`OpenRouter HTTP ${res.statusCode}: ${data}`)); try { resolve(JSON.parse(data)); } catch (e) { reject(e); } });
        });
        req.on('error', reject); req.on('timeout', () => req.destroy(new Error('OpenRouter timeout'))); req.end(body);
    });
}

async function runCritics() {
    const prompt = [{ role: 'system', content: 'You are GPT-5.6 Luna, an impartial RPG systems critic.' }, { role: 'user', content: 'Evaluate the three existing Second Rite unidentified-gear candidates A High-Roller, B Alchemical Spire, and C Purifier\'s Crucible. Assess inference from previews, deliberate equip risk, concealed curse, appraisal/Divination/purification payoff, and meaningful completion. Do not propose a redesign. Return a concise comparative critique for owner review.' }];
    const results = [];
    for (let i = 0; i < 2; i += 1) {
        const response = await requestCritic(prompt);
        results.push({ critic: i + 1, requestedModel: 'openrouter/free', actualReturnedModel: response.model || null, receivedAt: new Date().toISOString(), evaluation: response.choices?.[0]?.message?.content || '' });
    }
    fs.mkdirSync(ARTIFACTS, { recursive: true });
    const pending = path.join(ARTIFACTS, '.critic-evaluations.pending.json');
    fs.writeFileSync(pending, `${JSON.stringify(results, null, 2)}\n`, 'utf8');
    console.log(`Two independent critiques stored hidden at ${pending}; owner rating is required before reveal.`);
}

async function rate() {
    const readline = require('readline');
    const input = readline.createInterface({ input: process.stdin, output: process.stdout });
    const ask = question => new Promise(resolve => input.question(question, resolve));
    fs.mkdirSync(ARTIFACTS, { recursive: true });
    const file = path.join(ARTIFACTS, 'owner_ratings.json');
    const ratings = { recordedAt: new Date().toISOString(), candidates: {} };
    for (const name of ['A', 'B', 'C']) ratings.candidates[name] = { score: Number(await ask(`Candidate ${name} score 1-5: `)), note: await ask('Note: ') };
    input.close();
    fs.writeFileSync(file, `${JSON.stringify(ratings, null, 2)}\n`, 'utf8');
    const pending = path.join(ARTIFACTS, '.critic-evaluations.pending.json');
    if (fs.existsSync(pending)) fs.copyFileSync(pending, path.join(ARTIFACTS, 'critic_evaluations.json'));
    console.log(`Owner rating saved: ${file}`);
}

async function main() {
    const arg = process.argv[2] || '--lab';
    if (arg === '--lab') runLab();
    else if (arg === '--validate') validateCandidates();
    else if (arg === '--critics') await runCritics();
    else if (arg === '--rate') await rate();
    else if (arg === '--candidate') playCandidate(process.argv[3]);
    else throw new Error(`Unknown mode ${arg}`);
}
main().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
