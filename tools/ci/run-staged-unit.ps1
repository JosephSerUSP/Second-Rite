param(
    [Parameter(Mandatory = $true)]
    [string]$GameRoot,

    [string]$Lovec = $env:LOVEC
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$resolvedGameRoot = (Resolve-Path $GameRoot).Path
if (-not $Lovec) {
    $Lovec = "C:\Program Files\LOVE\lovec.exe"
}
if (-not (Test-Path $Lovec)) {
    throw "lovec not found: $Lovec"
}

$previousRepositoryRoot = $env:THESTRA_REPOSITORY_ROOT
$exitCode = 1
try {
    # Runtime/world tests intentionally inherit the staged Project as process
    # CWD: native Effekseer resolves authored effect paths against process CWD.
    # Repository-verification tests use this explicit authority instead.
    $env:THESTRA_REPOSITORY_ROOT = $repoRoot
    Push-Location $resolvedGameRoot
    try {
        & $Lovec $resolvedGameRoot unittest | Tee-Object -Variable unitOutput
        $exitCode = $LASTEXITCODE
        # Assert the positive verdict, never the absence of failure: a renamed
        # CLI token boots the game, which can exit 0 having run no suite.
        if ($exitCode -eq 0 -and -not ($unitOutput -match "^ALL UNIT TESTS OK")) {
            Write-Host "unit gate: exit 0 but no 'ALL UNIT TESTS OK' line; no suite verdict was observed"
            $exitCode = 1
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($null -eq $previousRepositoryRoot) {
        Remove-Item Env:THESTRA_REPOSITORY_ROOT -ErrorAction SilentlyContinue
    }
    else {
        $env:THESTRA_REPOSITORY_ROOT = $previousRepositoryRoot
    }
}

exit $exitCode
