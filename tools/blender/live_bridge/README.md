# Thestra Live Bridge

The Thestra Live Bridge is an opt-in co-authoring surface for the owner's
currently open Blender document. It gives the same repository-aware agent that
works on Second Rite structured scene inspection, owner-published captures, and
small reviewable edits. It does not replace recipes, headless Blender, export,
baking, or validation, and it is never a semantic authority for runtime data.

## Security and ownership boundary

- The server binds only to `127.0.0.1` and accepts newline-delimited JSON no
  larger than 1 MiB.
- Every start creates a new random token. The token is hidden, skipped by
  Blender preference persistence, never stored in a `.blend`, and never logged.
  **Copy Token** places it on the clipboard; **Rotate Token** invalidates the
  previous value immediately.
- Requests carry protocol version 1, a unique ID, and a timestamp no more than
  five minutes from the server clock. Duplicate IDs, unknown fields, stale
  timestamps, malformed/non-finite numbers, and unsupported operations fail
  with structured error codes.
- Socket threads only authenticate and enqueue. All `bpy` work is serialized on
  Blender's main thread. A second concurrent mutation is rejected rather than
  queued behind live state it did not inspect.
- Every mutation requires the fingerprint returned by `inspect` or a share.
  The fingerprint covers the open file, scene, frame, selection, active object,
  every object transform/datablock/material/modifier/collection membership,
  material state, and the bridge mutation generation.
- There is no arbitrary Python, shell, save, delete, hierarchy destruction,
  modifier application, conversion, purge, or unrestricted filesystem API.
  Captures and reports can only use safe basenames under
  `out/blender-live-bridge/<session-id>/`.
- One successful request is one Blender undo operation. The bridge validates
  all targets and arguments before writes and restores touched state if an
  operation fails partway. It never saves the document; saving remains an
  explicit owner action.

## Build and install

Build the deterministic ZIP from the repository root:

```powershell
python tools/blender/live_bridge/package.py `
  --output out/blender-live-bridge/thestra_live_bridge.zip
```

The package manifest records add-on, client, and protocol versions. Its test
audits an exact file allowlist, so project assets, tokens, captures, bytecode,
and unrelated Blender tools cannot enter the ZIP.

In Blender 5.1:

1. Open **Edit > Preferences > Add-ons**.
2. Choose **Install from Disk** and select the ZIP.
3. Enable **Thestra Live Bridge**.
4. Open **3D View > Sidebar (`N`) > Thestra** and select **Start Bridge**.
5. Select **Copy Token**. Do not paste the token into logs, Issues, or commits.

Reinstalling a development build requires restarting Blender so Python does not
retain the previous module in memory.

## Inspect, share, and capture

Use a process-local environment variable rather than a command-line token:

```powershell
$env:THESTRA_BRIDGE_TOKEN = '<copied token>'
python tools/blender/live_bridge/client.py status
python tools/blender/live_bridge/client.py inspect > out/context.json
python tools/blender/live_bridge/client.py capabilities
python tools/blender/live_bridge/client.py share-context
python tools/blender/live_bridge/client.py latest-share
python tools/blender/live_bridge/client.py validate
python tools/blender/live_bridge/client.py geometry ARCH_west_house --grid 1
python tools/blender/live_bridge/client.py capture-viewport --out viewport.png
python tools/blender/live_bridge/client.py capture-selection --out selection.png --width 426 --height 240
python tools/blender/live_bridge/client.py capture-camera --out game.png --width 426 --height 240
python tools/blender/live_bridge/client.py capture-camera --out diagnostic.png --width 256 --height 144
```

`geometry` measures modelling discipline rather than appearance. With no
object names it reads the current selection. It returns local and world
bounding boxes, where the origin sits inside its own bounds (`min`/`mid`/`max`
per axis, so a base-anchored asset is visible as `z: min`), whether location
and dimensions land on the grid, whether scale and rotation are still
unapplied, and every vertex that misses the grid by more than the tolerance
with the sixteen worst named. `--vertices` lists positions too, capped and
flagged when truncated, because the protocol caps a message at 1 MiB.

Compact JSON is the default machine interface. Add global `--pretty` before the
command for indented human-readable output.

Viewport capture preserves the active 3D view's framing, shading, overlays, and
perspective. Selection capture temporarily hides non-selected objects, frames
the selection against a neutral solid background, and restores visibility,
selection, active object, framing, shading, overlays, and world state in
`finally`. Camera capture requires a camera in `TH_CAMERA_PREVIEW`; using the
scene camera instead requires `--allow-active-camera-fallback`.

Every PNG has a sibling JSON manifest containing its SHA-256, exact dimensions,
capture kind, timestamp, session, fingerprint, selection, camera/view metadata,
and warnings. Each share also writes a coherent bundle manifest with the
matching full context. `latest-share` returns only the most recently
owner-published bundle.

## Bounded mutations

Copy `fingerprint` from a fresh `inspect` result and pass it to every mutation:

```powershell
python tools/blender/live_bridge/client.py transform Wall_A `
  --fingerprint <sha256> --location-x 11.5 --delta-z 0.1
python tools/blender/live_bridge/client.py assign-material Wall_A Wall_B `
  --fingerprint <sha256> --semantic lime_plaster
