$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir

# The harness prints one very large JSON document (base64 PNGs) between its
# markers. Redirect to a file rather than piping: PowerShell 5.1 re-encodes
# pipeline strings, and a 2.5MB single line is not worth risking that.
$tempOut = New-TemporaryFile
try {
    & lovec . screenshots | Out-File -FilePath $tempOut.FullName -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        throw "lovec . screenshots exited with $LASTEXITCODE"
    }
    & python "tools/golden/screens.py" check --input $tempOut.FullName
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
} finally {
    Remove-Item $tempOut.FullName -ErrorAction SilentlyContinue
}
