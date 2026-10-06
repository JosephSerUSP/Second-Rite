# Continuous Surface Gauntlet

A self-contained Thestra Project used to pressure-test continuous authored-room traversal and, later, a continuous arena combat host.

This Project is intentionally **not Second Gate**. It owns its own data, maps, scenes, environment assets and character art under this directory. The only shared dependency is the Thestra installation/runtime (plus the pinned neutral RTP revision).

The current spatial slice proves the Lane A / early Lane B substrate from #1402:

- a Map selects `traversal.provider = "continuous_surface"`;
- the walk surface is Project gameplay data rather than a grid or bounded lane;
- the environment package contributes render geometry and stable anchors;
- the Map Scene selects `world = "continuous_surface"`;
- held canonical directions drive free 8-way locomotion;
- diagonal speed is normalized by the shared semantic;
- authored polygon obstacles and irregular walk boundaries constrain motion;
- ordinary world-space Map Events use the existing Thestra Event program host;
- `Archive Antechamber` and `Service Annex` form a two-way room loop through ordinary `LOAD_MAP` commands;
- the existing `LOAD_MAP.arrival` string selects named environment anchors for provider-backed Maps, just as it already does for bounded-lane town Maps;
- provider-owned world position, facing, distance state and arrival-anchor identity survive save/load;
- presentation uses the existing fixed-eye WorldCamera math without giving camera ownership to traversal.

The two Maps deliberately reuse the Project's own Archive Antechamber environment package while the transfer/lifecycle contract is under test. They author distinct gameplay walk surfaces; a later visual-content lane can give the Service Annex its own environment without changing transfer semantics.

No Parasite Eve names, maps, dialogue, characters or art are used. The reference game is requirements evidence only.

## Run

Stage this Project through the ordinary Thestra Project exporter, then run the staged directory with LÖVE. It should never require `projects/hichaukitoden-game` to exist.
