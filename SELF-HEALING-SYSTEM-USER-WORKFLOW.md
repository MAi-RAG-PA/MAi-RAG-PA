<p align="center">
  <img src="MAi-RAG.png" alt="MAi-RAG-PA Personal Assistant" width="150">
</p>

<h1 align="center">MAi-RAG-PA</h1>
<h3 align="center">Your Offline Privacy, Self-Healing, Personal Assistant</h3>

<p align="center">
  <strong>MAi-RAG-PA (Memory-Augmented Intelligence with Retrieval-Augmented Generation - Personal Assistant)</strong> is a privacy-focused personal AI assistant that runs entirely on your local machine. No cloud. No subscriptions. No data leaving your computer.
</p>

<p align="center">
  <a href="README.md">Home</a> •
  <a href="MAi-README.md">Full Documentation</a> •
  <a href="MAi-INSTALLATION.md">Installation</a> •
  <a href="MAi-OLLAMA-MODELS.md">Models</a> •
  <a href="MAi-SSH-SETUP.md">SSH & LAN</a> •
  <a href="SELF-HEALING-SYSTEM-USER-WORKFLOW.md">Self-Healing System</a> •
  <a href="CHANGELOG.md">Changelog</a> •
  <a href="MAi-LICENCE-LEGAL-NOTICE.md">License</a>
</p>

<p align="center">
  <strong>Version 1.0 | Effective Date: June 2026</strong><br />
  <strong>Copyright © 2026 MAi-RAG-PA. All Rights Reserved.</strong>
</p>

-----------------------------------------------------------------------------------

# MAi-RAG-PA User Workflow Guide for Self-Healing System

## Directory Structure

- `app/` - Backend Python code (modify with caution)
- `frontend/src/` - Frontend React code (modify with caution)
- `models/` - Do Not Modify! Needed for system functions
- `workspace/` - Your personal files (safe to modify)
- `dev-sandbox/MAi-RAG-DEV/` - AI self-healing workspace (auto-managed)
- `memory/` - Short-Term Memory Database files (auto-managed)
- `storage/` - Long-Term Memory Database files (auto-managed)
- `venv/` - Virtual enviornment DO NOT Modify  (auto-managed)


# Self-Healing System Initiation Process:

## Sandbox Initialization
    - The sandbox must be initialized before any self-healing can occur. This can be done in two ways:

### Method 1. API Endpoint (Recommended)

**The AI can fix its own code in a safe sandbox:**
    - Initialize sandbox:

      curl -X POST http://localhost:8000/api/system/dev-sandbox/init -H "X-API-Key: YOUR_KEY"

      This command Copies necessary dependencies and files to the sandbox from the live running MAi-RAG-PA system installed.

**To get "YOUR KEY" if you dont already have, open a terminal and type:**

    sqlite3 ~/MAi-RAG-PA/memory/memory_store.db "SELECT value FROM short_term_memory WHERE key='api_key';"

    - Then in MAi-RAG-PA WebUI Chat Console, Ask codeqwen:7b, or other *qualified models (see below) to fix:
    "Fix the error in app/main.py line 123"

    - Test changes: Review the sandbox at ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/

    - Deploy: Copy/Edit fixed files/snippets from sandbox files to the main directory where the file belongs


### Method 2. Automatic on First Self-Healing Request

    1. When a capable model receives a "self-healing" request and the sandbox doesn't exist, the system can automatically initialize it.

    2. Model Capability Check

    Before self-healing instructions are injected into the system prompt, the system checks if the current model is capable:

    "qwen2.5-coder:32b",
    "qwen2.5-coder:14b",
    "codeqwen:7b",
    "devstral:24b",
    "mistral-small:24b",
    "qwen3-coder-30b",
    "gemma3:27b",

    3. Only models in the list above can receive the SELF_HEALING_PROTOCOL instructions in their system prompt.

### Check your system:

curl http://localhost:8000/api/system/hardware -H "X-API-Key: YOUR_KEY"

**To get your personal key open a terminal and enter this command:**

sqlite3 ~/MAi-RAG-PA/memory/memory_store.db "SELECT value FROM short_term_memory WHERE key='api_key';"

### Hardware Requirements To run the Self Healing System:

    - Minimum: 8GB RAM, 4 CPU cores
    - Recommended: 16GB RAM, 8 CPU cores
    - Optimal: 32GB+ RAM, 8+ CPU cores

### Self-healing is only enabled for capable models:

    qwen2.5-coder:32b
    qwen2.5-coder:14b
    codeqwen:7b (included)
    devstral:24b
    mistral-small:24b
    qwen3-coder-30b
    gemma3:27b


## Self-Healing Request Flow

When a user makes a request that requires code modification:

**Step 1: User Request**

  User: "Fix the error in app/main.py line 245"

**Step 2: System Prompt Injection**

  The system automattically checks the current model capability.

**Step 3: AI Reads ARCHITECTURE.md**

  The capable model reads ARCHITECTURE.md to understand the project structure and locate the relevant files.

**Step 4: AI Works in Sandbox**

  The AI:

    - Reads files from the main project (read-only access to ~/MAi-RAG-PA/)
    - Makes modifications in the sandbox (~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/)
    - Provides backup commands for the user to run
    - Suggests verification commands

**Step 5: User Review & Deploy**

  The user reviews the changes in the sandbox and can:

    - Deploy: Copy files from sandbox to main project
    - Revert: Discard sandbox changes
    - Reset: Delete and reinitialize sandbox


## Path Validation
All file operations in the sandbox are validated:

## Monitoring Sandbox Status
You can check the sandbox status at any time in terminal:

curl http://localhost:8000/api/system/dev-sandbox/status \
  -H "X-API-Key: YOUR_API_KEY"

**Response:**

{
  "status": "initialized",
  "path": "/home/user/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV",
  "file_count": 127,
  "directory_count": 23,
  "message": "Sandbox is ready for self-healing operations"
}


## Complete Workflow Example:

# 1. Initialize sandbox
curl -X POST http://localhost:8000/api/system/dev-sandbox/init \
  -H "X-API-Key: YOUR_API_KEY"

# 2. Make a self-healing request (via chat interface or API)
# The AI will work in the sandbox

# 3. Check sandbox status
curl http://localhost:8000/api/system/dev-sandbox/status \
  -H "X-API-Key: YOUR_API_KEY"

# 4. Review changes in sandbox
cd ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV
git diff  # If you initialized with git

# 5. Deploy changes (manual copy)
cp ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/app/main.py ~/MAi-RAG-PA/app/main.py

# 6. Or reset sandbox
curl -X DELETE http://localhost:8000/api/system/dev-sandbox/reset \
  -H "X-API-Key: YOUR_API_KEY"

########################################################################
########################################################################

## Updating MAi-RAG-PA

### If You Haven't Modified Source Code, or just want to reinstall from scratch:
You will need to specifically backup your databases, and any created files saved in workspace:

mkdir -p ~/MAi-RAG-BKP && cp -r ~/MAi-RAG-PA/workspace ~/MAi-RAG-PA/storage ~/MAi-RAG-PA/memory ~/MAi-RAG-BKP/

cd ~/MAi-RAG-PA
git pull origin main
./install.sh  # Re-run installer to update dependencies
./first_launch.py
./start.sh

### If You Have previously Modified Source Code

cd ~/MAi-RAG-PA

# Save your changes
git stash

# Pull updates
git pull origin main

# Reapply your changes
git stash pop

# Resolve any conflicts
# Then restart
./stop.sh
./start.sh
