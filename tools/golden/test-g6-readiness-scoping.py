"""#815: a readiness wait must not be shorter than the contract it waits on.

POST /api/map-inspection is allowed BRIDGE_TIMEOUT_MS to answer. The two Map
inspection frames were falling through to STEP_TIMEOUT, so the harness abandoned
an operation the system was still legitimately performing and reported it as a
stall. Every observed occurrence had map-inspection-status still reading
"Resolving through the real engine..." -- the in-progress state.

The negative controls are the load-bearing half: ordinary frames must NOT get the
producer bound, or a genuinely stuck page costs the long timeout everywhere.
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCREENS = ROOT / "tools/golden/editor-screens.py"

mod = {"__file__": str(SCREENS), "__name__": "editor_screens_under_test"}
exec(compile(io.open(SCREENS, encoding="utf-8").read(), str(SCREENS), "exec"), mod)

scoped = mod["scoped_readiness_timeout"]
ready_timeout = mod["runtime_authority_ready_timeout"]
INSPECTION_RUNTIME_STEPS = mod["INSPECTION_RUNTIME_STEPS"]
WORKSPACE_RUNTIME_STEPS = mod["WORKSPACE_RUNTIME_STEPS"]

ORDINARY = 30.0
PRODUCER = 60.0
WORKSPACE_READY = "document.getElementById('x').dataset.workspaceReady === '1'"
INSPECTION_PREDICATE = ("document.getElementById('map-inspection-status').textContent"
                        ".indexOf('Resolved preview') === 0")

failures = []


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        failures.append(name)


# --- the fix ----------------------------------------------------------------
for step in sorted(INSPECTION_RUNTIME_STEPS):
    got = scoped(INSPECTION_PREDICATE, step, WORKSPACE_READY, ORDINARY, PRODUCER)
    check("%s waits for the producer bound" % step, got == PRODUCER, "got %s" % got)

check("a suffixed inspection wait is still scoped",
      scoped(INSPECTION_PREDICATE, "map-editor/generated-inspection.png reseed",
             WORKSPACE_READY, ORDINARY, PRODUCER) == PRODUCER)

# --- NEGATIVE CONTROLS: everything else keeps the ordinary bound -------------
check("NEGATIVE CONTROL: an unrelated frame keeps the ordinary bound",
      scoped("document.getElementById('database-status').textContent === 'ok'",
             "database/units.png", WORKSPACE_READY, ORDINARY, PRODUCER) == ORDINARY)

check("NEGATIVE CONTROL: a workspace frame's non-readiness wait stays ordinary",
      scoped("document.getElementById('other').textContent === 'ok'",
             "map-editor/workspace-light.png", WORKSPACE_READY, ORDINARY, PRODUCER) == ORDINARY)

check("NEGATIVE CONTROL: a near-miss name is not scoped",
      scoped(INSPECTION_PREDICATE, "map-editor/generated-inspection-other.png",
             WORKSPACE_READY, ORDINARY, PRODUCER) == ORDINARY)

# --- the existing workspace behaviour is unchanged ---------------------------
check("a workspace readiness wait still gets the producer bound",
      scoped(WORKSPACE_READY, "map-editor/workspace-perspective.png",
             WORKSPACE_READY, ORDINARY, PRODUCER) == PRODUCER)

check("the two step sets stay disjoint",
      not (INSPECTION_RUNTIME_STEPS & WORKSPACE_RUNTIME_STEPS))

# --- the bound is derived from the bridge, not hardcoded ---------------------
derived = ready_timeout(ROOT)
check("the producer bound is read from BRIDGE_TIMEOUT_MS", derived >= 30.0,
      "got %s" % derived)
check("the producer bound exceeds the ordinary one", derived > 30.0,
      "producer=%s ordinary=30.0 -- if these ever match, this fix is inert" % derived)

# --- the frames named here are the frames the harness actually captures ------
source = io.open(SCREENS, encoding="utf-8").read()
core = io.open(ROOT / "tools/golden/editor-screens-core.py", encoding="utf-8").read()
for step in sorted(INSPECTION_RUNTIME_STEPS):
    check("%s is a real capture target" % step, step in core or step in source,
          "named in neither harness file -- a typo here silently reverts the fix")

print()
if failures:
    print("FAILED: %d" % len(failures))
    raise SystemExit(1)
print("all G6 readiness-scoping checks passed")
