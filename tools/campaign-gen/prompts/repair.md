# Stage: bounded Project repair

The real engine validator rejected the generated Project. Make the smallest targeted
correction inside THIS Project only.

Failure category:
{{CATEGORY}}

## Validator problems (verbatim)

{{PROBLEMS}}

## Reusable RTP command language

{{COMMANDS}}

## Neutral schema context

{{SCHEMAS}}

## Current generated Project resources

{{FILES}}

## Deliverable

ONE JSON object containing ONLY changed Project resources, complete:
`{ "<filename>": <complete corrected content>, ... }`

Rules:
- Repair only the specific reported failure; preserve unrelated authored design/content.
- Every replacement reference must resolve from the resources already present in FILES,
  or be a new Project-owned record created in the appropriate changed resource when that
  is genuinely required by this Project's design.
- NEVER copy, import, infer, or restore a missing skill/element/role/unit/item/state/
  passive/asset from Second Gate, the repository's canonical data/, or another Project.
- RTP is engine language only: command/formula semantics and declared reusable defaults.
  Do not turn RTP into game content.
- Do not invent asset paths or raw Lua escape hatches.
- A sparse database may remain empty when irrelevant. Do not repair emptiness by filling
  it with generic RPG content.
- If the validator failure cannot be repaired without changing engine/runtime or another
  Project, emit no speculative substitute; the bounded repair budget will surface the
  unresolved failure instead.
