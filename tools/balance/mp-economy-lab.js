#!/usr/bin/env node
'use strict';

// Development-only economy simulator for #376. It deliberately does not import
// runtime mutation code: inputs are explicit traces/profiles and the production
// semantics it mirrors are stated in assumptions below.
const fs = require('fs');
const path = require('path');

const CAP = 9999;
const round = n => Math.round(n * 1000) / 1000;

function battleCost(model, mpd) {
  if (model.type === 'mpd') return mpd;
  if (model.type === 'mpd_multiplier') return mpd * model.multiplier;
  if (model.type === 'flat_plus_mpd') return model.base + mpd * (model.multiplier ?? 1);
  throw new Error(`unknown battle activation model: ${model.type}`);
}

function veilStepCost(model, consecutive) {
  if (model.type === 'flat') return model.base;
  if (model.type === 'linear') return model.base + model.increment * (consecutive - 1);
  if (model.type === 'power') return model.base * Math.pow(consecutive, model.exponent);
  throw new Error(`unknown Veil model: ${model.type}`);
}

function strainCost(mpd, rounds) {
  let total = 0;
  for (let r = 6; r <= rounds; r++) {
    total += mpd * (r >= 15 ? 16 : r >= 10 ? 8 : 4);
  }
  return total;
}

function normalizeTrace(trace) {
  if (!Array.isArray(trace.events)) throw new Error(`trace ${trace.id} needs events[]`);
  return trace.events.map((ev, i) => ({ ...ev, seq: i + 1 }));
}

function validateOpeningMaxMp(value) {
  if (!Number.isInteger(value) || value < 0 || value > CAP) {
    throw new Error(`openingMaxMp must be an integer from 0 to ${CAP}; got ${value}`);
  }
  return value;
}

