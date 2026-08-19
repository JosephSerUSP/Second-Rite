---
type: design
scope: game
status: active
---

# Art direction

## Visual identity

Second Gate should feel like a dark, strange late-1990s/early-2000s console RPG rather than a generic modern retro filter.

The core substrate is first-person low-poly 3D with deliberately limited resolution, fog/depth, period-shaped interface geometry, and selective use of richer authored art. Low fidelity is not an excuse for visual vagueness: silhouette, value grouping, material identity, and composition should remain deliberate.

## Production hierarchy

Exploration should search controlled variations rather than maximize random breadth. Historical image-generation experiments found broad contact sheets increasingly generic; prefer smaller authored subject/treatment sets where every variation has a reason to exist.

Generated/reference material is a development aid, not automatically final Second Gate art. Player-facing finished assets remain authored selections/works under the Project's art policy.

## Portraits and characters

Portraits should read as expressive console-RPG artwork at game scale rather than polished contemporary concept-art renders shrunk afterward.

Favor:
- strong asymmetric silhouettes and face/hair shapes;
- readable value blocks at target size;
- restrained but character-specific color;
- selective detail that survives reduction;
- imperfect/hand-shaped edges where they contribute personality;
- emotion and posture over generic beauty rendering.

Avoid smoothing every face toward the same model-like finish, over-rendering surfaces that disappear at game scale, and using ornamental detail as a substitute for character identity.

## World rendering

The 3D world should exploit low-poly geometry, vertex/texture behavior, fog, lighting, and deliberate resolution as one aesthetic system. “PSX-like” is a relationship among projection, texture, geometry, color, motion, and composition—not a single shader toggle.

Strata should differ through material/color/spatial language as well as asset swaps. Oddness and specificity are preferable to expensive-looking generic fantasy.

## Battle and UI presentation

Battle UI should make creature roles, current consequence, formation, resources, and prompts legible through stable geometry. Avoid duplicating the same fact in adjacent windows.

Text hierarchy normally moves from short noun-phrase title → current object/consequence → optional explanation → one action row. Prefer abstract actions such as `Confirm` and `Cancel` to physical key names when the action itself is what matters.

Color is semantic rather than decorative: focus/selection, ordinary content, secondary context, benefits, resources, damage/cost, and warnings should keep consistent roles. Do not scatter arbitrary per-scene emphasis colors when an established semantic role already communicates the meaning.

## Cultural position

The game may retain deliberate translation-like awkwardness, unexpected combinations, and culturally specific lived-world fragments when they remain comprehensible and evocative. It should not sand itself into generic “international indie RPG” neutrality.

## Authority note

This document owns Second Gate's intended look and presentation. Renderer implementation, shader contracts, Studio preview behavior, and reusable Thestra UI architecture remain repository-level technical concerns. Historical visual/UI briefs are preserved in the [legacy archive](archive/legacy-repo-design/README.md).
