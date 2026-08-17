param(
    [string]$GameRoot = "."
)

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir
$game = [System.IO.Path]::GetFullPath($GameRoot)

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
