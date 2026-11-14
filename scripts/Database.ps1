param(
 [Parameter(Mandatory=$true)][ValidateSet('backup','restore')][string]$Action,
 [Parameter(Mandatory=$true)][string]$Source,
 [Parameter(Mandatory=$true)][string]$Destination,
 [string]$ConfirmRestore=''
)
$ErrorActionPreference='Stop'
$python=Join-Path (Split-Path $PSScriptRoot -Parent) '.venv\Scripts\python.exe'
# Resolver rutas antes de cambiar el directorio; los destinos deben ser nuevos.
$origin=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Source)
$target=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Destination)
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($Action -eq 'restore') {
 if ($ConfirmRestore -ne 'RESTAURAR') { throw 'Detén ambos servicios y confirma con -ConfirmRestore RESTAURAR.' }
 foreach ($name in @('TrofollosTraining','TrofollosAdmin')) {
  $service=Get-Service -Name $name -ErrorAction SilentlyContinue
  if ($service -and $service.Status -ne 'Stopped') { throw "Detén $name antes de restaurar" }
 }
}
& $python -m trofollos.database $Action --source $origin --destination $target --confirm-restore $ConfirmRestore
if ($LASTEXITCODE -ne 0) { throw 'Operación de base de datos fallida' }
