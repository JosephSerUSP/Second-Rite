# Sterile town-gauntlet agent boundary

This file exists to make the next visual-research handoff mechanically simple.

A fresh town art agent should read:

- `docs/design/town-authoring-known-good.md`;
- current issue #838 for the playable-slice goal;
- current issue #695 only for the traversal/environment ownership boundary;
- generic non-visual camera/bake tooling specifically named by the task.

It should **not browse earlier town visual pull requests or branches**.

Do not provide the agent with previous town contact sheets, attempt reports, `.blend` files, environment packages, town-specific builders, material directories, screenshots, winner names, or architectural descriptions.

The only pre-existing repository visual asset permitted as an input is:

`projects/hichaukitoden-game/assets/character/walker.png`

If a task requires generic tooling that has not yet landed on `main`, provide the exact generic file/path or a sterile integration branch. Do not tell the art agent to inspect an old town branch to find it.

Independent architectural directions start from empty Blender state. Iterations within one direction may refine that direction's own newly authored scene. Prefer a few serious lineages with iterative refinement over a large batch of shallow complete scenes.

Before aesthetic scoring, fail loudly unless:

- Walker is upright and feet-anchored;
- actor scale matches the native presentation target;
- camera/lens/pitch invariants pass;
- TH_SOURCE / TH_RENDER / preview collection isolation is correct;
- the environment remains coarse real 3D plus a source-derived baked beauty atlas rather than a camera-space background plane;
- the claimed beauty atlas is actually derived from TH_SOURCE surface appearance and mapped to TH_RENDER UVs, not copied from a framebuffer and not synthesized independently;
- a real 426×240 render exists;
- floor/ground reads as part of a complete environment rather than ending as a clipped strip;
- no accidental world void or set edge is visible at center or representative projection-window offsets;
- the authored environment has enough world-space overscan to survive the intended tracking envelope;
- a genuine foreground layer exists at a meaningfully different camera depth and participates naturally in overlap/occlusion;
- hero materials show material-specific structure at native size rather than relying only on generic noise/bump;
- any generated/downloaded material claimed as evidence is actually connected to and visible in the final TH_SOURCE scene.

The intended research loop is:

**empty scene → one serious architectural proposition → native 426×240 clay review → continuity/foreground gate → critique → refine → material-specific texturing → source-derived bake/runtime proof**

not:

**browse old attempts → inherit their visual vocabulary → produce another descendant**.
