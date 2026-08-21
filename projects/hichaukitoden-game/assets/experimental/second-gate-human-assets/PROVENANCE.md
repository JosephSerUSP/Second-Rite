# Second Gate human-asset gauntlet provenance

Retrieval date: 2026-08-21.  This experiment uses only public, human-made
assets.  No AI-generated 3D model or environment image is used.

## Licenses and source records

| Creator | Source URL | License | Original asset/model name | Local role |
| --- | --- | --- | --- | --- |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `building_market_blue` | A primary market mass |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `building_tavern_blue` | A inhabited secondary architecture |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `building_church_blue` | A deep civic/religious landmark |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `fence_stone_straight_gate` | A doorway/continuation gate |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `building_bridge_A` | A water-edge depth cue |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `wheelbarrow` | Street clutter and foreground incident |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `barrel` | Market storage prop |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `crate_A_big` | Market storage prop |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `building_blacksmith_green` | B primary forge mass |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `building_home_A_green` | B inhabited secondary architecture |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `building_home_B_green` | B deep continuation architecture |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `fence_wood_straight_gate` | B courtyard doorway |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `wall_corner_A_inside` | B retaining/occlusion wall |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `hills_A_trees` | B distant green continuation |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `tree_single_B` | B foreground vegetation |
| Kay Lousberg / KayKit | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 Universal | `sack` | B forge/courtyard clutter |
| Poly Haven staff / contributing artist | https://polyhaven.com/a/street_lamp_01 | CC0 | `street_lamp_01` | A foreground lamp and vertical scale cue |
| Poly Haven staff / contributing artist | https://polyhaven.com/a/wine_barrel_01 | CC0 | `wine_barrel_01` | A water-street landmark, rescaled and recolored by lighting |
| Poly Haven staff / contributing artist | https://polyhaven.com/a/wooden_lantern_01 | CC0 | `wooden_lantern_01` | A warm market light |
| Poly Haven staff / contributing artist | https://polyhaven.com/a/potted_plant_01 | CC0 | `potted_plant_01` | B planted courtyard incident |
| Poly Haven staff / contributing artist | https://polyhaven.com/a/wooden_crate_01 | CC0 | `wooden_crate_01` | B foreground storage clutter |

The KayKit checkout retains the original `LICENSE.txt` files.  Poly Haven
assets were downloaded from the public model API at 1K glTF resolution; the
local model directories retain the glTF, binary mesh and referenced textures.
The local source path is `sources/` beside this record.

## Audition accounting

- Two empty-scene directions were authored: A / Cinderbridge Market and B /
  Pinewatch Court.
- 21 unique sourced model candidates were imported into the two direction
  scenes (16 KayKit, 5 Poly Haven).  The KayKit sparse checkout contains the
  candidate folders used for selection; the scene script names every imported
  candidate explicitly.
- The selected winner is direction A.  The winning scene keeps 11 sourced
  candidates in the source set: 8 KayKit architectural/prop meshes and 3
  Poly Haven props, plus minimal scene glue geometry.
- The final production assets are intentionally not claimed here; this is a
  source-dressing experiment and the external meshes remain under
  `TH_SOURCE`.