function simulate(trace, profile, openingMaxMp, battleModel, veilModel, options) {
  openingMaxMp = validateOpeningMaxMp(openingMaxMp);
  let maxMp = openingMaxMp, mp = openingMaxMp, veilRun = 0, ordinarySinceVeil = 0;
  const paid = { battleActivation: 0, veil: 0, battleStrain: 0 };
  const requested = { battleActivation: 0, veil: 0, battleStrain: 0 };
  const milestones = [], timeline = [];
  const events = normalizeTrace(trace);
  let blockedAt = null;

  // An unaffordable spend is an experiment-feasibility boundary, not a chosen
  // production failure rule. The lab never partially pays an action: it records
  // the requested/paid amounts, marks the attempt unaffordable, and stops the run.
  function spend(kind, rawCost) {
    const requestedCost = Math.max(0, Math.floor(rawCost));
    requested[kind] += requestedCost;
    const availableBefore = mp;
    const affordable = availableBefore >= requestedCost;
    const paidCost = affordable ? requestedCost : 0;
    if (affordable) {
      mp -= paidCost;
      paid[kind] += paidCost;
    }
    return {
      requestedCost,
      paidCost,
      availableBefore,
      affordable,
      blocked: !affordable,
      shortfall: affordable ? 0 : requestedCost - availableBefore
    };
  }

  function markBlocked(ev, phase, payment) {
    if (!payment || !payment.blocked) return;
    blockedAt = {
      seq: ev.seq,
      type: ev.type,
      label: ev.label,
      phase,
      requestedCost: payment.requestedCost,
      paidCost: payment.paidCost,
      availableMp: payment.availableBefore,
      shortfall: payment.shortfall
    };
  }

  for (const ev of events) {
    let detail = null;
    if (ev.type === 'step') {
      if (ev.veil) {
        veilRun += 1; ordinarySinceVeil = 0;
        detail = spend('veil', veilStepCost(veilModel, veilRun));
        markBlocked(ev, 'veil', detail);
      } else {
        ordinarySinceVeil += 1;
        if (veilModel.reset === 'release') veilRun = 0;
        else if (veilModel.reset === 'ordinary_steps' && ordinarySinceVeil >= (veilModel.resetSteps || 1)) veilRun = 0;
      }
    } else if (ev.type === 'battle') {
      if (veilModel.reset === 'battle') veilRun = 0;
      const activation = spend('battleActivation', battleCost(battleModel, profile.mpd));
      let strain = { requestedCost: 0, paidCost: 0, availableBefore: mp, affordable: true, blocked: false, shortfall: 0, attempted: false };
      markBlocked(ev, 'battleActivation', activation);
      if (!blockedAt && options.battleStrain && (ev.rounds || 0) >= 6) {
        strain = { ...spend('battleStrain', strainCost(profile.mpd, ev.rounds)), attempted: true };
        markBlocked(ev, 'battleStrain', strain);
      }
      detail = { activation, strain, rounds: ev.rounds || 0 };
    } else if (ev.type === 'mp_up') {
      const requestedIncrease = Math.max(0, Math.floor(ev.amount));
      const applied = Math.min(requestedIncrease, CAP - maxMp);
      maxMp += applied;
      mp = Math.min(maxMp, mp + applied); // production max_mp_plus restores the applied gain.
      milestones.push({ seq: ev.seq, label: ev.label || 'MP Up', requested: requestedIncrease, applied, maxMp, mp });
      detail = { requested: requestedIncrease, applied };
    } else if (ev.type === 'milestone') {
      milestones.push({ seq: ev.seq, label: ev.label, maxMp, mp });
    } else {
      throw new Error(`unknown trace event: ${ev.type}`);
    }
    timeline.push({ seq: ev.seq, type: ev.type, label: ev.label, veil: ev.veil || undefined, mp, maxMp, detail, blocked: blockedAt?.seq === ev.seq || undefined });
    if (blockedAt) break;
  }

  const oneBattle = Math.floor(battleCost(battleModel, profile.mpd));
  const burstLength = options.representativeVeilBurst || 10;
  let burst = 0;
  for (let n = 1; n <= burstLength; n++) burst += Math.floor(veilStepCost(veilModel, n));
  const affordableBattles = oneBattle > 0 ? Math.floor(openingMaxMp / oneBattle) : null;
  const veilShare = burst / openingMaxMp;
  const veilAssessment = veilShare <= 0.03 ? 'appears effectively always-on at this tested burst scale'
    : veilShare >= 0.35 ? 'appears unusably costly at this tested burst scale'
    : 'appears plausibly burst-oriented at this tested burst scale';

  return {
    id: [trace.id, profile.id, openingMaxMp, battleModel.id, veilModel.id, options.battleStrain ? 'strain' : 'no-strain'].join('__'),
    status: blockedAt ? 'blocked' : 'complete',
    blockedAt,
    inputs: { trace: trace.id, party: profile, openingMaxMp, battleModel, veilModel, battleStrain: !!options.battleStrain },
    totals: {
      ...paid,
      requested: { ...requested },
      totalSpent: paid.battleActivation + paid.veil + paid.battleStrain,
      totalRequested: requested.battleActivation + requested.veil + requested.battleStrain,
      endingMp: mp,
      endingMaxMp: maxMp
    },
    milestones,
    metrics: {
      representativeBattleCost: oneBattle,
      representativeBattleFractionOfOpeningMax: round(oneBattle / openingMaxMp),
      representativeVeilBurstSteps: burstLength,
      representativeVeilBurstCost: burst,
      representativeVeilBurstFractionOfOpeningMax: round(veilShare),
      affordableBattlesBeforeExhaustionIgnoringOtherSpend: affordableBattles,
      veilAssessment
    },
    timeline
  };
}

function veilBurstTable(model, lengths = [5, 10, 20]) {
  return lengths.map(steps => {
    let total = 0;
    for (let n = 1; n <= steps; n++) total += Math.floor(veilStepCost(model, n));
    return { steps, total };
  });
}

