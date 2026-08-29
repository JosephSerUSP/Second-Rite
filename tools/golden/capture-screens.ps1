param(
    [string]$GameRoot = ""
)

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir

. "$rootDir/tools/golden/gate-stage.ps1"

# Regenerating golden screenshots is an OWNER-SIGNED action. A red G5 means a
# visual regression until proven otherwise -- never run this to silence a diff
# (AGENTS.md, same rule as G2/G3).
#
# This script stages and launches the game through tools/golden/gate-stage.ps1,
# exactly as check-screens.ps1 does. It used to run `lovec .` from the
# repository root, which #700 turned into the installation rather than a
# runnable game: recapture failed with "no SCREENSHOTS BEGIN/END block", and had
# it not failed it would have written references the gate never compares
# against (issue #960).
$stage = New-GateStage -GameRoot $GameRoot

# A stale native shim can produce a convincing renderer/GPU regression. Refuse
# it before spending time rendering references that bake it in.
& powershell -NoProfile -ExecutionPolicy Bypass -File "tools/effekseer/check-provenance.ps1"
if ($LASTEXITCODE -ne 0) { throw "Effekseer shim provenance check failed" }

# GetTempFileName rather than New-TemporaryFile: the latter is unresolvable on
# the hosted runner, which is what turned G2 red once already (AGENTS.md).
$tempOut = [System.IO.Path]::GetTempFileName()
$tempWide = [System.IO.Path]::GetTempFileName()
try {
    Invoke-GateHarness -Stage $stage -Arguments @("screenshots") -OutFile $tempOut
    & python "tools/golden/screens.py" capture --input $tempOut
    if ($LASTEXITCODE -ne 0) {
        throw "Golden screenshot capture failed"
    }

    # #199: a curated Wide set, so the expanded surface is not shipped with the
    # classic frames as its only evidence. Its own tree and scene list live in
    # screens.py (SURFACE_COVERAGE).
    Invoke-GateHarness -Stage $stage -Arguments @("surface=wide", "screenshots") -OutFile $tempWide
    & python "tools/golden/screens.py" capture --input $tempWide --surface wide
    if ($LASTEXITCODE -ne 0) {
        throw "Wide golden screenshot capture failed"
    }
} finally {
    Remove-Item $tempOut -ErrorAction SilentlyContinue
    Remove-Item $tempWide -ErrorAction SilentlyContinue
    Remove-GateStage -Stage $stage
}
