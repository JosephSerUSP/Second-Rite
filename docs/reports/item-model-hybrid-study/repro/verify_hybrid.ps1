param([switch]$SkipCompile)
$ErrorActionPreference='Continue'
$env:BLENDER_EXECUTABLE='C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$env:PYTHONUTF8='1'
$env:PATH='C:\Program Files\LOVE;'+$env:PATH
if (-not $SkipCompile) {
$watch=[System.Diagnostics.Stopwatch]::StartNew()
python tools/blender/compile_item_blends.py --project-root docs/reports/item-model-hybrid-study/source-project --check > out/work/hybrid-compile-check.txt 2>&1
$code=$LASTEXITCODE;$watch.Stop()
node tools/ci/time-step.js --record --label 'compile six hybrid studies' --ms $watch.ElapsedMilliseconds --exit $code
if ($code -ne 0) {Get-Content out/work/hybrid-compile-check.txt -Tail 14;exit $code}
}
python tools/blender/script_index.py --check
if ($LASTEXITCODE -ne 0) {exit $LASTEXITCODE}
node tools/ci/stage-project-gates.js --output out/stage-hybrid-gates > out/work/hybrid-stage.txt 2>&1
if ($LASTEXITCODE -ne 0) {Get-Content out/work/hybrid-stage.txt -Tail 10;exit $LASTEXITCODE}
$gateRoot=(Resolve-Path out/stage-hybrid-gates).Path
foreach ($gate in @(@{Script='tools/golden/check-validate.ps1';Label='G1 validate';Log='g1'},@{Script='tools/golden/check.ps1';Label='G2 battle';Log='g2'},@{Script='tools/golden/check-ui.ps1';Label='G3 UI';Log='g3'},@{Script='tools/golden/check-state.ps1';Label='G4 state';Log='g4'},@{Script='tools/ci/run-staged-unit.ps1';Label='unit hybrid tooling';Log='unit'})) {
 $watch=[System.Diagnostics.Stopwatch]::StartNew()
 powershell -NoProfile -ExecutionPolicy Bypass -File $gate.Script -GameRoot $gateRoot > "out/work/hybrid-$($gate.Log).txt" 2>&1
 $code=$LASTEXITCODE;$watch.Stop()
 node tools/ci/time-step.js --record --label $gate.Label --ms $watch.ElapsedMilliseconds --exit $code
 if ($code -ne 0) {Get-Content "out/work/hybrid-$($gate.Log).txt" -Tail 14;exit $code}
 Get-Content "out/work/hybrid-$($gate.Log).txt" -Tail 2
}
Push-Location $gateRoot
try {& 'C:\Program Files\LOVE\lovec.exe' . savetest > ../work/hybrid-save.txt 2>&1;$code=$LASTEXITCODE}
finally {Pop-Location}
Get-Content out/work/hybrid-save.txt -Tail 3
exit $code
