#!/bin/bash

set -x

# Detect operating system
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
elif [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_TYPE="linux"
    LINUX_DISTRO=$ID
else
    echo "Cannot detect operating system"
    exit 1
fi

# Install Docker
if ! command -v docker &>/dev/null; then
    if [ "$OS_TYPE" == "macos" ]; then
        # Install Homebrew if not present
        if ! command -v brew &>/dev/null; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        # Install Docker Desktop for macOS
        brew install --cask docker
        open /Applications/Docker.app
        echo "Waiting for Docker to start..."
        sleep 10
    else
        # Install Docker for Linux
        case $LINUX_DISTRO in
            ubuntu|debian)
                sudo apt-get update
                sudo apt-get install -y ca-certificates curl gnupg
                sudo install -m 0755 -d /etc/apt/keyrings
                curl -fsSL https://download.docker.com/linux/$LINUX_DISTRO/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
                sudo chmod a+r /etc/apt/keyrings/docker.gpg
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$LINUX_DISTRO $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
                sudo apt-get update
                sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;
            fedora|rhel|centos)
                sudo yum install -y yum-utils
                sudo yum-config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
                sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;
            arch)
                sudo pacman -S --noconfirm docker docker-compose
                ;;
        esac
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
    fi
fi

# Install Thunderbird
if [ "$OS_TYPE" == "macos" ]; then
    if [ ! -d "/Applications/Thunderbird.app" ]; then
        brew install --cask thunderbird
    fi
else
    if ! command -v thunderbird &>/dev/null; then
        case $LINUX_DISTRO in
            ubuntu|debian)
                sudo apt-get install -y thunderbird
                ;;
            fedora|rhel|centos)
                sudo yum install -y thunderbird
                ;;
            arch)
                sudo pacman -S --noconfirm thunderbird
                ;;
        esac
    fi
fi

# Determine Python executable
if command -v python3 &>/dev/null; then
    PYTHON_EXEC=python3
else
    PYTHON_EXEC=python
fi

# Set directory based on OS
if [ "$OS_TYPE" == "macos" ]; then
    DIR="$HOME/Library/Application Support/Riamu Mail"
else
    DIR="$HOME/.local/share/riamumail"
fi

mkdir -p "$DIR"

if [ -d "$DIR/riamumail" ]; then
    rm -rf "$DIR/riamumail"
fi

curl -L -o /tmp/repo-main.zip https://github.com/umrashrf/riamumail-app/archive/main.zip
unzip /tmp/repo-main.zip -d /tmp/
mv /tmp/riamumail-app-main/* "$DIR/"
rm -rf /tmp/riamumail-app-main/
rm /tmp/repo-main.zip
cd "$DIR" || exit

# Create shortcut/launcher for macOS
if [ "$OS_TYPE" == "macos" ]; then
    if [ -f "Riamu Mail.command" ]; then
        cp "Riamu Mail.command" /Applications/ 2>/dev/null || true
    fi
fi

$PYTHON_EXEC -m venv venv
venv/bin/python3 -m pip install -U pip
venv/bin/python3 -m pip install -U ./riamumail

cd "$DIR/riamumail/src" || exit
nohup ../../venv/bin/python3 -m riamumail > /dev/null 2>&1 &

# Close Terminal window on macOS
if [ "$OS_TYPE" == "macos" ]; then
    osascript -e 'tell application "Terminal" to close first window' & exit
fi

echo "Installation complete!"
if [ "$OS_TYPE" == "linux" ]; then
    echo "You may need to log out and back in for Docker group permissions to take effect."
fi
