$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Checked { & $args[0] @($args | Select-Object -Skip 1); if ($LASTEXITCODE -ne 0) { throw "Command failed: $args" } }
Checked git status --short --branch
Checked py -3.12 -m venv .venv
$p = Join-Path $PWD '.venv/Scripts/python.exe'
Checked $p -m pip install -c requirements-tested.txt -e '.[dev]'
Checked $p -m ruff check .
Checked $p -m mypy src
Checked $p -m pytest -q --cov=quantforge
$out = Join-Path 'runs' ([guid]::NewGuid().ToString())
Checked $p -m quantforge.cli backtest examples/golden.csv $out --strategy buy-hold --capital 100 --units 4 --fixed 1
$row = Import-Csv (Join-Path $out 'equity.csv') | Select-Object -Last 1
if ([double]$row.equity -ne 95) { throw 'Smoke result mismatch' }
Checked git status --short --branch
