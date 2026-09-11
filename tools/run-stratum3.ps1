param(
    [string]$StageDir = "out/stage",
    [string]$Lovec = $env:LOVEC
)

$ErrorActionPreference = "Stop"

if (-not $Lovec) {
    if (Test-Path "C:\Program Files\LOVE\lovec.exe") {
        $Lovec = "C:\Program Files\LOVE\lovec.exe"
    } elseif (Get-Command lovec -ErrorAction SilentlyContinue) {
        $Lovec = (Get-Command lovec).Source
    } else {
        throw "lovec not found"
    }
}

& node "tools/ci/stage-project-gates.js" --output $StageDir
if ($LASTEXITCODE -ne 0) { throw "Staging failed" }

& $Lovec $StageDir stratum3
