# MAi-RAG-P.A. Complete System Architecture

## System Overview

MAi-RAG-P.A. is a privacy-focused, offline personal AI assistant with:
- **Dual-Layer Memory**: SQLite (STM) + Qdrant (LTM)
- **Self-Healing Capabilities**: AI-powered code repair in isolated sandbox
- **Agentic File Creation**: Generate → Verify → Fix → Save pipeline
- **Multi-Model Support**: Hardware-aware model recommendations
- **Persistent Storage**: All data in SQLite, survives browser cache clears
- **Protected System Models**: codeqwen:7b for core functionality
- **Mandatory Citations**: End-of-response References section

**Why it exists:** MAi-RAG-P.A. runs entirely on the user's own machine, so conversations, documents, and prompts never leave the hardware, and the assistant keeps working with no internet connection. Privacy is enforced by architecture (localhost services, API-key gate, sandboxed writes) rather than promised by policy.

-----------------------------------------------------------------------------------

## Data Flow

Every flow below runs through the FastAPI backend; each call requires the `X-API-Key` header except `/api/health` and the `/api/auth/*` bootstrap routes (see API Key Management).

### Chat Request Flow (with Database Persistence)

User Input → ChatConsoleApp.tsx
  ↓
Frontend saves thread to database:
  POST /api/memory/sqlite/chat/thread
  ↓
Frontend saves user message to database:
  POST /api/memory/sqlite/chat/message
  ↓
POST /api/chat endpoint (main.py)
  ↓
_build_stm_context_for_prompt() → Load user facts, reminders, events
  ↓
get_system_prompt() → Inject STM context + system instructions
  ↓
_get_llm() → Get cached ChatOllama instance
  ↓
llm.invoke() → Send to Ollama
  ↓
Response → Return to frontend
  ↓
Frontend saves AI message to database:
  POST /api/memory/sqlite/chat/message
  ↓
Chat persists across browser refreshes and system restarts

### STM Quick Entry Flow

User Input → /api/memory/stm/quick-entry (main.py)
  ↓
parse_stm_with_llm() → codeqwen:7b (JSON parsing with regex fast-path)
  ↓
Save to SQLite → reminders/events/todos/user_profile tables

### RAG Ingestion Flow

File Upload → /api/memory/qdrant/chunk-and-ingest (main.py)
  ↓
Phase 1: Chunk text → Write to disk (storage/chunk_cache/)
  ↓
Phase 2: Embed chunks → Ingest to Qdrant collection
  ↓
Deduplication: Check content_hash before inserting

### File Creation Flow (with Overwrite Protection)

[FILE]-prefixed (or natural-language) request → filename extracted → numbered suffix if the file exists → agentic_create_file() runs Generate → Verify → Fix → Save → path and size returned. Full mechanics are covered in File Creation with Overwrite Protection below.

### System Prompt Management Flow

"Reset to Default" → GET /api/settings/system-prompt/default returns DEFAULT_SYSTEM_PROMPT from agent_core.py → user edits → "Save Prompt" → POST /api/settings/system-prompt → stored in the short_term_memory table (key='system_prompt') → the next request uses the updated prompt. Details are covered in System Prompt Management below.

-----------------------------------------------------------------------------------

## Directory Structure & File Purposes

