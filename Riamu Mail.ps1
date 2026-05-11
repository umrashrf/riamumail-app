# Enable verbose output (equivalent to set -x)
Set-PSDebug -Trace 1

# Determine Python executable
if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PYTHON_EXEC = "python3"
} else {
    $PYTHON_EXEC = "python"
}

# Set directory path (Windows equivalent)
$DIR = "$env:LOCALAPPDATA\Riamu Mail"

if (Test-Path $DIR) {
    Set-Location $DIR
} else {
    # Download and extract repository
    $zipPath = "$env:TEMP\repo-main.zip"
    $extractPath = "$env:TEMP"
    
    Invoke-WebRequest -Uri "https://github.com/umrashrf/riamumail-app/archive/main.zip" -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
    Move-Item "$extractPath\riamumail-app-main" $DIR
    Remove-Item $zipPath
    
    Set-Location $DIR
    if (-not $?) { exit }
    
    # Copy shortcut to Start Menu (Windows equivalent of /Applications)
    $StartMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
    Copy-Item "Riamu Mail.lnk" $StartMenuPath -ErrorAction SilentlyContinue
    
    # Create virtual environment
    & $PYTHON_EXEC -m venv venv
    
    # Upgrade pip
    & .\venv\Scripts\python.exe -m pip install -U pip
    
    # Install riamumail
    & .\venv\Scripts\python.exe -m pip install -U .\riamumail
}

# Change to riamumail/src directory
Set-Location riamumail\src
if (-not $?) { exit }

# Start process in background (equivalent to nohup ... &)
Start-Process -FilePath "..\..\venv\Scripts\python.exe" `
              -ArgumentList "-m", "riamumail" `
              -WindowStyle Hidden `
              -RedirectStandardOutput "NUL" `
              -RedirectStandardError "NUL"

# Exit (no Terminal window to close in PowerShell)
exit
