$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $appDir
$errorLog = Join-Path $appDir "startup_error.txt"
Remove-Item -LiteralPath $errorLog -Force -ErrorAction SilentlyContinue
trap {
    ($_ | Out-String) | Set-Content -LiteralPath $errorLog -Encoding UTF8
    exit 1
}

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

$runtimeDir = Join-Path $env:LOCALAPPDATA "AshizawaTranscriber"
$venvDir = Join-Path $runtimeDir "venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPythonw = Join-Path $venvDir "Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    $uvPath = Join-Path $runtimeDir "uv.exe"
    if (-not (Test-Path -LiteralPath $uvPath)) {
        $uvZip = Join-Path $updateDir "uv.zip"
        $uvUrl = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -c "import sys,urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])" $uvUrl $uvZip
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -c "import sys,urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])" $uvUrl $uvZip
        } else {
            Invoke-WebRequest -Uri $uvUrl -OutFile $uvZip -TimeoutSec 120
        }
        if (-not (Test-Path -LiteralPath $uvZip)) { throw "Runtime download failed" }
        Expand-Archive -LiteralPath $uvZip -DestinationPath $runtimeDir -Force
        Remove-Item -LiteralPath $uvZip -Force -ErrorAction SilentlyContinue
    }
    & $uvPath venv --python 3.11 --seed $venvDir
    if (-not (Test-Path -LiteralPath $venvPython)) { throw "Python environment setup failed" }
    & $venvPython -m pip install --upgrade pip
}

$requirementsMarker = Join-Path $updateDir "requirements.sha256"
$requirementsHash = (Get-FileHash -LiteralPath (Join-Path $appDir "requirements.txt") -Algorithm SHA256).Hash
$installedHash = if (Test-Path -LiteralPath $requirementsMarker) { Get-Content -LiteralPath $requirementsMarker -Raw } else { "" }
$savedErrorAction = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
& $venvPython -c "import faster_whisper, fastapi, pydub, docx" 2>$null
$dependenciesReady = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $savedErrorAction
if (($requirementsHash -ne $installedHash.Trim()) -or (-not $dependenciesReady)) {
    $installOutput = (& $venvPython -m pip install -r (Join-Path $appDir "requirements.txt") 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed`r`n$installOutput" }
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
[System.Windows.MessageBox]::Show("Startup timed out. Please restart the PC and try again.", "Transcription System") | Out-Null

