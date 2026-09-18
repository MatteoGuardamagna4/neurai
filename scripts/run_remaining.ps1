# The Phase V runs that do not depend on Centaur (PLAN.md S9, S11, S12, S13), one after another, each resumable.
#
#   powershell -ExecutionPolicy Bypass -File scripts/run_remaining.ps1 [-WaitForPid N] [-SkipSpecCurve]
#
# Every run names the five v_main scenarios explicitly: the config also lists free_choice_centaur, whose rule is
# refitted after centaur_free_calib (scripts/run_centaur_rule.ps1), and these runs must not pick up the interim fit.
# The spec curve goes last because it is the longest (~1.5-2 h) and the first thing to cut if time runs short.
param([int]$WaitForPid = 0, [switch]$SkipSpecCurve)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$uv = (Get-Command uv).Source
$log = Join-Path $root "outputs/logs/remaining_runs.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
function Log([string]$msg) { Add-Content $log ("{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg) }
if ($WaitForPid) {
    Log "waiting for pid $WaitForPid"
    Wait-Process -Id $WaitForPid -ErrorAction SilentlyContinue
}
$scen = @("--scenarios", "traditional", "scaffolding_rapid", "scaffolding_nofade", "substitution", "free_choice")
$y10 = @("--years", "10")
$runs = @(
    # S12 controls at 10 years (Table 6, F4)
    @("--tag", "v_z0_10y", "--draws", "50", "--learners", "500", "--zero-plasticity"),
    @("--tag", "v_e0_10y", "--draws", "50", "--learners", "500", "--zero-effort"),
    @("--tag", "v_uniform", "--draws", "50", "--learners", "500", "--distribution", "uniform"),
    # S11 mechanism decomposition
    @("--tag", "v_mediation", "--draws", "50", "--learners", "500", "--mediate", "E,F,D"),
    # S13 replicates: same parameters and learners, new behaviour stream (--seed-offset)
    @("--tag", "v_repl0", "--draws", "50", "--learners", "200"),
    @("--tag", "v_repl1", "--draws", "50", "--learners", "200", "--seed-offset", "1"),
    @("--tag", "v_repl2", "--draws", "50", "--learners", "200", "--seed-offset", "2"),
    # S9 exposure
    @("--tag", "v_epw1", "--draws", "200", "--learners", "1000", "--epw", "1"),
    @("--tag", "v_epw5", "--draws", "200", "--learners", "1000", "--epw", "5")
)
foreach ($r in $runs) {
    $args_ = @("run", "python", "-m", "neurotutorsim.longitudinal") + $r + $y10 + $scen
    if (Test-Path (Join-Path $root "data/processed/phase5/$($r[1])/run.json")) { $args_ += "--resume" }
    $started = Get-Date
    & $uv @args_ *> (Join-Path $root "outputs/logs/remaining_$($r[1]).out")
    Log ("{0}: exit {1} in {2:N0} min" -f $r[1], $LASTEXITCODE, ((Get-Date) - $started).TotalMinutes)
}
if (-not $SkipSpecCurve) {
    $started = Get-Date
    & $uv run python scripts/run_spec_curve.py --scenarios $scen[1..($scen.Count - 1)] *> (Join-Path $root "outputs/logs/remaining_spec_curve.out")
    Log ("spec curve (72 runs): exit {0} in {1:N0} min" -f $LASTEXITCODE, ((Get-Date) - $started).TotalMinutes)
}
Log "done"
