param(
    [string]$GameRoot = "."
)

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir
$game = [System.IO.Path]::GetFullPath($GameRoot)

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
