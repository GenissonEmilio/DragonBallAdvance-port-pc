param([string]$Rom = '', [int]$Jobs = 2)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run tools/setup_native.ps1 first' }
if (-not $Rom) { $Rom = Join-Path $projectRoot 'baserom.gba' }
$romPath = (Resolve-Path -LiteralPath $Rom).Path
& $python -X utf8 (Join-Path $projectRoot 'tools/generate_native_game.py') --rom $romPath
if ($LASTEXITCODE -ne 0) { throw 'Native source generation failed' }
& $python -X utf8 (Join-Path $projectRoot 'tools/build_native_game.py') --rom $romPath --jobs $Jobs
if ($LASTEXITCODE -ne 0) { throw 'Native Windows compilation failed' }
Write-Output ('Executable: ' + (Join-Path $projectRoot 'build/windows_native/bin/dbaa_game.exe'))
