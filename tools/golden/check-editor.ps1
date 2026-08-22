$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir

# #579: prove the dependency preflight and evidence-record classification without
# Chrome/Node before asking the real gate to boot either of them.
& python "tools/golden/test-g6-harness-boundaries.py"
if ($LASTEXITCODE -ne 0) {
    throw "G6 harness boundary regression test failed"
}

& python "tools/golden/test-g6-dependency-preflight.py"
if ($LASTEXITCODE -ne 0) {
    throw "G6 dependency preflight regression test failed"
}

# #831: a stall must report what the page said. These are pure-Python and
# run here for the same reason as the two above -- prove the diagnostics
# before asking the real gate to depend on them.
& python "tools/golden/test-harness-error-visibility.py"
if ($LASTEXITCODE -ne 0) {
    throw "G6 harness error-visibility regression test failed"
}

# #815: a readiness wait must not be shorter than the bridge contract it
# waits on. Pure-Python, so it runs with the other preflight guards.
& python "tools/golden/test-g6-readiness-scoping.py"
if ($LASTEXITCODE -ne 0) {
    throw "G6 readiness scoping regression test failed"
}

# #646: editor-screens-actual/ is evidence for this run, not an append-only
# history. Reset it and stamp the run before the harness can write any frame.
& python "tools/golden/actual_run.py" g6
if ($LASTEXITCODE -ne 0) {
    throw "Could not prepare G6 current-run actual output"
}

# G6 boots the editor server and a headless Chrome itself, so unlike G2/G3/G5
# there is no engine stdout to marshal through a temp file -- the Python driver
# owns the whole run.
#
# A direct gate uses the same-process timing entry (#815). Under record.py the
# Python executable is a recorder shim and MUST continue to see the canonical
# editor-screens.py spelling so it classifies this as `editor-check`, preserves
# G6's semantic timeout ownership, and then swaps the real execution to the
# timing entry itself. SECOND_RITE_RECORD_ROOT is set by that recorder context.
if ([string]::IsNullOrEmpty($env:SECOND_RITE_RECORD_ROOT)) {
    & python "tools/golden/g6-timed-entry.py" check
} else {
    & python "tools/golden/editor-screens.py" check
}
$g6Exit = $LASTEXITCODE
if ($g6Exit -eq 1) {
    Write-Error "G6 visual mismatch: inspect actual vs owner-signed references before any recapture"
    exit 1
}
if ($g6Exit -eq 2) {
    Write-Error "G6 harness stalled before pixel comparison; this is not a visual mismatch"
    exit 2
}
if ($g6Exit -ne 0) {
    Write-Error "G6 harness execution failed (exit $g6Exit)"
    exit $g6Exit
}
