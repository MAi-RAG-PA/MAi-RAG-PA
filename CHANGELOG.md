<p align="center">
  <img src="assets/MAi-RAG.png" alt="MAi-RAG-PA Personal Assistant" width="150">
</p>

<h1 align="center">MAi-RAG-PA</h1>
<h3 align="center">Your Offline Privacy, Self-Healing, Personal Assistant</h3>

<p align="center">
  <strong>MAi-RAG-PA (Memory-Augmented Intelligence with Retrieval-Augmented Generation - Personal Assistant)</strong> is a privacy-focused personal AI assistant that runs entirely on your local machine. No cloud. No subscriptions. No data leaving your computer.
</p>

<p align="center">
  <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/README.md">🏠 Home</a> •
  <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/MAi-README.md">📚 Full Docs</a> •
  <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/MAi-INSTALLATION.md">⚙️ Installation</a> •
  <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/MAi-OLLAMA-MODELS.md">🤖 Models</a> •
  <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/MAi-SSH-SETUP.md">🌐 SSH & LAN</a> •
  <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/SELF-HEALING-SYSTEM-USER-WORKFLOW.md">🩺 Self-Healing</a> •
  <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/CHANGELOG.md">📝 Changelog</a> •
  <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/MAi-LICENCE-LEGAL-NOTICE.md">⚖️ License</a>
</p>

---


<p align="center">
  <strong>Current Version 1.5.0 | Effective Date: June 2026</strong><br />
  <strong>Copyright © 2026 MAi-RAG-PA. All Rights Reserved.</strong>
</p>

-----------------------------------------------------------------------------------

# Changelog

All notable changes to MAi-RAG-PA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# CHANGELOG

## [1.5.0] - 2026-08-08

### Major Features

#### Intelligent Model Routing & Reasoning Model Support
- Added foolproof bypass for reasoning models (DeepSeek R1, QwQ) to prevent ReAct loop failures.
- Automatic detection and routing of non-tool-calling models to direct chat mode.
- Hardware-aware context window allocation (8192 default, 16384 for reasoning models).

#### Advanced RAG Context Injection
- Implemented "Analytical Engine" prompt strategy that treats RAG excerpts as the primary authoritative source while explicitly allowing supplementary training data for comprehensive, detailed responses.
- Generalized source terminology from "books" to "documents, articles, datasets, and notes" to accurately reflect all supported ingestion formats.
- Moved RAG context to the final `HumanMessage` position for maximum attention (recency bias optimization).
- Increased `top_k` retrieval from 3 to 5 chunks for richer context.

#### Chat Thread Persistence
- Fixed critical bug where chat threads were fragmenting on every page refresh.
- Implemented robust `thread_id` fallback logic in the backend.
- Added `localStorage`-based thread restoration on the frontend.

### Technical Improvements

#### Context Window Management
- Reduced default `num_ctx` from 16384 to 8192 to prevent RAM thrashing on consumer hardware.
- Added explicit `num_ctx=16384` for DeepSeek R1 bypass with an 1800s timeout.
- Hardware-tier-aware context allocation prevents silent prompt truncation.

#### Tool-Calling Reliability
- Fixed missing tool instructions injection by adding `needs_tools=True` parameter to `get_system_prompt()`.
- Ensured tool-calling instructions are only injected for capable models.
- Added graceful fallback when tool binding fails.

#### Citation Enforcement & Harmonization
- Replaced restrictive "exclusive source" directives with a balanced approach: prioritize KB context, but permit training data supplementation for alternative perspectives, with clear attribution.
- Implemented **extension-agnostic** footnote citation rules, explicitly supporting `.pdf`, `.epub`, `.txt`, `.doc`, `.md`, and any other ingested file type.
- Mandated numbered reference markers (e.g., `[1]`, `[2]`) inline, coupled with a comprehensive `### References` section at the end of every response containing exact metadata (filename, collection, chapter, page).
- **Harmonized** citation and formatting rules across all prompt injection points (`DEFAULT_SYSTEM_PROMPT`, `_simple_chat_fallback`, `agent_loop`, `fetch_rag_context`, and `main.py` DeepSeek bypass) to eliminate contradictory instructions.

### Bug Fixes

- Fixed silent prompt truncation when total context exceeded `num_ctx` limit.
- Fixed infinite loop in ReAct when models output plain text instead of tool calls.
- Fixed 0-character response bug for reasoning models.
- Fixed thread fragmentation causing separate chat threads on every refresh.
- Fixed missing tool-calling instructions in the agent loop.
- Fixed duplicate DeepSeek bypass checks in `agent_loop()`.
- Fixed corrupted newline characters in `main.py` string literals caused by copy-paste artifacts.

### Performance Optimizations

