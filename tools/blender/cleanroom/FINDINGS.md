# Divergence findings 01-06

These are the ONLY things that cross into attempts 07-09. No geometry, no
coordinates, no .blend and no building from 01-06 is carried forward. Each
convergence attempt starts from `read_factory_settings(use_empty=True)` and
authors a new independent interpretation of these sentences.

## What the blind panel said

Three passes, two vendors (OpenAI gpt-4.1, OpenAI gpt-4o, NVIDIA
nemotron-nano-12b-vl via OpenRouter). Aggregates were tightly clustered
(5.55 - 5.82 / 10), so the aggregate decided nothing and the free text decided
everything.

Weakest criteria, averaged over all six:

| criterion | mean |
|---|---|
| foreground_relationship | **4.28** |
| distinct_identity | **4.33** |
| architectural_specificity | 4.44 |
| npc_staging | 4.67 |
| avoids_modular_repetition | 4.78 |
| expensive_prerendered | 4.89 |

Strongest: traversal_clarity 7.67, collapsible_to_runtime 7.11,
material_restraint 6.78, surface_scale 6.78.

Every single attempt, from every evaluator, drew the same complaint in
different words: **empty, plain, no props, no environmental storytelling, a
blockout or engine test.**

## Findings to author against

1. **Restraint was over-applied.** The vocabulary and the palette were
   disciplined and scored well for it (restraint 6.78, surface scale 6.78), but
   a quiet surface only reads as quiet when something beside it is genuinely
   dense. Six scenes of quiet-beside-quiet read as unfinished. Each scene needs
   a real high-density ZONE, not merely a high-density material.

2. **Environmental storytelling is the single biggest gap.** The missing thing
   is objects that imply use and a recent human. This is not permission for
   random barrels: every object should answer "who put it there and why".

3. **Foreground relationship scored worst of all seventeen criteria.** Even the
   deliberately honest foregrounds -- a see-through railing, a well-head, hung
   cloth, a balustrade -- still read as devices. A foreground plane must be
   *occupied*: something is happening at it, ideally with a figure.

4. **Distinctiveness died in the restricted palette.** Disciplined grey-green
   and bone read to every evaluator as "generic medieval". Each scene needs one
   bold, specific, slightly strange architectural idea that could not be
   swapped into another game, plus more colour incident.

5. **NPCs must form a situation, not a spacing.** Figures evenly distributed
   along the lane scored 4.67. Group them: two in conversation, one working,
   one waiting at a door.

6. **Light the door.** Doorway readability was best where warm light marked the
   opening (03, 6.67) and worst where the door was small and far along the
   lane (06, 4.67). The door should be the brightest warm thing in frame.

7. **Darkness is not atmosphere.** 03 was the darkest and scored the *lowest*
   native readability (5.67). Contrast must be structured, not global.

8. **What already works, keep:** an unobstructed continuous floor band gives
   traversal clarity 8.0; world-scale UV mapping gives believable surface scale
   6.78; coarse runtime collapse is never in doubt (7.11).

## Convergence briefs derived from the above

- **07** -- density band and occupied foreground: a service stair-street whose
  vertical surfaces are crowded with the evidence of use, floor left quiet.
- **08** -- one bold functional silhouette: a working machine that dominates the
  frame and puts a suspended load in the foreground.
- **09** -- concentrated ornament and colour: a votive corner where a single
  wall carries hundreds of small offerings against one large quiet mass.