function report(result, config) {
  const lines = ['# MP economy lab — structural evidence', '',
    'This is deterministic economic evidence, not a claim that any configuration is fun.', '',
    '## Assumptions mirrored from production', '',
    '- Party MPD is the sum of living active-party MPD (the same meaning as `party.mpd`).',
    '- Battle Strain is optional in the lab and mirrors production bands: rounds 1–5 free, 6–9 ×4 MPD, 10–14 ×8, 15+ ×16.',
    '- Injected MP Up uses production `max_mp_plus` semantics: cap 9999 and restore the applied increase.',
    '- Ordinary experimental traversal is free here; production walking MPD drain is intentionally untouched.',
    '- Insufficient MP is represented only as experiment infeasibility: requested and paid cost are recorded, no partial payment occurs, and the run stops at the blocked attempt. This does not select a production failure policy.', '',
    '## Veil cumulative arithmetic', ''];
  for (const v of config.veilModels) {
    lines.push(`- **${v.id}**: ${veilBurstTable(v).map(x => `${x.steps} steps = ${x.total} MP`).join('; ')}`);
  }
  lines.push('', 'The power-1.2 curve is therefore described by its cumulative burden, not by the exponent alone.', '', '## Comparison', '',
    '| Route | Party | Max MP | Battle | Veil | Strain | Status | End MP | Battle % | 10-step Veil % | Battles* | Veil reading |',
    '|---|---|---:|---|---|---|---|---:|---:|---:|---:|---|');
  for (const r of result.runs) {
    const status = r.status === 'blocked' ? `blocked @ ${r.blockedAt.seq} ${r.blockedAt.phase}` : 'complete';
    lines.push(`| ${r.inputs.trace} | ${r.inputs.party.id} (${r.inputs.party.mpd} MPD) | ${r.inputs.openingMaxMp} | ${r.inputs.battleModel.id} | ${r.inputs.veilModel.id} | ${r.inputs.battleStrain ? 'on' : 'off'} | ${status} | ${r.totals.endingMp} | ${(100*r.metrics.representativeBattleFractionOfOpeningMax).toFixed(1)}% | ${(100*r.metrics.representativeVeilBurstFractionOfOpeningMax).toFixed(1)}% | ${r.metrics.affordableBattlesBeforeExhaustionIgnoringOtherSpend} | ${r.metrics.veilAssessment} |`);
  }
  lines.push('', '\* Affordable battles isolates activation cost from Veil/Strain/MP Up so party pressure is directly comparable.', '',
    '## Reading the evidence', '',
    'Compare light and heavy rows with the same route/pool/model to see composition pressure. Compare pool rows to see the same absolute spend as a fraction of contemporary Max MP. Blocked rows are infeasible experiment traces, not simulations of a chosen live-game insufficient-MP behavior. Milestone MP and all individual spends are preserved in the JSON timeline for later #374 encounter traces and #366/#375 post-hoc playthrough correlation.', '',
    'No row is a recommendation or final balance decision.');
  return lines.join('\n') + '\n';
}

function main() {
  const args = process.argv.slice(2);
  const configPath = path.resolve(args[0] || 'tools/balance/mp-economy-scenarios.json');
  const outDir = path.resolve(args[1] || 'tools/balance/mp-economy-results');
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const runs = [];
  for (const trace of config.traces) for (const profile of config.partyProfiles)
    for (const pool of config.openingMaxMp) for (const battle of config.battleModels)
      for (const veil of config.veilModels) for (const battleStrain of config.battleStrain)
        runs.push(simulate(trace, profile, pool, battle, veil, { battleStrain, representativeVeilBurst: 10 }));
  const result = { schema: 'second-rite.mp-economy-lab.v1', generatedFrom: path.relative(process.cwd(), configPath), cap: CAP, runs };
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'runs.json'), JSON.stringify(result, null, 2) + '\n');
  fs.writeFileSync(path.join(outDir, 'report.md'), report(result, config));
  console.log(`MP ECONOMY LAB OK: ${runs.length} deterministic runs -> ${path.relative(process.cwd(), outDir)}`);
}

if (require.main === module) main();
module.exports = { battleCost, veilStepCost, strainCost, veilBurstTable, simulate };
