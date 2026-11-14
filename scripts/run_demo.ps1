# Run the offensive scan and write an English report. Windows PowerShell.
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $PSScriptRoot
Set-Location $here

if (-not (Test-Path "venv-ciberseguridad")) {
    python -m venv --prompt venv-ciberseguridad venv-ciberseguridad
}
. .\venv-ciberseguridad\Scripts\Activate.ps1

python -m pip install --upgrade pip | Out-Null
python -m pip install -e . | Out-Null

python -m agentbreak.cli scan --report --no-journal @args
