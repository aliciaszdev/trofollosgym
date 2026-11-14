Get-Service -Name TrofollosTraining,TrofollosAdmin -ErrorAction SilentlyContinue | Select-Object Name,Status,StartType
foreach ($port in @(8080,8081)) {
    try { Invoke-RestMethod -Uri "http://127.0.0.1:$port/health" -TimeoutSec 3 }
    catch { Write-Warning "Puerto $port sin respuesta" }
}
