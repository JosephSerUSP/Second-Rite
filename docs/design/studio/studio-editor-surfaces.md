# Thestra Studio Editor Surfaces

Current architecture after #530, #536, #537, #538, #539, #542, and #546. This document
closes the architecture/inventory deliverable of #521 and records the policy that
future Studio-window work must preserve.

This is a **Studio design/ownership contract**, not engine runtime state.
`docs/ENGINE-STATE.md` remains the generated authority on runtime/content facts,
and `docs/design/contracts/project-editor-runtime-boundaries.md` remains the authority on
Project vs installation ownership.

## First principle

> **A substantial editor is an EditorSurface. A BrowserWindow is only one host
> for an EditorSurface.**

A surface is defined by its authoring responsibility, working-state/commit
contract, multiplicity policy, interaction ownership, and close lifecycle. It is
not defined by `.modal-overlay`, by draggable faux-window chrome, or by Electron
OS parentage.

Likewise, a short-lived picker is not promoted into an EditorSurface merely
because it visually resembles a window.

## Current first-class surface registry

`studio/editor/studio-surface-registry.js` is the executable policy registry.
Today it contains the surfaces that have completed first-class migration:

| id | category | multiplicity | production host | browser/G6 host | close policy |
| --- | --- | --- | --- | --- | --- |
| `main` | workspace | singleton | native main `BrowserWindow` | root workspace | coordinated Studio shutdown |
| `database` | editor | singleton | independent native `BrowserWindow` | existing DOM Database modal | resource transaction |
| `engine` | editor | singleton | independent native `BrowserWindow` | existing DOM Engine modal | resource transaction |
| `tileset` | editor | singleton | independent native `BrowserWindow` | existing DOM Tileset Studio modal | record transaction |

`main` is not an openable secondary surface. `database`, `engine`, and `tileset`
are current secondary native surfaces; opening any again focuses/reuses its
existing instance.

The registry describes semantic identity and host policy. Native lifecycle is
implemented by `StudioWindowManager`; browser/DOM composition is implemented by
renderer adapters. Do not collapse those responsibilities back together.

## Current durable surface inventory

The G6 inventory in `tools/golden/editor-screens-inventory.md` is the durable UI
census baseline. The classification below states current hosting **and** migration
policy; “candidate” does not mean “make this native now.”

### Workspace / editor surfaces

| Current surface | Current host | Classification / policy |
| --- | --- | --- |
| **Map workspace** (Event/Map/Light/Override modes) | main Studio workspace | First-class workspace (`main`). Remains the primary Studio workspace for now. A future detachable Map document would require a demonstrated workflow need, not merely native-window symmetry. |
| **Database Manager** | native secondary in Electron; same existing `#db-modal` content in browser/G6 | First-class editor (`database`), singleton. This is the reference first native-host proof. |
| **Engine Editor** | native secondary in Electron; same existing `#engine-modal` content in browser/G6 | First-class editor (`engine`), singleton. Owns a renderer working transaction over `system`/`engine` resources and reuses the generic native close/session lifecycle. |
| **Tileset Studio** | native secondary in Electron; same existing `#tileset-studio-modal` content in browser/G6 | First-class editor (`tileset`), singleton. Owns a record-local working transaction over one tileset record, saves through the dedicated tileset endpoint with authored-storage version tokens, and participates in generic Studio close/shutdown lifecycle. |
| **Animation Editor** | Animations tab inside Database Manager | Sub-editor of Database today. It is substantial enough to become its own EditorSurface later, but only if independent focus/workflow outweighs the cost of another renderer and its cross-resource dependencies are made explicit. |
| **Event Editor** | contextual DOM editor (`event-modal`) launched from Map | Substantial contextual editor and future EditorSurface candidate. It remains DOM-hosted because its current working copy is tightly scoped to the selected Map event and no independent-window workflow has yet justified promotion. |
| **Command Editor** (`cmd-modal`) | nested contextual DOM editor | Authoring editor, but subordinate to Event/command context today. Keep lightweight until there is evidence for independent document lifecycle. |

A “future candidate” is still not a BrowserWindow by default. Migration means:
first give the editor an explicit EditorSurface contract, then choose a host.

### Tool / palette surfaces

| Current surface | Current host | Policy |
| --- | --- | --- |
| **Map Inspector / Properties** | persistent panel in main workspace | Tool/palette. Keep docked; detachable hosting is an optional future convenience, not a process boundary requirement. |
| **Map/sidebar palettes and 3D view controls** | main workspace | Tools owned by the Map surface, not independent EditorSurfaces. |
| **Studio Preferences** (`studio-modal`) | DOM dialog/tool | Preferences workflow, not a Project document. Keep lightweight. |
| **Project generator** (`campaign-gen-modal`, legacy element id) | DOM workflow | Tool/workflow. The legacy DOM id does not restore Campaign as an ontology; generated output is Projects. No native window requirement. |
| **Export Game** | DOM workflow | Tool/workflow. Keep in Studio unless export becomes a genuinely long-lived independent job surface. |

