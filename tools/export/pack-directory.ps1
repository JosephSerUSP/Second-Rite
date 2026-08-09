<# Packages a distributable directory without including its parent folder. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SourceDir,
    [Parameter(Mandatory = $true)][string]$ZipPath
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $SourceDir)) { throw "Directory is missing: $SourceDir" }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ZipPath) | Out-Null
Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $SourceDir "*") -DestinationPath $ZipPath -CompressionLevel Optimal