~/MAi-RAG-PA/
├── alembic/                      # Database migrations
│   └── versions/                 # Migration scripts
├── app/                          # Backend Python application
│   ├── agents/                   # LLM interaction, system prompts, self-healing
│   ├── api/                      # API routing (v1)
│   ├── documents/                # File parsing, chunking, and processing
│   ├── rag/                      # RAG retrieval, context, and model management
│   ├── security/                 # Auth, encryption, validation, rate limiting
│   ├── utils/                    # Logging and utilities
│   ├── voice/                    # Voice recognition
│   ├── main.py                   # FastAPI app, ALL endpoints, Pydantic models
│   ├── metrics.py                # Prometheus metrics
│   └── websocket_manager.py      # WebSocket connections
├── dev-sandbox/                  # Self-healing workspace (DYNAMICALLY CREATED)
│   └── MAi-RAG-DEV/              # Staging environment (mirrors app/ and frontend/src/)
├── frontend/                     # React frontend
│   ├── public/                   # Static assets (fonts, sounds, manifest, sw.js)
│   └── src/                      # Source code
│       ├── api/                  # API clients (Axios, WebSocket, Voice)
│       ├── components/           # React components (e.g., chat/ChatConsoleApp.tsx)
│       ├── contexts/             # React Context API
│       ├── hooks/                # Custom React hooks
│       ├── i18n/                 # Internationalization
│       ├── store/                # State management
│       ├── styles/               # CSS/Tailwind styles
│       ├── utils/                # Frontend utilities
│       ├── App.tsx               # Main app component
│       └── main.tsx              # Entry point
├── memory/                       # SQLite database (memory_store.db)
├── qdrant/                       # Qdrant vector store (local instance)
├── logs/                         # Server and service logs
├── workspace/                    # User files & AI-generated content
├── alembic.ini                   # Alembic configuration
├── ARCHITECTURE.md               # System architecture documentation
├── first_launch.py               # Initial setup script
├── install.sh                    # Universal installer (Linux/macOS/WSL2)
├── requirements.txt              # Python dependencies
├── start.sh / stop.sh            # Service management scripts
└── ... (other documentation: README.md, CHANGELOG.md, etc.)

-----------------------------------------------------------------------------------

## Core Components

### 1. Backend (FastAPI)

**File: `app/main.py`**

**Responsibilities:**
- API endpoint definitions
- Pydantic model validation
- Request routing and orchestration
- Dependency injection (API key verification)

**Key Endpoints:**