python tools/blender/live_bridge/client.py link-mesh SourceWall Wall_A Wall_B `
  --fingerprint <sha256>
python tools/blender/live_bridge/client.py make-unique HeroFacade `
  --fingerprint <sha256>
python tools/blender/live_bridge/client.py collection Lamp_A Lamp_B `
  --fingerprint <sha256> --collection 30_PROPS --mode link
python tools/blender/live_bridge/client.py create-primitive cube `
  --fingerprint <sha256> --name Blockout_A --collection 30_PROPS --size 1
python tools/blender/live_bridge/client.py modifier Wall_A BEVEL `
  --fingerprint <sha256> --name AuthoringBevel --setting width=0.03 --setting segments=2
python tools/blender/live_bridge/client.py thestra recalculate_normals `
  --fingerprint <sha256> --objects Wall_A Wall_B
```

Inspection explains shared meshes and duplicate-name families rather than
choosing an instancing strategy automatically. Material assignment refuses to
silently change non-target objects through a shared mesh; make the intended
objects unique or include every mesh user explicitly.

`stale_context` means Blender changed after the inspection. Do not retry with
the old fingerprint: inspect again, reconsider the proposed edit against the
new state, and submit a new request. `mutation_busy` means another mutation is
pending; wait for it to finish and inspect again. A failed mutation does not
increment the generation and restores all touched state.

## Undo, saving, and cleanup

Focus a 3D View and press Ctrl+Z once to undo one successful bridge request.
Blender may continue to show an unsaved marker even when the restored values
match the opened file; the bridge reports current values but never decides
whether to save. Close with **Don't Save** to discard a supervised experiment,
or save manually only after the owner approves the artistic result.

Session output is diagnostic and gitignored. Stop Blender/bridge users before
removing an individual directory below `out/blender-live-bridge/`; never point a
cleanup command at the repository or `out/` root.

## Troubleshooting and verification

- **Add-on is installed but absent:** install the ZIP, not its parent folder;
  verify the ZIP root contains `thestra_live_bridge/__init__.py`, then restart
  Blender.
- **Connection refused:** start the bridge and use the panel's displayed port
  (`THESTRA_BRIDGE_PORT` overrides the CLI default 8765).
- **Authentication failed:** copy the current token again; starting or rotating
  the bridge invalidates the previous token.
- **No viewport:** captures and undoable mutations require a windowed Blender
  session with a `VIEW_3D` editor.
- **No selection/camera:** select at least one object for selection capture;
  refresh the calibrated camera or explicitly request the active-camera
  fallback.
- **Bridge stopped during a call:** queued requests receive `bridge_stopped`;
  restart, copy the new token, inspect again, and do not reuse an old request.

Run the focused suite with:

```powershell
python -m unittest tools.blender.tests.test_live_bridge
```

The suite covers protocol limits/authentication, package contents, windowed
viewport/selection/camera captures and dimensions, negative pixel controls,
state restoration, stale rejection, rollback under injected failure,
concurrent-mutation rejection, terminal shutdown, and add-on registration.
The owner-observed one-Ctrl+Z proof is recorded under `docs/reports/` because a
background test cannot prove the physical keyboard/viewport interaction.
