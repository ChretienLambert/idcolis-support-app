$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.idcolis-venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path $python)) { throw 'No virtual environment found. Run setup.bat first.' }
Get-CimInstance Win32_Process -Filter "Name = 'python.exe' or Name = 'pythonw.exe'" | Where-Object { $_.CommandLine -match 'backend\.serve|streamlit.*app\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath $python -ArgumentList '-m backend.serve' -WorkingDirectory $PSScriptRoot -WindowStyle Minimized
Start-Sleep -Seconds 3
Start-Process -FilePath $python -ArgumentList '-m streamlit run app.py --server.port 8501 --server.headless true' -WorkingDirectory $PSScriptRoot -WindowStyle Minimized
Start-Sleep -Seconds 5
Start-Process 'http://localhost:8501/'
Write-Host 'ID Colis is running at http://localhost:8501/'
