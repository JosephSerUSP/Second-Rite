param(
    [string]$GameRoot = ""
)

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir

# Regenerates docs/ENGINE-STATE.md from the live engine + data. Run this after
# any change G4 flags: the report is generated, so a G4 failure means the doc is
# stale, not that the engine is wrong.
#
# #700/#741 moved the runnable game out of the repository root, so this capture
# must stage the semantic default Project exactly as check-state.ps1 does.
# Running `lovec .` against the installation root produces no engine output at
# all, which left G4's own documented fix path unusable.
$ownedGameRoot = $false
if ([string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("thestra-g4-capture-" + [guid]::NewGuid().ToString("N"))
    & node "tools/ci/stage-project-gates.js" --output $GameRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not stage default Project for the G4 capture" }
    $ownedGameRoot = $true
}
$game = [System.IO.Path]::GetFullPath($GameRoot)

try {
    $output = & lovec $game engine-state
    $inBlock = $false
    $report = @()
    foreach ($line in $output) {
        if ($line -match "ENGINE STATE BEGIN") {
            $inBlock = $true
        } elseif ($line -match "ENGINE STATE END") {
            $inBlock = $false
        } elseif ($inBlock) {
            $report += $line
        }
    }

    if ($report.Count -eq 0) {
        Write-Host "ENGINE STATE capture produced no output - is the staged Project erroring?"
        exit 1
    }

    $path = "docs/ENGINE-STATE.md"
    [System.IO.File]::WriteAllLines((Join-Path $rootDir $path), $report)
    Write-Host "Captured engine state -> $path ($($report.Count) lines)"
} finally {
    if ($ownedGameRoot) {
        Remove-Item $game -Recurse -Force -ErrorAction SilentlyContinue
    }
}
