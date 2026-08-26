$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $appDir

$repoBase = "https://raw.githubusercontent.com/Ashizawa-s/-/main"
$updateDir = Join-Path $appDir ".update"
New-Item -ItemType Directory -Path $updateDir -Force | Out-Null

function Download-Safely([string]$name) {
    $tempPath = Join-Path $updateDir ($name + ".new")
    try {
        Invoke-WebRequest -Uri "$repoBase/$name" -OutFile $tempPath -TimeoutSec 30
        if ((Get-Item -LiteralPath $tempPath).Length -lt 20) { throw "Downloaded file is empty" }
        $destination = Join-Path $appDir $name
        if ($name -eq "main.py" -and (Test-Path -LiteralPath $destination)) {
            Copy-Item -LiteralPath $destination -Destination (Join-Path $updateDir "main.py.lastgood") -Force
        }
        Move-Item -LiteralPath $tempPath -Destination $destination -Force
    } catch {
        Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
        if (-not (Test-Path -LiteralPath (Join-Path $appDir $name))) { throw }
    }
}

Download-Safely "main.py"
Download-Safely "requirements.txt"

$venvPython = Join-Path $appDir ".venv\Scripts\python.exe"
$venvPythonw = Join-Path $appDir ".venv\Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    $basePython = $null
    if (Get-Command py -ErrorAction SilentlyContinue) { $basePython = "py" }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $basePython = "python" }
    if (-not $basePython) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show("Python 3が見つかりません。最初にPythonをインストールしてください。", "文字起こしシステム") | Out-Null
        exit 1
    }
    & $basePython -m venv (Join-Path $appDir ".venv")
    & $venvPython -m pip install --upgrade pip
}

$requirementsMarker = Join-Path $updateDir "requirements.sha256"
$requirementsHash = (Get-FileHash -LiteralPath (Join-Path $appDir "requirements.txt") -Algorithm SHA256).Hash
$installedHash = if (Test-Path -LiteralPath $requirementsMarker) { Get-Content -LiteralPath $requirementsMarker -Raw } else { "" }
if ($requirementsHash -ne $installedHash.Trim()) {
    & $venvPython -m pip install -r (Join-Path $appDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
    Set-Content -LiteralPath $requirementsMarker -Value $requirementsHash -Encoding ascii
}

& $venvPython -m py_compile (Join-Path $appDir "main.py")
if ($LASTEXITCODE -ne 0) {
    $lastGood = Join-Path $updateDir "main.py.lastgood"
    if (Test-Path -LiteralPath $lastGood) {
        Copy-Item -LiteralPath $lastGood -Destination (Join-Path $appDir "main.py") -Force
    } else {
        throw "main.py validation failed"
    }
}

Start-Process -FilePath $venvPythonw -ArgumentList 'main.py' -WorkingDirectory $appDir -WindowStyle Hidden

for ($i = 0; $i -lt 600; $i++) {
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -TimeoutSec 2 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Start-Process "http://127.0.0.1:8000/"
            exit 0
        }
    } catch { }
}

Add-Type -AssemblyName PresentationFramework
[System.Windows.MessageBox]::Show("起動に時間がかかりすぎています。PCを再起動してからお試しください。", "文字起こしシステム") | Out-Null

