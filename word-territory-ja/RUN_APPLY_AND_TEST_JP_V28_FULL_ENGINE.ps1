$ErrorActionPreference = "Stop"

# v28 FULL ENGINE: clean v18 backend physical replacement + v28 dictionary guard
$repo = "$env:USERPROFILE\Downloads\word-territory-new\word-territory"
$src  = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== JP v28 FULL ENGINE RELEASE ===" -ForegroundColor Cyan
Write-Host "source: $src"
Write-Host "repo:   $repo"

if (!(Test-Path "$repo\backend")) { throw "repo backend not found: $repo\backend" }
if (!(Test-Path "$src\backend\engine.py")) { throw "source engine.py not found: $src\backend\engine.py" }
if (!(Test-Path "$src\scorecard.py")) { throw "source scorecard.py not found: $src\scorecard.py" }

# 1) Validate source engine before copying
Set-Location "$src"
py validate_v28_full_engine.py
py validate_jp_v28_dictionary.py

# 2) Show current repo contamination state
Write-Host "=== BEFORE: repo engine signature ===" -ForegroundColor Yellow
Set-Location "$repo\backend"
py -c "s=open('engine.py',encoding='utf-8').read(); print('repo contaminated =', ('-14.0' in s or '_JP_V26_BANNED_WORDS' in s)); print('repo seed refs =', s.count('seed')); print('repo punitive -14 =', s.count('-14.0')); print('repo v26 banned refs =', s.count('_JP_V26_BANNED_WORDS'))"

# 3) Backup existing backend engine and core files
$backup = "$repo\backend_BACKUP_BEFORE_V28_FULL_ENGINE"
if (Test-Path $backup) { Remove-Item $backup -Recurse -Force }
New-Item -ItemType Directory $backup | Out-Null
Copy-Item "$repo\backend\engine.py" "$backup\engine.py" -Force -ErrorAction SilentlyContinue
Copy-Item "$repo\backend\dictionary.py" "$backup\dictionary.py" -Force -ErrorAction SilentlyContinue
Copy-Item "$repo\backend\bot_match_test_ja.py" "$backup\bot_match_test_ja.py" -Force -ErrorAction SilentlyContinue

# 4) Physical replacement: backend files, including engine.py
Copy-Item "$src\backend\*" "$repo\backend\" -Recurse -Force
Copy-Item "$src\scorecard.py" "$repo\scorecard.py" -Force
Copy-Item "$src\validate_jp_v28_results_strict.py" "$repo\validate_jp_v28_results_strict.py" -Force

# 5) Verify repo engine after copy
Write-Host "=== AFTER: repo engine signature ===" -ForegroundColor Yellow
Set-Location "$repo\backend"
py -c "s=open('engine.py',encoding='utf-8').read(); import sys; bad=('-14.0' in s or '_JP_V26_BANNED_WORDS' in s); print('repo contaminated =', bad); print('repo seed refs =', s.count('seed')); print('repo punitive -14 =', s.count('-14.0')); print('repo v26 banned refs =', s.count('_JP_V26_BANNED_WORDS')); print('marker =', 'JP_V28_FULL_ENGINE_CLEAN_V18_RELEASE' in s); sys.exit(1 if bad else 0)"

# 6) Clean cache and compile
Remove-Item __pycache__ -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem . -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
$env:WT_LANG = "ja"
py -m py_compile engine.py dictionary.py models.py main.py spectator_seed.py bot_match_test_ja.py

# 7) Dictionary check in repo runtime
py -c "import os; os.environ['WT_LANG']='ja'; import dictionary; w=set(dictionary.get_words()); banned=['やか','くもの','くりから','やさいか','うみか']; kept=['やきもの','よみもの','のみもの','たべもの','かきもの','うみかぜ','うみかつき','うみからまつ','うみかわ','うみかわうそ']; print('banned:', [(x, x in w) for x in banned]); print('kept:', [(x, x in w) for x in kept])"

# 8) Remove old result files
Remove-Item bot_match_results_ja_v28_full_engine.csv -ErrorAction SilentlyContinue
Remove-Item bot_match_results_ja_v28_full_engine.json -ErrorAction SilentlyContinue
Remove-Item bot_match_summary_ja_v28_full_engine.csv -ErrorAction SilentlyContinue
Remove-Item bot_match_results_ja_v28_full_engine_FAILED.csv -ErrorAction SilentlyContinue
Remove-Item bot_match_results_ja_v28_full_engine_FAILED.json -ErrorAction SilentlyContinue
Remove-Item bot_match_summary_ja_v28_full_engine_FAILED.csv -ErrorAction SilentlyContinue

# 9) Run 90-game validation
py bot_match_test_ja.py --games 90 --mode normal --bot-level normal --force-synergy active3 --csv bot_match_results_ja_v28_full_engine.csv --json bot_match_results_ja_v28_full_engine.json --summary-csv bot_match_summary_ja_v28_full_engine.csv

# 10) Scorecard and strict validation
Set-Location "$repo"
py scorecard.py backend\bot_match_results_ja_v28_full_engine.csv

$strictOK = $true
try {
  py validate_jp_v28_results_strict.py backend\bot_match_results_ja_v28_full_engine.csv
} catch {
  $strictOK = $false
}

if (-not $strictOK) {
  Write-Host "STRICT VALIDATION FAILED. Renaming outputs to *_FAILED.*" -ForegroundColor Red
  Set-Location "$repo\backend"
  if (Test-Path bot_match_results_ja_v28_full_engine.csv) { Rename-Item bot_match_results_ja_v28_full_engine.csv bot_match_results_ja_v28_full_engine_FAILED.csv -Force }
  if (Test-Path bot_match_results_ja_v28_full_engine.json) { Rename-Item bot_match_results_ja_v28_full_engine.json bot_match_results_ja_v28_full_engine_FAILED.json -Force }
  if (Test-Path bot_match_summary_ja_v28_full_engine.csv) { Rename-Item bot_match_summary_ja_v28_full_engine.csv bot_match_summary_ja_v28_full_engine_FAILED.csv -Force }
  throw "v28 FULL ENGINE strict validation failed. Upload the *_FAILED files only for diagnosis."
}

Write-Host "" 
Write-Host "SUCCESS: JP v28 FULL ENGINE clean run complete." -ForegroundColor Green
Write-Host "Upload these files:" -ForegroundColor Cyan
Write-Host "$repo\backend\bot_match_results_ja_v28_full_engine.csv"
Write-Host "$repo\backend\bot_match_summary_ja_v28_full_engine.csv"
Write-Host "$repo\backend\bot_match_results_ja_v28_full_engine.json"
