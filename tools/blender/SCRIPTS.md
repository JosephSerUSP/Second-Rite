# Blender script roles

Generated from [SCRIPTS.json](SCRIPTS.json). Start with the [authoring routes](README.md) and [furnishings catalogue](recipes/FURNISHINGS.md). An experiment or source-editing migration is evidence, not a template for a fresh room.

Run `python tools/blender/script_index.py --check`; after classifying a new top-level Python or JS file in the manifest, run `--write`. Classification preserves paths and bytes. Nested recipe, test and bridge directories have their own entry points; this manifest covers the top-level tool surface.

## Supported authoring and verification entry points (26)

| Script | Purpose |
|---|---|
| [asset_library.py](asset_library.py) | Browse a Blender remote asset library without Blender, and without downloading an asset. |
| [build_asset_library.py](build_asset_library.py) | Our own Blender asset library: SR_GroundCover, browsable like any remote library. |
| [capture_environment.py](capture_environment.py) | Capture one staged environment at real runtime surfaces, including device ratios. |
| [check_thestra_camera.py](check_thestra_camera.py) | Run the #837 runtime->Blender WorldCamera numerical parity fixture. |
| [compile_item_blends.py](compile_item_blends.py) | Compile authoritative item ``.blend`` sources without allowing source writes. |
| [compile_room_spec.py](compile_room_spec.py) | Compile relational JSON scaffolds through existing Interior and furnishing builders. |
| [environment_sources.py](environment_sources.py) | Which `.blend` is the source of an environment, as a record rather than a guess (#1269). |
| [export_exterior_environment.py](export_exterior_environment.py) | Bake an authored modelled exterior into its runtime environment package. |
| [export_map_blend.js](export_map_blend.js) | Export a renderable map bundle through the canonical Studio authority. |
| [export_room_environment.py](export_room_environment.py) | Bake one authored interior into a real-3D town environment package. |
| [furnishings_catalogue.py](furnishings_catalogue.py) | Generate/check the furnishing catalogue without importing bpy on the host. |
| [inspect_architectural_assembly.py](inspect_architectural_assembly.py) | Render a source assembly independently from its scene, without saving changes. |
| [inspect_environment_parts.py](inspect_environment_parts.py) | Inspect named source furnishings individually without saving the document. |
| [inspect_environment_surfaces.py](inspect_environment_surfaces.py) | Read-only source/package geometry and atlas inspection from independent cameras. |
| [install_room_3d.py](install_room_3d.py) | Install a baked room export as a runtime town environment package. |
| [make_town_camera.py](make_town_camera.py) | Derive the Second Gate town side-view camera calibration record. |
| [offline_blender.py](offline_blender.py) | Run a Blender Python tool with Python network connections denied in this process. |
| [pack_environment_source.py](pack_environment_source.py) | Save a new self-contained source revision from a working source document. |
| [photograph_room_package.py](photograph_room_package.py) | Photograph a baked room package the way the game draws it: unlit, nearest-sampled, native size. |
| [preview_diff_sheet.py](preview_diff_sheet.py) | A before / after / difference sheet for renders that should look alike. |
| [review_room_source.py](review_room_source.py) | Photograph an interior source using camera records from native staged captures. |
| [script_index.py](script_index.py) | Generate/check the role index for every top-level Blender Python/JS tool. |
| [stage_room_model.py](stage_room_model.py) | Stage a generated room model against the calibrated Second Gate town camera. |
| [sync_asset_core.py](sync_asset_core.py) | Synchronize canonical Blender contract sources into the portable toolkit. |
| [validate_item_obj_runtime.py](validate_item_obj_runtime.py) | Validate item OBJ products against the runtime's non-degenerate-face contract. |
| [vendor_assets.py](vendor_assets.py) | Acquire named assets deliberately, or verify the committed selection entirely offline. |

## Implementation modules and Blender workers (34)

| Script | Purpose |
|---|---|
| [asset_library_source.py](asset_library_source.py) | Blender side of build_asset_library.py: mark SR_GroundCover as an asset, or describe it. |
| [atlas_allocation.py](atlas_allocation.py) | Atlas layout for a room: packed tight, and optionally spent where the camera looks (#877). |
| [atlas_alpha.py](atlas_alpha.py) | Preserve authored cutout coverage independently of atlas beauty and camera visibility. |
| [atlas_denoise.py](atlas_denoise.py) | Fast OIDN study on isolated UV charts, preserving small charts and alpha. |
| [bake_correspondence.py](bake_correspondence.py) | Sampled selected-to-active ray preflight with authored receiver/source bindings. |
| [blender_locator.py](blender_locator.py) | The one place a Blender executable is chosen, and its version asserted. |
| [build_synthetic_environment.py](build_synthetic_environment.py) | Build a synthetic Blender environment fixture conforming to the Second Rite V0 contract. |
| [build_world_props.py](build_world_props.py) | Blender-side staged builder for deterministic Second Rite world props. |
| [compile_item_blend.py](compile_item_blend.py) | Compile one already-open authoritative item ``.blend`` into runtime OBJ/MTL. |
| [cycles_source.py](cycles_source.py) | Temporary evaluated beauty batching for selected-to-active Cycles baking. |
| [eevee_bake.py](eevee_bake.py) | The EEVEE atlas bake: what an exporter runs in place of Cycles' selected-to-active bake. |
| [eevee_projection.py](eevee_projection.py) | Bake an atlas with EEVEE, by camera projection: the shared core of the EEVEE atlas bake. |
| [emissive_lights.py](emissive_lights.py) | Companion area lights for emissive surfaces, so EEVEE lights a room the way a glowing surface should. |
| [furnishing_geometry.py](furnishing_geometry.py) | Evaluated geometry measurements shared by catalogue and scaffold placement. |
| [ground_cover.py](ground_cover.py) | Ground cover as a Geometry Nodes modifier (the #1257 pilot). |
| [import_map_bundle.py](import_map_bundle.py) | Blender-side importer for Thestra's authoritative renderable-bundle JSON. |
| [item_mtl_runtime.py](item_mtl_runtime.py) | Finalize Blender-exported item MTL files with Second Rite runtime passes. |
| [light_fixtures.py](light_fixtures.py) | Let a lamp shine out of a fixture smaller than itself: the housing stops shadowing its light. |
| [map_bundle_scene.py](map_bundle_scene.py) | Pure planning helpers for Thestra renderable-bundle -> Blender scene import. |
| [material_library.py](material_library.py) | Second Gate material library: textures bound to semantic material IDs. |
| [mesh_export_geometry.py](mesh_export_geometry.py) | Derived mesh preparation; never alters authored mesh datablocks. |
| [placement_rules.py](placement_rules.py) | Pure authoring support and protected-volume checks; not runtime collision. |
| [render_furnishings_catalogue.py](render_furnishings_catalogue.py) | Pinned-Blender worker for furnishings_catalogue.py; never saves a .blend. |
| [render_profiles.py](render_profiles.py) | Shared render quality; camera, lighting, output encoding and source files belong to callers. |
| [second_rite_asset_core.py](second_rite_asset_core.py) | Shared Blender infrastructure for Second Rite asset pipelines. |
| [source_dependencies.py](source_dependencies.py) | Fail before rendering when an editable source cannot resolve its dependencies. |
| [surface_finishes.py](surface_finishes.py) | World-scale procedural finishes for authored environment studies. |
| [thestra_camera.py](thestra_camera.py) | Blender preview helpers for serialized Thestra WorldCamera calibration records. |
| [town_environment_pipeline.py](town_environment_pipeline.py) | Blender-authored baked environment pipeline for Second Gate town slices. |
| [tree_generator.py](tree_generator.py) | Deterministic, low-poly procedural tree skeletons. |
| [tree_material.py](tree_material.py) | The one Blender material for foliage atlas cards. |
| [tree_mesh.py](tree_mesh.py) | Blender-free meshing for :mod:`tree_generator` skeletons. |
| [vendor_assets_blender.py](vendor_assets_blender.py) | Build/check a portable named-datablock library; no network or preferences changes. |
| [wide_screen.py](wide_screen.py) | Render a whole side-view location in one frame, at canon scale. |

## Experiments and measurements (23)

| Script | Purpose |
|---|---|
| [build_registry_readability_review.py](build_registry_readability_review.py) | Pair native before/after frames with isolated source-shape inspections. |
| [capture_courtyard.py](capture_courtyard.py) | Capture the staged courtyard through the native compositor; never recapture goldens. |
| [depth_baseline.py](depth_baseline.py) | Verify deterministic Blender depth maps and manage reviewed baseline changes. |
| [ground_cover_placement.py](ground_cover_placement.py) | Ground-cover placement on the adopted Praca: the candidate layouts and how they are painted (#1270). |
| [registry_workflow.py](registry_workflow.py) | Run a repeatable Registry experiment from an editable source into native review. |
| [review_courtyard.py](review_courtyard.py) | Native source review and floor/profile verification, without saving the source. |
| [stage_courtyard_candidate.js](stage_courtyard_candidate.js) | Stage a recorded courtyard candidate for native review. |
| [stage_registry_candidate.js](stage_registry_candidate.js) | Stage a recorded Registry candidate for native review. |
| [study_atlas_denoise.py](study_atlas_denoise.py) | Create a denoised comparison package without overwriting its raw input. |
| [study_atlas_drift.py](study_atlas_drift.py) | What does Blender 5.2.2 change in the baked atlases we already ship? A measurement. |
| [study_courtyard_geometry_loss.py](study_courtyard_geometry_loss.py) | Measure export geometry loss without altering the scaffold or production package. |
| [study_cycles_courtyard.py](study_cycles_courtyard.py) | Native full-geometry Cycles budget study; never saves or exports the source. |
| [study_cycles_surface_bake.py](study_cycles_surface_bake.py) | Actual Cycles selected-to-active atlas study; source stays unchanged. |
| [study_eevee_atlas.py](study_eevee_atlas.py) | Can an atlas be baked with EEVEE? A camera-projection bake, measured against Cycles. |
| [study_eevee_exterior.py](study_eevee_exterior.py) | The Praça exterior: its atlas as Cycles bakes it today, and as EEVEE would by projection. |
| [study_eevee_exterior_blender.py](study_eevee_exterior_blender.py) | Blender side of study_eevee_exterior.py: the Praça atlas baked by Cycles today and by EEVEE projection. |
| [study_eevee_pilot.py](study_eevee_pilot.py) | One room, plate and atlas both on EEVEE, judged next to Cycles: the Padaria pilot. |
| [study_engine_parity.py](study_engine_parity.py) | Can EEVEE stand in for Cycles on the interior plates? A measurement, not a switch. |
| [study_environment_receivers.py](study_environment_receivers.py) | Inspect receiver admission/culling and geometric source correspondence without saving. |
| [study_ground_cover_placement.py](study_ground_cover_placement.py) | Where should grass grow on the adopted Praça? Candidate layouts at the plate camera (#1270). |
| [study_ground_cover_sheet.py](study_ground_cover_sheet.py) | Contact sheets for the ground-cover placement study (`study_ground_cover_placement.py`). |
| [study_house_grammar.py](study_house_grammar.py) | Photograph the first grammar-generated building as CLAY, against the real camera. |
| [study_town_perspective.py](study_town_perspective.py) | Compare level/pitched town cameras on an exterior and an interior. |

## Recorded source surgery and migrations (11)

| Script | Purpose |
|---|---|
| [define_registry_bay.py](define_registry_bay.py) | Fix counter support and add a wall-connected timber service screen. |
| [enrich_registry_source.py](enrich_registry_source.py) | Edit the Registry document: tactile finishes, coherent windows, selected props. |
| [extend_registry_frontage.py](extend_registry_frontage.py) | Extend existing service joinery to the right wall and add a wall-backed cabinet. |
| [finish_registry_shell.py](finish_registry_shell.py) | Close the retained Registry ceiling junction without regenerating the room. |
| [fit_registry_ceiling.py](fit_registry_ceiling.py) | Fit the retained timber service divider to the existing ceiling and beams. |
| [open_registry_plan.py](open_registry_plan.py) | Remove the detached masonry frame from an existing Registry source revision. |
| [probe_registry_shell.py](probe_registry_shell.py) | Read-only probe of the recorded Registry shell experiment. |
| [reauthor_praca_spiral.py](reauthor_praca_spiral.py) | Re-author st_maria_praca.blend for the spiral layout. |
| [refine_registry_cabinet.py](refine_registry_cabinet.py) | Edit the retained Registry: larger records press and a public-side woven runner. |
| [refine_registry_materials.py](refine_registry_materials.py) | Refine the existing Registry source: book silhouettes and material hierarchy. |
| [revise_registry_source.py](revise_registry_source.py) | Edit an existing Registry document into the recessed service-hatch study. |
