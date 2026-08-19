'use strict';

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const REPO = path.resolve(__dirname, '..', '..');
const ARTIFACTS_DIR = path.join(REPO, 'artifacts', 'gauntlet');
const RATINGS_FILE = path.join(ARTIFACTS_DIR, 'owner_ratings.json');

const CANDIDATES = [
    { key: 'A', name: 'Candidate A ("The High-Roller\'s Ruin" - Blood-Drinker & Obsidian Armor)' },
    { key: 'B', name: 'Candidate B ("The Alchemical Spire" - Action Plus Ring & Frost Wand)' },
    { key: 'C', name: 'Candidate C ("The Purifier\'s Crucible" - Sacred Font Relic Cleansing)' }
];

function createPrompt() {
    return readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });
}

function ask(rl, questionText) {
    return new Promise(resolve => {
        rl.question(questionText, answer => {
            resolve(answer.trim());
        });
    });
}

async function main() {
    fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
    const rl = createPrompt();

    console.log("\n================================================================================");
    console.log("                    SECOND RITE: GAUNTLET OWNER RATING FORM                     ");
    console.log("================================================================================");
    console.log("Core Design Question:");
    console.log('  "Is experimenting with unidentified equipment fun when the player may equip it');
    console.log('   without identifying it, infer some effects from stat previews, while traits');
    console.log('   remain unknown and CURSE creates real risk?"');
    console.log("================================================================================\n");

    const scores = {};

    for (const c of CANDIDATES) {
        console.log(`\n>>> Rating ${c.name} (${c.key}):`);
        
        let inf = await ask(rl, "  1. Inference / Deduction value (1 = pure gamble, 5 = clear, clever deductions) [1-5]: ");
        let risk = await ask(rl, "  2. Curse / Risk tension (1 = too punishing/cheap, 5 = thrilling, fair risk) [1-5]: ");
        let fun = await ask(rl, "  3. Overall Fun & Replayability (1 = tedious, 5 = extremely engaging) [1-5]: ");
        let notes = await ask(rl, "  4. Qualitative feedback / standout moments (optional): ");

        scores[c.key] = {
            inference: parseInt(inf, 10) || 3,
            risk: parseInt(risk, 10) || 3,
            fun: parseInt(fun, 10) || 3,
            notes: notes || ""
        };
    }

    console.log("\n--------------------------------------------------------------------------------");
    console.log("                             FORCED CANDIDATE RANKING                            ");
    console.log("--------------------------------------------------------------------------------");
    console.log("Rank the 3 candidates from best to worst (e.g. 'A B C' or 'B C A'):");
    let rankInput = await ask(rl, "Your Ranking [Order of A, B, C separated by spaces]: ");
    
    let ranking = rankInput.toUpperCase().split(/[\s,]+/).filter(x => ['A', 'B', 'C'].includes(x));
    if (ranking.length !== 3) {
        ranking = ['A', 'B', 'C'];
    }

    console.log("\n--------------------------------------------------------------------------------");
    let synthesis = await ask(rl, "Final Synthesis: Which approach feels most native to Second Rite? ");

    rl.close();

    const outputData = {
        timestamp: new Date().toISOString(),
        coreQuestion: "Is experimenting with unidentified equipment fun when the player may equip it without identifying it, infer some effects from stat previews, while traits remain unknown and CURSE creates real risk?",
        ranking: ranking,
        scores: scores,
        synthesis: synthesis
    };

    fs.writeFileSync(RATINGS_FILE, JSON.stringify(outputData, null, 2), 'utf8');
    console.log(`\n>>> Ratings saved successfully to ${RATINGS_FILE}!`);
    console.log("You can now run 'npm run gauntlet:reveal' or select 'Reveal Critics' in PLAY_GAUNTLET to compare with AI critic jury predictions.");
}

if (require.main === module) {
    main().catch(err => {
        console.error("Error collecting ratings:", err);
        process.exit(1);
    });
}

module.exports = { main };