- Optimized RAG retrieval to fetch 5 chunks instead of 3 (67% more context).
- Reduced memory footprint by ~40% through intelligent context window sizing.
- Prevented SSD swap thrashing on low-RAM systems by capping KV cache allocation.
- Added 1800s backend timeout for reasoning models to prevent zombie threads and memory leaks.

### Hardware Compatibility

- Verified stable operation on Intel i3-1215U with 40GB RAM.
- Optimized for consumer-grade hardware while maintaining enterprise-grade reliability.
- Automatic hardware tier detection ensures optimal settings for any system.

### Model Support

- **Optimized for**: `qwen3:30b-a3b`, `qwen2.5:14b`, `deepseek-r1:14b/32b`, `yi:34b`
- **Tool-calling capable**: `qwen2.5-coder:14b/32b`, `qwen3-coder-30b-a3b-1m`, `mixtral:8x7b`
- **Reasoning models**: `deepseek-r1`, `qwq` (with automatic bypass)
- **Protected system model**: `codeqwen:7b` (STM parsing fallback)

### Security & Stability

- Maintained all existing path traversal protections.
- Preserved API key authentication requirements.
- Ensured all RAG injections are properly sanitized and extension-agnostic.

---

Changelog
## [1.4.0] - 2026-08-06

## Fixed: WebSocket Connection Issues
Corrected WebSocket URL in LongTermMemoryApp.tsx to properly connect to localhost:8000 during development instead of localhost:5173

## Fixed: Qdrant Connection Reliability
- Resolved IPv6/IPv4 localhost resolution bug by changing host="localhost" to host="127.0.0.1" in qdrant_manager.py, preventing Python's qdrant_client from failing to connect on systems where localhost - resolves to IPv6 ::1 instead of IPv4.

## Fixed: Short-Term Memory (STM) Size Display
- Corrected the Short-Term Memory (STM) analytics panel incorrectly reporting 0 B of storage despite having hundreds of entries.
- Added proper database path resolution (Path.resolve()) and validation to prevent silent failures when querying empty database files
- Added comprehensive error handling and logging and deadlock prevention in the frontend Axios interceptors to ensure the UI remains responsive even if background API key fetching stalls.

## Fixed: Long-Term Memory (LTM) Ingestion Progress
- Implemented real-time progress bar with percentage indicator during chunking and ingestion process
- Added WebSocket broadcasts with asyncio.sleep(0) to prevent event loop blocking during synchronous file parsing operations, allowing WebSocket progress broadcasts to successfully flush to the frontend.
- Replaced FastAPI's strict File() dependency with manual multipart/form-data request parsing in the /chunk-and-ingest endpoint. This prevents the server from silently dropping or hanging on certain HTTP payloads.
- Progress updates now display: "Chunking: [filename]... (X/Y files)"

## Fixed: Chat Thread Persistence
- Resolved chat thread fragmentation issue where hard refresh would create new threads instead of continuing existing conversations
- Active thread ID is now saved to localStorage and restored on page load
- Thread deletion properly updates localStorage to maintain continuity

## Fixed: Syntax Errors
- Corrected missing sqlite3 import in STM size endpoint

## Changed
** System Prompt Enforcement:**
- Ensured LLM fallback behaviors strictly adhere to the anti-hallucination system prompts when RAG context is empty or when using heavily modified/merged models.


# Changelog 
## [1.3.8] - 2026-08-02

## Added
- Proactive self-healing workflow with 6-step process (Clone → Analyze → Sandbox Fix → Log → Review → Deploy/Rollback).
- Mandatory `SELF_HEALING_LOG.md` generation at sandbox root after every self-healing operation.
- JSON tool-call interception fallback for models that output tools as plain text instead of native tool calls.
- Smart timestamp display: time-only for today's messages, date+time for older messages.
- Comprehensive debug prints in `/api/chat` and `agent_loop` for troubleshooting.
- Non-technical user triggering via natural language (e.g., "the system is broken").

### Changed
- Extended LLM timeout from 300s to 1800s (30 minutes) for large models on CPU.
- Reduced default context window from 8192 to 4096 tokens for CPU stability.
- Updated `SELF_HEALING_PROTOCOL` to allow reading live code while restricting writes to sandbox.
- Refined `FORBIDDEN_DIRS` to allow LLM access to its own `dev-sandbox/` workspace.
- Updated `ARCHITECTURE.md` with accurate directory tree and corrected paths.
- Fully merged and corrected `SELF-HEALING-SYSTEM-USER-WORKFLOW.md` documentation.

