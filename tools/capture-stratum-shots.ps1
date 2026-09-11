param(
    [string]$StageDir = "out/stage"
)

$ErrorActionPreference = "Stop"
$lovec = "C:\Program Files\LOVE\lovec.exe"
$outDir = "out/shots"
$artifactDir = "C:\Users\josep\.gemini\antigravity\brain\4ba4a222-181c-4731-9be7-d3f745ffa175"

if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

$targets = @(
    @{ Name = "stratum3_l1_wagon_view"; MapId = 32; X = 6; Y = 2; Dir = "S" },
    @{ Name = "stratum3_l1_wagon_door"; MapId = 32; X = 6; Y = 3; Dir = "S" },
    @{ Name = "stratum3_l1_platform_column"; MapId = 32; X = 5; Y = 3; Dir = "W" },
    @{ Name = "stratum3_l1_santacruz"; MapId = 32; X = 4; Y = 19; Dir = "S" },
    @{ Name = "stratum3_l2_consolacao"; MapId = 33; X = 14; Y = 2; Dir = "S" },
    @{ Name = "stratum3_l3_se"; MapId = 34; X = 6; Y = 2; Dir = "S" },
    @{ Name = "stratum3_l4_farialima"; MapId = 35; X = 6; Y = 12; Dir = "S" },
    @{ Name = "stratum3_l5_tatuzao"; MapId = 36; X = 14; Y = 11; Dir = "S" },
    @{ Name = "stratum3_wagon_interior"; MapId = 37; X = 2; Y = 4; Dir = "N" }
)

$stageAbs = (Resolve-Path $StageDir).Path

foreach ($t in $targets) {
    Write-Host "Capturing $($t.Name)..."
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        Push-Location $stageAbs
        try {
            & $lovec $stageAbs preview-map $($t.MapId) $($t.X) $($t.Y) $($t.Dir) | Out-File -FilePath $tempFile -Encoding utf8
        } finally {
            Pop-Location
        }
        $raw = Get-Content $tempFile -Raw
        if ($raw -match 'PREVIEW BEGIN\r?\n([\s\S]*?)\r?\nPREVIEW END') {
            $json = $matches[1] | ConvertFrom-Json
            if ($json.image) {
                $bytes = [Convert]::FromBase64String($json.image)
                [IO.File]::WriteAllBytes((Join-Path $outDir "$($t.Name).png"), $bytes)
                [IO.File]::WriteAllBytes((Join-Path $artifactDir "$($t.Name).png"), $bytes)
                Write-Host "  Success: $($bytes.Length) bytes"
            } else {
                Write-Warning "No image field in JSON"
            }
        } else {
            Write-Warning "Could not find PREVIEW BEGIN/END in output"
        }
    } finally {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "All captures complete."
