#!/bin/bash

set -x

if command -v python3 &>/dev/null; then
    PYTHON_EXEC=python3
else
    PYTHON_EXEC=python
fi

DIR=/Applications/Riamu\ Mail
if [ -d "$DIR" ]; then
    cd "$DIR" || exit
else
    git clone https://github.com/umrashrf/riamumail-app.git "$DIR"
    cd "$DIR" || exit
    cp Riamu\ Mail.command /Applications
    $PYTHON_EXEC -m venv venv
    venv/bin/python3 -m pip install -U pip
    venv/bin/python3 -m pip install -U ./riamumail
fi
cd riamumail/src || exit
nohup ../../venv/bin/python3 -m riamumail > /dev/null 2>&1 &
osascript -e 'tell application "Terminal" to close first window' & exit
