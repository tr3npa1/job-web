param([ValidateSet('start', 'stop')][string]$Action = 'start')
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$runtime = Join-Path $project '.local'
$stateFile = Join-Path $runtime 'processes.json'
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$vite = Join-Path $project 'frontend/node_modules/vite/bin/vite.js'

function Stop-ManagedProcesses {
    if (-not (Test-Path -LiteralPath $stateFile)) { return }
    $records = Get-Content -Raw -LiteralPath $stateFile | ConvertFrom-Json
    foreach ($record in $records) {
        $process = Get-Process -Id $record.Id -ErrorAction SilentlyContinue
        $identity = Get-CimInstance Win32_Process -Filter "ProcessId=$($record.Id)" -ErrorAction SilentlyContinue
        if ($process -and $identity.ExecutablePath -eq $record.Path -and
            [string]$process.StartTime.ToUniversalTime().Ticks -eq $record.StartTicks) {
            # Python's virtual-environment launcher can own a child interpreter.
            & taskkill.exe /PID $process.Id /T /F | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Could not stop $($record.Name)." }
        }
    }
    Remove-Item -LiteralPath $stateFile
}

if ($Action -eq 'stop') {
    Stop-ManagedProcesses
    Write-Host 'Stopped managed application processes. XAMPP is unchanged.'
    exit
}

if (Test-Path -LiteralPath $stateFile) {
    throw 'Process state already exists. Run local.ps1 stop before starting again.'
}
foreach ($file in @($python, $vite, (Join-Path $PSScriptRoot '.env'))) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Missing $file. Follow docs/SETUP.md first." }
}
$node = (Get-Command node.exe -ErrorAction Stop).Source
foreach ($port in @(5000, 5173)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is occupied. This launcher will not stop an existing server."
    }
}
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$records = @()
function Start-ManagedProcess($name, $executable, $arguments, $directory) {
    $process = Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $directory -WindowStyle Hidden -PassThru -RedirectStandardOutput "$runtime/$name.log" -RedirectStandardError "$runtime/$name-error.log"
    $process = Get-Process -Id $process.Id
    $script:records += @{Name=$name; Id=$process.Id; Path=[IO.Path]::GetFullPath($executable); StartTicks=[string]$process.StartTime.ToUniversalTime().Ticks}
    ConvertTo-Json -InputObject @($script:records) | Set-Content -LiteralPath $stateFile
}
try {
    Start-ManagedProcess 'flask' $python ('"{0}"' -f (Join-Path $PSScriptRoot 'app.py')) $PSScriptRoot
    Start-ManagedProcess 'vite' $node ('"{0}" --host 127.0.0.1' -f $vite) (Join-Path $project 'frontend')
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:5173/api/health' -TimeoutSec 2
            if ($health.database -eq 'connected') {
                Write-Host 'job-web: http://127.0.0.1:5173'
                Write-Host 'Stop with: powershell -File backend/local.ps1 stop'
                exit
            }
        } catch { Start-Sleep -Milliseconds 300 }
    }
    throw 'Startup failed. Check XAMPP, backend/.env and the project .local logs.'
} catch {
    Stop-ManagedProcesses
    throw
}
