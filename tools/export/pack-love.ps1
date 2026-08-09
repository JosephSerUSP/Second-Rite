<# Packs the contents (not the parent folder) of a staged runtime into a .love zip. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$StageDir,
    [Parameter(Mandatory = $true)][string]$LovePath
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath (Join-Path $StageDir "main.lua"))) {
    throw "Stage directory has no main.lua: $StageDir"
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LovePath) | Out-Null
Remove-Item -LiteralPath $LovePath -Force -ErrorAction SilentlyContinue
$zipPath = Join-Path (Split-Path -Parent $LovePath) "second-rite-export.zip"
Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $StageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Move-Item -LiteralPath $zipPath -Destination $LovePath
