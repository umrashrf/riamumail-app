#!/bin/bash

set -x

if command -v python3 &>/dev/null; then
    PYTHON_EXEC=python3
else
    PYTHON_EXEC=python
fi

DIR="/Applications/Riamu Mail"
if [ -d "$DIR" ]; then
    cd "$DIR" || exit
else
    curl -L -o /tmp/repo-main.zip https://github.com/umrashrf/riamumail-app/archive/main.zip
    unzip /tmp/repo-main.zip -d /tmp/
    mv /tmp/riamumail-app-main "$DIR"
    rm /tmp/repo-main.zip
    cd "$DIR" || exit
    cp Riamu\ Mail.command /Applications
    $PYTHON_EXEC -m venv venv
    venv/bin/python3 -m pip install -U pip
    venv/bin/python3 -m pip install -U ./riamumail
fi
cd riamumail/src || exit
nohup ../../venv/bin/python3 -m riamumail > /dev/null 2>&1 &
osascript -e 'tell application "Terminal" to close first window' & exit
