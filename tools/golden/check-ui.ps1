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
    $GameRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("thestra-g3-" + [guid]::NewGuid().ToString("N"))
    & node "tools/ci/stage-project-gates.js" --output $GameRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not stage default Project for G3" }
    $ownedGameRoot = $true
}
$game = [System.IO.Path]::GetFullPath($GameRoot)

try {

    $output = & lovec $game validate golden-ui
    $inBlock = $false
    $log = @()
    foreach ($line in $output) {
        if ($line -match "UI GOLDEN BEGIN") {
            $inBlock = $true
        } elseif ($line -match "UI GOLDEN END") {
            $inBlock = $false
        } elseif ($inBlock) {
            $log += $line
        }
    }

    $currentScene = ""
    $currentLog = @()
    $sceneLogs = @{}
    foreach ($line in $log) {
        if ($line -match "^scene\|(.+?)\|name\|") {
            if ($currentScene -ne "" -and $currentLog.Count -gt 0) {
                $sceneLogs[$currentScene] = $currentLog
            }
            $currentScene = $matches[1]
            $currentLog = @($line)
        } else {
            $currentLog += $line
        }
    }
    if ($currentScene -ne "" -and $currentLog.Count -gt 0) {
        $sceneLogs[$currentScene] = $currentLog
    }

    $allMatch = $true
    foreach ($key in $sceneLogs.Keys) {
        $refPath = "tools/golden/scene_$key.log"
        if (-not (Test-Path $refPath)) {
            Write-Host "WARNING: No reference log for scene '$key' at $refPath"
            $allMatch = $false
            continue
        }

        $tempLog = New-TemporaryFile
        $refContent = @("UI GOLDEN BEGIN") + $sceneLogs[$key] + @("UI GOLDEN END")
        $refContent | Out-File -FilePath $tempLog.FullName -Encoding utf8

        $referenceLog = (Get-Content $refPath -Raw).Replace("`r`n", "`n")
        $newLog = (Get-Content $tempLog.FullName -Raw).Replace("`r`n", "`n")

        if ($referenceLog -eq $newLog) {
            Write-Host "Golden UI log matches for scene '$key'."
        } else {
            Write-Host "Golden UI log MISMATCH for scene '$key'!"
            if ($env:GITHUB_ACTIONS) {
                $referenceLines = $referenceLog -split "`n"
                $actualLines = $newLog -split "`n"
                $max = [Math]::Max($referenceLines.Count, $actualLines.Count)
                $first = -1
                for ($i = 0; $i -lt $max; $i++) {
                    $refLine = if ($i -lt $referenceLines.Count) { $referenceLines[$i] } else { "<missing>" }
                    $actualLine = if ($i -lt $actualLines.Count) { $actualLines[$i] } else { "<missing>" }
                    if ($refLine -ne $actualLine) { $first = $i; break }
                }
                if ($first -ge 0) {
                    $refLine = if ($first -lt $referenceLines.Count) { $referenceLines[$first] } else { "<missing>" }
                    $actualLine = if ($first -lt $actualLines.Count) { $actualLines[$first] } else { "<missing>" }
                    $msg = "scene=$key line=$($first + 1) expected=[$refLine] actual=[$actualLine]"
                    Write-Host "::error title=G3 mismatch $key::$msg"
                }
            }
            $allMatch = $false
        }
        Remove-Item $tempLog.FullName
    }

    if (-not $allMatch) {
        throw "Golden UI log mismatch detected"
    }
} finally {
    if ($ownedGameRoot) {
        Remove-Item $game -Recurse -Force -ErrorAction SilentlyContinue
    }
}
