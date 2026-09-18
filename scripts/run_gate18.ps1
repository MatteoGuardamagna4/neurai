# Decision gate 18 (PLAN.md S8): the one-year pilot and its controls, then the gate table.
#
#   powershell -ExecutionPolicy Bypass -File scripts/run_gate18.ps1
#
# Runs one after another, each resumable under its own tag. The first v_* pilot tags (2026-09-18 20:03) predate the
# year-0 baseline rows and are superseded by these g18_* tags; they are kept, not deleted. The break-length runs use
# only the central draw (-1, every parameter at medium) with the pilot's population (same --learners), so their
# retention differs from g18_pilot's only through the break (the G4 dose-response).
$ErrorActionPreference = "Continue"  # uv writes warnings to stderr; failures are caught by exit code
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$uv = (Get-Command uv).Source
$log = Join-Path $root "outputs/logs/gate18_runs.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null

$runs = @(
    @("--tag", "g18_pilot", "--years", "1", "--draws", "50", "--learners", "1000"),
    @("--tag", "g18_z0", "--years", "1", "--draws", "20", "--learners", "500", "--zero-plasticity"),
    @("--tag", "g18_e0", "--years", "1", "--draws", "20", "--learners", "500", "--zero-effort"),
    @("--tag", "g18_crn", "--years", "1", "--draws", "20", "--learners", "500", "--set",
      "phase5.scenarios.traditional_copy={protocol: traditional, policy: persistent}"),
    @("--tag", "g18_break4", "--years", "1", "--draws", "0", "--learners", "1000", "--set", "calendar.break_weeks=4"),
    @("--tag", "g18_break24", "--years", "1", "--draws", "0", "--learners", "1000", "--set", "calendar.break_weeks=24")
)
foreach ($r in $runs) {
    $args_ = @("run", "python", "-m", "neurotutorsim.longitudinal") + $r
    if (Test-Path (Join-Path $root "data/processed/phase5/$($r[1])/run.json")) { $args_ += "--resume" }
    $started = Get-Date
    # the call operator quotes arguments that contain spaces (Start-Process does not, which breaks --set values)
    & $uv @args_ *> "$log.$($r[1]).out"
    $code = $LASTEXITCODE
    Add-Content $log ("{0} {1}: exit {2} in {3:N0} s" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $r[1], $code, ((Get-Date) - $started).TotalSeconds)
    if ($code -ne 0) { throw "run $($r[1]) failed; see $log.$($r[1]).out" }
}
& $uv run python -m neurotutorsim.report gate18 --pilot g18_pilot --zero-plasticity g18_z0 --zero-effort g18_e0 `
    --crn g18_crn --breaks 4=g18_break4 12=g18_pilot 24=g18_break24 *>> "$log.report"
Add-Content $log ("{0} gate18 table written: outputs/tables/gate18_checks.csv" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