### Dialogs / pickers / transient interactions

These remain lightweight interactions and **must not** become one Chromium
renderer each merely to look more window-like:

- Map Properties;
- icon picker;
- shared image/sprite asset picker;
- shared 3D model picker;
- Command Selector;
- Damage Popup Settings;
- Change Maximum;
- command parameter/help popovers;
- toast/feedback modal;
- context menus and confirmations.

`state.js` adapts the exact registered lightweight interaction set into
`ThestraInteractionState`. Map/3D consumes semantic interaction ownership and no
longer infers focus from broad `.modal`, `.modal-overlay`, or `.picker-overlay`
CSS scans.

## EditorSurface contract

A first-class EditorSurface has all of the following properties.

### 1. Stable semantic identity

A surface has a stable id and category independent from its container. Current
ids are `main`, `database`, `engine`, and `tileset`. New ids belong in
`studio-surface-registry.js` only after the editor has a real lifecycle contract.

### 2. Explicit multiplicity

Multiplicity is policy, not an accident of whether `window.open()` happened to
be called twice. Current first-class surfaces are singleton.

For a singleton native surface, repeated Open must focus/reuse the existing
window. Multiple-document support requires an explicit document identity model
before multiplicity changes.

### 3. Host independence

The surface’s authoring behavior must survive a host change.

Database, Engine, and Tileset demonstrate the intended shape:

```text
browser / G6
    existing editor content -> DOM modal host

Electron
    same editor content -> native BrowserWindow host
```

The native window does not own editor semantics. Existing forms, mutation logic,
authored resources, and save paths are shared.

A future docked/native toggle should therefore be a host-policy change, not a
rewrite of the editor itself.

### 4. Bounded working transaction

Each renderer owns a working copy, not committed Project authority.

For the bulk-resource path used by main, Database, and Engine, `net.js` records
the baseline and authored-storage version tokens loaded by that renderer. Save
sends only top-level resources that diverged from that baseline. A save may
therefore commit `units` without writing a stale `maps` copy.

If a resource lacks a version token, save fails before sending an unsafe request.
If another renderer already committed the same resource revision, the existing
server/authored-storage stale-version guard rejects the stale save.

Tileset Studio exercises the same principle with a different transaction shape:
it loads one tileset record into a record-local working copy, captures a baseline
and compound authored-storage `_storageVersion`, and saves only that record
through `/api/tilesets/save`. Dirty state is derived from the working record vs
its baseline. Successful save adopts the returned persisted version as the new
baseline; stale or failed save stays dirty and open.

### 5. Observable commit lifecycle

After a successful commit, Electron transports **resource invalidations**, not
Project values. The sender announces bounded resource names; sibling renderers
re-read committed truth from the appropriate server-owned source.

Bulk resources refresh through `/data`. Record-managed `tilesets` refreshes
through `/api/tilesets`; the invalidation still carries only the resource name,
never authored tileset values.

A sibling adopts a notified resource only if that resource is still locally
clean at apply time. If local editing began before or while the refresh request
was in flight, the local working copy and old version token are retained. The
next same-resource save therefore remains safely stale rather than silently
blessing conflicting state.

This is the current same-session synchronization model:

```text
renderer working copy
      |
      | scoped save + expected version
      v
editor server / authored-storage
      |
      | successful committed resource name
      v
sibling invalidation
      |
      | re-read authoritative bulk or record-managed source
      | adopt only if locally clean
      v
other renderer working copies
```

## StudioSession / Project authority

#521 deliberately did **not** create a second in-memory Project database in
Electron main.

The explicit committed authority is the existing editor server plus
`authored-storage` and its revision/version tokens. This boundary already owns
validated Project reads/writes and is shared by every renderer.

Therefore:

- renderer working state (`dbPayload` or a record-local transaction) is not global Project truth;
- Electron main owns application/window coordination, not authored values;
- IPC carries bounded lifecycle/invalidation metadata, never arbitrary authored
  object mutation;
- committed Project truth is read from the server/storage boundary;
- sibling working copies are refreshed conservatively after commits.

This server-owned session model is the chosen #521 option because it reuses the
real authored-storage authority instead of duplicating it in a new main-process
service.

## Dirty / save / close semantics

### Native secondary surface

Database, Engine, and Tileset native close, title-bar X, and Alt+F4 converge on
one close intent:

```text
native close
  -> resolve staged lightweight child interactions
  -> clean? close
  -> dirty? Save / Discard / Cancel
       Save    -> await the surface's scoped commit; close only on clean success
       Discard -> close working copy without writing
       Cancel  -> keep BrowserWindow open
```

Database/Engine use resource-scoped working transactions. Tileset uses its
record-local tileset transaction. The shell lifecycle is shared; the authored
transaction authority remains surface-specific.

