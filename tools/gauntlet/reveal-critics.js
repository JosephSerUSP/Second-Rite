'use strict';

const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..', '..');
const ARTIFACTS_DIR = path.join(REPO, 'artifacts', 'gauntlet');

const OWNER_RATINGS_FILE = path.join(ARTIFACTS_DIR, 'owner_ratings.json');
const CRITIC_EVAL_FILE = path.join(ARTIFACTS_DIR, 'critic_evaluations.json');

const CANDIDATE_NAMES = {
    A: "Candidate A: The High-Roller's Ruin (Extreme Raw Stats & Bleed/Fire Curses)",
    B: "Candidate B: The Alchemical Spire (Action Plus, Freeze Wand & Conduit Vuln)",
    C: "Candidate C: The Purifier's Crucible (Cursed Gear -> Sacred Font Transfiguration)"
};

function main() {
    console.log("================================================================================");
    console.log("                    GAUNTLET CRITIC JURY REVEAL & COMPARISON                   ");
    console.log("================================================================================\n");

    let ownerRatings = null;
    if (fs.existsSync(OWNER_RATINGS_FILE)) {
        try {
            ownerRatings = JSON.parse(fs.readFileSync(OWNER_RATINGS_FILE, 'utf8'));
        } catch (e) {
            console.warn("Could not parse owner ratings:", e.message);
        }
    }

    let criticEvals = [];
    if (fs.existsSync(CRITIC_EVAL_FILE)) {
        try {
            criticEvals = JSON.parse(fs.readFileSync(CRITIC_EVAL_FILE, 'utf8'));
        } catch (e) {
            console.warn("Could not parse critic evaluations:", e.message);
        }
    }

    if (ownerRatings) {
        console.log("--------------------------------------------------------------------------------");
        console.log("                                OWNER VERDICT                                   ");
        console.log("--------------------------------------------------------------------------------");
        console.log(`Submitted At: ${ownerRatings.timestamp || 'N/A'}`);
        console.log(`Forced Ranking:`);
        if (ownerRatings.ranking) {
            ownerRatings.ranking.forEach((r, idx) => {
                const label = CANDIDATE_NAMES[r] || r;
                console.log(`  #${idx + 1}: ${label}`);
            });
        }
        console.log("\nDetailed Scores (1-5 scale):");
        ['A', 'B', 'C'].forEach(c => {
            const score = ownerRatings.scores && ownerRatings.scores[c];
            if (score) {
                console.log(`\n  [${c}] ${CANDIDATE_NAMES[c]}:`);
                console.log(`      - Inference / Deduction Satisfaction : ${score.inference || 'N/A'}/5`);
                console.log(`      - Risk & Curse Impact Balance       : ${score.risk || 'N/A'}/5`);
                console.log(`      - Overall Fun & Replayability       : ${score.fun || 'N/A'}/5`);
                if (score.notes) console.log(`      - Notes                             : "${score.notes}"`);
            }
        });
        if (ownerRatings.synthesis) {
            console.log(`\nOwner Final Thoughts:\n  ${ownerRatings.synthesis}`);
        }
        console.log("\n");
    } else {
        console.log("[NOTE] No owner ratings recorded yet in artifacts/gauntlet/owner_ratings.json.\n");
    }

    console.log("================================================================================");
    console.log("                         EXTERNAL CRITIC JURY PREDICTIONS                       ");
    console.log("================================================================================");

    if (criticEvals.length === 0) {
        console.log("No critic evaluations found.");
        return;
    }

    criticEvals.forEach((critic, idx) => {
        console.log(`\n--------------------------------------------------------------------------------`);
        console.log(`CRITIC #${idx + 1}: ${critic.criticId} (Actual Model: ${critic.actualReturnedModel})`);
        console.log(`Evaluated At: ${critic.timestamp}`);
        console.log(`Blind Mapping Used During Critique:`);
        if (critic.blindMapping) {
            Object.entries(critic.blindMapping).forEach(([blindKey, actualKey]) => {
                console.log(`  - ${blindKey} was -> ${actualKey} (${CANDIDATE_NAMES[actualKey]})`);
            });
        }
        console.log(`\n--- CRITIC EVALUATION TEXT ---\n`);
        console.log(critic.evaluation);
        console.log(`\n--------------------------------------------------------------------------------`);
    });
}

if (require.main === module) {
    main();
}

module.exports = { main };
