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
  <a href="MAi-LICENCE-LEGAL-NOTICE.md">📄 License</a>
</p>

<p align="center">
  <strong>Version 1.0 | Effective Date: June 2026</strong><br />
  <strong>Copyright © 2026 MAi-RAG-PA. All Rights Reserved.</strong>
</p>

<h3 align="center">How MAi-RAG-PA Works</h3>

-----------------------------------------------------------------------------------

### Knowledge Base Integration

   **Every time you send a query, MAi-RAG-PA automatically triggers a database search. The LLM receives:**

   1. **Your knowledge base** (injected as system message with source citations)
   2. **Its own training data** (built into the model)
   3. **System prompt instructions** to use retrieved information when relevant

   **The LLM:**
   1. Reads retrieved documents from Long-Term Memory
   2. Decides if they're relevant
   3. Combines them with its own knowledge
   4. Generates responses with citations when appropriate

  **Benefits:**
   - Grounded responses based on your actual documents
   - Fallback to general knowledge when needed
   - Automatic citation tracking
   - No manual context management required

-----------------------------------------------------------------------------------

## Features (UI Walkthrough)

### 1. Navigation Menu (Top Header)

   **The sticky header provides instant access to all system functions:**
   - **Logo Click**: Instantly scrolls to the top of the page
   - **Section Links**: Jump directly to Chat Console, Notes, Memory, Planner, or Settings
   - **Theme Selector**: 24 unique color themes (Dark Space Teal, Cyberpunk Neon, Arctic Frost, etc.)
   - **Start/Stop Buttons**: Control MAi-RAG-PA backend service directly from the UI

### 2. Chat Console (The Brain)

   **Your primary interface for AI interaction with multi-threaded conversations and system monitoring.**


#### Threads Pane (Left Sidebar)
   - **Conversation History**: All chats saved in local SQLite database
   - **Persistence**: Survives browser sessions and device changes
   - **Auto-Title**: Threads automatically name themselves based on first message
   - **Thread Management**: Create new chats, delete old ones with one click

#### System Resources Monitor
   **Real-time visibility into your machine's health:**
   - **CPU Usage**: Live percentage with color-coded progress bar
   - **RAM Usage**: Current vs. total available memory
   - **Swap Usage**: Monitor virtual memory to prevent crashes
   - **Auto-Refresh**: Updates every 30 seconds

#### Model Selector
   - **Dynamic Loading**: Fetches models live from Ollama's API
   - **Smart Filtering**: Embedding models automatically hidden
   - **Set as Default**: Choose permanent default model
   - **Hot-Swapping**: Change models without restarting

#### Chat Interface
   - **Multi-Turn Conversations**: Context-aware responses with memory
   - **Clean Rendering**: Automatic stripping of AI reasoning tokens
   - **Abort Button**: Stop long-running generations mid-stream
   - **File Creation**: Use `[FILE]` prefix or natural language to generate files

#### Voice-to-Text Input
   - **Offline Operation**: Uses bundled Vosk model (vosk-model-small-en-us-0.15)
   - **16kHz Mono Recording**: Optimized for speech recognition
   - **Visual Feedback**: Microphone button pulses red while recording
   - **Auto-Insert**: Transcribed text automatically added to input field

#### File Attachments
   - Attach PDF, DOCX, TXT, MD, HTML files for context
   - AI reads and incorporates file content into conversation
   - Useful for document analysis and information extraction

### 3. Text Editor (Notes & Code)

   **Multi-format editor supporting 16 file types:**
   - **Text & Docs**: .txt, .md, .html, .css, .xml, .ini, .cfg, .log
   - **Programming**: .py, .js, .ts, .sh, .sql
   - **Data**: .json, .yaml, .yml, .toml, .csv

   **Smart File Handling:**
   - **Chrome/Edge/Vivaldi**: Files save directly to original location using File System Access API
   - **Firefox**: Files save to `~/MAi-RAG-PA/workspace/` due to security policies
   - **Syntax Highlighting**: Automatic detection based on file extension
   - **Find Function**: Ctrl+F to search within current file

   **AI-Assisted Editing:**
   - Request code improvements, refactoring, or optimization
   - Generate documentation comments
   - Convert between file formats
   - Find and fix bugs or syntax errors

