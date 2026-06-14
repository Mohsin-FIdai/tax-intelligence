$ErrorActionPreference = 'Stop'
$InstallDir = 'C:\Users\Mohsin\.gemini\antigravity\scratch\tax-intelligence\python_env'
if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir | Out-Null }
cd $InstallDir

Write-Host 'Downloading Python...'
Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile 'python.zip'
Write-Host 'Extracting Python...'
Expand-Archive -Path 'python.zip' -DestinationPath '.' -Force

Write-Host 'Configuring Python for pip...'
$pthPath = 'python311._pth'
$pthContent = Get-Content $pthPath
$pthContent = $pthContent -replace '#import site', 'import site'
Set-Content -Path $pthPath -Value $pthContent

Write-Host 'Downloading get-pip.py...'
Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'

Write-Host 'Installing pip...'
.\python.exe get-pip.py

Write-Host 'Python environment setup complete!'
.\python.exe -m pip --version
