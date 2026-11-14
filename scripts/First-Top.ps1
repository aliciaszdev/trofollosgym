param([string]$Username='top')
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\python.exe -m trofollos.app bootstrap --username $Username
if ($LASTEXITCODE -ne 0) { throw 'No se ha podido crear el primer TOP' }