### 4. Memory System (Dual-Layer Architecture)

#### Long-Term Memory (LTM) - Qdrant Vector Database

   **Your personal knowledgebase that guides AI responses:**

   **Supported Document Formats (17 formats):**
   - **Documents**: PDF, EPUB, DOCX, TXT, RTF, ODT
   - **Web**: HTML, HTM, MD (Markdown)
   - **Data**: CSV, TSV, JSON, XML
   - **Presentations**: PPTX (PowerPoint)
   - **Spreadsheets**: XLSX (Excel)
   - **Academic**: TEX (LaTeX), RST (reStructuredText)
   - **All document processing is handled automatically - no additional system packages required.**

   **How to Use:**
   1. Select existing database or create new one
   2. Upload single file or entire directory (ensure the directory is subject-centric)
   3. Documents automatically chunked and embedded
   4. AI references your documents when answering questions

   **Best Practices:**
   - Organize by topic (Tax-Code-Database, Biology-Database, Finance-Expenses)
   - Use clear, descriptive filenames
   - Separate databases for different subjects speed up searches

   **Technical Details:**
   - **Document Ingestion**: All 17 formats supported
   - **Semantic Chunking**: SpaCy sentence tokenization with overlap
   - **Vector Embeddings**: all-MiniLM-L6-v2 model (384 dimensions)
   - **Persistent Storage**: Qdrant collections organized by topic
   - **RAG Retrieval**: Automatic search with source citations
   - **Rich Metadata**: Author, title, creation date, auto-extracted keywords
   - **Change Detection**: Skip unchanged files using SHA256 hashing

#### Short-Term Memory (STM) - SQLite Database

   **Operational memory that grows with you:**
   - **Chat History**: All conversations with timestamps and thread organization
   - **Calendar Data**: Events, appointments, reminders, tasks
   - **To-Do Lists**: Tasks with priorities and due dates
   - **User Facts**: Information learned from conversations (preferences, role, context)
   - **System Settings**: Custom prompts, heartbeat intervals, notifications

   **Automatic Learning:**
   - Observes patterns in conversations
   - Extracts facts like name, role, preferences
   - Provides personalized responses based on context

### 5. Calendar Planner

   **Full-featured time management system:**

   **Multi-View Calendar:**
   - **Year View**: All 12 months at a glance
   - **Month View**: Detailed grid with event pills
   - **Week View**: 7-day cards with hour-by-hour breakdown
   - **Day View**: Full hourly timeline with action buttons

   **Event Management:**
   - Create/Edit/Delete events with rich metadata
   - Recurring events (daily, weekly, monthly, yearly)
   - End date or indefinite recurrence
   - Edit or delete all instances at once

   **Alerts & Notifications:**
   - Customizable reminders (24h, 1h, 30m, 15m, 5m, at time)
   - Browser notifications when events are due
   - Upcoming events panel (next 15 events)
   - Toast notifications (non-intrusive pop-ups)

   **To-Do Manager:**
   - Task lists with priorities (low, medium, high)
   - Due dates with overdue/upcoming filters
   - Integration with calendar events

### 6. Assistant Settings

   **Control center for MAi-RAG-PA's behavior and maintenance:**

#### System Doctor (One-Click Diagnostics)

   **Comprehensive health check:**

   **Diagnostic Checks:**
   - Ollama connectivity and model count
   - Qdrant vector database status
   - SQLite database integrity
   - Workspace directory permissions
   - Frontend build existence
   - Disk space availability
   - Python dependency verification

   **Auto-Fix Capabilities:**
   - Rebuilds corrupted virtual environments
   - Restarts unresponsive services
   - Clears orphaned Qdrant blobs
   - Re-pulls missing Ollama models

   **Health Score:** 0-100% with color-coded status (green ≥80%, yellow ≥60%, red <60%)