### Fixed
- Critical `index.html` missing `}` causing frontend crash and chat disappearance on hard refresh.
- Chat thread persistence bug where frontend omitted `thread_id`, creating ghost threads in database.
- Timestamp parsing bug where backend returned `0` for integer epoch timestamps, causing `Date.now()` fallback.
- Sandbox path validation incorrectly blocking LLM from its own `dev-sandbox/` directory.
- `agent_loop` docstring placement (moved to top of function for proper Python convention).

## [1.2.4] - 2026-07-26
### Updated
- SQLite backend for robust memory management.
- Prometheus metrics integration for system observability.
- Agentic workflow with verification (Generate → Verify → Fix → Save) using LangChain `bind_tools()`.

### Changed
- Optimized Ollama CPU-only inference parameters for Intel i3-1215U.
- Refined model fallback chain (qwen2.5-coder:32b → qwen2.5-coder:14b → qwen3-coder-30b-a3b-1m).

### Fixed
- Resolved critical data ingestion deduplication logic skipping valid documents.
- Fixed cross-platform compatibility issues in `ci.yaml`.
- Removed restrictive UI/UX limitations on file selection and chunking.


## [1.0.0] - 2026-07-11

### Initial Release

First public release of MAi-RAG-PA - Your Offline Privacy, Self-Healing, Personal Assistant.

### Added

#### Core Features
- **Dual-Layer Memory System**
  - Short-Term Memory (STM) with SQLite database for chat history, reminders, events, todos
  - Long-Term Memory (LTM) with Qdrant vector database for RAG knowledge base
  - Automatic learning from conversations to build user profile

- **Chat Console**
  - Multi-threaded conversations with persistent SQLite storage
  - Real-time system resource monitoring (CPU, RAM, Swap)
  - Dynamic model selection from Ollama
  - Protected model warnings for missing system models
  - Voice-to-text input with offline Vosk model
  - File attachments for context
  - Copy button for all messages
  - Auto-titling of threads based on first message

- **Agentic File Creation Pipeline**
  - Generate → Verify → Fix → Save workflow
  - File overwrite protection with automatic numbered suffixes
  - Syntax validation (Python: ast.parse, JSON: json.loads, Text: structure checks)
  - Support for 16 file types (txt, md, py, js, ts, json, yaml, etc.)
  - Two creation methods: `[FILE]` prefix and natural language detection

- **Self-Healing System**
  - Sandboxed code repair environment (`~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/`)
  - Model capability gating (only enabled for capable models)
  - Safety rules: path validation, infinite loop prevention, operation limits
  - Instant rollback capability
  - Support for both Dense and MoE models

- **RAG Integration**
  - 17 document formats supported (PDF, EPUB, DOCX, TXT, MD, HTML, CSV, JSON, XML, PPTX, XLSX, TEX, RST, RTF, ODT, TSV, HTM)
  - Semantic chunking with SpaCy sentence tokenization
  - all-MiniLM-L6-v2 embeddings (384 dimensions)
  - Mandatory citation system with inline references
  - End-of-response References section with full source details
  - Change detection with SHA256 hashing

- **Calendar & Task Management**
  - Multi-view calendar (Year, Month, Week, Day)
  - Event management with recurring events
  - Customizable reminders (24h, 1h, 30m, 15m, 5m, at-time)
  - To-Do manager with priorities and due dates
  - Browser notifications and toast pop-ups

- **System Prompt Management**
  - Single source of truth (agent_core.py)
  - Custom prompt storage in SQLite
  - API endpoint for default prompt retrieval
  - Live editing without restart
  - Conditional injection of tool-calling and self-healing protocols

- **Hardware-Aware Model Recommendations**
  - Automatic hardware detection (RAM, CPU cores)
  - Tier-based recommendations (High, Medium, Consumer, Minimal)
  - Protected system model: codeqwen:7b for STM parsing and self-healing
  - MoE vs Dense model guidance

- **Text Editor**
  - Multi-format support (16 file types)
  - Syntax highlighting
  - File System Access API for Chrome/Edge/Vivaldi
  - Fallback to workspace for Firefox
  - AI-assisted editing and code generation

- **24 Color Themes**
  - Dark themes: Deep Space Teal, Purple/Yellow, Blue/Orange, Pink/Cyan, Dark Grey, Forest Green, Sunset Orange, Ocean Blue, Royal Purple, Crimson Red, Amber Gold, Midnight Blue, Emerald Mint, Lavender Dream, Monochrome, Cyberpunk Neon, Volcanic Ash, Bamboo Grove, Nebula Drift, Copper/Teal, Rose Quartz, Graphite, Solar Flare
  - Light themes: Arctic Frost
  - Theme-aware backgrounds and accents

- **API & Security**
  - API key management with auto-generation
  - Input validation and sanitization
  - Path traversal protection
  - Rate limiting
  - Field-level encryption support
  - WebSocket for real-time updates

