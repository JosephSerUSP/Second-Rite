param(
    [string]$GameRoot = ""
)

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir

# #700: G5 is a player/runtime gate, while the repository root is now only the
# Thestra installation. When the caller does not provide an already-materialized
# runnable tree, stage the semantic default Project through the one canonical
# exporter boundary. The recorder still observes the same screenshots/crop
# commands and all references remain repository-owned.
$ownedGameRoot = $false
if ([string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("thestra-g5-" + [guid]::NewGuid().ToString("N"))
    & node "tools/ci/stage-project-gates.js" --output $GameRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not stage default Project for G5" }
    $ownedGameRoot = $true
}
$game = [System.IO.Path]::GetFullPath($GameRoot)

# #646: each G5 invocation owns fresh actual-output trees. This keeps the
# side-by-side inspection surface useful without letting old red frames leak
# into triage for a later run.
& python "tools/golden/actual_run.py" g5
if ($LASTEXITCODE -ne 0) {
    throw "Could not prepare G5 current-run actual output"
}

# A stale native shim can produce a convincing renderer/GPU regression. Refuse
# it before G5 spends time rendering or asks anyone to interpret pixel diffs.
& powershell -NoProfile -ExecutionPolicy Bypass -File "tools/effekseer/check-provenance.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "Effekseer shim provenance check failed"
}

# The harness prints one very large JSON document (base64 PNGs) between its
# markers. Redirect to a file rather than piping: PowerShell 5.1 re-encodes
# pipeline strings, and a 2.5MB single line is not worth risking that.
$tempOut = [System.IO.Path]::GetTempFileName()
$tempWide = [System.IO.Path]::GetTempFileName()
$failures = @()
try {
    try {
        & lovec $game screenshots | Out-File -FilePath $tempOut -Encoding utf8
        if ($LASTEXITCODE -ne 0) { throw "lovec Project screenshots exited with $LASTEXITCODE" }
        & python "tools/golden/screens.py" check --input $tempOut |
            Where-Object { $_ -ne "SCREENS OK" }
        if ($LASTEXITCODE -ne 0) { throw "Golden screenshot mismatch detected" }
        Write-Host "[G5] classic: PASS"
    } catch {
        $failures += "classic"
        Write-Host "[G5] classic: FAIL - $($_.Exception.Message)"
    }

    # #199: G5 owns world-image verification. Compare Classic against the
    # canonical 256x240 crop of Wide through the real viewport renderer in one
    # process/GPU invocation. This does not create or update any golden files.
    try {
        & lovec $game surface-crop-check
        if ($LASTEXITCODE -ne 0) { throw "Expanded-surface center-crop invariant failed" }
        Write-Host "[G5] crop invariant: PASS"
    } catch {
        $failures += "crop invariant"
        Write-Host "[G5] crop invariant: FAIL - $($_.Exception.Message)"
    }

    # The crop check only proves Wide's CENTRE matches Classic. It says nothing
    # about what the extra columns draw, or about anything framed over them --
    # which is where every #199 overlay bug actually lived. These frames are
    # that evidence.
    try {
        & lovec $game surface=wide screenshots | Out-File -FilePath $tempWide -Encoding utf8
        if ($LASTEXITCODE -ne 0) { throw "lovec Project surface=wide screenshots exited with $LASTEXITCODE" }
        & python "tools/golden/screens.py" check --input $tempWide --surface wide |
            Where-Object { $_ -ne "SCREENS OK" }
        if ($LASTEXITCODE -ne 0) { throw "Wide golden screenshot mismatch detected" }
        Write-Host "[G5] wide: PASS"
    } catch {
        $failures += "wide"
        Write-Host "[G5] wide: FAIL - $($_.Exception.Message)"
    }
} finally {
    Remove-Item $tempOut -ErrorAction SilentlyContinue
    Remove-Item $tempWide -ErrorAction SilentlyContinue
    if ($ownedGameRoot) {
        Remove-Item $game -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# These are independent coverage surfaces; accumulate failures so one stale
# frame cannot silently disable the crop or wide checks.
if ($failures.Count -gt 0) {
    throw "G5 failed: $($failures -join ', ')"
}
Write-Host "SCREENS OK"
