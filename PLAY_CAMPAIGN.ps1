# Launch Second Gate: Pale Crossing
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " SECOND GATE: PALE CROSSING (Campaign Interpretation)" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Launching full authored campaign..." -ForegroundColor Green

& node tools/editor/project-cli.js play projects/labs/pale-crossing
