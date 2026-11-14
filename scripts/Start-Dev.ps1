param([ValidateSet('training','admin')][string]$Area='training')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:TROF_ENV='development'
$env:TROF_DATABASE=Join-Path (Get-Location) '.runtime\development\identity.sqlite3'
$port=8080
if ($Area -eq 'admin') { $port=8081 }
& .\.venv\Scripts\python.exe -m trofollos.app serve --area $Area --port $port
