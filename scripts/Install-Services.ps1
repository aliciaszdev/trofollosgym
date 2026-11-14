param(
    [Parameter(Mandatory=$true)][string]$WinSW,
    [Parameter(Mandatory=$true)][string]$DataDirectory,
    [Parameter(Mandatory=$true)][string]$TrainingUrl,
    [Parameter(Mandatory=$true)][string]$AdminUrl
)
# Ejecutar como administrador. Requiere WinSW 2.x x64 oficial, instalado por el operador.
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Split-Path $PSScriptRoot -Parent)).Path
$wrapper=(Resolve-Path -LiteralPath $WinSW).Path
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Ejecuta PowerShell como administrador para instalar servicios y sus ACL.' }
if ($TrainingUrl -notmatch '^https://' -or $AdminUrl -notmatch '^https://') { throw 'Producción requiere direcciones HTTPS.' }
if (-not [IO.Path]::IsPathRooted($DataDirectory)) { throw 'Usa una ruta absoluta persistente fuera del código y de OneDrive.' }
$data=[IO.Path]::GetFullPath($DataDirectory)
if ($data.StartsWith($root,[StringComparison]::OrdinalIgnoreCase) -or $data -match '(?i)OneDrive|\\Temp\\') { throw 'Los datos de producción deben estar fuera del código, OneDrive y Temp.' }
New-Item -ItemType Directory -Force -Path $data | Out-Null
# LocalService: sin privilegios administrativos. Administradores/SYSTEM mantienen gestión y recuperación.
& icacls.exe $data /inheritance:r /grant:r '*S-1-5-19:(OI)(CI)M' '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron restringir los datos' }
$escape = { param($value) [Security.SecurityElement]::Escape($value) }
foreach ($item in @(@('Training','training',8080),@('Admin','admin',8081))) {
    $id='Trofollos'+$item[0]
    $exe=Join-Path $data ($id+'.exe')
    if (Get-Service -Name $id -ErrorAction SilentlyContinue) { throw "$id ya existe. No se sobrescribirá: consulta la guía de actualización." }
    Copy-Item -LiteralPath $wrapper -Destination $exe
    $python=& $escape (Join-Path $root '.venv\Scripts\python.exe')
    $work=& $escape $root
    $database=& $escape (Join-Path $data 'identity.sqlite3')
    $train=& $escape $TrainingUrl
    $admin=& $escape $AdminUrl
    $xml=@"
<service>
  <id>$id</id><name>$id</name><description>TrofollosGym $($item[1])</description>
  <executable>$python</executable><arguments>-m trofollos.app serve --area $($item[1]) --port $($item[2])</arguments>
  <workingdirectory>$work</workingdirectory><startmode>Automatic</startmode>
  <serviceaccount><username>NT AUTHORITY\LocalService</username></serviceaccount>
  <env name="TROF_ENV" value="production"/><env name="TROF_DATABASE" value="$database"/>
  <env name="TROF_TRAINING_URL" value="$train"/><env name="TROF_ADMIN_URL" value="$admin"/>
  <log mode="roll-by-size"><sizeThreshold>1024</sizeThreshold><keepFiles>5</keepFiles></log>
  <onfailure action="restart" delay="10 sec"/>
</service>
"@
    $xml | Set-Content -Encoding UTF8 (Join-Path $data ($id+'.xml'))
    & $exe install
    if ($LASTEXITCODE -ne 0) { throw "Error instalando $id" }
}
Write-Host 'Servicios instalados y no iniciados. Concede lectura/ejecución a LocalService sobre Python y el código; configura HTTPS y crea el primer TOP en producción antes de arrancarlos. Consulta docs/OPERACION.md.'
