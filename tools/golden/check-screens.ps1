$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir

# A stale native shim can produce a convincing renderer/GPU regression. Refuse
# it before G5 spends time rendering or asks anyone to interpret pixel diffs.
& powershell -NoProfile -ExecutionPolicy Bypass -File "tools/effekseer/check-provenance.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "Effekseer shim provenance check failed"
}

# The harness prints one very large JSON document (base64 PNGs) between its
# markers. Redirect to a file rather than piping: PowerShell 5.1 re-encodes
# pipeline strings, and a 2.5MB single line is not worth risking that.
# Use the .NET primitive rather than New-TemporaryFile because the recorder's
# deliberately minimal PowerShell path must stay compatible with PS 5.1 hosts.
$tempOut = [System.IO.Path]::GetTempFileName()
$tempWide = [System.IO.Path]::GetTempFileName()
try {
    & lovec . screenshots | Out-File -FilePath $tempOut -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        throw "lovec . screenshots exited with $LASTEXITCODE"
    }
    & python "tools/golden/screens.py" check --input $tempOut
    if ($LASTEXITCODE -ne 0) {
        throw "Golden screenshot mismatch detected"
    }

    # #199: G5 owns world-image verification. Compare Classic against the
    # canonical 256x240 crop of Wide through the real viewport renderer in one
    # process/GPU invocation. This does not create or update any golden files.
    & lovec . surface-crop-check
    if ($LASTEXITCODE -ne 0) {
        throw "Expanded-surface center-crop invariant failed"
    }

    # The crop check only proves Wide's CENTRE matches Classic. It says nothing
    # about what the extra columns draw, or about anything framed over them --
    # which is where every #199 overlay bug actually lived. These frames are
    # that evidence.
    & lovec . surface=wide screenshots | Out-File -FilePath $tempWide -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        throw "lovec . surface=wide screenshots exited with $LASTEXITCODE"
    }
    & python "tools/golden/screens.py" check --input $tempWide --surface wide
    if ($LASTEXITCODE -ne 0) {
        throw "Wide golden screenshot mismatch detected"
    }
} finally {
    Remove-Item $tempOut -ErrorAction SilentlyContinue
    Remove-Item $tempWide -ErrorAction SilentlyContinue
}