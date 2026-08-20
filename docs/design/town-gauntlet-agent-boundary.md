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

Independent architectural directions start from empty Blender state. Iterations within one direction may refine that direction's own newly authored scene.

The intended research loop is:

**empty scene → one serious architectural proposition → native 426×240 review → critique → refine or kill → only then material/bake/runtime preparation**

not:

**browse old attempts → inherit their visual vocabulary → produce another descendant**.
