param(
    [string]$GameRoot = ""
)

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir

# #700/#741: G1 validates authored game data, which now lives in a Project
# rather than at the repository root. Stage the semantic default Project
# through the one canonical exporter boundary and validate that, exactly as
# the required CI verification lane does.
$ownedGameRoot = $false
if ([string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("thestra-g1-" + [guid]::NewGuid().ToString("N"))
    & node "tools/ci/stage-project-gates.js" --output $GameRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not stage default Project for G1" }
    $ownedGameRoot = $true
}
$game = [System.IO.Path]::GetFullPath($GameRoot)

try {
    & lovec $game validate
    if ($LASTEXITCODE -ne 0) {
        throw "G1 failed (exit $LASTEXITCODE)"
    }
} finally {
    if ($ownedGameRoot) {
        Remove-Item $game -Recurse -Force -ErrorAction SilentlyContinue
    }
}
