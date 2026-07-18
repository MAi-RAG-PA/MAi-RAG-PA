#!/bin/bash
# MAi-RAG-PA Universal Updater
cd "$(dirname "$0")"

echo "Checking for MAi-RAG-PA updates..."

# Ensure we are in a git repository
if [ ! -d ".git" ]; then
    echo "Error: This does not appear to be a valid MAi-RAG-PA installation."
    echo "   Please reinstall using the official installer."
    read -p "Press Enter to exit..."
    exit 1
fi

# Fetch latest changes from GitHub
git fetch origin

# Check if we are behind
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "MAi-RAG-PA is already up to date!"
else
    echo "Downloading latest updates..."
    # Force overwrite local code with GitHub version (safe, user data is in .gitignore)
    git reset --hard origin/main

    # Ensure scripts are executable
    chmod +x launch.sh install.sh update.sh

    echo "Update successful! Your code is now up to date."
    echo "   (Your chats, workspace, and settings are safe and untouched)."
fi

echo ""
read -p "Press Enter to close this window..."
