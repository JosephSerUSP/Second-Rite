<#
.SYNOPSIS
    Second Rite - Unidentified Equipment & Curse Risk Playable Gauntlet Launcher
.DESCRIPTION
    One-touch interactive launcher for playing, testing, rating, and evaluating
    the 3 gauntlet candidate slices for Unidentified Equipment and Curse mechanics.
#>

[CmdletBinding()]
param(
    [string]$Candidate = "",
    [switch]$Rate,
    [switch]$RevealCritics,
    [switch]$Validate
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Header {
    Clear-Host
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "         SECOND RITE - PLAYABLE GAUNTLET: UNIDENTIFIED GEAR & CURSE RISK       " -ForegroundColor Yellow
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host " CORE DESIGN QUESTION:" -ForegroundColor White
    Write-Host " 'Is experimenting with unidentified equipment fun when the player may equip it" -ForegroundColor Gray
    Write-Host "  without identifying it, infer some effects from stat previews, while traits" -ForegroundColor Gray
    Write-Host "  remain unknown and CURSE creates real risk?'" -ForegroundColor Gray
    Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "  Candidate 1: High-Roller's Ruin (+32 ATK brute power vs 10% HP round bleed)" -ForegroundColor White
    Write-Host "  Candidate 2: Alchemical Spire (+8 ASP action-plus ring, freeze wand, vuln conduit)" -ForegroundColor White
    Write-Host "  Candidate 3: Purifier's Crucible (corrupted demon gear -> Sacred Font transfigure)" -ForegroundColor White
    Write-Host "================================================================================" -ForegroundColor Cyan
}

function Launch-Candidate([string]$CandidateName) {
    $projectPath = Join-Path $RepoRoot "projects\experiments\gauntlet-unidentified-gear\$CandidateName"
    Write-Host "`n>>> Staging and launching $CandidateName..." -ForegroundColor Green
    Write-Host "    Project: $projectPath" -ForegroundColor DarkGray
    Write-Host "    Press Ctrl+C or close the game window when done playing.`n" -ForegroundColor DarkGray
    
    node "$RepoRoot\tools\editor\project-cli.js" play $projectPath
}

if ($Validate) {
    node "$RepoRoot\tools\gauntlet\validate-candidates.js"
    exit 0
}

if ($RevealCritics) {
    node "$RepoRoot\tools\gauntlet\reveal-critics.js"
    exit 0
}

if ($Rate) {
    node "$RepoRoot\tools\gauntlet\rate-candidates.js"
    exit 0
}

if ($Candidate -ne "") {
    switch ($Candidate.ToLower()) {
        "1" { Launch-Candidate "candidate-a"; exit 0 }
        "a" { Launch-Candidate "candidate-a"; exit 0 }
        "2" { Launch-Candidate "candidate-b"; exit 0 }
        "b" { Launch-Candidate "candidate-b"; exit 0 }
        "3" { Launch-Candidate "candidate-c"; exit 0 }
        "c" { Launch-Candidate "candidate-c"; exit 0 }
        default {
            Write-Error "Unknown candidate '$Candidate'. Choose 1 (candidate-a), 2 (candidate-b), or 3 (candidate-c)."
            exit 1
        }
    }
}

# Interactive Menu Loop
while ($true) {
    Show-Header
    Write-Host "`nAVAILABLE ACTIONS:" -ForegroundColor Yellow
    Write-Host "  [1] Play Candidate A: The High-Roller's Ruin" -ForegroundColor Green
    Write-Host "  [2] Play Candidate B: The Alchemical Spire" -ForegroundColor Green
    Write-Host "  [3] Play Candidate C: The Purifier's Crucible" -ForegroundColor Green
    Write-Host "  -------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "  [R] Rate Candidates (Record your scores & feedback)" -ForegroundColor Magenta
    Write-Host "  [C] Reveal Critics (Compare with AI Critic Jury)" -ForegroundColor Cyan
    Write-Host "  [V] Run Validations (G1 & schema checks on all slices)" -ForegroundColor Gray
    Write-Host "  [Q] Quit" -ForegroundColor Red
    Write-Host ""

    $choice = Read-Host "Select an option [1, 2, 3, R, C, V, Q]"
    
    switch ($choice.Trim().ToUpper()) {
        "1" {
            Launch-Candidate "candidate-a"
            Write-Host "`nPress Enter to return to menu..."
            [void][System.Console]::ReadLine()
        }
        "2" {
            Launch-Candidate "candidate-b"
            Write-Host "`nPress Enter to return to menu..."
            [void][System.Console]::ReadLine()
        }
        "3" {
            Launch-Candidate "candidate-c"
            Write-Host "`nPress Enter to return to menu..."
            [void][System.Console]::ReadLine()
        }
        "R" {
            node "$RepoRoot\tools\gauntlet\rate-candidates.js"
            Write-Host "`nPress Enter to return to menu..."
            [void][System.Console]::ReadLine()
        }
        "C" {
            node "$RepoRoot\tools\gauntlet\reveal-critics.js"
            Write-Host "`nPress Enter to return to menu..."
            [void][System.Console]::ReadLine()
        }
        "V" {
            node "$RepoRoot\tools\gauntlet\validate-candidates.js"
            Write-Host "`nPress Enter to return to menu..."
            [void][System.Console]::ReadLine()
        }
        "Q" {
            Write-Host "Goodbye!" -ForegroundColor Yellow
            break
        }
        default {
            Write-Host "Invalid selection. Please choose 1, 2, 3, R, C, V, or Q." -ForegroundColor Red
            Start-Sleep -Seconds 1
        }
    }
}
