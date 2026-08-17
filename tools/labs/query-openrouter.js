'use strict';

const fs = require('fs');

const OPENROUTER_KEY = process.env.OPENROUTER_API_KEY;

const CRITIQUE_PROMPT = `You are an insightful and rigorous game critic evaluating an experimental authored indie RPG campaign: "Second Gate: Pale Crossing".
Format: 45–75 minute complete first-person dungeon RPG campaign with 8 authored maps and 6 stratum floors.

Core Mechanics & Themes:
- Protagonist is an outsider Summoner arriving in St. Maria with their bonded starting companion: Saban, a Level 3 Moa (Cooking discipline).
- Traversal Economy: Summons exert MP Drain (MPD) on every step taken in the labyrinth. Saban drains 2 MPD. Optional heavy contracts: Cerberus (Level 4, Fire Claw, high ATK 28, but brutal MPD 6) and Daphne (Level 3, Water Healer, MPD 4).
- Structure:
  * Act I: St. Maria hub (Room 3, Registrar Celina giving Crossing Writ, Alicia bakery, Laura forge, Sister Agnes chapel) -> Floor 1 (Ines mark, Cerberus chamber) -> Floor 2 (The Salt Table, Daphne spring, Bellroot Recovery Font, Rupture Hatch).
  * Act II: Subterranean Rupture — São Paulo Metro Stratum (Floor 3: Estação Sé Concourse with ticket booth & turnstiles; Floor 4: Platform 2 & ghost tracks with commuter train, lost bag, Guardian Talos sub-boss).
  * Revisit: Vigil of the Bells in St. Maria (twilight lighting, prayer, Yukio encounter, Thestra lantern).
  * Act III: Floor 5 (The Rusted Choir, Borrowed Room replicating Room 3, 3-bell chime puzzle [Salt -> Iron -> Dusk], Red Dragon boss fight) -> Floor 6 (The Pale Crossing / Thestra Seam, ending choice) -> Map 8 (Authored ending / epilogue).

Please write a structured critical review covering:
1. Mechanical & Thematic Resonance (Summoner MP traversal tension vs Saban attachment)
2. Stratum Transition & Anachronism (São Paulo Metro Estação Sé surrealism)
3. Pacing & Climax Structure (Borrowed Room, 3-Bell puzzle, Red Dragon, dual ending)
4. Distinct Strengths & Notable Rough Edges
5. Verdict & Rating (1–5 scale) with a one-sentence final judgment.`;

async function testModel(model) {
    console.log(`Trying model: ${model}...`);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
        const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
            method: 'POST',
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${OPENROUTER_KEY}`,
                'HTTP-Referer': 'https://github.com/JosephSerUSP/Second-Rite',
                'X-Title': 'Second Rite Pale Crossing Critique'
            },
            body: JSON.stringify({
                model,
                messages: [
                    { role: 'system', content: 'You are an incisive indie game design and narrative systems critic.' },
                    { role: 'user', content: CRITIQUE_PROMPT }
                ],
                temperature: 0.7
            })
        });
        clearTimeout(timeout);
        if (!res.ok) {
            console.log(`Failed ${model}: ${res.status} ${res.statusText}`);
            return null;
        }
        const data = await res.json();
        if (data.choices && data.choices[0] && data.choices[0].message) {
            console.log(`SUCCESS with ${model}!`);
            return data.choices[0].message.content;
        }
        return null;
    } catch (err) {
        clearTimeout(timeout);
        console.log(`Error with ${model}: ${err.message}`);
        return null;
    }
}

async function main() {
    const candidates = [
        'openai/gpt-oss-20b:free',
        'nvidia/nemotron-3.5-lightning:free',
        'liquid/lfm-2.5-2.6b:free',
        'z-ai/glm-5.2:free',
        'cohere/north-mini-code:free',
        'poolside/laguna-s-2.1:free'
    ];

    const results = [];
    for (const model of candidates) {
        const content = await testModel(model);
        if (content) {
            results.push({ model, content });
            if (results.length >= 2) break;
        }
    }

    console.log(`Collected ${results.length} OpenRouter reviews.`);

    // Read existing CRITIQUE.md to preserve Luna
    const critiquePath = 'projects/labs/pale-crossing/CRITIQUE.md';
    let current = fs.readFileSync(critiquePath, 'utf8');

    // Remove the two old failed sections
    current = current.split('## Critique by OpenRouter')[0];

    for (let i = 0; i < results.length; i++) {
        const item = results[i];
        const letter = i === 0 ? 'A' : 'B';
        current += `## Critique by OpenRouter Critic ${letter} (${item.model})\n\n${item.content.trim()}\n\n---\n\n`;
    }

    fs.writeFileSync(critiquePath, current, 'utf8');
    console.log(`Updated ${critiquePath}`);
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
