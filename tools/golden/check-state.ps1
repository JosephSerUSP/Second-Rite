param(
    [string]$GameRoot = ""
)

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir

# #700/#741: these gates run the real game, but the repository root is now only
# the Thestra installation -- it owns no `data/`. When the caller does not pass
# an already-materialized runnable tree, stage the semantic default Project
# through the one canonical exporter boundary, exactly as check-screens.ps1
# does. Golden references stay repository-owned.
$ownedGameRoot = $false
if ([string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("thestra-g4-" + [guid]::NewGuid().ToString("N"))
    & node "tools/ci/stage-project-gates.js" --output $GameRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not stage default Project for G4" }
    $ownedGameRoot = $true
}
$game = [System.IO.Path]::GetFullPath($GameRoot)

try {

    # G4: docs/ENGINE-STATE.md must match what the engine actually reports. The
    # repository owns the reference; the selected runnable Project owns semantic
    # game data. #700 therefore runs the report against the canonical Project stage
    # rather than pretending the repository root itself is a game.
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
        Write-Host "ENGINE STATE produced no output -- is the staged Project erroring?"
        exit 1
    }

    $refPath = "docs/ENGINE-STATE.md"
    if (-not (Test-Path $refPath)) {
        Write-Host "MISSING $refPath -- run tools/golden/capture-state.ps1"
        exit 1
    }

    $reference = ((Get-Content $refPath -Raw -Encoding UTF8) -replace "`r`n", "`n").TrimEnd()
    $current = (($report -join "`n") -replace "`r`n", "`n").TrimEnd()

    if ($reference -eq $current) {
        Write-Host "Engine state doc matches."
        exit 0
    }

    Write-Host "Engine state doc is STALE (docs/ENGINE-STATE.md != live engine)."
    Write-Host "Fix: run tools/golden/capture-state.ps1 and commit the updated file."
    Write-Host ""
    $refLines = $reference -split "`n"
    $curLines = $current -split "`n"
    $max = [Math]::Max($refLines.Count, $curLines.Count)
    $shown = 0
    for ($i = 0; $i -lt $max -and $shown -lt 20; $i++) {
        $a = if ($i -lt $refLines.Count) { $refLines[$i] } else { "" }
        $b = if ($i -lt $curLines.Count) { $curLines[$i] } else { "" }
        if ($a -ne $b) {
            Write-Host ("  line {0}:" -f ($i + 1))
            Write-Host ("    doc:    {0}" -f $a)
            Write-Host ("    engine: {0}" -f $b)
            $shown++
        }
    }
    exit 1
} finally {
    if ($ownedGameRoot) {
        Remove-Item $game -Recurse -Force -ErrorAction SilentlyContinue
    }
}
