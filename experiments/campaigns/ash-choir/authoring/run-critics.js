#!/usr/bin/env node
'use strict';

// The critic pass is deliberately opt-in and writes only campaign-local
// artifacts. It never stores a provider key and never edits gameplay data.

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const criticsDir = path.join(root, 'critics');
const manifestPath = path.join(criticsDir, 'manifest.json');
const openRouterOnly = process.argv.includes('--openrouter-only');
const now = new Date().toISOString();

const manifest = {
  generatedAt: now,
  ownerGate: 'held_until_owner_rating',
  calls: [
    {
      name: 'Luna',
      provider: 'OpenAI',
      requestedModel: 'gpt-5.6-luna',
      credential: 'OPENAI_API_KEY',
      status: 'not-run'
    },
    {
      name: 'OpenRouter Free A',
      provider: 'OpenRouter',
      tier: 'free',
      requestedModel: 'z-ai/glm-5.2:free',
      credential: 'OPENROUTER_API_KEY',
      status: 'not-run'
    },
    {
      name: 'OpenRouter Free B',
      provider: 'OpenRouter',
      tier: 'free',
      requestedModel: 'openai/gpt-oss-20b:free',
      credential: 'OPENROUTER_API_KEY',
      status: 'not-run'
    }
  ]
};

const prompt = `You are Luna, a demanding but constructive game-design critic.
Review the attached textual package for the experimental LÖVE2D campaign
"Ash Choir". This is a static package review, not a claim that you played it.

Premise: each descent leaves gray writing on the contracts of the creatures
who return; St. Maria calls it ash, while the Labyrinth calls it a receipt.
The campaign is intentionally noncanonical and machine-authored. It uses the
existing Second Rite / Thestra Project engine, has New Game -> town -> first
expedition -> return to town -> second expedition -> Ash Choir climax -> two
endings. It is designed for 45–75 minutes. The first expedition offers an
optional Ether Seed and optional Pixie contract; the return beat gives a Town
Portal and optional Bell Salt; the second expedition revisits two floors and
reaches a final ash-choir guardian. The endings are Carry the ember back or
Break the ember over the contract. Shared art is reused; procedural room
placement, battle balance, and the generic post-ending quiet-town handoff are
known rough edges. The owner must play and rate it before consuming this report.

Give a clear critique with these exact sections:
1. CENTRAL THESIS — one paragraph on what the campaign is really about.
2. THREE STRENGTHS — concrete and specific.
3. THREE WEAKNESSES — concrete, prioritized, and actionable without deleting
   authored content.
4. PACING / ARC — assess the two-expedition compression and return beat.
5. GENERIC VS SECOND GATE — distinguish engine-generic ideas from the strongest
   Second Gate / Thestra-specific material.
6. STEAL FOR CANON — ideas worth carrying into canonical work.
7. KEEP EXPERIMENTAL — ideas that should remain noncanonical for now.
8. OWNER PLAYTEST QUESTIONS — five questions that map to the journal.

Do not rewrite the campaign, invent playtest observations, or recommend
removing content merely because it is strange. Call out the generic engine
ending handoff as a platform gap if relevant, separate from campaign quality.`;

function writeJson() {
  fs.writeFileSync(path.join(criticsDir, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
}

function textFromResponse(body) {
  if (typeof body.output_text === 'string' && body.output_text.trim()) return body.output_text.trim();
  const chunks = [];
  for (const item of body.output || []) {
    for (const part of item.content || []) {
      if (typeof part.text === 'string') chunks.push(part.text);
    }
  }
  return chunks.join('\n').trim();
}

async function runLuna() {
  const key = process.env.OPENAI_API_KEY;
  if (!key) {
    manifest.calls[0].status = 'not-run';
    manifest.calls[0].reason = 'OPENAI_API_KEY missing';
    return;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch('https://api.openai.com/v1/responses', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${key}`
      },
      body: JSON.stringify({ model: 'gpt-5.6-luna', input: prompt, store: false }),
      signal: controller.signal
    });
    const body = await response.json();
    if (!response.ok) {
      manifest.calls[0].status = 'error';
      manifest.calls[0].httpStatus = response.status;
      manifest.calls[0].reason = body.error?.message || 'OpenAI request failed';
      return;
    }
    const output = textFromResponse(body);
    if (!output) throw new Error('OpenAI response contained no text output');
    manifest.calls[0].status = 'responded';
    manifest.calls[0].actualModel = body.model || 'not-reported';
    manifest.calls[0].responseId = body.id || 'not-reported';
    fs.writeFileSync(
      path.join(criticsDir, 'critic-luna.md'),
      `# Luna critic — held until owner rating\n\nGenerated: ${now}\n\n${output}\n`
    );
  } catch (error) {
    manifest.calls[0].status = 'error';
    manifest.calls[0].reason = error.name === 'AbortError' ? 'request timed out' : error.message;
  } finally {
    clearTimeout(timer);
  }
}

async function runOpenRouter(call, outputName) {
  const key = process.env.OPENROUTER_API_KEY;
  if (!key) {
    call.status = 'not-run';
    call.reason = 'OPENROUTER_API_KEY missing';
    return;
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${key}`,
        'X-Title': 'Ash Choir campaign critic'
      },
      body: JSON.stringify({
        model: call.requestedModel,
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.4
      }),
      signal: controller.signal
    });
    const body = await response.json();
    if (!response.ok) {
      call.status = 'error';
      call.httpStatus = response.status;
      call.reason = body.error?.message || 'OpenRouter request failed';
      return;
    }
    const output = body.choices?.[0]?.message?.content?.trim();
    if (!output) throw new Error('OpenRouter response contained no text output');
    call.status = 'responded';
    call.actualModel = body.model || 'not-reported';
    call.responseId = body.id || 'not-reported';
    fs.writeFileSync(
      path.join(criticsDir, outputName),
      `# ${call.name} — held until owner rating\n\nGenerated: ${now}\n\n${output}\n`
    );
  } catch (error) {
    call.status = 'error';
    call.reason = error.name === 'AbortError' ? 'request timed out' : error.message;
  } finally {
    clearTimeout(timer);
  }
}

async function main() {
  fs.mkdirSync(criticsDir, { recursive: true });
  if (openRouterOnly && fs.existsSync(manifestPath)) {
    const previous = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    if (previous.calls?.[0]) manifest.calls[0] = previous.calls[0];
  } else {
    await runLuna();
  }
  await runOpenRouter(manifest.calls[1], 'critic-openrouter-a.md');
  await runOpenRouter(manifest.calls[2], 'critic-openrouter-b.md');
  writeJson();
  console.log(JSON.stringify(manifest, null, 2));
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
