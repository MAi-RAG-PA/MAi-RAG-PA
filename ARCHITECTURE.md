# MAi-RAG-PA Complete System Architecture

## System Overview

MAi-RAG-PA is a privacy-focused, offline personal AI assistant with:
- **Dual-Layer Memory**: SQLite (STM) + Qdrant (LTM)
- **Self-Healing Capabilities**: AI-powered code repair in isolated sandbox
- **Agentic File Creation**: Generate → Verify → Fix → Save pipeline
- **Multi-Model Support**: Hardware-aware model recommendations
- **Persistent Storage**: All data in SQLite, survives browser cache clears
- **Protected System Models**: codeqwen:7b for core functionality
- **Mandatory Citations**: End-of-response References section

-----------------------------------------------------------------------------------

## Directory Structure & File Purposes

~/MAi-RAG-PA/
├── app/                          # Backend Python application
│   ├── main.py                   # FastAPI app, ALL endpoints, Pydantic models
│   │                             # - Routes: /api/* endpoints
│   │                             # - Models: Request/response validation
│   │                             # - Orchestration: Connects all components
│   │
│   ├── agents/
│   │   ├── agent_core.py         # LLM interaction layer
│   │   │                         # - get_llm(): Model instantiation & caching
│   │   │                         # - get_system_prompt(): System instructions
│   │   │                         # - process_request(): Main agent loop
│   │   │                         # - Tool definitions for file operations
│   │   │
│   │   └── verifier.py           # Code validation (ast.parse for Python)
│   │
│   ├── memory/
│   │   ├── sqlite_memory.py      # SQLite database operations
│   │   │                         # - SQLiteMemoryManager class
│   │   │                         # - Tables: chat_threads, chat_messages, reminders,
│   │   │                         #           events, todos, user_profile, notes
│   │   │                         # - Methods: get, save_, delete_*
│   │   │
│   │   └── qdrant_manager.py     # Qdrant vector database operations
│   │                             # - QdrantMemoryManager class
│   │                             # - Collections: One per document category
│   │                             # - Methods: ingest_documents(), search(), etc.
│   │
│   ├── rag/
│   │   ├── retriever.py          # RAG retrieval logic
│   │   │                         # - AdvancedRetriever class
│   │   │                         # - Query expansion, deduplication
│   │   │
│   │   ├── rag_server.py         # RAG-specific endpoints (/api/rag/*)
│   │   │
│   │   ├── rag_core.py           # Core RAG operations
│   │   │
│   │   ├── context_manager.py    # Context window management
│   │   │                         # - Token counting, truncation
│   │   │
│   │   └── model_manager.py      # Model selection & fallback logic
│   │
│   ├── security/
│   │   ├── auth.py               # API key authentication
│   │   │                         # - verify_api_key() dependency
│   │   │
│   │   ├── encryption.py         # Field-level encryption
│   │   │                         # - FieldEncryptor class
│   │   │
│   │   ├── input_validation.py   # Input sanitization
│   │   │                         # - sanitize_string(), validate_path()
│   │   │
│   │   └── rate_limiter.py       # API rate limiting
│   │
│   ├── utils/
│   │   └── structured_logging.py # Logging configuration
│   │
│   ├── websocket_manager.py      # WebSocket connections
│   │                             # - ConnectionManager class
│   │                             # - Broadcasts: heartbeat, notifications
│   │
│   └── metrics.py                # Prometheus metrics
│                                 # - REQUEST_COUNT, MODEL_DURATION, etc.
│
├── dev-sandbox/                  # Self-healing workspace (DYNAMICALLY CREATED)
│   └── MAi-RAG-DEV/              # Staging environment (created on-demand)
│
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── api/                  # API client modules
│   │   │   ├── client.ts         # Axios instance with auth
│   │   │   ├── websocket.ts      # WebSocket client
│   │   │   └── voice.ts          # Voice transcription
│   │   │
│   │   ├── components/           # React components
│   │   │   ├── ChatConsoleApp.tsx
│   │   │   ├── ShortTermMemoryApp.tsx
│   │   │   ├── LongTermMemoryApp.tsx
│   │   │   ├── CalendarPlannerApp.tsx
│   │   │   └── ...
│   │   │
│   │   ├── hooks/                # Custom React hooks
│   │   │   └── useChat.ts        # Chat state management
│   │   │
│   │   └── App.tsx               # Main app component
│   │
│   └── dist/                     # Built frontend (DO NOT MODIFY)
│
├── memory/
│   └── memory_store.db           # SQLite database file
│
├── models/                       # Local ML models
│   └── all-MiniLM-L6-v2/         # Embedding model
│
└── workspace/                    # User files & AI workspace

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

# LTM Operations
POST /api/memory/qdrant/chunk-and-ingest       # RAG ingestion
GET  /api/memory/qdrant/status                 # Qdrant status

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
- **chat_threads** (id TEXT PK, title TEXT, created_at, last_message_at)
- **chat_messages** (id TEXT PK, thread_id FK, role, content, timestamp, model, filename)
- **reminders** (id TEXT PK, text, due_time, priority, completed, created_at, alert_type, alert_sound)
- **events** (id TEXT PK, title, description, start_time, end_time, category, is_recurring, recurrence_type, recurrence_days, recurrence_end_date)
- **todos** (id TEXT PK, title, description, priority, completed, due_date, created_at)
- **user_profile** (key TEXT PK, value TEXT, updated_at)
- **notes** (id TEXT PK, title, content, created_at, updated_at)
- **short_term_memory** (key TEXT PK, value TEXT, updated_at) - Stores: system_prompt, default_model, api_key