#### Notification Schedule
   - Interval toggles (24h, 1h, 30m, 15m, 5m, at-time)
   - Quiet hours to suppress notifications
   - Browser permission for native notifications

#### System Prompt Editor

   **Customize AI behavior and personality:**
   - **Default Prompt**: Comprehensive, production-ready system prompt pre-loaded
   - **Live Editing**: Modify and save instantly (no restart required)
   - **Persistent Storage**: Custom prompts saved to SQLite

   **Customization Tips:**
   - Edit to match your specific needs
   - Add domain-specific instructions
   - Include company terminology
   - Adjust tone (formal, casual, technical)

#### Heartbeat Configuration

   **Background process for system health monitoring:**
   - **Interval Setting**: Configure check frequency (default: 5 minutes)
   - **Silent Operation**: Runs without user intervention
   - **Alert Trigger**: Notifies if critical issues detected

   **Monitors:**
   - Ollama responsiveness
   - Qdrant availability
   - Database connection
   - File system access
   - Memory usage

-----------------------------------------------------------------------------------

## Agentic Workflow: Generate → Verify → Fix → Save

   **Zero broken code ever reaches your filesystem.**

   MAi-RAG-PA's signature feature — a deterministic verification pipeline ensuring every AI-created file is syntactically valid and structurally sound.

### The Pipeline

   **1. GENERATE**
   - LLM creates content based on your request
   - Uses selected model and system prompt
   - Incorporates conversation context

   **2. VERIFY**
   **Content checked against strict rules:**
   - **.py files** → `ast.parse()` guarantees valid Python syntax
   - **.json files** → `json.loads()` guarantees valid JSON structure
   - **.txt/.md files** → Structure checks (paragraphs, capitalization, grammar)
   - **Other files** → Basic non-empty check

   **3. FIX (if needed)**
   - If verification fails, error fed back to LLM
   - LLM attempts correction
   - Up to 3 retry attempts
   - Each attempt logged for debugging

   **4. SAVE**
   - Only verified content written to disk
   - Files saved to `~/MAi-RAG-PA/workspace/` (or original location in Chrome/Edge)
   - User receives confirmation with file path

### Supported File Types

| Extension | Verification Method | What's Checked |
|-----------|---------------------|----------------|
| .py | ast.parse() | 100% Python syntax validity |
| .json | json.loads() | Valid JSON structure |
| .txt | Heuristic rules | Paragraph breaks, capitalization, typo detection |
| .md | Heuristic rules | Same as .txt + Markdown-aware structure |
| Other | Basic check | Non-empty content |

### File Creation Methods


   **Method 1: Explicit `[FILE]` Prefix (Most Reliable)**

   [FILE] Create notes.txt with content: Hello World
   [FILE] Write adder.py: def add(a,b): return a+b
   [FILE] Save config.json with {"key": "value"}


   **Pros:** Zero false positives, easy to debug, works with any phrasing
   **Cons:** Requires remembering the prefix


   **Method 2: Natural Language (Smart Regex)**

   - Save these notes to my_notes.txt: Hello World
   - Write a Python function named adder.py that adds two numbers
   - Create config.json with {"app": "MAi-RAG-PA", "version": "1.0"}


   **Pros:** Works with natural language, no prefix required
   **Cons:** Slightly higher risk of false positives

### Self-Correction Example

   **Request:** "Create a Python function with a syntax error"

   **Attempt 1:**
   - Generated: `def broken(  # missing parenthesis`
   - Verified: ✗ SyntaxError: unexpected EOF
   - Action: Feed error back to LLM + retry

   **Attempt 2:**
   - Generated: `def broken(): return 42`
   - Verified: ✓ Syntax OK
   - Action: Save to workspace/

   **Note:** If you explicitly request broken code, the system retries up to 3 times but ultimately fails — preventing broken code from being saved.

