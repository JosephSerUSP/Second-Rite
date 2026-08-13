'use strict';
const assert = require('assert');
const lab = require('./mp-economy-lab');

assert.strictEqual(lab.battleCost({ type: 'mpd' }, 7), 7);
assert.strictEqual(lab.battleCost({ type: 'mpd_multiplier', multiplier: 4 }, 7), 28);
assert.strictEqual(lab.battleCost({ type: 'flat_plus_mpd', base: 20, multiplier: 2 }, 7), 34);
assert.strictEqual(lab.strainCost(5, 5), 0);
assert.strictEqual(lab.strainCost(5, 6), 20);
assert.strictEqual(lab.strainCost(5, 10), 120); // rounds 6-9: 4*20; round 10: 40.

const power = { type: 'power', base: 4, exponent: 1.2, reset: 'release' };
const cumulative = lab.veilBurstTable(power);
assert.deepStrictEqual(cumulative.map(x => x.steps), [5, 10, 20]);
assert(cumulative[0].total < cumulative[1].total && cumulative[1].total < cumulative[2].total);

const run = lab.simulate(
  { id: 'test', events: [
    { type: 'step', veil: true }, { type: 'step', veil: true }, { type: 'step' },
    { type: 'battle', rounds: 6 }, { type: 'mp_up', amount: 10000, label: 'cap test' },
    { type: 'milestone', label: 'end' }
  ] },
  { id: 'party', mpd: 5 }, 820,
  { id: 'battle', type: 'mpd' },
  { id: 'veil', type: 'flat', base: 8, reset: 'release' },
  { battleStrain: true, representativeVeilBurst: 10 }
);
assert.strictEqual(run.status, 'complete');
assert.strictEqual(run.totals.battleActivation, 5);
assert.strictEqual(run.totals.veil, 16);
assert.strictEqual(run.totals.battleStrain, 20);
assert.strictEqual(run.totals.endingMaxMp, 9999);
const capMilestone = run.milestones.find(x => x.label === 'cap test');
assert(capMilestone);
assert.strictEqual(capMilestone.requested, 10000);
assert.strictEqual(capMilestone.applied, 9179); // 9999 - 820.
assert.strictEqual(run.totals.endingMp, 9958); // 820 - 41 + 9179 restored.
assert.throws(() => lab.simulate(
  { id: 'bad-opening', events: [] }, { id: 'party', mpd: 1 }, 10000,
  { id: 'battle', type: 'mpd' }, { id: 'veil', type: 'flat', base: 1, reset: 'release' },
  { battleStrain: false }
), /openingMaxMp.*9999/);

const blocked = lab.simulate(
  { id: 'blocked', events: [
    { type: 'step', veil: true, label: 'too expensive' },
    { type: 'battle', rounds: 1, label: 'must not continue' }
  ] },
  { id: 'party', mpd: 1 }, 5,
  { id: 'battle', type: 'mpd' },
  { id: 'veil', type: 'flat', base: 8, reset: 'release' },
  { battleStrain: false, representativeVeilBurst: 10 }
);
assert.strictEqual(blocked.status, 'blocked');
assert.strictEqual(blocked.blockedAt.seq, 1);
assert.strictEqual(blocked.blockedAt.phase, 'veil');
assert.strictEqual(blocked.blockedAt.requestedCost, 8);
assert.strictEqual(blocked.blockedAt.paidCost, 0);
assert.strictEqual(blocked.totals.requested.veil, 8);
assert.strictEqual(blocked.totals.veil, 0);
assert.strictEqual(blocked.totals.endingMp, 5);
assert.strictEqual(blocked.timeline.length, 1);
assert.strictEqual(blocked.timeline[0].detail.affordable, false);
assert.strictEqual(blocked.timeline[0].detail.blocked, true);

console.log('MP ECONOMY LAB TEST OK');