### Critical Files (DO NOT DELETE)
- `app/main.py` - Core application
- `app/agents/agent_core.py` - AI agent logic, system prompt, self-healing
- `app/memory/sqlite_memory.py` - Database operations
- `frontend/src/App.tsx` - Main React component
- `frontend/src/api/client.ts` - API client
- `frontend/src/components/chat/ChatConsoleApp.tsx` - Chat interface with persistence

-----------------------------------------------------------------------------------

## Data Flow

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
_build_stm_context() → Load user facts, reminders, events
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

User Request → /api/chat with [FILE] prefix
  ↓
Extract filename from query
  ↓
Check if file exists in workspace/
  ↓
If exists: Add numbered suffix (filename_1.txt, filename_2.txt, etc.)
  ↓
agentic_create_file() → Generate → Verify → Fix → Save
  ↓
Return file path and size to user

### System Prompt Management Flow

User clicks "Reset to Default" in WebUI
  ↓
GET /api/settings/system-prompt/default
  ↓
Backend returns DEFAULT_SYSTEM_PROMPT from agent_core.py
  ↓
User edits prompt in textarea
  ↓
User clicks "Save Prompt"
  ↓
POST /api/settings/system-prompt
  ↓
Save to SQLite: short_term_memory table (key='system_prompt')
  ↓
Next request uses updated prompt

-----------------------------------------------------------------------------------

## Protected System Models

MAi-RAG-PA designates certain models as **Protected System Models**. These are automatically installed during setup and are critical for optimal system performance.

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
Automatically installed during setup:

    ollama pull codeqwen:7b

**Warning System:**
If codeqwen:7b is missing, MAi-RAG-PA displays a warning in the WebUI under the model selector:

    ⚠️ codeqwen:7b is not installed. Optimized for consumer hardware. Required for optimal system performance.

**Can I Remove It?**
Yes, but:
- STM parsing will be slower (regex-only fallback)
- Self-healing may not work optimally
- Basic chat will use your primary model (slower on low-end hardware)
- System will show persistent warnings

**Recommendation:** Keep it installed unless you're critically low on disk space.

**API Endpoint:**

    GET /api/system/protected-models - Returns status of protected models

-----------------------------------------------------------------------------------

## Self-Healing System

**The system includes a self-healing capability that allows capable AI models to fix their own code in a safe sandbox environment.**

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

1. **WORKING DIRECTORY**: You are STRICTLY CONFINED to ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/
   - NEVER read, write, or reference files outside this directory
   - NEVER create subdirectories containing "dev-sandbox" or "MAi-RAG-DEV"

2. **INFINITE LOOP PREVENTION**:
   - NEVER recursively copy or move directories
   - NEVER create symbolic links
   - Maximum directory depth: 10 levels
   - Maximum files per operation: 50 files
   - If you need to process more than 50 files, ask for explicit approval

3. **FORBIDDEN PATHS** (NEVER access these):
   - ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/dev-sandbox/
   - ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/venv/
   - ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/node_modules/
   - ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/.git/
   - ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/__pycache__/
   - Any path containing "dev-sandbox/dev-sandbox"

4. **FILESYSTEM TRAVERSAL LIMITS**:
   - Maximum recursive depth: 5 levels
   - Maximum files to read in single operation: 20 files
   - Maximum files to write in single operation: 10 files
   - If you exceed these limits, STOP and request approval

5. **OPERATION VALIDATION**:
   - Before any file operation, verify the target path is within allowed boundaries
   - Use `pathlib.Path.resolve()` to get absolute paths
   - Verify path starts with ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/
   - Verify path does NOT contain forbidden patterns

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

MAi-RAG-PA enforces mandatory citations for all knowledge base responses.

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

## Hardware Detection

The system automatically detects hardware capabilities and recommends appropriate settings:

| Tier | RAM | CPU Cores | Recommended Model | Max Concurrent Requests |
|------|-----|-----------|-------------------|------------------------|
| High | 32GB+ | 8+ | 35b+ | 3 |
| Medium | 16GB+ | 4+ | 14b | 2 |
| Low | 8GB+ | 2+ | 7b | 1 |
| Minimal | <8GB | 1-2 | 3b | 1 |

**Check Your System:**

    curl http://localhost:8000/api/system/hardware -H "X-API-Key: YOUR_API_KEY"

-----------------------------------------------------------------------------------

## API Key Management

### Getting Your API Key

- **Automatic**: Frontend retrieves it automatically on first load
- **Manual**: curl http://localhost:8000/api/auth/auto-key
- **Generate New**: curl -X POST http://localhost:8000/api/auth/generate-key

### Important Notes

- Each installation has a unique API key
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

<p align="center">
  <strong>MAi-RAG-PA Architecture — Privacy-First, Self-Healing, Production-Ready</strong>
</p>

<p align="center">
  Version 1.0.0 | Updated July 2026
</p>
