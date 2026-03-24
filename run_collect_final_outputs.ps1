$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $repo ".venv\Scripts\python.exe"
$script = Join-Path $repo "collect_final_outputs.py"

& $py $script

