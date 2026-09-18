# Run centaur_main to completion, restarting it after server failures (PLAN.md S3).
#
#   powershell -ExecutionPolicy Bypass -File scripts/centaur_loop.ps1 -Remote   # models on Colab (serve_models.ipynb)
#   powershell -ExecutionPolicy Bypass -File scripts/centaur_loop.ps1           # models in the laptop's LM Studio
#
# -Remote: simulate.py gets --remote and reads NEUROTUTOR_SERVER_URL / _TOKEN from .env at every start, so when the
# Colab session is restarted, pasting its two new lines into .env is enough: this loop retries every
# $RetrySeconds until the server answers again. Local: LM Studio is reloaded before each start. Diagnosed
# 2026-09-18: the local slowdown is RAM exhaustion (both models ~9 GB of shared GPU memory, hard faults up to
# 61k/s), which a reload does not cure, so this loop no longer restarts on slowness; it only logs the speed.
# Nothing is lost on a restart: the run is append-only and resumes from episodes.jsonl (the in-flight episode is
# redone). The run flags are fixed on purpose: simulate.py refuses a resume with other --learners/--episodes.
param(
    [switch]$Remote,
    [string]$Tag = "centaur_main",
    [int]$Learners = 40,
    [int]$Episodes = 30,
    [string]$Conditions = "",   # comma list, e.g. "free_choice"; empty = the config's four arms
    [int]$RetrySeconds = 120,
    [int]$MaxRounds = 200,
    [int]$Ttl = 604800   # local only: a week, since LM Studio's default 1 h idle TTL has unloaded a model mid-run
)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
# PowerShell names are case-insensitive: $Episodes (the param) and a path variable must not share a name
$callsPath = Join-Path $root "outputs/logs/$Tag/calls_centaur.jsonl"
$episodesPath = Join-Path $root "data/processed/$Tag/episodes.jsonl"
$logPath = Join-Path $root "outputs/logs/$Tag/loop.log"
New-Item -ItemType Directory -Force (Split-Path $logPath) | Out-Null
$armList = if ($Conditions) { $Conditions.Split(",") | ForEach-Object { $_.Trim() } } else { @() }
$nArms = if ($armList.Count) { $armList.Count } else { 4 }
$uv = (Get-Command uv -ErrorAction Stop).Source

function Log([string]$msg) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $logPath -Value $line -Encoding utf8
}
function LineCount([string]$path) {
    if (Test-Path $path) { return [System.IO.File]::ReadAllLines($path).Count } else { return 0 }
}
function MedianSeconds([string]$path, [int]$n) {
    $secs = @(Get-Content $path -Tail $n | ForEach-Object { [double](($_ | ConvertFrom-Json).seconds) }) | Sort-Object
    if ($secs.Count -eq 0) { return 0 }
    return $secs[[math]::Floor($secs.Count / 2)]
}

$mode = if ($Remote) { "remote (Colab)" } else { "local (LM Studio)" }
Log "loop started: $mode, tag $Tag"
# never run two simulate processes on one tag: both would append to the same episodes.jsonl
$pattern = "neurotutorsim\.simulate.*--tag $Tag(\s|$)"
$existing = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match $pattern })
if ($existing.Count) {
    Log "waiting for the simulate already running on $Tag (pids $($existing.ProcessId -join ', ')) to exit"
    $existing | ForEach-Object { Wait-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
}
$finished = $false
for ($round = 1; $round -le $MaxRounds; $round++) {
    if (-not $Remote) {
        Log "round ${round}: reloading LM Studio"
        lms unload --all | Out-Null
        lms load llama-3.1-centaur-8b --context-length 8192 --parallel 1 --ttl $Ttl -y | Out-Null
        if ($LASTEXITCODE -ne 0) { Log "lms load centaur failed ($LASTEXITCODE)"; Start-Sleep $RetrySeconds; continue }
        lms load qwen2.5-3b-instruct --parallel 1 --ttl $Ttl -y | Out-Null
        if ($LASTEXITCODE -ne 0) { Log "lms load qwen failed ($LASTEXITCODE)"; Start-Sleep $RetrySeconds; continue }
    }
    $simArgs = @("run", "python", "-m", "neurotutorsim.simulate", "--learners", $Learners, "--episodes", $Episodes,
                 "--tag", $Tag, "--resume")
    if ($Remote) { $simArgs += "--remote" }
    if ($armList.Count) { $simArgs += @("--conditions") + $armList }
    $out = Join-Path $root "outputs/logs/$Tag/run_console_$round.log"
    $err = Join-Path $root "outputs/logs/$Tag/run_console_$round.err"
    $startedAt = Get-Date
    $p = Start-Process -FilePath $uv -ArgumentList $simArgs -WorkingDirectory $root -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError $err
    $null = $p.Handle  # without a cached handle, ExitCode stays empty after the process exits (measured 2026-09-18)
    Log "round ${round}: simulate started (pid $($p.Id)), episodes done $(LineCount $episodesPath) of $($Learners * $Episodes * $nArms)"
    while (-not $p.HasExited) {
        Start-Sleep -Seconds 300
        if (-not $p.HasExited) {
            Log ("progress: episodes {0}, median of the last 30 Centaur calls {1:N1} s" -f (LineCount $episodesPath), (MedianSeconds $callsPath 30))
        }
    }
    $p.WaitForExit()
    $code = $p.ExitCode
    $minutes = ((Get-Date) - $startedAt).TotalMinutes
    Log ("round {0}: simulate exited with code {1} after {2:N0} min, episodes done {3}" -f $round, $code, $minutes, (LineCount $episodesPath))
    if ($code -eq 0) { Log "FINISHED"; $finished = $true; break }
    $tail = (Get-Content $err -Tail 3 -ErrorAction SilentlyContinue) -join " | "
    Log "last error lines: $tail"
    if ($code -ne 1) { Log "exit code $code means the run refused to start (see above); stopping"; break }
    Log "retrying in $RetrySeconds s (remote: update .env if the Colab URL changed)"
    Start-Sleep -Seconds $RetrySeconds
}
Log "loop ended"
if ($finished) { exit 0 } else { exit 1 }
