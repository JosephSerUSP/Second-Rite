'use strict';

const fs = require('fs');
const path = require('path');
const https = require('https');

const REPO = path.resolve(__dirname, '..', '..');
const ARTIFACTS_DIR = path.join(REPO, 'artifacts', 'gauntlet');

const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;

const CANDIDATE_DESCRIPTIONS = {
    A: {
        theme: "The High-Roller's Ruin (Extreme Temptation & Severe Downside)",
        dungeon: "Crypt of the Cursed Vanguard",
        previewMechanic: "Massive stat preview boosts (+32 ATK on Vanguard Blood-Drinker, +26 DEF / +14 MDF on Obsidian Bulwark).",
        curseRisk: "Severe hidden curses: 10% max HP bleed per combat round on the Blood-Drinker; +60% Fire damage vulnerability on Obsidian armor against Cerberus who breathes Hellfire.",
        appraisalEconomy: "Town Appraiser charges 150 Gold per appraisal; starting gold is 150G (can only appraise 1 item before entering).",
        encounterDesign: "Skeleton Patrols, Lurking Ghouls, Mimics, and Tomb Sentinel Cerberus boss."
    },
    B: {
        theme: "The Alchemical Spire (Subtle Fingerprints & Action-Economy Payoffs)",
        dungeon: "Spire Testing Corridors",
        previewMechanic: "Subtle stat fingerprints (+8 ASP on Chronos Humming Ring, +14 MAT / -3 ASP on Crystalline Frost-Wand).",
        curseRisk: "Tactical vulnerabilities and turn order shifts: Volatile Conduit gives +22 MAT but +70% vulnerability to Lightning/Dark against Arch-Automaton Proteus.",
        appraisalEconomy: "In-dungeon Divination Altar allows 1 free item identification per run, forcing mid-dungeon triage.",
        encounterDesign: "Arcane Wisps, Spire Lamias, Homunculus Sentinels, and Arch-Automaton Proteus boss."
    },
    C: {
        theme: "The Purifier's Crucible (Direct Curse-to-Relic Transfiguration)",
        dungeon: "Sunken Catacomb",
        previewMechanic: "High upfront stat boosts (+20 ATK on Tarnished Blade, +24 DEF on Corrupted Mail) with negative previews (-4 DEF, -10 ASP).",
        curseRisk: "Active combat bleed (-8% HP per round) and sluggish speed while unpurified.",
        appraisalEconomy: "No town appraiser; players must delve deep into the Catacomb to reach the Sacred Purification Font, transforming cursed items into blessed relics (Radiant Sunblade with +5% HP regen, Paladin's Cuirass with Poison Immunity).",
        encounterDesign: "Imp Raiders, Demon Stalkers, Demonic Vanguards, and Corrupted Seraph Diablos boss."
    }
};

const GAUNTLET_CORE_QUESTION = `
Is experimenting with unidentified equipment fun when the player may equip it without identifying it, infer some effects from stat previews, while traits remain unknown and CURSE creates real risk?
`;

function requestOpenRouter(model, messages) {
    return new Promise((resolve, reject) => {
        if (!OPENROUTER_API_KEY) {
            return reject(new Error("OPENROUTER_API_KEY environment variable is not set"));
        }

        const data = JSON.stringify({
            model: model,
            messages: messages,
            temperature: 0.7,
            max_tokens: 1500
        });

        const req = https.request('https://openrouter.ai/api/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://github.com/JosephSerUSP/Second-Rite',
                'X-Title': 'Second-Rite Gauntlet Critic Jury'
            },
            timeout: 60000
        }, (res) => {
            let body = '';
            res.on('data', chunk => { body += chunk; });
            res.on('end', () => {
                if (res.statusCode !== 200) {
                    return reject(new Error(`OpenRouter HTTP ${res.statusCode}: ${body}`));
                }
                try {
                    const parsed = JSON.parse(body);
                    resolve(parsed);
                } catch (e) {
                    reject(new Error(`Failed to parse OpenRouter response: ${e.message}`));
                }
            });
        });

        req.on('error', reject);
        req.on('timeout', () => {
            req.destroy();
            reject(new Error("OpenRouter request timed out"));
        });

        req.write(data);
        req.end();
    });
}

