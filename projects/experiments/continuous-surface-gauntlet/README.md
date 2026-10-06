# Continuous Surface Gauntlet

A self-contained Thestra Project used to pressure-test continuous authored-room traversal and, later, a continuous arena combat host.

This Project is intentionally **not Second Gate**. It owns its own data, maps, scenes, environment assets and character art under this directory. The only shared dependency is the Thestra installation/runtime (plus the pinned neutral RTP revision).

The first room proves the Lane A substrate from #1402:

- a Map selects `traversal.provider = "continuous_surface"`;
- the walk surface is Project gameplay data rather than a grid or bounded lane;
- the environment package contributes render geometry and stable anchors;
- the Map Scene selects `world = "continuous_surface"`;
- held canonical directions drive free 8-way locomotion;
- diagonal speed is normalized by the shared semantic;
- the room contains a solid central obstacle and an irregular walk boundary;
- presentation uses the existing fixed-eye WorldCamera math without giving camera ownership to traversal.

No Parasite Eve names, maps, dialogue, characters or art are used. The reference game is requirements evidence only.

## Run

Stage this Project through the ordinary Thestra Project exporter, then run the staged directory with LÖVE. It should never require `projects/hichaukitoden-game` to exist.
