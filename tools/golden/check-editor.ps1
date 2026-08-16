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

# G6 boots the editor server and a headless Chrome itself, so unlike G2/G3/G5
# there is no engine stdout to marshal through a temp file -- the Python driver
# owns the whole run. editor-screens.py now fails causally before this boot when
# its gitignored Three.js vendor surface is absent.
& python "tools/golden/editor-screens.py" check
$g6Exit = $LASTEXITCODE
if ($g6Exit -eq 1) {
    throw "G6 visual mismatch: inspect actual vs owner-signed references before any recapture"
}
if ($g6Exit -eq 2) {
    throw "G6 harness stalled before pixel comparison; this is not a visual mismatch"
}
if ($g6Exit -ne 0) {
    throw "G6 harness execution failed (exit $g6Exit)"
}