function shuffle(array) {
    const arr = array.slice();
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

async function evaluateCritic(criticIndex, freeModel) {
    console.log(`Running Critic Jury #${criticIndex} with model '${freeModel}'...`);

    // Shuffle and blind candidate order for this critic
    const keys = shuffle(['A', 'B', 'C']);
    const blindMapping = {};
    keys.forEach((key, idx) => {
        blindMapping[`Candidate_${idx + 1}`] = key;
    });

    const candidateTexts = keys.map((key, idx) => {
        const c = CANDIDATE_DESCRIPTIONS[key];
        return `### Candidate ${idx + 1}
- Design Approach: ${c.theme}
- Dungeon Setting: ${c.dungeon}
- Stat Preview & Inference: ${c.previewMechanic}
- Curse & Downside Risk: ${c.curseRisk}
- Identification & Economy: ${c.appraisalEconomy}
- Combat & Climax: ${c.encounterDesign}`;
    }).join('\n\n');

    const prompt = `You are an expert RPG system designer serving on an impartial design jury for the indie dungeon crawler 'Second Rite'.

CORE GAUNTLET QUESTION:
"${GAUNTLET_CORE_QUESTION.trim()}"

We are evaluating 3 blinded candidate implementations of the Unidentified Equipment & Curse mechanic:

${candidateTexts}

Please provide an evaluation addressing:
1. Analysis of each Candidate: How effectively does its risk/reward loop make equipping unknown gear an engaging tactical decision rather than a chore or pure luck?
2. Fun & Tension Assessment: Rate each candidate (1-5 scale) on:
   - Inference/Deduction value (Can the player make meaningful guesses from stat previews?)
   - Risk/Curse Impact (Is the curse meaningful without feeling cheap?)
   - Overall Fun & Replayability
3. Blind Ranking: Rank Candidate 1, 2, and 3 from best to worst with concise rationale.
4. Recommendation: Which single design direction should the development team adopt as canonical?

Format your response cleanly with clear section headings.`;

    const messages = [
        { role: 'system', content: 'You are a veteran turn-based RPG systems critic and gameplay balancer.' },
        { role: 'user', content: prompt }
    ];

    const response = await requestOpenRouter(freeModel, messages);
    const returnedModel = response.model || freeModel;
    const content = response.choices && response.choices[0] && response.choices[0].message ? response.choices[0].message.content : '';

    return {
        criticId: `OpenRouter_Critic_${criticIndex}`,
        requestedModel: freeModel,
        actualReturnedModel: returnedModel,
        timestamp: new Date().toISOString(),
        blindMapping: blindMapping,
        evaluation: content
    };
}

async function main() {
    fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });

    console.log("==================================================");
    console.log("Running Pre-Play Critic Jury (OpenRouter Free)");
    console.log("==================================================");

    const criticResults = [];

    const candidateModels = [
        'openrouter/free',
        'nvidia/nemotron-3-super-120b-a12b:free',
        'nvidia/nemotron-3-ultra-550b-a55b:free',
        'z-ai/glm-5.2:free',
        'openai/gpt-oss-20b:free'
    ];

    let modelIdx = 0;
    // Critic 1
    while (modelIdx < candidateModels.length && criticResults.length < 1) {
        const model = candidateModels[modelIdx++];
        try {
            const c1 = await evaluateCritic(1, model);
            if (c1.evaluation && c1.evaluation.length > 50) {
                criticResults.push(c1);
                console.log(`Critic #1 evaluation recorded (Model: ${c1.actualReturnedModel}).`);
            }
        } catch (err) {
            console.warn(`Critic #1 attempt with ${model} failed: ${err.message}`);
        }
    }

    // Critic 2
    while (modelIdx < candidateModels.length && criticResults.length < 2) {
        const model = candidateModels[modelIdx++];
        try {
            const c2 = await evaluateCritic(2, model);
            if (c2.evaluation && c2.evaluation.length > 50) {
                criticResults.push(c2);
                console.log(`Critic #2 evaluation recorded (Model: ${c2.actualReturnedModel}).`);
            }
        } catch (err) {
            console.warn(`Critic #2 attempt with ${model} failed: ${err.message}`);
        }
    }

    if (criticResults.length < 2 && candidateModels.length > 0) {
        // Retry with openrouter/free if needed
        try {
            const cRetry = await evaluateCritic(criticResults.length + 1, 'openrouter/free');
            criticResults.push(cRetry);
        } catch (e) {
            console.warn("Retry failed:", e.message);
        }
    }

    const outputFile = path.join(ARTIFACTS_DIR, 'critic_evaluations.json');
    fs.writeFileSync(outputFile, JSON.stringify(criticResults, null, 2), 'utf8');

    console.log(`\nCritic jury evaluations saved securely to ${outputFile}`);
    console.log("Note: Results are hidden until post-play evaluation is completed via PLAY_GAUNTLET or REVEAL_CRITICS.");
}

if (require.main === module) {
    main().catch(err => {
        console.error("FATAL:", err);
        process.exit(1);
    });
}

module.exports = { evaluateCritic };
