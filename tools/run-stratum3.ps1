param(
    [string]$StageDir = "out/stage"
)

$ErrorActionPreference = "Stop"
$lovec = "C:\Program Files\LOVE\lovec.exe"

& node "tools/ci/stage-project-gates.js" --output $StageDir
if ($LASTEXITCODE -ne 0) { throw "Staging failed" }

& $lovec $StageDir stratum3