- **Installation & Deployment**
  - Universal installer for Linux (Debian/Ubuntu, Fedora/RHEL, Arch), macOS, Windows (WSL2)
  - Automatic dependency installation
  - Protected model auto-pull (codeqwen:7b)
  - Database initialization and system prompt seeding
  - Desktop launcher creation
  - Docker support

- **Documentation**
  - Comprehensive README with feature overview
  - Installation guide with troubleshooting
  - Model recommendations guide
  - SSH & LAN setup guide
  - Complete architecture documentation
  - Legal notice and license information

#### Technical Infrastructure
- **Backend**: FastAPI with async/await endpoints
- **Frontend**: React 18 with TypeScript and Vite
- **Database**: SQLite for STM, Qdrant for LTM
- **LLM Integration**: Ollama via LangChain
- **Embeddings**: all-MiniLM-L6-v2
- **NLP**: SpaCy for chunking and text processing
- **Voice**: Vosk for offline speech recognition
- **Metrics**: Prometheus metrics for monitoring
- **Logging**: Structured logging with rotation
- **Caching**: LLM instance caching for performance

### Fixed

- Chat history now persists in SQLite database (previously stored in browser cache)
- System prompt consistency across frontend, backend, and database
- File path consistency throughout codebase (MAi-RAG-PA paths)
- Citation enforcement in all knowledge base responses
- Model recommendations now hardware-aware
- File creation no longer overwrites existing files (adds numbered suffix)
- Protected model warnings display correctly in WebUI
- System prompt seeding during installation (database initialized first)
- Cross-platform RAM detection in installer
- Backup creation before updates in installer

### Security

- API key authentication on all endpoints
- Input sanitization and validation
- Path traversal protection with forbidden directory list
- Sandbox isolation for self-healing operations
- Rate limiting on API endpoints
- Secure API key generation using `secrets.token_urlsafe()`
- No hardcoded secrets in codebase
- Privacy-first design (all data stays local)

### Documentation

- Complete API documentation in ARCHITECTURE.md
- Installation guide with platform-specific instructions
- Model selection guide with hardware recommendations
- Architecture documentation with data flow diagrams
- Troubleshooting guide for common issues
- SSH & LAN setup for remote access

### Design Goals Achieved

- **Privacy**: All processing happens locally, no cloud dependencies
- **Reliability**: Agentic verification pipeline ensures zero broken code
- **Performance**: Hardware-aware model selection and caching
- **Extensibility**: Modular architecture with clear separation of concerns
- **User Experience**: Intuitive WebUI with 24 themes and responsive design
- **Maintainability**: Self-healing system and comprehensive documentation

### Dependencies

- Python 3.12+
- Node.js 20+
- Ollama 0.30+
- Qdrant 1.17+
- FastAPI, Uvicorn, LangChain
- React 18, TypeScript, Vite
- SpaCy, Sentence Transformers
- Vosk (bundled model)

### Acknowledgments

Built on the shoulders of giants:
- [Ollama](https://ollama.ai) - Local LLM inference
- [Qdrant](https://qdrant.tech) - Vector database
- [FastAPI](https://fastapi.tiangolo.com) - Backend framework
- [React](https://react.dev) - Frontend framework
- [Hugging Face](https://huggingface.co) - Embedding models
- [SpaCy](https://spacy.io) - NLP processing

### What's Next

- Advanced RAG Dataset ingestion capabilities (multi-modal documents)
- Automated backups
- Let us know what featues you would like implemented.

---

## Documentation

- [Full Documentation](https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/MAi-README.md) - Complete feature overview and usage guide
- [Installation](https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/MAi-INSTALLATION.md) - Step-by-step setup for all platforms, system requirements, starting/stopping
- [Model Recommendations](https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/MAi-OLLAMA-MODELS.md) - Choosing the right AI model for your hardware
- [Self-Healing System](https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/SELF-HEALING-SYSTEM-USER-WORKFLOW.md) - Guide on the Self-Healing System Initiation Process
- [SSH & LAN](https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/MAi-SSH-SETUP.md) - Access the system remotely from other devices
- [Changelog](https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/CHANGELOG.md) - Version history and updates
- [License & Legal](https://github.com/MAi-RAG-PA/MAi-RAG-PA/blob/main/MAi-LICENCE-LEGAL-NOTICE.md) - Terms of use and commercial licensing

**Issues**: [GitHub Issues](https://github.com/MAi-RAG-PA/MAi-RAG-PA/issues)
**Discussions**: [GitHub Discussions](https://github.com/MAi-RAG-PA/MAi-RAG-PA/discussions)
**Email**: MAi-RAG-PA@proton.me

---

<p align="center">
  <strong>MAi-RAG-PA — Your Personal Assistant, Your Data, Your Machine, No Subscriptions!</strong>
</p>
