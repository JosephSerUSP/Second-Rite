<#
.SYNOPSIS
    Shared runnable-tree staging for the G5 screenshot scripts.

.DESCRIPTION
    #700 made the repository root the Thestra *installation*; the runnable game
    is an ordinary Project underneath it. Every script that launches `lovec` for
    a gate therefore has to stage the default Project through the one canonical
    exporter boundary first, and then run the game from inside that tree.

    check-screens.ps1 was updated for this. capture-screens.ps1 was not, and
    kept running `lovec .` from the repository root -- so the owner-signed
    recapture path and the path the gate checks against disagreed about what the
    game even was, and recapture failed outright with "no SCREENSHOTS BEGIN/END
    block" (issue #960). Both now call this file, so they cannot drift again.

    Dot-source it:  . "$PSScriptRoot/gate-stage.ps1"
#>

# Stage the default Project into a temporary runnable tree, unless the caller
# already handed us one. Returns an object carrying the tree's full path and
# whether we own it (and must therefore delete it afterwards).
function New-GateStage {
    param([string]$GameRoot = "")

    if (-not [string]::IsNullOrWhiteSpace($GameRoot)) {
        return [pscustomobject]@{
            Path  = [System.IO.Path]::GetFullPath($GameRoot)
            Owned = $false
        }
    }

    $staged = Join-Path ([System.IO.Path]::GetTempPath()) ("thestra-g5-" + [guid]::NewGuid().ToString("N"))
    & node "tools/ci/stage-project-gates.js" --output $staged
    if ($LASTEXITCODE -ne 0) { throw "Could not stage default Project for G5" }

    return [pscustomobject]@{
        Path  = [System.IO.Path]::GetFullPath($staged)
        Owned = $true
    }
}

function Remove-GateStage {
    param([Parameter(Mandatory = $true)]$Stage)

    if ($Stage.Owned) {
        Remove-Item $Stage.Path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Run the game and capture its stdout to a file.
#
# Two things here are load-bearing and were the actual bugs:
#
# 1. The working directory. The Effekseer shim is native code: it hands the
#    effect path straight to Effekseer::Effect::Create, which resolves it
#    against the PROCESS working directory and never sees LOVE's virtual
#    filesystem. Run from anywhere else and the two effect-bearing frames
#    silently render without their effect while every other frame matches.
#
# 2. Redirecting rather than piping. The harness prints one very large JSON
#    document (base64 PNGs) between its markers, and PowerShell 5.1 re-encodes
#    pipeline strings -- not worth risking on a single 2.5MB line.
function Invoke-GateHarness {
    param(
        [Parameter(Mandatory = $true)]$Stage,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$OutFile
    )

    Push-Location $Stage.Path
    try {
        & lovec $Stage.Path @Arguments | Out-File -FilePath $OutFile -Encoding utf8
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0) {
        throw "lovec Project $($Arguments -join ' ') exited with $LASTEXITCODE"
    }
}
