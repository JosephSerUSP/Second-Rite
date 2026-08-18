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
    $GameRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("thestra-g2-" + [guid]::NewGuid().ToString("N"))
    & node "tools/ci/stage-project-gates.js" --output $GameRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not stage default Project for G2" }
    $ownedGameRoot = $true
}
$game = [System.IO.Path]::GetFullPath($GameRoot)

try {

    # Native build artifacts are machine-local. If one is present, prove it was
    # built from this checkout before any golden output is interpreted.
    & powershell -NoProfile -ExecutionPolicy Bypass -File "tools/effekseer/check-provenance.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "Effekseer shim provenance check failed"
    }

    $output = & lovec $game validate golden
    $inBlock = $false
    $log = @()
    foreach ($line in $output) {
        if ($line -match "GOLDEN BEGIN") {
            $inBlock = $true
        } elseif ($line -match "GOLDEN END") {
            $inBlock = $false
        } elseif ($inBlock) {
            $log += $line
        }
    }

    $currentKey = ""
    $currentLog = @()
    $fixtureLogs = @{}
    foreach ($line in $log) {
        if ($line -match "^battle\|(.+?)\|name\|") {
            if ($currentKey -ne "" -and $currentLog.Count -gt 0) {
                $fixtureLogs[$currentKey] = $currentLog
            }
            $currentKey = $matches[1]
            $currentLog = @($line)
        } else {
            $currentLog += $line
        }
    }
    if ($currentKey -ne "" -and $currentLog.Count -gt 0) {
        $fixtureLogs[$currentKey] = $currentLog
    }

    if ($fixtureLogs.Count -eq 0) {
        throw "No golden battle fixtures produced any output"
    }

    $allMatch = $true
    foreach ($key in $fixtureLogs.Keys) {
        $refPath = "tools/golden/battle_$key.log"
        if (-not (Test-Path $refPath)) {
            Write-Host "WARNING: No reference log for fixture '$key' at $refPath"
            $allMatch = $false
            continue
        }

        $tempLog = New-TemporaryFile
        $refContent = @("GOLDEN BEGIN") + $fixtureLogs[$key] + @("GOLDEN END")
        $refContent | Out-File -FilePath $tempLog.FullName -Encoding utf8

        $referenceLog = (Get-Content $refPath -Raw).Replace("`r`n", "`n")
        $newLog = (Get-Content $tempLog.FullName -Raw).Replace("`r`n", "`n")

        if ($referenceLog -eq $newLog) {
            Write-Host "Golden log matches for fixture '$key'."
        } else {
            Write-Host "Golden log MISMATCH for fixture '$key'!"
            $allMatch = $false
        }
        Remove-Item $tempLog.FullName
    }

    foreach ($refFile in Get-ChildItem "tools/golden/battle_*.log") {
        $key = $refFile.BaseName -replace "^battle_", ""
        if (-not $fixtureLogs.ContainsKey($key)) {
            Write-Host "WARNING: $($refFile.Name) has no matching fixture in the selected Project"
            $allMatch = $false
        }
    }

    if (-not $allMatch) {
        throw "Golden log mismatch detected"
    }
} finally {
    if ($ownedGameRoot) {
        Remove-Item $game -Recurse -Force -ErrorAction SilentlyContinue
    }
}