Escape is separate: it dismisses the appropriate lightweight interaction and
does not substitute for native window close. In a native editor with no nested
lightweight interaction left, Escape is consumed rather than closing the host
BrowserWindow.

### Main Studio window

Main-window close is an application shutdown intent. `studio-shutdown.js`
resolves open secondary native surfaces first through their ordinary close
contracts. Any cancellation aborts shutdown and keeps main alive. Only then does
main resolve its own staged interactions and Save/Discard/Cancel decision.

This means Alt+F4 cannot destroy main and strand/kill a dirty secondary working
copy.

### Project switching

Project opening is currently a full-process relaunch. It is therefore refused
while a secondary native EditorSurface is open. The user closes that surface
through Save/Discard/Cancel, then retries the Project switch. This conservative
rule is preferable to silently destroying a renderer transaction.

## WindowManager contract

`StudioWindowManager` owns native host lifecycle only:

- register/open/get/has/close surfaces;
- singleton reuse/focus behavior;
- persisted bounds/maximized state per surface;
- hidden-until-renderer-ready hosting where requested;
- deferred native destruction while the renderer resolves close intent;
- `closeAndWait()` for coordinated shutdown.

WindowManager does not own Project data, editor forms, or OS parentage policy
beyond the BrowserWindow options supplied by the surface registration.

Studio-owned editor windows are independent top-level windows by default. Do not
make them Electron `parent`/modal children of main unless the interaction is a
true blocking native dialog. Application ownership and OS parent-child z-order
are separate facts.

## Interaction ownership

`ThestraInteractionState` is the semantic interaction boundary for the current
renderer.

Existing DOM interactions are represented through the exact registered dialog
ids. Future hosts/tools can participate explicitly with `setBlocked(ownerId,
true/false)`. The Map backend asks only whether Map is blocked; it does not know
which CSS classes or window implementation produced that fact.

This is intentionally separate from native OS focus. A BrowserWindow owns native
focus while lightweight interactions inside that renderer own local interaction
focus.

## Preload / security boundary

Keep:

- `nodeIntegration: false`;
- `contextIsolation: true`;
- narrow `contextBridge` APIs.

`thestraStudio` exposes only registered surface lifecycle, close decisions,
Project-switch readiness, and bounded resource commit notifications. It does not
expose raw `ipcRenderer`, generic main-process invocation, arbitrary filesystem
access, or arbitrary authored object mutation.

Project lifecycle remains on `thestraProjects`. Do not grow one generic bridge
that can “do anything.”

## Verification contract

EditorSurface verification is deliberately split by responsibility.

### Browser/G6

Surface content should remain mountable in browser-hosted deterministic tests
where useful. Database, Engine, and Tileset keep their DOM hosts specifically so
native plumbing does not make editor content untestable.

Do not recapture G5/G6 merely to prove BrowserWindow lifecycle. Reference changes
still require the normal owner-signoff rules when visible composition actually
changes.

### Electron/Windows

`test:studio-host` covers:

- surface registry/multiplicity policy;
- WindowManager singleton/focus/persistence;
- native close cancellation and shutdown ordering;
- sender-owned narrow IPC;
- bulk-resource and record-managed transaction synchronization;
- semantic interaction ownership;
- a real Windows Electron smoke that creates main + Database + Engine + Tileset
  as four actual BrowserWindows and requires Database + Engine + Tileset renderer
  readiness.

### Repository gates

Normal G1/unit/save/G2/G3/G4 verification remains required. EditorSurface work
must not bypass Project/runtime ownership or turn native-host success into a
substitute for engine/UI regression coverage.

## Follow-up migration rules

When considering another current editor for first-class migration:

1. demonstrate that it is a durable editor/workspace rather than a result-returning dialog;
2. define the authored resources/working transaction it owns;
3. add it to the surface registry with explicit multiplicity and host policy;
4. preserve browser-hosted content where useful;
5. reuse WindowManager, resource invalidation, shutdown, and semantic interaction contracts;
6. add focused native tests before enabling the production host;
7. do not add Electron parent/modal relationships unless true modal OS behavior is intended.

Likely next candidates are—if independent workflow proves useful—the Animation
Editor or substantial Event editing. Neither is promoted by this document.

## Non-goals reaffirmed

- no BrowserWindow per picker/control;
- no full docking framework yet;
- no `BaseWindow`/`WebContentsView` migration without a demonstrated composed-native-pane need;
- no BroadcastChannel/browser-global object as Project authority;
- no automatic multiple-document support;
- no silent Project switching while secondary renderer work is open;
- no reintroduction of Campaign as a runnable Project ontology.

The architectural result is intentionally hybrid: **one Studio session, bounded
renderer working copies, substantial first-class surfaces where useful, and
lightweight interactions where a new renderer would be waste.**
