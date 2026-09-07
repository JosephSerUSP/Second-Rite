# SPOILERS — do not read until you have rated the campaign

Three independent critics examined the finished playable package (README,
validation evidence, and the complete authored content — every line of text,
every choice, every ending) and answered a fixed question set: central thesis,
strongest three ideas, weakest three, likely pacing collapse, likely owner
favourite, likely owner complaint, generic versus Second Gate, one thing worth
stealing into canon, one thing to leave experimental.

**Reading these first will bias your ratings**, which are the only thing in
this directory that cannot be reconstructed later. Fill in
[`../OWNER-JOURNAL.md`](../OWNER-JOURNAL.md) first.

Critics do not have authority to remove content they dislike. Their reports are
evidence, not verdicts.

## Models that actually responded

| Slug | Provider | Model reported by the provider |
|---|---|---|
| `luna` | OpenAI | `gpt-5-2025-08-07` |
| `openrouter-a` | OpenRouter Free | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| `openrouter-b` | OpenRouter Free | `nvidia/nemotron-3-super-120b-a12b:free` |

`z-ai/glm-5.2:free` and `openai/gpt-oss-20b:free` were tried first for the
second free slot and returned 503 / 429; the Nemotron Super run is the first
free model that answered. No Terra and no Gemini were used, and no Google model
was queried at all. Machine-readable record in `manifest.json`.
