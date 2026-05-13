# Enable verbose output (equivalent to set -x)
Set-PSDebug -Trace 1

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "This script requires administrator privileges for Docker and Thunderbird installation."
    Write-Host "Restarting as administrator..."
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Install Chocolatey if not present (Windows package manager)
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Install Docker Desktop
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Docker Desktop..."
    choco install docker-desktop -y
    
    # Start Docker Desktop
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Write-Host "Waiting for Docker to start (this may take a minute)..."
    Start-Sleep -Seconds 30
} else {
    Write-Host "Docker is already installed."
}

# Install Thunderbird
$thunderbirdPath = "C:\Program Files\Mozilla Thunderbird\thunderbird.exe"
if (-not (Test-Path $thunderbirdPath)) {
    Write-Host "Installing Thunderbird..."
    choco install thunderbird -y
} else {
    Write-Host "Thunderbird is already installed."
}

# Determine Python executable
if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PYTHON_EXEC = "python3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PYTHON_EXEC = "python"
} else {
    Write-Host "Python is not installed. Installing Python..."
    choco install python -y
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $PYTHON_EXEC = "python"
}

# Set directory path (Windows equivalent)
$DIR = "$env:LOCALAPPDATA\Riamu Mail"

if (Test-Path $DIR) {
    Write-Host "Removing existing Riamu Mail directory..."
    Remove-Item -Path $DIR -Recurse -Force
}

# Download and extract repository
$zipPath = "$env:TEMP\repo-main.zip"
$extractPath = "$env:TEMP"

Write-Host "Downloading Riamu Mail..."
Invoke-WebRequest -Uri "https://github.com/umrashrf/riamumail-app/archive/main.zip" -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
Move-Item "$extractPath\riamumail-app-main" $DIR
Remove-Item $zipPath

Set-Location $DIR
if (-not $?) { exit }

# Create shortcut in Start Menu
$StartMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"

# If .lnk exists, copy it; otherwise create a shortcut
if (Test-Path "Riamu Mail.lnk") {
    Copy-Item "Riamu Mail.lnk" $StartMenuPath -ErrorAction SilentlyContinue
} else {
    # Create shortcut programmatically
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$StartMenuPath\Riamu Mail.lnk")
    $Shortcut.TargetPath = "$DIR\venv\Scripts\python.exe"
    $Shortcut.Arguments = "-m riamumail"
    $Shortcut.WorkingDirectory = "$DIR\riamumail\src"
    $Shortcut.Save()
}

Write-Host "Creating virtual environment..."
& $PYTHON_EXEC -m venv venv

Write-Host "Upgrading pip..."
& .\venv\Scripts\python.exe -m pip install -U pip

Write-Host "Installing riamumail..."
& .\venv\Scripts\python.exe -m pip install -U .\riamumail

# Change to riamumail/src directory
Set-Location riamumail\src
if (-not $?) { exit }

Write-Host "Starting Riamu Mail..."
# Start process in background (equivalent to nohup ... &)
Start-Process -FilePath "..\..\venv\Scripts\python.exe" `
              -ArgumentList "-m", "riamumail" `
              -WindowStyle Hidden `
              -RedirectStandardOutput "NUL" `
              -RedirectStandardError "NUL"

Write-Host "`nInstallation complete!"
Write-Host "- Docker Desktop has been installed and started"
Write-Host "- Thunderbird has been installed"
Write-Host "- Riamu Mail is now running in the background"
Write-Host "`nNote: You may need to restart your computer for Docker to work properly."

# Pause to show messages before closing
Start-Sleep -Seconds 3

exit
