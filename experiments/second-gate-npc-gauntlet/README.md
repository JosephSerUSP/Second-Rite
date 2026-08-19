# Second Gate NPC Sprite Gauntlet

An isolated, non-production experiment for evaluating Blender-authored NPCs as
192x192 DRPG sprites. Run `python run_gauntlet.py build` to create the three
editable Blender sources, all sprite frames, diagnostics and contact sheets.
Run `python luna_evaluate.py <round-dir> <images...>` to send a compact package
to `gpt-5.6-luna`; it requires `OPENAI_API_KEY` but never records it.

The shared presentation contract is `contract.json`: orthographic front camera,
neutral three-point light, transparent film, 192x192 RGBA PNGs, bottom-centre
anchor `(96, 176)`, and 124px ordinary standing height. It is deliberately
owned here, not by production assets or the game runtime.
