$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir

# Regenerating golden screenshots is an OWNER-SIGNED action. A red G5 means a
# visual regression until proven otherwise -- never run this to silence a diff
# (AGENTS.md, same rule as G2/G3).
$tempOut = New-TemporaryFile
$tempWide = New-TemporaryFile
try {
    & lovec . screenshots | Out-File -FilePath $tempOut.FullName -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        throw "lovec . screenshots exited with $LASTEXITCODE"
    }
    & python "tools/golden/screens.py" capture --input $tempOut.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Golden screenshot capture failed"
    }

    # #199: a curated Wide set, so the expanded surface is not shipped with the
    # classic frames as its only evidence. Its own tree and scene list live in
    # screens.py (SURFACE_COVERAGE).
    & lovec . surface=wide screenshots | Out-File -FilePath $tempWide.FullName -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        throw "lovec . surface=wide screenshots exited with $LASTEXITCODE"
    }
    & python "tools/golden/screens.py" capture --input $tempWide.FullName --surface wide
    if ($LASTEXITCODE -ne 0) {
        throw "Wide golden screenshot capture failed"
    }
} finally {
    Remove-Item $tempOut.FullName -ErrorAction SilentlyContinue
    Remove-Item $tempWide.FullName -ErrorAction SilentlyContinue
}
