# G6 editor surface inventory

This is the durable-surface audit for `tools/golden/editor-screens.py`. The
static modal inventory comes from `tools/editor/index.html`; dynamically-created
surfaces come from the editor JavaScript modules. G6 is representative coverage
of durable Studio surfaces, not an exhaustive capture of every transient or
nested interaction.

## Captured

| Surface | G6 state |
| --- | --- |
| Map modes | Event, Map, Light, and Override mode frames |
| Map Properties | Populated tileset selector |
| Event Editor | Map 2 / Event 5, an authored event inheriting Common Event 12's dungeon chest model; the effective 3D preview must be painted before capture |
| Command Selector | Open selector from the Event command surface |
| Database Manager | Every `DB_TABS` tab, including the async animation preview |
| Engine Editor | Every `ENGINE_TABS` tab, including the fog and rendering preview readiness states |
| Studio Preferences | Preferences modal with its form populated |
| Tileset Studio | Populated tileset list and painted atlas |
| Campaign Generator | Offline catalogue branch with the modal chrome visible |
| Export Game | Populated `.love` preflight |
| Icon Picker | Populated icon grid |
| Shared image/sprite asset picker | `assets/sprites/NPC00.png` selected with the positive painted-preview marker |
| Shared 3D model picker | `assets/models/items/bottle_family__basis.obj` selected with populated metadata and painted model preview |

## Missing - should capture

| Surface | Reason |
| --- | --- |
| Command Editor (`cmd-modal`) | Durable command authoring is visually important, but this issue keeps the new capture additions focused on the shared asset/model picker seam; it should receive a deterministic command-edit frame in a follow-up. |

## Intentionally excluded

| Surface | Rationale |
| --- | --- |
| Damage Popup Settings (`damage-popup-modal`) | Nested configuration utility launched from the Engine surface; a separate frame would duplicate a small generated form rather than add coverage of a navigation surface. |
| Change Maximum (`max-modal`) | Nested database-list maintenance dialog; its visual contract is subordinate to the captured Database Manager surfaces. |
| Toast (`toast-modal`) | Transient feedback whose text and visibility are event outcomes, not a durable authoring surface. |
| Map, canvas, and command context menus | Transient pointer/keyboard overlays; their contents depend on the interaction location and add noise to byte-identity coverage. |
| Command help popover (`cmd-help-popover`) | Transient contextual help attached to a parameter field, not an independently durable modal. |
| Campaign model catalogue contents | Live remote catalogue data is deliberately suppressed; the durable G6 claim is the stable offline modal state, not a changing external inventory. |

The reset path force-closes the newly covered asset/model pickers, clears their
selection and preview readiness state, resets picker scroll, and invalidates
late async responses before the next step begins.
