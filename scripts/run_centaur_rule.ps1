# After centaur_free_calib (PLAN.md D18): validate the rule fitted on centaur_main out of sample, refit it on both
# runs, then run the sixth Phase V scenario (free_choice_centaur) next to its traditional comparator.
#
#   powershell -ExecutionPolicy Bypass -File scripts/run_centaur_rule.ps1 [-WaitForPid N]
#
# -WaitForPid: the Centaur chain (outputs/logs/centaur_main.pid). The script refuses to go on unless the calibration
# batch has all its episodes. v_main_fcc uses v_main's seed, draws and learners, so its traditional arm is v_main's.
param([int]$WaitForPid = 0, [int]$Expected = 4800)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$uv = (Get-Command uv).Source
$log = Join-Path $root "outputs/logs/centaur_rule.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
function Log([string]$msg) { Add-Content $log ("{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg) }
if ($WaitForPid) {
    Log "waiting for pid $WaitForPid"
    Wait-Process -Id $WaitForPid -ErrorAction SilentlyContinue
}
$calib = Join-Path $root "data/processed/centaur_free_calib/episodes.jsonl"
$n = if (Test-Path $calib) { (Get-Content $calib | Measure-Object -Line).Lines } else { 0 }
if ($n -lt $Expected) { Log "centaur_free_calib has $n / $Expected episodes: stopping"; exit 1 }

$dir = Join-Path $root "data/processed/choice_rule"
$rule = Join-Path $dir "choice_rule.json"
$first = Join-Path $dir "choice_rule_centaur_main.json"
if (-not (Test-Path $first)) { Copy-Item $rule $first }   # keep the centaur_main-only fit that is validated
& $uv run python -m neurotutorsim.choice_rule validate --rule $first --runs data/processed/centaur_free_calib *> (Join-Path $root "outputs/logs/centaur_rule_validate.out")
Log "validate (centaur_main fit on centaur_free_calib): exit $LASTEXITCODE"
& $uv run python -m neurotutorsim.choice_rule fit --runs data/processed/centaur_main data/processed/centaur_free_calib *> (Join-Path $root "outputs/logs/centaur_rule_fit.out")
Log "refit on centaur_main + centaur_free_calib: exit $LASTEXITCODE"
if ($LASTEXITCODE -ne 0) { exit 1 }

$args_ = @("run", "python", "-m", "neurotutorsim.longitudinal", "--tag", "v_main_fcc", "--years", "10", "--draws", "500",
           "--learners", "2000", "--scenarios", "traditional", "free_choice_centaur")
if (Test-Path (Join-Path $root "data/processed/phase5/v_main_fcc/run.json")) { $args_ += "--resume" }
$started = Get-Date
& $uv @args_ *> (Join-Path $root "outputs/logs/centaur_rule_v_main_fcc.out")
Log ("v_main_fcc: exit {0} in {1:N0} min" -f $LASTEXITCODE, ((Get-Date) - $started).TotalMinutes)
