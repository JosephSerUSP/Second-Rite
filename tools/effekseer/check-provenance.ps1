<#
.SYNOPSIS
    Verifies that a present effekseer_shim.dll was built from the current
    tools/effekseer/efk_shim.cpp.

.DESCRIPTION
    A missing shim is allowed: clean worktrees and CI deliberately do not carry
    the native build artifact. A present shim is different. It must have the
    provenance sidecar written by build.ps1, and that sidecar's sourceSha256
    must match the tracked shim source currently in the checkout.

    This check needs only PowerShell and SHA-256. It does not load LÖVE, create
    a GL context, or touch Effekseer.

.PARAMETER SelfTest
    Exercises the contract in a temporary synthetic checkout: absent -> green,
    matching -> green, source mutation -> red, rewritten provenance -> green.
    Used by CI as the negative control required by issue #269.
#>
[CmdletBinding()]
param(
    [switch]$SelfTest,
    [string]$RepoRoot
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
}

$sourceRel = "tools\effekseer\efk_shim.cpp"
$dllRel = "effekseer_shim.dll"
$provenanceRel = "effekseer_shim.provenance.json"
$buildCommand = ".\tools\effekseer\build.ps1"

function Get-ShimProvenanceStatus {
    param([Parameter(Mandatory = $true)][string]$Root)

    $sourcePath = Join-Path $Root $sourceRel
    $dllPath = Join-Path $Root $dllRel
    $provenancePath = Join-Path $Root $provenanceRel

    if (-not (Test-Path -LiteralPath $dllPath -PathType Leaf)) {
        return [pscustomobject]@{
            Ok = $true
            State = "absent"
            Message = "EFFEKSEER SHIM ABSENT: $dllRel is not present (allowed)."
        }
    }

    if (-not (Test-Path -LiteralPath $provenancePath -PathType Leaf)) {
        return [pscustomobject]@{
            Ok = $false
            State = "unprovenanced"
            Message = "EFFEKSEER SHIM UNPROVENANCED: $dllRel is present but $provenanceRel is missing. Rebuild with $buildCommand."
        }
    }

    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        return [pscustomobject]@{
            Ok = $false
            State = "source-missing"
            Message = "EFFEKSEER SHIM CHECK FAILED: tracked source $sourceRel is missing; cannot prove $dllRel provenance."
        }
    }

    try {
        $provenance = Get-Content -LiteralPath $provenancePath -Raw | ConvertFrom-Json
    } catch {
        return [pscustomobject]@{
            Ok = $false
            State = "invalid-provenance"
            Message = "EFFEKSEER SHIM PROVENANCE INVALID: $provenanceRel is not valid JSON. Rebuild with $buildCommand."
        }
    }

    $recorded = [string]$provenance.sourceSha256
    if ($recorded -notmatch "^[0-9A-Fa-f]{64}$") {
        return [pscustomobject]@{
            Ok = $false
            State = "invalid-provenance"
            Message = "EFFEKSEER SHIM PROVENANCE INVALID: $provenanceRel has no valid sourceSha256. Rebuild with $buildCommand."
        }
    }

    $current = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $recorded = $recorded.ToLowerInvariant()
    if ($recorded -ne $current) {
        return [pscustomobject]@{
            Ok = $false
            State = "stale"
            Message = "STALE EFFEKSEER SHIM: $dllRel was built from a different $sourceRel. Rebuild with $buildCommand.`n  recorded source SHA-256: $recorded`n  current source SHA-256:  $current"
        }
    }

    return [pscustomobject]@{
        Ok = $true
        State = "current"
        Message = "EFFEKSEER SHIM CURRENT: $dllRel matches $sourceRel ($current)."
    }
}

function Write-TestProvenance {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Hash
    )
    $payload = [ordered]@{
        sourceSha256 = $Hash.ToLowerInvariant()
        builtAtUtc = "2026-08-10T00:00:00Z"
        exports = 18
    } | ConvertTo-Json
    $utf8NoBom = New-Object System.Text.UTF8Encoding -ArgumentList $false
    [System.IO.File]::WriteAllText((Join-Path $Root $provenanceRel), $payload + [Environment]::NewLine, $utf8NoBom)
}

function Invoke-SelfTest {
    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("second-rite-shim-provenance-" + [guid]::NewGuid().ToString("N"))
    try {
        New-Item -ItemType Directory -Path (Join-Path $tempRoot "tools\effekseer") -Force | Out-Null
        Set-Content -LiteralPath (Join-Path $tempRoot $sourceRel) -Value "source-v1" -NoNewline

        $status = Get-ShimProvenanceStatus -Root $tempRoot
        if (-not $status.Ok -or $status.State -ne "absent") {
            throw "negative control setup failed: absent shim should be allowed, got '$($status.State)'"
        }

        Set-Content -LiteralPath (Join-Path $tempRoot $dllRel) -Value "synthetic-dll" -NoNewline
        $hashV1 = (Get-FileHash -LiteralPath (Join-Path $tempRoot $sourceRel) -Algorithm SHA256).Hash
        Write-TestProvenance -Root $tempRoot -Hash $hashV1
        $status = Get-ShimProvenanceStatus -Root $tempRoot
        if (-not $status.Ok -or $status.State -ne "current") {
            throw "matching provenance should pass, got '$($status.State)': $($status.Message)"
        }

        Set-Content -LiteralPath (Join-Path $tempRoot $sourceRel) -Value "source-v2" -NoNewline
        $status = Get-ShimProvenanceStatus -Root $tempRoot
        if ($status.Ok -or $status.State -ne "stale") {
            throw "mutating efk_shim.cpp must make the check red, got '$($status.State)'"
        }
        if ($status.Message -notlike "*$buildCommand*") {
            throw "stale failure did not name the rebuild command"
        }

        $hashV2 = (Get-FileHash -LiteralPath (Join-Path $tempRoot $sourceRel) -Algorithm SHA256).Hash
        Write-TestProvenance -Root $tempRoot -Hash $hashV2
        $status = Get-ShimProvenanceStatus -Root $tempRoot
        if (-not $status.Ok -or $status.State -ne "current") {
            throw "rewritten provenance should restore green, got '$($status.State)': $($status.Message)"
        }

        Remove-Item -LiteralPath (Join-Path $tempRoot $provenanceRel) -Force
        $status = Get-ShimProvenanceStatus -Root $tempRoot
        if ($status.Ok -or $status.State -ne "unprovenanced") {
            throw "present DLL without provenance must fail, got '$($status.State)'"
        }

        Write-Host "SHIM PROVENANCE SELFTEST OK"
    } finally {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if ($SelfTest) {
    Invoke-SelfTest
    exit 0
}

$status = Get-ShimProvenanceStatus -Root $RepoRoot
Write-Host $status.Message
if (-not $status.Ok) {
    exit 1
}
exit 0