All routes require the X-API-Key header except /api/health and the /api/auth/* bootstrap routes.

# Chat & Memory
POST /api/chat                      # Main chat endpoint
GET  /api/memory/sqlite/chat/threads           # List all chat threads
GET  /api/memory/sqlite/chat/messages/{id}     # Get messages for thread
POST /api/memory/sqlite/chat/thread            # Create/update thread
POST /api/memory/sqlite/chat/message           # Save message
DELETE /api/memory/sqlite/chat/thread/{id}     # Delete thread

# STM Operations
GET  /api/memory/sqlite/reminders/upcoming     # Get upcoming reminders
POST /api/memory/sqlite/reminders              # Create reminder
DELETE /api/memory/sqlite/reminders/{id}       # Delete reminder
GET  /api/memory/sqlite/events/upcoming        # Get upcoming events
POST /api/memory/sqlite/events                 # Create event
DELETE /api/memory/sqlite/events/{id}          # Delete event
POST /api/memory/stm/quick-entry               # Natural language STM entry
GET  /api/memory/sqlite/export                  # Export STM data as JSON
POST /api/memory/sqlite/import                  # Import/merge STM data from JSON

# LTM Operations
POST /api/memory/qdrant/chunk-and-ingest       # RAG ingestion
GET  /api/memory/qdrant/status                 # Qdrant status
POST /api/rag/query                             # RAG search over ingested content

# System
GET  /api/health                               # Health check
GET  /api/system/doctor                        # System diagnostics
GET  /api/system/hardware                      # Hardware info
GET  /api/system/cpu                           # CPU usage
GET  /api/system/ram                           # RAM usage
GET  /api/system/protected-models              # Protected model status
POST /api/system/dev-sandbox/init              # Initialize self-healing sandbox
GET  /api/system/dev-sandbox/status            # Sandbox status
DELETE /api/system/dev-sandbox/reset           # Reset sandbox
POST /api/system/backup                        # Create backup
GET  /api/system/backups                       # List backups
POST /api/system/restore/{filename}            # Restore backup

# Settings
GET  /api/settings/system-prompt               # Get system prompt
POST /api/settings/system-prompt               # Update system prompt
GET  /api/settings/system-prompt/default       # Get default prompt (from agent_core.py)
GET  /api/settings/heartbeat                   # Get heartbeat settings
POST /api/settings/heartbeat                   # Set heartbeat interval
GET  /api/settings/default-model               # Get default model
POST /api/settings/default-model               # Set default model

# Authentication
GET  /api/auth/status                          # Check auth status
POST /api/auth/generate-key                    # Generate API key
GET  /api/auth/auto-key                        # Auto-generate key

# Voice
POST /api/voice/transcribe                     # Transcribe audio (multipart upload)

# Roles (versioned API, /api/v1)
GET  /api/v1/roles/active                      # List roles
GET  /api/v1/roles/{role_id}                   # Get role
PUT  /api/v1/roles/{role_id}                   # Update role
DELETE /api/v1/roles/{role_id}                 # Delete role
POST /api/v1/roles/{role_id}/activate          # Activate role

## Key Architectural Patterns

### Backend (Python/FastAPI)
- **Routes**: Defined in `app/main.py` using `@app.get/post/delete` decorators
- **Pydantic Models**: Request/response validation in `app/main.py`
- **Database**: SQLite via `SQLiteMemoryManager` in `app/memory/sqlite_memory.py`
- **Vector DB**: Qdrant via `QdrantMemoryManager` in `app/memory/qdrant_manager.py`
- **LLM**: Ollama via LangChain's `ChatOllama` in `app/agents/agent_core.py`
- **Authentication**: API key via `X-API-Key` header, verified by `verify_api_key()`

### Frontend (React/TypeScript)
- **API Client**: Axios-based client in `frontend/src/api/client.ts`
- **Components**: Functional components with hooks in `frontend/src/components/`
- **State Management**: React Context API in `frontend/src/contexts/`
- **Styling**: Inline styles + CSS variables (no CSS modules)
- **Chat Persistence**: All messages saved to SQLite via API calls (not localStorage)

### Database Schema (SQLite)

DDL lives in `app/memory/sqlite_memory.py` (`_create_all_tables`); schema changes go through Alembic migrations.

- **chat_threads** (id TEXT PK, title TEXT, created_at, last_message_at)
- **chat_messages** (id TEXT PK, thread_id FK -> chat_threads ON DELETE CASCADE, role, content, timestamp, model, filename)
- **reminders** (id TEXT PK, text, due_time, priority, completed, created_at)
- **events** (id TEXT PK, title, description, start_time, end_time, location, category, is_recurring, recurrence_type, recurrence_days, recurrence_end_date, created_at, updated_at, order_index)
- **todos** (id TEXT PK, title, description, priority, completed, due_date, created_at, order_index)
- **user_profile** (key TEXT PK, value TEXT, updated_at)
- **notes** (id TEXT PK, title, content, created_at, updated_at)
- **short_term_memory** (id INTEGER PK, key TEXT UNIQUE, value TEXT, timestamp) - Stores: system_prompt, default_model, api_key
- **user_facts** (id INTEGER PK, fact, category, confidence, created_at, is_active)
- **prompt_versions** (id TEXT PK, name, content, version, created_at, created_by, is_active)
- **token_usage** (id INTEGER PK, timestamp, model, prompt_tokens, completion_tokens, total_tokens, endpoint)

### Critical Files (DO NOT DELETE)
- `app/main.py` - Core application
- `app/agents/agent_core.py` - AI agent logic, system prompt, self-healing
- `app/memory/sqlite_memory.py` - Database operations
- `frontend/src/App.tsx` - Main React component
- `frontend/src/api/client.ts` - API client
- `frontend/src/components/chat/ChatConsoleApp.tsx` - Chat interface with persistence

-----------------------------------------------------------------------------------

## Protected System Models

MAi-RAG-P.A. designates certain models as **Protected System Models**. `install.sh` installs them automatically during setup (skipping any that are already present), and they are critical for optimal system performance.

### codeqwen:7b (Protected)

**Purpose:** Core system functionality
- STM (Short-Term Memory) parsing fallback when regex fails
- Self-healing operations
- Basic chat and file creation
- Text-to-SQL queries

**Why It's Protected:**
- Optimized for consumer hardware (8-12GB RAM)
- Fast response times (~4.5GB RAM requirement)
- Reliable for system operations
- Ensures core features work even if primary model fails

**Installation:**
Automatically installed by `install.sh` during setup (after a RAM check):

    ollama pull codeqwen:7b

The installer also pulls `nomic-embed-text` (RAG embedding model, required for document ingestion).

**Warning System:**
If codeqwen:7b is missing, MAi-RAG-P.A. shows a warning in the Chat Console (banner and toast):

    codeqwen:7b is not installed. Optimized for consumer hardware. Required for optimal system performance.

**Must I Keep It?**
Yes — protected models are necessary system models: they run the Self-Healing system and the SQLite short-term-memory parser. The model-deletion feature has been removed from the Chat Console; do not remove protected models manually (for example with `ollama rm`). If they are removed:
- STM parsing falls back to regex-only (slower)
- Self-healing may not work optimally
- Basic chat uses your primary model instead (slower on low-end hardware)
- The Chat Console shows persistent warnings until the model is reinstalled

**API Endpoint:**

    GET /api/system/protected-models - Returns status of protected models

-----------------------------------------------------------------------------------

## Hardware Detection

The system automatically detects hardware capabilities and recommends appropriate settings:

| Tier | RAM | CPU Cores | Recommended Model | Max Concurrent Requests |
|------|-----|-----------|-------------------|------------------------|
| High | 32GB+ | 8+ | 35b+ | 3 |
| Medium | 16GB+ | 4+ | 14b | 2 |
| Low | 8GB+ | any | 7b | 1 |
| Minimal | <8GB | any | 3b | 1 |

**Check Your System:**

    curl http://localhost:8000/api/system/hardware -H "X-API-Key: YOUR_API_KEY"

The tier also drives num_predict, context length, and how many requests the server processes concurrently.

Example response:

    {"ram_gb": 63.7, "cpu_cores": 16, "recommendations": {"recommended_model_size": "35b+", "recommended_model_type": "MoE", "recommended_models": ["..."], "num_predict": 4096, "context_length": 8192, "tier": "high", "max_concurrent_requests": 3}, "message": "System tier: HIGH"}

-----------------------------------------------------------------------------------

## Self-Healing System

**The system includes a self-healing capability that allows capable AI models to fix their own code in a safe sandbox environment.**

codeqwen:7b runs these tasks by default; on 16GB+ RAM systems, qwen2.5-coder:14b (or any model from the gating list below) can take them over.

### Sandbox Location

- Path: ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/
- Creation: Dynamic via POST /api/system/dev-sandbox/init
- Purpose: Isolated environment for AI to modify code safely

### Safety Rules

- Working Directory: Strictly confined to ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/
- Forbidden Paths: No access to venv/, node_modules/, .git/, __pycache__/
- Infinite Loop Prevention: Max 50 files per operation, max 10 directory depth
- Verification: All code must pass syntax checks before deployment

### Model Capability Gating

**Self-healing is only enabled for capable models:**

**Dense Models:**
- qwen2.5-coder:32b
- qwen2.5-coder:14b
- codeqwen:7b
- devstral:24b
- mistral-small:24b
- qwen3-coder-30b
- gemma3:27b

**MoE Models:**
- qwen3-235b-a22b
- qwen3-30b-a3b
- qwen3.6-35b-a3b
- mixtral-8x7b
- mixtral-8x22b
- deepseek-v2

### API Endpoints for Sandbox Management

    POST /api/system/dev-sandbox/init - Initialize sandbox
    GET /api/system/dev-sandbox/status - Check sandbox status
    DELETE /api/system/dev-sandbox/reset - Reset sandbox

### Self-Healing Protocol

When fixing errors:
1. **Diagnose**: Read the error message and relevant files
2. **Locate**: Identify the exact file and line causing the issue
3. **Verify**: Check if the fix breaks dependencies
4. **Backup**: Provide a `cp` command to backup the original file
5. **Fix**: Output the complete corrected file (no truncation)
6. **Test**: Suggest a command to verify the fix (e.g., `python -m py_compile <file>`)

### Critical Safety Rules (NON-NEGOTIABLE)

1. **READ ANYWHERE, WRITE TO SANDBOX**: You CAN read from ANY file under `~/MAi-RAG-PA/` (except forbidden directories) to analyze the live code. You MUST write all fixes and the `SELF_HEALING_LOG.md` ONLY to `~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/` or `~/MAi-RAG-PA/workspace/`.

2. **MIRROR DIRECTORY STRUCTURE**: When writing a fix to the sandbox, preserve the original path structure relative to the project root (e.g., if you read `~/MAi-RAG-PA/app/main.py`, write the fix to `~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/app/main.py`). NEVER create subdirectories containing "dev-sandbox" or "MAi-RAG-DEV" inside the sandbox.

3. **INFINITE LOOP PREVENTION**:
   - NEVER recursively copy or move directories.
   - NEVER create symbolic links.
   - Maximum directory depth: 10 levels.
   - Maximum files per operation: 50 files.
   - If you need to process more than 50 files, ask for explicit approval.

4. **FORBIDDEN PATHS** (NEVER access, read, or write to these):
   - `venv/`, `env/`, `.venv/`
   - `node_modules/`
   - `.git/`
   - `__pycache__/`
   - `memory/`, `storage/`, `models/`
   - `logs/`, `alembic/`, `tests/`, `scripts/`

5. **OPERATION VALIDATION**:
   - Before any file operation, verify the target path is within allowed boundaries.
   - Use `pathlib.Path.resolve()` to get absolute paths.
   - Verify write paths start with `~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/` or `~/MAi-RAG-PA/workspace/`.
   - Verify paths do NOT contain forbidden patterns.

### Path Validation Example

from pathlib import Path

def validate_path(user_path: str) -> Path:
    sandbox_root = Path.home() / "MAi-RAG-PA" / "dev-sandbox" / "MAi-RAG-DEV"
    resolved = Path(user_path).resolve()

    try:
        resolved.relative_to(sandbox_root)
    except ValueError:
        raise ValueError(f"Path {user_path} is outside sandbox")

    path_str = str(resolved)
    forbidden = ["dev-sandbox/dev-sandbox", "venv/", "node_modules/", ".git/", "__pycache__/"]
    for pattern in forbidden:
        if pattern in path_str:
            raise ValueError(f"Path contains forbidden pattern: {pattern}")

    return resolved

### Verification Checklist

Before providing code:
- [ ] Python: `python -m py_compile <filepath>` will pass
- [ ] TypeScript: All imports are valid, hooks are at top level
- [ ] Database: Schema matches queries, uses parameterized arguments
- [ ] API: Pydantic models match request/response structure
- [ ] Frontend: No infinite loops in useEffect, proper cleanup
- [ ] Path validation: All file operations use validated paths

-----------------------------------------------------------------------------------

## Mandatory Citations System

MAi-RAG-P.A. enforces mandatory citations for all knowledge base responses.

**Why:** Citations keep every knowledge-grounded answer traceable to the user's own documents, so claims can be checked at the source instead of taken on faith.

### Citation Format

**Inline Citations:**
- Format: [Source N: filename]
- Example: "blue [Source 1: file.txt]"
- Multiple sources: "blue [Source 1: a.txt], [Source 2: b.txt]"

**End-of-Response References Section:**

At the END of every response that uses knowledge base content, include:

### References
- [Source 1]: filename.pdf, Author (if known), Page X
- [Source 2]: filename.md, Section Y

### Source Attribution Rules

- If information is from knowledge base ONLY: Cite the source(s) as shown above
- If information is from model training ONLY: State "Based on model training data"
- If combining KB and training: Cite KB sources AND state "Combined with model training data"
- If no KB context was provided: State "Based on model training data" at the end

### Citation Placement Rules

- NEVER list sources at the beginning of responses
- ALWAYS integrate citations inline
- Sources are reference material only - do not echo them verbatim as preamble
- At the END of every response that uses knowledge base content, add a References section

-----------------------------------------------------------------------------------

## System Prompt Management

### Single Source of Truth

The system prompt is managed through a unified system:

1. **Default Prompt**: Stored in `app/agents/agent_core.py` as `DEFAULT_SYSTEM_PROMPT`
2. **Custom Prompt**: Saved to SQLite database (`short_term_memory` table, key='system_prompt')
3. **API Endpoint**: `GET /api/settings/system-prompt/default` returns the default from agent_core.py
4. **Frontend**: Fetches from backend API (no hardcoded duplicates)

### System Prompt Components

The default system prompt includes:
- Core identity and behavioral protocols
- Mandatory citation requirements
- Tool-calling instructions (conditionally injected)
- Technical standards
- File creation rules
- Security guidelines
- Architecture separation

### Conditional Injections

**Tool-Calling Instructions:**
- Only injected for models that support tool-calling
- Controlled by `_model_tool_support` dictionary
- Injected when `needs_tools=True` parameter is passed

**Self-Healing Protocol:**
- Only injected for capable models (see Model Capability Gating section)
- Controlled by `is_self_healing_capable()` function
- Injected when model is in `SELF_HEALING_CAPABLE_MODELS` list

**STM Context:**
- Always injected for personalized responses
- Built by `_build_stm_context_for_prompt()` function
- Includes user facts, preferences, and recent interactions

-----------------------------------------------------------------------------------

## File Creation with Overwrite Protection

### Automatic Numbering

When creating a file that already exists:
1. System checks if filename exists in workspace/
2. If exists, adds numbered suffix: `filename_1.ext`, `filename_2.ext`, etc.
3. Continues until unique name found
4. Logs the name change for transparency

### Example

- Request: "Create Philosophy.txt"
- If `Philosophy.txt` exists → creates `Philosophy_1.txt`
- If that exists → creates `Philosophy_2.txt`
- And so on...

### File Creation Methods

**Method 1: Explicit [FILE] Prefix (Most Reliable)**

    [FILE] Create notes.txt with content: Hello World
    [FILE] Write adder.py: def add(a,b): return a+b

**Method 2: Natural Language (Smart Regex)**

    Save these notes to my_notes.txt: Hello World
    Write a Python function named adder.py that adds two numbers

### Verification Pipeline

1. **Generate**: LLM creates content
2. **Verify**: Check syntax (ast.parse for Python, json.loads for JSON)
3. **Fix**: If verification fails, retry up to 3 times
4. **Save**: Write verified content to workspace/

-----------------------------------------------------------------------------------

## API Key Management

### Getting Your API Key

- **Automatic**: Frontend retrieves it automatically on first load
- **Manual**: curl http://localhost:8000/api/auth/auto-key
- **Generate New**: curl -X POST http://localhost:8000/api/auth/generate-key

### Important Notes

- Each installation has a unique API key
- auto-key responds on localhost only by default; access from other machines requires MAI_ALLOW_REMOTE_AUTOKEY=1 in .env
- The key is stored in memory/memory_store.db
- If you reinstall, you'll get a new key
- The frontend handles this automatically

-----------------------------------------------------------------------------------

## Critical Code Patterns

### Database Operations (ALWAYS use context managers)

mgr = get_sqlite_manager()
with mgr.get_cursor() as cur:
    cur.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
    result = cur.fetchone()

### LLM Invocation (ALWAYS use cached instances)

llm = _get_llm(model_name, temperature=0.7)
response = llm.invoke(prompt)

### API Endpoints (ALWAYS validate input)

@app.post("/api/example")
async def example_endpoint(request: ExampleRequest, api_key: str = Depends(verify_api_key)):
    # request is already validated by Pydantic
    # api_key is already verified
    pass

### Common Error Patterns & Fixes

**ImportError: No module named 'X'**
- Check if file exists in app/ directory
- Verify import path is correct
- Check for circular imports

**sqlite3.OperationalError: no such column**
- Verify column exists in schema (check sqlite_memory.py _create_tables())
- Check for typos in column name
- May need database migration

**Pydantic ValidationError**
- Check request model definition in main.py
- Verify field types match
- Check for missing required fields

**WebSocket Connection Failed**
- Check if ws_manager is initialized
- Verify frontend URL matches backend
- Check for CORS issues

**Chat History Not Persisting**
- Verify frontend is calling save endpoints (check browser Network tab)
- Check database: sqlite3 ~/MAi-RAG-PA/memory/memory_store.db "SELECT COUNT(*) FROM chat_messages;"
- Verify API key is set correctly
- Check backend logs for save errors

-----------------------------------------------------------------------------------

<p align="center">
  <strong>MAi-RAG-P.A. Architecture — Privacy-First, Self-Healing, Production-Ready</strong>
</p>

<p align="center">
  Version 2.0.0 | Updated October 2026
</p>
