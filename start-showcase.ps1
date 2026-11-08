$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' }
}
& $pythonPath -c "import fastapi,uvicorn,pydantic_settings,sqlalchemy,httpx,openai,requests,rich,dotenv" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $pythonPath -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
& $pythonPath scripts/setup_showcase.py
if ($LASTEXITCODE -ne 0) { throw 'Workspace initialization failed.' }
Write-Host 'Your local lab accounts (do not share these outside your computer):'
Get-Content -LiteralPath (Join-Path $PSScriptRoot '.local/credentials.json')
try {
    $runningWorkspace = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/ops/status' -TimeoutSec 2
    if ($runningWorkspace.name -eq 'AegisMesh AI') {
        Write-Host 'AegisMesh is already running. Open http://127.0.0.1:8000'
        return
    }
} catch { }
& $pythonPath run_server.py
