# The robustness frontier, tipping-point lines and neural diagram (PLAN.md S10), one after another, each resumable.
#
#   powershell -ExecutionPolicy Bypass -File scripts/run_frontier.ps1 [-WaitForPid N]
#
# -WaitForPid lets the chain start after another Phase V run (e.g. v_main) so the two do not compete.
param([int]$WaitForPid = 0)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$uv = (Get-Command uv).Source
$log = Join-Path $root "outputs/logs/frontier_runs.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
if ($WaitForPid) {
    Add-Content $log ("{0} waiting for pid {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $WaitForPid)
    Wait-Process -Id $WaitForPid -ErrorAction SilentlyContinue
}
$runs = @(
    @("--tag", "v_frontier", "--frontier", "grid", "--years", "10", "--draws", "100", "--learners", "300", "--no-neural"),
    @("--tag", "v_tipping", "--frontier", "lines", "--years", "10", "--draws", "200", "--learners", "300", "--no-neural"),
    @("--tag", "v_neural", "--frontier", "neural", "--years", "10", "--draws", "100", "--learners", "300")
)
foreach ($r in $runs) {
    $args_ = @("run", "python", "-m", "neurotutorsim.longitudinal") + $r
    if (Test-Path (Join-Path $root "data/processed/phase5/$($r[1])/run.json")) { $args_ += "--resume" }
    $started = Get-Date
    & $uv @args_ *> (Join-Path $root "outputs/logs/frontier_$($r[1]).out")
    Add-Content $log ("{0} {1}: exit {2} in {3:N0} min" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $r[1], $LASTEXITCODE, ((Get-Date) - $started).TotalMinutes)
}