-----------------------------------------------------------------------------------

## Troubleshooting (See Also MAi-INSTALLATION.md for a detailed list of troubleshooting issues) 

### Quick Fixes

| Issue | Solution |
|-------|----------|
| MAi-RAG-PA won't start | Is Ollama running? Verify Python 3.12+. Check Node.js 18+. Run System Doctor |
| Slow response times | Use smaller model (7B vs 14B). Close RAM-intensive apps. Reduce context window |
| Models not appearing | Verify Ollama: `curl http://localhost:11434/api/tags`. Pull model: `ollama pull qwen2.5-coder:7b` |
| Ollama connection refused | Ensure `ollama serve` is running |
| Qdrant not available | Run or install Qdrant if not installed |
| Voice transcription fails | Check microphone permissions. Ensure Vosk model exists in `models/vosk-model-small-en-us-0.15/` |
| File not saved to workspace | Check `~/MAi-RAG-PA/workspace/` exists and is writable. Use `[FILE]` prefix |


### System Doctor

   **For persistent issues, click System Doctor in Assistant Settings:**
   1. Runs comprehensive diagnostics
   2. Identifies root causes
   3. Suggests fixes
   4. Generates detailed JSON report for debugging

   See <a href="MAi-INSTALLATION.md">MAi-Installation.md</a> for detailed troubleshooting.

-----------------------------------------------------------------------------------

## Acknowledgments

   **MAi-RAG-PA is built on the shoulders of giants:**

   - **[Ollama](https://ollama.ai)** - Local LLM inference
   - **[Qdrant](https://qdrant.tech)** - Vector database
   - **[all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)** - Embedding model
   - **[FastAPI](https://fastapi.tiangolo.com)** - Backend framework
   - **[React](https://react.dev)** - Frontend framework
   - **[FasterWhisper](https://github.com/SYSTRAN/faster-whisper)** - Offline speech recognition
   - **[Vosk](https://alphacephei.com/vosk/)** - Offline speech recognition
   - **[Sentence Transformers](https://www.sbert.net)** - Text embeddings
   - **[SpaCy](https://spacy.io)** - NLP and chunking

   **And the countless open-source contributors who make this possible.**

   **Documentation:**

   <a href="MAi-README.md">Full Documentation</a> Complete feature overview and usage guide<br />
   <a href="MAi-INSTALLATION.md">Installation</a> Step-by-step setup for all platforms, System requirements, starting/stopping<br />
   <a href="MAi-OLLAMA-MODELS.md">Model Recommendations</a> Choosing the right AI model for your needs<br />
   <a href="MAi-SSH-SETUP.md">SSH & LAN</a> Access the system remotely from other devices via SSH or on the same network<br />
   <a href="MAi-LICENCE-LEGAL-NOTICE.md">Terms of use and commercial licensing</a>

   **Support & Contact:**

   **Issues**: <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/issues">GitHub Issues</a>
   **Discussions**: <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/discussions">GitHub Discussions</a>
   **Email**: MAi-RAG-PA@proton.me

-----------------------------------------------------------------------------------

## 💝 Support MAi-RAG-PA

MAi-RAG-PA is a labor of love developed over thousands of hours. If this software brings value to your life or work, **donations are deeply appreciated** and help fund continued development.

MAi-RAG-PA is free for personal use. If you find it valuable, donations are greatly appreciated:

- **PayPal**: <a href="https://www.paypal.com/ncp/payment/GSTCK29MSGCH4">Grateful for your Contributions</a>

Every donation helps keep MAi-RAG-PA free and continuously improving.

**Commercial Licensing**: For business deployments or enterprise support, please contact: MAi-RAG-PA@proton.me

-----------------------------------------------------------------------------------

<p align="center">
  <strong>MAi-RAG-PA — Your Personal Assistant, Your Data, Your Machine, No Subscriptions!</strong>
</p>

<p align="center">
  Version 1.0.0 | Released June 2026
</p>