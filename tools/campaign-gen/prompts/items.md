# Stage: items

This stage runs only because the capability plan says the game needs authored items or
inventory/equipment content. Generate exactly that Project-owned content; do not build a
stock JRPG inventory for completeness.

Goal:
{{GOAL}}

Plan:
{{PLAN}}

Outline:
{{OUTLINE}}

Current Project manifest:
{{MANIFEST}}

Neutral schema context:
{{SCHEMAS}}

## Deliverable

ONE JSON object:

```json
{
  "items.json": [],
  "shops.json": {}
}
```

Populate only what the walkthrough needs. Empty shops are correct when the game has no
shop. Item ids must be unique and every reference must resolve inside this Project.
Do not import item types, crafting vocabulary, equipment slots, prices, balance bands,
or lore from Second Gate merely because those concepts exist in the engine.
