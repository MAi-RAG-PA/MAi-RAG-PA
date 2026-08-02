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

# MAi-RAG-PA Self-Healing System User Workflow Guide

## Table of Contents

- [Overview](#overview)
- [At a Glance](#at-a-glance)
- [Project Structure](#project-structure)
- [Sandbox Initialization](#sandbox-initialization)
- [Model Capability Check](#model-capability-check)
- [Hardware Requirements](#hardware-requirements)
- [Self-Healing Request Flow](#self-healing-request-flow)
- [Tool Activation](#tool-activation)
- [Available Tools](#available-tools)
- [Self-Healing Workflow](#self-healing-workflow)
- [Example Fix Flow](#example-fix-flow)
- [Path Validation](#path-validation)
- [Monitoring Sandbox Status](#monitoring-sandbox-status)
- [Capabilities](#capabilities)
- [Model Guidance](#model-guidance)
- [Safety Rules](#safety-rules)
- [Troubleshooting](#troubleshooting)
- [Complete Workflow Example](#complete-workflow-example)
- [Future Enhancements](#future-enhancements)
- [API Reference](#api-reference)
- [Conclusion](#conclusion)

## Overview

The MAi-RAG-PA self-healing system lets the AI assistant read, analyze, and fix code inside a controlled sandbox. It is designed to diagnose errors, identify bugs, and produce corrections safely while preserving the privacy and local-only operation of the assistant.

## At a Glance

- **Sandbox:** `~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/`
- **Core workflow:** detect → read → analyze → fix → verify
- **Primary routing method:** keyword-based tool activation
- **Main purpose:** safe autonomous code repair

## Project Structure

### Directory Structure

- `app/` - Backend Python code. Modify with caution.
- `frontend/src/` - Frontend React code. Modify with caution.
- `workspace/` - Your personal files. Safe to modify.
- `dev-sandbox/MAi-RAG-DEV/` - AI self-healing workspace. Auto-managed.
- `memory/` - Short-term memory database files. Auto-managed.
- `storage/` - Long-term memory database files. Auto-managed.
- `models/` - Do not modify. Required for system functions.
- `venv/` - Virtual environment. Do not modify.
- `.git/` - Version control metadata. Do not modify.

## Sandbox Initialization

The sandbox must be initialized before any self-healing can occur. This can happen in either of the following ways.

### Method 1: API Endpoint (Recommended)

Initialize the sandbox:

```bash
curl -X POST http://localhost:8000/api/system/dev-sandbox/init \
  -H "X-API-Key: YOUR_API_KEY"
```

This command copies necessary dependencies and files to the sandbox from the live running MAi-RAG-PA system.

To get your API key:

```bash
sqlite3 ~/MAi-RAG-PA/memory/memory_store.db \
  "SELECT value FROM short_term_memory WHERE key='api_key';"
```

Then, in the MAi-RAG-PA WebUI chat console, ask a qualified model to fix an issue such as:

> Fix the error in `app/main.py` line 123.

Review the sandbox at:

```bash
~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/
```

Deploy fixed files or snippets from the sandbox to the main directory where the file belongs.

### Method 2: Automatic on First Self-Healing Request

When a capable model receives a self-healing request and the sandbox does not exist, the system can initialize it automatically.

## Model Capability Check

Before self-healing instructions are injected into the system prompt, the system checks whether the current model is capable.

### Supported Capable Models

- `qwen2.5-coder:32b`
- `qwen2.5-coder:14b`
- `codeqwen:7b`
- `devstral:24b`
- `mistral-small:24b`
- `qwen3-coder-30b`
- `gemma3:27b`

Only models in this list receive the `SELF_HEALING_PROTOCOL` instructions in the system prompt.

## Hardware Requirements

To run the self-healing system:

- **Minimum:** 8 GB RAM, 4 CPU cores
- **Recommended:** 16 GB RAM, 8 CPU cores
- **Optimal:** 32 GB+ RAM, 8+ CPU cores


## Self-Healing Request Flow

When a user makes a request that requires code modification:


### Step 1: User Request

Example:

> Fix the error in `app/main.py` line 245.


### Step 2: System Prompt Injection

The system automatically checks the current model capability.


### Step 3: AI Reads `ARCHITECTURE.md`

The capable model reads `ARCHITECTURE.md` to understand the project structure and locate the relevant files.


### Step 4: AI Works in Sandbox

The AI:

- Reads files from the main project in read-only mode.
- Makes modifications in the sandbox at `~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/`.
- Provides backup commands for the user to run.
- Suggests verification commands.


### Step 5: User Review and Deploy

The user reviews the changes in the sandbox and can:

- **Deploy:** Copy files from the sandbox to the main project.
- **Revert:** Discard sandbox changes.
- **Reset:** Delete and reinitialize the sandbox.


## Tool Activation

The system uses keyword routing to decide when to enable tool-calling:

```python
tool_keywords = [
    "create file", "write file", "save", "calendar", "event", "reminder",
    "todo", "read", "fix", "diagnose", "sandbox", "error", "search", "backup",
]
```

When a query matches these keywords, the system:

1. Enters tool-calling mode.
2. Binds available tools such as `read_file`, `write_file`, and `list_directory`.
3. Runs the ReAct loop for reasoning and action.

## Available Tools

| Tool | Purpose | Example |
|---|---|---|
| `read_file` | Read file contents | Read `app/main.py`. |
| `write_file` | Create or update files | Fix a bug in `test.py`. |
| `list_directory` | Inspect folder structure | Show the workspace tree. |
| `search_files` | Find files by pattern | Find all Python files. |
| `search_knowledge_base` | Search the RAG knowledge base | Find authentication examples. |

## Self-Healing Workflow

When fixing an issue, the system follows this sequence:

1. **Diagnose** the error message and related files.
2. **Locate** the exact file and line causing the problem.
3. **Verify** that the fix will not break dependencies.
4. **Backup** the original file before editing it.
5. **Fix** the issue by outputting the full corrected file.
6. **Test** the result with a verification command such as:

```bash
python -m py_compile <file>
```

## Example Fix Flow

If a file like `dev-sandbox/MAi-RAG-DEV/app/utils/broken_memory_query.py` is broken, the AI should:

- Read the file.
- Identify syntax, import, and logic issues.
- Provide a backup command.
- Return the complete corrected file.
- Suggest a compile check command.

Example verification:

```bash
python -m py_compile dev-sandbox/MAi-RAG-DEV/app/utils/broken_memory_query.py
```

## Path Validation

All file operations in the sandbox are validated to ensure they stay within allowed boundaries.

## Monitoring Sandbox Status

Check the sandbox status at any time in terminal:

```bash
curl http://localhost:8000/api/system/dev-sandbox/status \
  -H "X-API-Key: YOUR_API_KEY"
```

Example response:

```json
{
  "status": "initialized",
  "path": "/home/user/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV",
  "file_count": 127,
  "directory_count": 23,
  "message": "Sandbox is ready for self-healing operations"
}
```

## Capabilities

### Supported

- Read and analyze code files.
- Detect syntax errors, import issues, and logic bugs.
- Produce complete corrected files.
- Suggest backup and verification commands.
- Search the knowledge base for relevant examples.
- Create new files from a description.

### Not Supported

- Automatically detect runtime errors without logs.
- Execute code directly.
- Access files outside the sandbox.
- Modify database schemas directly.
- Install new dependencies.

## Model Guidance

| Model | Size | Tool Support | Speed | Notes |
|---|---:|---|---|---|
| `qwen2.5-coder:14b` | 14B | Yes | 30–60 min | Best accuracy, slower on CPU. |
| `qwen2.5-coder:7b` | 7B | Yes | 15–25 min | Good balance. |
| `codeqwen:7b` | 7B | No | 10–15 min | Fast, but may hallucinate tool calls. |

## Safety Rules

### Forbidden Directories

The AI must not access:

- `venv/`, `env/`, `.venv/`
- `node_modules/`
- `.git/`
- `__pycache__/`
- `memory/`
- `storage/`
- `models/`
- `logs/`
- `alembic/`
- `tests/`
- `scripts/`

### Safety Protocols

- Validate every path before file operations.
- Limit directory depth to 10 levels.
- Limit operations to 50 files at a time.
- Always back up files before modifying them.
- Always suggest a verification command after changes.

## Troubleshooting

### Empty response

**Cause:** Model timeout or resource limits.
**Fix:** Use a smaller model, increase `_get_llm()` timeout, and check system usage with `top` or `htop`.

### Refuses to read files

**Cause:** File path includes a forbidden directory.
**Fix:** Keep files inside `dev-sandbox/MAi-RAG-DEV/` or `workspace/`, and check `FORBIDDEN_DIRS` in `agent_core.py`.

### Tool calls do not execute

**Cause:** The model does not support tool calling.
**Fix:** Use a model with tools support, and fall back to JSON interception if needed.

## Complete Workflow Example:

# 1. Initialize sandbox
curl -X POST http://localhost:8000/api/system/dev-sandbox/init \
  -H "X-API-Key: YOUR_API_KEY"

# 2. Make a self-healing request
# The AI will work in the sandbox

# 3. Check sandbox status
curl http://localhost:8000/api/system/dev-sandbox/status \
  -H "X-API-Key: YOUR_API_KEY"

# 4. Review changes in sandbox
cd ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV
git diff  # If you initialized with git

# 5. Deploy changes manually
cp ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/app/main.py ~/MAi-RAG-PA/app/main.py

# 6. Reset sandbox if needed
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
