#!/bin/bash
# macOS One-Click Updater
cd "$HOME/MAi-RAG-PA" || exit

# Ensure Homebrew Python is in PATH
if [ -f "/opt/homebrew/bin/brew" ]; then
    export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"
fi

# Run the core update script
./update.sh
