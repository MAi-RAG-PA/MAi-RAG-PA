# app/agents/agent_core.py  (MAI-PATCH agent_core.py v1)
"""
Agentic Workflow Core: Generate → Verify → Fix → Save
Supports dynamic model selection, system prompt customization, tool-calling, and RAG integration.
"""

import itertools
import json
import logging
import logging.handlers
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import (AIMessage, HumanMessage, SystemMessage,
                                     ToolMessage)
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from app.agents.role_registry import RoleContext, get_registry, tools_for_role
from app.agents.verifier import ContentVerifier
from app.config import Config
from app.memory.sqlite_memory import SQLiteMemoryManager

# Single source of truth for the Ollama endpoint (MAI_OLLAMA_URL / OLLAMA_URL, see app/config.py)
OLLAMA_BASE_URL = Config.OLLAMA_URL.rstrip("/")
# ----- FINAL STABILIZATION: inlined model/runtime profiles -----
# This replaces the external app.agents.model_profiles dependency.
# The framework remains role-agnostic; roles do not need to know these names.

_SUPPORTED_LLM_KWARGS = {
    "temperature",
    "repeat_penalty",
    "num_predict",
    "timeout",
    "num_ctx",
}

_MODEL_PROFILES = {
    "general_chat": {
        "temperature": 0.70,
        "repeat_penalty": 1.10,
        "num_predict": 2048,
        "num_ctx": Config.CONTEXT_WINDOW,
        "timeout": None,
    },
    # Strict deterministic temporal answering.
    # Stabilized for CPU-only local use.
    "temporal_strict": {
        "temperature": 0.35,
        "repeat_penalty": 1.05,
        "num_predict": 500,  # Capped to prevent 45+ min generation times on CPU
        "num_ctx": 8192,  # Reduced to save RAM and speed up prompt processing
        "timeout": 1200,  # Reduced to fail fast if Ollama hangs
    },
    # Small/local fallback class.
    "lite_local": {
        "temperature": 0.45,
        "repeat_penalty": 1.05,
        "num_predict": 1400,
        "num_ctx": 12288,
        "timeout": 3600,
    },
    # 30B/35B-class local patient Pro mode.
    "pro_local_patient": {
        "temperature": 0.35,
        "repeat_penalty": 1.05,
        "num_predict": 1800,
        "num_ctx": 12288,
        "timeout": 7200,
    },
    # Highest-quality but slow local batch mode.
    "batch_high_fidelity": {
        "temperature": 0.35,
        "repeat_penalty": 1.05,
        "num_predict": 2200,
        "num_ctx": 12288,
        "timeout": 9000,
    },
}

_AUTO_PROFILE_RULES = [
    ("qwen2.5:3b", "lite_local"),
    ("qwen2.5:7b", "lite_local"),
    ("qwen3-coder:30b", "pro_local_patient"),
    ("danielsheep/qwen3-coder-30b", "pro_local_patient"),
    ("qwen3.6:35b", "pro_local_patient"),
    ("qwen3:30b", "batch_high_fidelity"),
]


def _auto_profile_for_model(model_name: Optional[str]) -> Optional[str]:
    if not model_name:
        return None

    m = str(model_name).lower()

    for pattern, profile in _AUTO_PROFILE_RULES:
        if pattern in m:
            return profile

    return None


def _resolve_llm_options(
    model_name: Optional[str] = None,
    role_ctx: Any = None,
    profile_name: Optional[str] = None,
    verified_temporal: bool = False,
    needs_tools: bool = True,
) -> Dict[str, Any]:
    """
    Resolve inference options.

    Priority:
      1. explicit profile_name
      2. role_ctx.runtime_profile
      3. model auto-profile
      4. general_chat
    """

    profile = (
        profile_name
        or getattr(role_ctx, "runtime_profile", None)
        or _auto_profile_for_model(model_name)
        or "general_chat"
    )

    if verified_temporal and profile == "general_chat":
        profile = "temporal_strict"

    opts = dict(_MODEL_PROFILES.get(profile, _MODEL_PROFILES["general_chat"]))

    # Active roles with large charters must never silently use 8192 ctx.
    # Stabilized ceiling: 12288, not 16384, to reduce CPU KV-cache pressure.
    if role_ctx is not None:
        opts["num_ctx"] = max(int(opts.get("num_ctx", 8192)), 13312)

        if verified_temporal:
            opts["temperature"] = min(float(opts.get("temperature", 0.35)), 0.35)
            opts["num_predict"] = max(int(opts.get("num_predict", 1800)), 1400)

    # Small local models get a quality-preserving CPU budget.
    # This restores richer synthesis while avoiding the old 16k pressure.
    if model_name:
        mn = str(model_name).lower()
        if "7b" in mn or "3b" in mn:
            opts["num_ctx"] = min(int(opts.get("num_ctx", 13312)), 13312)
            opts["num_predict"] = min(int(opts.get("num_predict", 1600)), 1600)
            if opts.get("timeout"):
                opts["timeout"] = min(int(opts["timeout"]), 4200)

    # Metadata for future engine governance. Not passed to _get_llm.
    opts["_profile"] = profile
    opts["_verified_temporal"] = bool(verified_temporal)
    opts["_needs_tools"] = bool(needs_tools)

    if model_name:
        mn = str(model_name).lower()
        if "qwen3:30b-a3b" in mn or "qwen3.6:35b-a3b-mtp" in mn:
            opts["_think"] = False

    return opts


def _supported_llm_kwargs(opts: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in opts.items() if k in _SUPPORTED_LLM_KWARGS}


# ----- END inlined model/runtime profiles -----


from functools import lru_cache

from app.rag.retriever import AdvancedRetriever


# Role tools are loaded dynamically by app.agents.role_registry.
@lru_cache(maxsize=100)
def get_cached_system_prompt(model: str, needs_tools: bool = False) -> str:
    """Cache system prompts to avoid repeated DB reads."""
    return get_system_prompt(model, needs_tools)


_models_cache = {"names": None}


def get_cached_available_models() -> list:
    """Model names from Ollama. Invalidate with get_cached_available_models.cache_clear().

    Only a SUCCESSFUL lookup is cached: @lru_cache also remembered the empty list returned while
    Ollama was not running yet, and kept returning it until the process was restarted.
    """
    cached = _models_cache["names"]
    if cached is not None:
        return list(cached)
    try:
        import urllib.request

        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
        names = [m["name"] for m in data.get("models", [])]
    except Exception:
        return []
    _models_cache["names"] = names
    return list(names)


get_cached_available_models.cache_clear = lambda: _models_cache.update(names=None)

logger = logging.getLogger(__name__)


def _mai_print(msg: str) -> None:
    """
    Temporary direct-stderr observability helper.

    This bypasses Python logging configuration issues.
    """
    try:
        import sys as _mai_sys_print

        _mai_sys_print.stderr.write(f"[MAI-AGENTS-PRINT] {msg}\n")

        _mai_sys_print.stderr.flush()
    except Exception:
        pass


def _setup_agent_logging() -> None:
    """One console handler and one ROTATING file handler for the app.agents loggers.

    This used to be set up twice (two near-identical blocks), so every line reached the console
    twice, and agent_governance.log grew without limit.
    """
    import sys

    agents_logger = logging.getLogger("app.agents")
    agents_logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [MAI-AGENTS] %(levelname)s %(name)s: %(message)s"
    )

    if not any(
        getattr(h, "_mai_console_handler", False) for h in agents_logger.handlers
    ):
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(logging.INFO)
        console.setFormatter(fmt)
        console._mai_console_handler = True
        agents_logger.addHandler(console)

    if not any(
        getattr(h, "_mai_governance_handler", False) for h in agents_logger.handlers
    ):
        try:
            log_dir = Path(__file__).resolve().parents[2] / "logs"
            log_dir.mkdir(exist_ok=True)
            handler = logging.handlers.RotatingFileHandler(
                log_dir / "agent_governance.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            handler.setLevel(logging.INFO)
            handler.setFormatter(fmt)
            handler._mai_governance_handler = True
            agents_logger.addHandler(handler)
        except (
            OSError
        ) as exc:  # read-only install folder etc.: never let logging stop the import
            logger.warning(
                "Agent governance log file unavailable (%s); logging to the console only.",
                exc,
            )


_setup_agent_logging()


# =============================================================================
# Configuration & Paths
# =============================================================================
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.resolve()
WORKSPACE: Path = PROJECT_ROOT / "workspace"
DEV_SANDBOX: Path = PROJECT_ROOT / "dev-sandbox"
SANDBOX_ROOT: Path = DEV_SANDBOX / "MAi-RAG-DEV"  # Self-healing workspace


def _home_relative(path: Path) -> str:
    """'~/MAi-RAG-PA/workspace/x' style display of a path under the user's home folder."""
    try:
        relative = path.relative_to(Path.home())
    except (ValueError, RuntimeError):
        return str(path)
    return "~" if str(relative) == "." else "~/" + relative.as_posix()


# The folder the application REALLY lives in. The prompts and messages used to say "~/MAi-RAG-PA"
# literally, which is wrong for any other install folder (e.g. your ~/MAi-RAG development copy).
PROJECT_DISPLAY = _home_relative(PROJECT_ROOT)


@contextmanager
def _db():
    """Short-lived READ-ONLY connection to the memory database.

    Closed on exit (the `with sqlite3.connect(...)` pattern only commits, it never closes) and waits up
    to 30 s for a lock instead of 5. Raises if the database does not exist (it is not created as a
    side effect). For WRITES use get_sqlite_manager().
    """
    uri = (PROJECT_ROOT / "memory" / "memory_store.db").resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        yield conn
    finally:
        conn.close()


# =============================================================================
# DEFAULT SYSTEM PROMPT - The "Ultimate" Prompt
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """You are MAi-RAG-PA, a strategic AI assistant with tool-calling and RAG capabilities.

## CORE IDENTITY
- Role: Grand Strategist & Protocol Master
- Mission: 98% accuracy, complete solutions, zero deviation
- Voice: Direct, technical, concise. No filler. Have opinions.
- Priority: User's time is sacred. Quality over speed.

## BEHAVIORAL PROTOCOLS
1. Skip filler ("Great question!", "I'd be happy to help!")
2. Be resourceful - figure it out before asking
3. Anticipate follow-ups, provide context proactively
4. If uncertain, state confidence level
5. Never truncate, never use placeholders ("// rest of code")
6. When using information from knowledge base, ALWAYS cite sources

## CITATION & REFERENCE PROTOCOL (CRITICAL - MANDATORY)
When knowledge base context is provided:
1. Treat KB excerpts as your primary, authoritative source.
2. You MAY supplement with your training data to provide comprehensive, detailed responses, but you MUST clearly distinguish KB information from training knowledge.
3. Use numbered footnote markers (e.g., [1], [2]) at the end of sentences or paragraphs that rely on specific KB sources.
4. NEVER fabricate or invent source filenames or details. Only cite what is explicitly provided in the context.
5. If no relevant KB context is provided, state "Based on model training data" and do not cite any sources.

## END-OF-RESPONSE REFERENCES (MANDATORY)
At the END of every response that uses knowledge base content, you MUST include a "### References" section:

### References
- [1]: filename.ext (e.g., .pdf, .epub, .txt, .doc, .md), Collection, Chapter, Page (exactly as provided in context)
- [2]: filename.ext, Section

Source Attribution Rules:
- You MUST use the exact filename and extension provided in the context, regardless of file type.
- If combining KB and training: Cite KB sources in the References section, and explicitly state "Combined with model training data" in the text.
- If using ONLY training data: State "Based on model training data" and omit the References section.

## TECHNICAL STANDARDS
Code Quality:
- Production-ready, type-hinted, error-handled
- No pseudocode unless requested
- Complete, runnable files (no partial snippets)

Python:
- Context managers for DB transactions
- Parameterized SQL (?)
- Type hints on all functions
- logger.error() with exc_info=True

TypeScript/React:
- Immutable state updates ([...array, item])
- Never mutate state directly
- useEffect cleanup functions
- Defensive: (array || []).map()
- Unique keys in lists

Database:
- Parameterized queries only
- Match schema exactly
- Never SELECT * in production

## FILESYSTEM ACCESS
- Read/write: ~/MAi-RAG-PA/workspace/ and ~/MAi-RAG-PA/
- Forbidden: venv/, node_modules/, .git/, __pycache__/, .env
- Use read_file tool before modifying
- All paths must resolve within ~/MAi-RAG-PA/

## VERIFICATION BEFORE SAVE
- Python: Mentally simulate py_compile
- TypeScript: Check imports (case-sensitive), closed JSX tags, unique keys
- JSON/YAML: Validate structure, quoted keys, no trailing commas

## RESPONSE FORMATS
Technical: Problem → Root Cause → Solution → Explanation → Prevention → References
Creative: Objectives → Options (min 3) → Trade-offs → Recommendation → Next Steps
File Creation: Requirements → Structure → Complete Content → Verification → Success
Research: Question → Sources Consulted → Findings (with citations) → Gaps → Recommendations → References

## PROHIBITED BEHAVIORS
- Filler phrases, excessive apologies
- Incomplete code, "..." placeholders, TODO without explanation
- Hallucinated sources, uncited claims when KB context available
- Silent exceptions (except: pass)
- Mutated state, missing cleanup functions
- Truncated responses, partial context
- Tunnel vision, oversimplification
- Repeating user's question back
- Omitting the References section when KB context was used

## DEPENDENCY RULES
- No new libraries unless approved
- Prefer Python stdlib (pathlib, json, uuid, logging)
- Python 3.12+, Node.js 18+ compatible

## ARCHITECTURE SEPARATION
- main.py: API routing, Pydantic models
- sqlite_memory.py/qdrant_manager.py: DB logic
- agent_core.py: LLM invocation, prompts, tools
- Async/await for all FastAPI endpoints

## GROWTH PROTOCOL
- Every 15 strategies: Refine playbooks, validate scenarios
- Every 20 sessions: Cluster analysis, template refinement
- Every 20 executions: Extract patterns, optimize efficiency

## ERROR RECOVERY
- Check logs first, provide exact output
- Reproduce before fixing
- Root cause analysis, not symptom fixes
- Test immediately after fix
- Always have rollback plan

## PERFORMANCE
- Index frequently queried columns
- Cache expensive operations
- Lazy load components/data
- Frontend bundle < 500KB
- Clear intervals/timeouts/listeners on unmount

## SECURITY
- Never expose sensitive info
- Never execute dangerous commands without approval
- Backup before major changes
- Path traversal protection enforced

Operate with precision and authority. Deviation from these standards is not permitted."""

# =============================================================================
# TOOL CALLING INSTRUCTIONS (LangChain Compatible)
# =============================================================================
TOOL_CALLING_INSTRUCTIONS = """
## TOOL USAGE PROTOCOL
You have access to tools. When you need to read a file, write a file, search, or check the database, you MUST use the provided tools.

CRITICAL: Do NOT output fake commands like "[Shell cmd]:", "```bash", or "<tool_code>".
The system will automatically handle the tool execution when you decide to use one.
If you need to read a file, simply decide to use the `read_file` tool, and the system will invoke it.
If you need to fix a file, use the `write_file` tool after diagnosing the issue.

## TOOL-CALLING PROTOCOL
Note: Tool-calling instructions are injected dynamically only when:
1. The model supports tool-calling (verified via Ollama capabilities)
2. The user request involves file operations
If you are seeing this but cannot use tools, simply generate the requested content as plain text.

When tool-calling IS enabled, follow this workflow:
1. Parse: Extract filename + requirements
2. Plan: Outline structure
3. Generate: Complete content, no truncation
4. Verify: Mental syntax check
5. Confirm: Report path + summary

## FILE CREATION RULES:
- **ONLY create files when the user EXPLICITLY asks to "create a file", "save to file", or "write a file"**
- If the user asks for information, examples, or explanations, provide them directly in the chat - DO NOT create a file unless explicitly requested
- When asked to write content to a file, ALWAYS create the file in the designated workspace or sandbox directory provided in the context.
- Use .txt
"""

# =============================================================================
# SELF-HEALING PROTOCOL (Only for capable models)
# =============================================================================

SELF_HEALING_PROTOCOL = f"""
## PROJECT SELF-HEALING & ARCHITECTURE AWARENESS

You have READ access to the entire live MAi-RAG-PA source code at {PROJECT_ROOT}.
You have WRITE access ONLY to the sandbox at {SANDBOX_ROOT}.

### PROACTIVE SELF-HEALING PROTOCOL

When analyzing or fixing code, you MUST follow this exact sequence:

1. **READ LIVE CODE**: Use the read_file tool to read files from the LIVE source code at {PROJECT_ROOT} (e.g., {PROJECT_ROOT}/app/main.py). This is READ-ONLY access.
2. **ANALYZE & DIAGNOSE**: Identify weaknesses, bugs, or improvements needed in the live code.
3. **WRITE FIXES TO SANDBOX**: Use the write_file tool to write corrected files to the SANDBOX at {SANDBOX_ROOT}. NEVER write to the live source code.
4. **BACKUP INSTRUCTIONS**: Provide cp commands for the user to backup the original live files before deployment.
5. **VERIFICATION**: Suggest terminal commands to verify the fixes (e.g., python -m py_compile <file>).
6. **GENERATE CHANGE LOG (MANDATORY)**: After all analysis and fixes, you MUST use the write_file tool to create or update the log file at: {SANDBOX_ROOT}/SELF_HEALING_LOG.md

### SELF_HEALING_LOG.md REQUIREMENTS

This log is the user's primary guide for safe deployment. It MUST contain:
# Self-Healing Log
**Date**: [Current timestamp]
**Objective**: [What was analyzed or fixed]

## Weaknesses Identified
- [Bullet points of bugs, inefficiencies, or risks found in live code]

## Files Modified in Sandbox
- `app/agents/agent_core.py` - [Brief explanation of why]
- `frontend/src/components/chat/ChatConsoleApp.tsx` - [Brief explanation of why]
- [List EVERY file you modified, with explanations]

## Deployment Instructions
Copy these commands to deploy the fixes from sandbox to live system:

# Step 1: Backup original files FIRST
cp ~/MAi-RAG-PA/app/agents/agent_core.py ~/MAi-RAG-PA/app/agents/agent_core.py.backup
cp ~/MAi-RAG-PA/frontend/src/components/chat/ChatConsoleApp.tsx ~/MAi-RAG-PA/frontend/src/components/chat/ChatConsoleApp.tsx.backup

# Step 2: Deploy fixes from sandbox
cp ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/app/agents/agent_core.py ~/MAi-RAG-PA/app/agents/agent_core.py
cp ~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/frontend/src/components/chat/ChatConsoleApp.tsx ~/MAi-RAG-PA/frontend/src/components/chat/ChatConsoleApp.tsx

## Rollback Instructions: If the new changes cause breakage, restore the backups:
cp ~/MAi-RAG-PA/app/agents/agent_core.py.backup ~/MAi-RAG-PA/app/agents/agent_core.py
cp ~/MAi-RAG-PA/frontend/src/components/chat/ChatConsoleApp.tsx.backup ~/MAi-RAG-PA/frontend/src/components/chat/ChatConsoleApp.tsx

## Verification Commands: After deployment, verify the fixes:
python -m py_compile ~/MAi-RAG-PA/app/agents/agent_core.py
cd ~/MAi-RAG-PA/frontend && npm run build


### CRITICAL SAFETY RULES (NON-NEGOTIABLE)

1. **READ ANYWHERE IN PROJECT**: You CAN read from ANY file under {PROJECT_ROOT} (except forbidden directories). You are NOT limited to specific files.
2. **WRITE TO SANDBOX ONLY**: You MUST write all fixes to {SANDBOX_ROOT}. NEVER write to live source code.
3. **MIRROR DIRECTORY STRUCTURE**: When writing a fix to the sandbox, preserve the original path structure relative to the project root.
4. **FORBIDDEN PATHS**: Never access venv/, node_modules/, .git/, __pycache__/, memory/, storage/, models/, logs/, alembic/, tests/, scripts/.
5. **GENERATE LOG**: You MUST create {SANDBOX_ROOT}/SELF_HEALING_LOG.md after every self-healing operation.
6. **NO TRUNCATION**: Always output complete files, never use "..." or placeholders.
"""

# =============================================================================
# Model Capability Detection for Self-Healing
# =============================================================================

SELF_HEALING_CAPABLE_MODELS = [
    # Dense models (high capability)
    "qwen2.5-coder:32b",
    "qwen2.5-coder:14b",
    "codeqwen:7b",
    "devstral:24b",
    "mistral-small:24b",
    "qwen3-coder-30b",
    "gemma3:27b",
    # MoE models (fast + capable)
    "qwen3-235b-a22b",  # Large MoE, excellent if hardware supports
    "qwen3-30b-a3b",  # Consumer-friendly MoE
    "qwen3.6-35b-a3b",  # Decent fast model
    "mixtral-8x7b",  # Excellent MoE coder
    "mixtral-8x22b",  # Large MoE, very capable
    "deepseek-v2",  # Strong MoE coder
]


def is_self_healing_capable(model_name: str) -> bool:
    """Check if model has sufficient capability for self-healing operations."""
    if not model_name:
        return False
    model_lower = model_name.lower()
    return any(capable in model_lower for capable in SELF_HEALING_CAPABLE_MODELS)


# =============================================================================
# Protected System Models (Users Should Not Remove)
# =============================================================================

PROTECTED_SYSTEM_MODELS = [
    {
        "name": "codeqwen:7b",
        "purpose": "STM parsing fallback, self-healing, and basic chat",
        "reason": "Optimized for consumer hardware. Required for optimal system performance.",
        "min_ram_gb": 8,
        "size_gb": 4.2,
        "critical": True,
    }
]


def get_protected_models_status() -> List[Dict[str, Any]]:
    """Get status of protected system models using Ollama HTTP API (PATH-independent)."""
    import json
    import urllib.request

    installed_models = []
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            # Extract just the model names in lowercase
            installed_models = [
                m.get("name", "").lower() for m in data.get("models", [])
            ]
    except Exception as e:
        logger.warning(f"Failed to fetch Ollama models for protected status: {e}")

    model_status = []
    for model in PROTECTED_SYSTEM_MODELS:
        model_name_lower = model["name"].lower()
        # Check if the protected model name is in any of the installed model names
        is_installed = any(model_name_lower in m for m in installed_models)

        model_status.append(
            {
                **model,
                "installed": is_installed,
                "warning": (
                    None
                    if is_installed
                    else f"{model['name']} is not installed. {model['reason']}"
                ),
            }
        )

    return model_status


# =============================================================================
# Configuration
# =============================================================================

os.makedirs(WORKSPACE, exist_ok=True)
os.makedirs(DEV_SANDBOX, exist_ok=True)

verifier = ContentVerifier(WORKSPACE)
retriever = AdvancedRetriever()

DEFAULT_SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT.replace("~/MAi-RAG-PA", PROJECT_DISPLAY)
SELF_HEALING_PROTOCOL = SELF_HEALING_PROTOCOL.replace("~/MAi-RAG-PA", PROJECT_DISPLAY)

FORBIDDEN_DIRS: List[str] = [
    # Environments & Dependencies (Prevent AI from deleting dependencies)
    "venv",
    "env",
    ".venv",
    "node_modules",
    # Version Control & Cache
    ".git",
    "__pycache__",
    ".env",
    # Build Artifacts
    "dist",
    "build",
    "public",
    # CRITICAL SYSTEM DIRECTORIES (AI must NEVER touch these directly)
    "memory",  # SQLite databases (prevent direct AI SQL manipulation)
    "storage",  # Chunk cache
    "models",  # Binary ML models (prevent accidental deletion of .gguf files)
    "logs",  # Log files
    "alembic",  # Database migrations
    # DEVELOPMENT & TESTING (Prevent AI from breaking your test suite or scripts)
    "tests",  # Pytest suites
    "scripts",  # Your audit and runtime scripts
    "backups",  # Database backups
]


def initialize_dev_sandbox() -> Dict[str, Any]:
    """
    Initialize the MAi-RAG-DEV sandbox by copying source code.

    Returns:
        Dict with status and details
    """
    if SANDBOX_ROOT.exists():
        return {
            "status": "exists",
            "path": str(SANDBOX_ROOT),
            "message": "Sandbox already exists",
        }

    try:
        # Create sandbox directory
        SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)

        # Define what to copy (source code only, no dependencies)
        items_to_copy = [
            ("app", "app"),
            ("frontend/src", "frontend/src"),
            ("ARCHITECTURE.md", "ARCHITECTURE.md"),
            ("requirements.txt", "requirements.txt"),
            ("frontend/package.json", "frontend/package.json"),
        ]

        copied_files = []
        for src_rel, dst_rel in items_to_copy:
            src_path = PROJECT_ROOT / src_rel
            dst_path = SANDBOX_ROOT / dst_rel

            if not src_path.exists():
                logger.warning(f"Source not found: {src_path}")
                continue

            if src_path.is_dir():
                # Copy directory
                import shutil

                if dst_path.exists():
                    shutil.rmtree(dst_path)
                shutil.copytree(
                    src_path,
                    dst_path,
                    ignore=shutil.ignore_patterns(
                        "__pycache__", "node_modules", "venv", ".git", "*.pyc"
                    ),
                )
                copied_files.append(f"{src_rel}/")
            else:
                # Copy file
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil

                shutil.copy2(src_path, dst_path)
                copied_files.append(src_rel)

        logger.info(
            f"Created dev sandbox at {SANDBOX_ROOT} with {len(copied_files)} items"
        )

        return {
            "status": "success",
            "path": str(SANDBOX_ROOT),
            "copied_items": copied_files,
            "message": f"Sandbox created with {len(copied_files)} items",
        }

    except Exception as e:
        logger.error(f"Failed to create dev sandbox: {e}", exc_info=True)
        return {
            "status": "error",
            "path": str(SANDBOX_ROOT),
            "message": f"Failed to create sandbox: {str(e)}",
        }


_sqlite_manager: Optional[SQLiteMemoryManager] = None
_model_tool_support: Dict[str, bool] = {}
_sqlite_manager_lock = threading.Lock()


def get_sqlite_manager() -> SQLiteMemoryManager:
    """Lazy initialization of SQLite manager."""
    global _sqlite_manager
    if _sqlite_manager is None:
        with (
            _sqlite_manager_lock
        ):  # two racing first calls would create two managers/connections
            if _sqlite_manager is None:
                db_path = PROJECT_ROOT / "memory" / "memory_store.db"
                _sqlite_manager = SQLiteMemoryManager(db_path=db_path)
    return _sqlite_manager


# =============================================================================
# Hardware Detection
# =============================================================================


def detect_hardware_capabilities() -> Dict[str, Any]:
    """Detect system hardware and recommend appropriate settings."""
    import psutil

    ram_gb = psutil.virtual_memory().total / (1024**3)
    cpu_cores = psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True)

    # Determine tier based on RAM and CPU
    if ram_gb >= 32 and cpu_cores >= 8:
        return {
            "recommended_model_size": "35b+",
            "recommended_model_type": "MoE",
            "recommended_models": [
                "Qwen3.6-35b-a3b-Claude4.7-Opus-uncensored-mtp:latest",
                "Mixtral-8x7B-Instruct-v0.1",
                "DeepSeek-V2",
            ],
            "num_predict": 4096,
            "context_length": 8192,
            "tier": "high",
            "max_concurrent_requests": 3,
        }
    elif ram_gb >= 16 and cpu_cores >= 4:
        return {
            "recommended_model_size": "14b",
            "recommended_model_type": "MoE",
            "recommended_models": [
                "Mixtral-8x7B-Instruct-v0.1",
                "Qwen2.5-Coder-14B",
                "DeepSeek-Coder-V2-Lite",
            ],
            "num_predict": 8192,
            "context_length": 4096,
            "tier": "medium",
            "max_concurrent_requests": 2,
        }
    elif ram_gb >= 8:
        return {
            "recommended_model_size": "7b",
            "recommended_model_type": "MoE",
            "recommended_models": [
                "Qwen2.5-Coder-7B",
                "DeepSeek-Coder-V2-Lite",
                "CodeQwen-7B",
            ],
            "num_predict": 4096,
            "context_length": 2048,
            "tier": "low",
            "max_concurrent_requests": 1,
        }
    else:
        return {
            "recommended_model_size": "3b",
            "recommended_model_type": "Dense",
            "recommended_models": ["Qwen2.5-3B", "Phi-3-mini"],
            "num_predict": 2048,
            "context_length": 1024,
            "tier": "minimal",
            "max_concurrent_requests": 1,
        }


# =============================================================================
# LLM Instance Management
# =============================================================================

_llm_cache: Dict[str, ChatOllama] = {}

_llm_cache_lock = threading.Lock()


def _explicit_ollama_base_url() -> Optional[str]:
    """base_url for ChatOllama -- only when the user configured one (MAI_OLLAMA_URL / OLLAMA_URL).

    Otherwise the library's own default applies, so a setup that relies on it (e.g. OLLAMA_HOST) keeps
    working exactly as before.
    """
    if os.environ.get("MAI_OLLAMA_URL") or os.environ.get("OLLAMA_URL"):
        return OLLAMA_BASE_URL
    return None


def _get_llm(
    model_name: str,
    temperature: float = 0.7,
    repeat_penalty: float = 1.1,
    num_predict: int = 2048,
    timeout: int = 1800,
    num_ctx: int = 8192,
) -> ChatOllama:
    """
    Get or create a cached ChatOllama instance.

    Args:
        model_name: Name of the Ollama model to use (None/empty = the default model)
        temperature: Sampling temperature (0.0-1.0)
        repeat_penalty: Penalty for repeated tokens
        num_predict: Maximum tokens to generate
        timeout: Request timeout in seconds (default 300 for large models on CPU)

    Returns:
        ChatOllama instance (cached for reuse)
    """
    target_model = model_name or get_default_model()
    if not target_model:
        raise RuntimeError("No default model available for ChatOllama initialization")

    if num_predict is None:
        hw_caps = detect_hardware_capabilities()
        num_predict = int(hw_caps["num_predict"])
        logger.info(
            "Auto-detected hardware: %s tier, using num_predict=%s",
            hw_caps["tier"],
            num_predict,
        )

    # (the cache key and the client both used `model_name` -- None when the caller wanted the
    # default model -- instead of the resolved target_model, so ChatOllama(model=None) failed.)
    cache_key = f"{target_model}_{temperature}_{repeat_penalty}_{num_predict}_{timeout}_{num_ctx}"

    with _llm_cache_lock:
        llm = _llm_cache.get(cache_key)
        if llm is None:
            kwargs = dict(
                model=target_model,
                temperature=temperature,
                repeat_penalty=repeat_penalty,
                num_predict=num_predict,
                timeout=timeout,
                num_ctx=num_ctx,
            )
            base_url = _explicit_ollama_base_url()
            if base_url:
                kwargs["base_url"] = base_url
            llm = _llm_cache[cache_key] = ChatOllama(**kwargs)
            logger.debug("Created new ChatOllama instance for: %s", target_model)

    return llm


def clear_model_cache(model_name: Optional[str] = None) -> None:
    """
    Clear cached LLM instances to free memory.

    Args:
        model_name: If provided, clear only instances for this model.
                   If None, clear all cached instances.
    """
    if model_name:
        keys_to_remove = [k for k in list(_llm_cache) if k.startswith(f"{model_name}_")]
        for key in keys_to_remove:
            _llm_cache.pop(key, None)
        logger.info(
            "Cleared %d cached instances for model: %s", len(keys_to_remove), model_name
        )
    else:
        count = len(_llm_cache)
        _llm_cache.clear()
        logger.info("Cleared all %d cached LLM instances", count)


# =============================================================================
# Dynamic Default Model Management
# =============================================================================


def get_default_model() -> Optional[str]:
    """Intelligently detect and select the best available model."""
    db_path = PROJECT_ROOT / "memory" / "memory_store.db"
    if db_path.exists():
        try:
            with _db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value FROM short_term_memory WHERE key = 'default_model'"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    logger.info("Using user-preferred model: %s", row[0].strip())
                    return row[0].strip()
        except Exception as e:
            logger.warning("Failed to load default model from SQLite: %s", e)

    env_model = os.getenv("MAI_RAG_DEFAULT_MODEL")
    if env_model:
        logger.info("Using environment variable model: %s", env_model)
        return env_model

    try:
        import urllib.request

        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            models = data.get("models", [])

            if not models:
                logger.error("No models found in Ollama.")
                return None

            chat_models: List[Dict[str, Any]] = []
            for model in models:
                name = model.get("name", "").lower()
                details = model.get("details", {})
                families = details.get("families", []) or []

                if "embed" in name or any("embed" in f.lower() for f in families):
                    continue
                capabilities = details.get("capabilities", []) or []
                if "vision" in name and "chat" not in capabilities:
                    continue

                chat_models.append(model)

            if not chat_models:
                logger.error("No chat-capable models found in Ollama")
                return None

            scored_models: List[Tuple[int, str, float]] = []
            for model in chat_models:
                name = model.get("name", "")
                size_bytes = model.get("size", 0) or 0
                details = model.get("details", {}) or {}

                score = 0
                size_gb = size_bytes / (1024**3) if size_bytes > 0 else 0.0

                if 4 <= size_gb <= 20:
                    score += 100
                elif 2 <= size_gb < 4:
                    score += 80
                elif 20 < size_gb <= 50:
                    score += 60
                elif size_gb > 50:
                    score += 40
                else:
                    score += 20

                param_size = str(details.get("parameter_size", ""))
                if any(
                    x in param_size.lower()
                    for x in ["a3b", "a1b", "a22b", "a14b", "moe"]
                ):
                    score += 30

                capabilities = details.get("capabilities", []) or []
                if "tools" in capabilities or "function-calling" in capabilities:
                    score += 50

                scored_models.append((score, name, size_gb))

            scored_models.sort(key=lambda x: x[0], reverse=True)

            if scored_models:
                best_score, best_model, best_size = scored_models[0]
                logger.info(
                    "Auto-detected best model: %s (%.1fGB, score: %s)",
                    best_model,
                    best_size,
                    best_score,
                )

                # Through the manager. The old direct INSERT named a column (updated_at) that
                # short_term_memory does not have, so the choice was NEVER saved and this whole
                # lookup (an HTTP call plus scoring) was repeated on every single request.
                try:
                    if not get_sqlite_manager().set("default_model", best_model):
                        logger.warning(
                            "Failed to save auto-detected model (see the database log)"
                        )
                except Exception as e:
                    logger.warning("Failed to save auto-detected model: %s", e)

                return best_model

            fallback = chat_models[0].get("name", "")
            logger.warning("Using first available model: %s", fallback)
            return fallback

    except Exception as e:
        logger.error("Failed to detect available models: %s", e, exc_info=True)
        return None


def resolve_model_with_fallback(
    requested_model: str, query_complexity: str = "medium"
) -> str:
    """Intelligent model resolution based on query complexity and hardware."""
    hw_caps = detect_hardware_capabilities()

    complexity_map = {
        "simple": ["qwen2.5:7b", "codeqwen:7b"],
        "medium": ["qwen2.5:14b", "qwen3:30b-a3b"],
        "complex": ["qwen3:30b-a3b", "mixtral:8x7b"],
        "reasoning": ["deepseek-r1:14b", "qwq:32b"],
    }

    preferred_models = complexity_map.get(query_complexity, complexity_map["medium"])

    # Try requested model first
    if requested_model:
        try:
            import urllib.request

            req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                available = [m["name"] for m in data.get("models", [])]
                if requested_model in available:
                    return requested_model
        except Exception:
            pass

    # Fall back to complexity-appropriate model
    for model in preferred_models:
        try:
            import urllib.request

            req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                available = [m["name"] for m in data.get("models", [])]
                if model in available:
                    logger.info(
                        f"Falling back to {model} for {query_complexity} complexity"
                    )
                    return model
        except Exception:
            continue

    # Ultimate fallback
    return get_default_model() or "qwen2.5:7b"


# =============================================================================
# System Prompt Management
# =============================================================================


def _build_stm_context_for_prompt() -> str:
    """Build a concise STM context block for LLM system prompt injection."""
    mgr = get_sqlite_manager()
    sections: List[str] = []

    try:
        profile = mgr.get_user_profile() or {}
        fact_lines: List[str] = []
        for key, value in profile.items():
            if key.startswith("stm_note_") or key == "api_key_retrieved":
                continue
            if isinstance(value, str):
                try:
                    fact_data = json.loads(value)
                    if (
                        isinstance(fact_data, dict)
                        and fact_data.get("type") == "user_fact"
                    ):
                        fact_lines.append(f"- {fact_data['raw']}")
                        continue
                except (json.JSONDecodeError, TypeError):
                    pass
            fact_lines.append(f"- {value}")
        if fact_lines:
            sections.append(
                "### Personal Facts & Preferences\n" + "\n".join(fact_lines[:10])
            )
    except Exception as e:
        logger.debug("Failed to load user profile for STM context: %s", e)

    if not sections:
        return ""

    header = (
        "## USER'S PERSONAL CONTEXT (Background Reference Only)\n"
        "Use this to personalize responses naturally. "
        "Do not quote, echo, or attribute these facts to any source."
    )
    return header + "\n\n" + "\n".join(sections)


def get_system_prompt(
    model_name: Optional[str] = None,
    needs_tools: bool = False,
    role_id: Optional[str] = None,
    citation_mode: str = "none",  # "rag" | "file" | "none"
) -> str:
    """
    Build the system prompt for a request.

    citation_mode controls whether citation/reference rules are injected:
      - "rag"  : KB context present → enforce citation + References section
      - "file" : attached file present → page refs only, no references section
      - "none" : no context → forbid all citation markers entirely
    """
    base_prompt = DEFAULT_SYSTEM_PROMPT
    db_path = PROJECT_ROOT / "memory" / "memory_store.db"

    if db_path.exists():
        try:
            with _db() as conn:
                cursor = conn.cursor()

                if role_id:
                    try:
                        cursor.execute(
                            "SELECT system_prompt, citations_enabled FROM roles WHERE id = ? OR name = ?",
                            (role_id, role_id),
                        )
                        row = cursor.fetchone()
                        prompt = row[0] if row else None
                        citations_enabled = row[1] if row else 1
                    except sqlite3.OperationalError:
                        cursor.execute(
                            "SELECT system_prompt FROM roles WHERE id = ? OR name = ?",
                            (role_id,),
                        )
                        row = cursor.fetchone()
                        prompt = row[0] if row else None
                        citations_enabled = 1

                    if prompt:
                        base_prompt = prompt.strip()
                        logger.info(
                            "Using role-specific system prompt (role=%s)", role_id
                        )

                    if int(citations_enabled or 0) == 0:
                        citation_mode = "none"
                        logger.debug(
                            "Role disables citations; forcing citation_mode=none."
                        )
                else:
                    cursor.execute(
                        "SELECT value FROM short_term_memory WHERE key = 'system_prompt'"
                    )
                    row = cursor.fetchone()
                    if row and row[0] and row[0].strip():
                        base_prompt = row[0].strip()
        except Exception as e:
            logger.warning("Failed to load system prompt: %s", e)

    # ── Citation rules are conditional on citation_mode ────────────────────
    if citation_mode == "rag":
        # KB context present → enforce citations + References section
        base_prompt += (
            "\n\n## MANDATORY CITATION RULES (ACTIVE FOR THIS REQUEST)\n"
            "- The KNOWLEDGE BASE CONTEXT block below contains excerpts with source labels.\n"
            "- Cite each factual claim inline using numbered markers: [1], [2], [3].\n"
            "- Group all citations from the same source under one number.\n"
            "- At the very end, add a '### References' section listing each number with "
            "Author, Title, Filename, and Page numbers.\n"
            "- Do NOT invent sources. Only cite what appears in the context block.\n"
        )
    elif citation_mode == "file":
        # Attached file → allow inline page refs, forbid References section
        base_prompt += (
            "\n\n## OUTPUT RULES FOR ATTACHED FILE\n"
            "- When you reference a specific passage, add the page number inline: (p. 42).\n"
            "- Do NOT add a References section, footnote list, or [Source N] markers.\n"
            "- Do NOT invent citations.\n"
        )
    else:
        # No context at all → forbid every citation marker
        base_prompt += (
            "\n\n## OUTPUT RULES (NO CONTEXT PROVIDED)\n"
            "- There is no knowledge base context for this request.\n"
            "- Do NOT output reference sections, footnote lists, or bracketed citation "
            "markers of any kind.\n"
            "- Answer naturally from conversation and general knowledge.\n"
        )

    # Tool-calling instructions
    if needs_tools and model_name:
        supports_tools = _model_tool_support.get(model_name, True)
        if supports_tools:
            base_prompt += "\n\n" + TOOL_CALLING_INSTRUCTIONS
            logger.debug("Tool-calling instructions injected for model: %s", model_name)

    # Self-healing protocol (capable models, no active role)
    if model_name and is_self_healing_capable(model_name) and not role_id:
        base_prompt += "\n\n" + SELF_HEALING_PROTOCOL
        logger.debug("Self-healing protocol enabled for model: %s", model_name)

    # STM context
    # Role isolation: do not inject global STM into active non-default role prompts.
    if not role_id or role_id == "default":
        stm_context = _build_stm_context_for_prompt()
        if stm_context:
            base_prompt += "\n\n" + stm_context

    return base_prompt


# =============================================================================
# Helper: Strip Markdown Fences
# =============================================================================


def _strip_markdown_fences(content: str) -> str:
    """Remove markdown code fences from LLM output."""
    content = re.sub(r"^```(?:\w+\s*)?\n?", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n?```$", "", content, flags=re.MULTILINE)
    return content.strip()


def _empty_response_message(model_name: str) -> str:
    """User-facing message when a model returns empty content."""
    return (
        f"⚠️ **The model `{model_name}` returned an empty response.**\n\n"
        f"This usually means the model doesn't handle chat-style prompts well "
        f"(code-completion models often fail here).\n\n"
        f"**Try:**\n"
        f"- A chat-tuned model: `qwen3:30b-a3b`, `qwen2.5:14b`, `qwen2.5:7b`\n"
        f"- Sending a longer query (some models ignore very short prompts)\n"
        f"- A smaller role system prompt\n"
    )


# =============================================================================
# Security Helpers for Tool-Calling
# =============================================================================


def _forbidden_reason(path: Path) -> Optional[str]:
    """Why `path` (already resolved) must not be touched, or None if it is allowed.

    * Folder names are compared case-INsensitively: macOS and Windows filesystems are
      case-insensitive, so 'Memory/' reaches the same folder as 'memory/'.
    * Only the part of the path INSIDE the project is examined. Before, an install under e.g.
      ~/build/ or ~/models/ made every single path "forbidden".
    * Secret / database FILES are blocked by name: .encryption_key*, .env, .env.*, *.db ...
      (they are files, not folders, so the folder list above never covered them).
    """
    try:
        inside = path.relative_to(PROJECT_ROOT).parts
    except ValueError:
        inside = path.parts
    folded = {part.casefold() for part in inside}
    for forbidden in FORBIDDEN_DIRS:
        if forbidden.casefold() in folded:
            return f"Access to '{forbidden}' directory is forbidden for safety"
    name = path.name.casefold()
    if (
        name == ".env"
        or name.startswith((".env.", ".envrc", ".encryption_key"))
        or name.endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3"))
    ):
        return f"Access to '{path.name}' is forbidden for safety (credentials / database file)"
    return None


def validate_path(
    path_str: str, allow_write: bool = True, sandbox_mode: bool = False
) -> Path:
    """
    Validate and resolve path within safe boundaries.

    Args:
        path_str: Path to validate
        allow_write: Whether write operations are allowed
        sandbox_mode: If True, restrict to MAi-RAG-DEV sandbox

    Returns:
        Validated Path object

    Raises:
        ValueError: If path is outside allowed boundaries
    """
    path = Path(path_str)

    if not path.is_absolute():
        if allow_write:
            path = (SANDBOX_ROOT if sandbox_mode else WORKSPACE) / path
        elif not str(path_str).startswith("~"):
            # Reads: files the model wrote live in the workspace, source files live in the project.
            # (This used to resolve against the process's CURRENT DIRECTORY, so a file written as
            # 'notes.txt' could not be read back as 'notes.txt', and the result depended on where the
            # server happened to be started from.)
            if sandbox_mode:
                path = SANDBOX_ROOT / path
            else:
                in_workspace = WORKSPACE / path
                path = (
                    in_workspace
                    if os.path.exists(in_workspace)
                    else PROJECT_ROOT / path
                )

    path = path.expanduser().resolve()

    reason = _forbidden_reason(path)
    if reason:
        raise ValueError(reason)

    # Sandbox-specific validation
    if sandbox_mode:
        try:
            path.relative_to(SANDBOX_ROOT)
        except ValueError:
            raise ValueError(f"Sandbox mode: Path must be within {SANDBOX_ROOT}")

        # Check for infinite loop patterns
        path_str = str(path)
        if "workspace/workspace" in path_str:
            raise ValueError(
                "Infinite loop detected: path contains 'workspace/workspace'"
            )
    else:
        if allow_write:
            try:
                path.relative_to(WORKSPACE)
            except ValueError:
                raise ValueError(f"Write operations are restricted to {WORKSPACE}")
        else:
            try:
                path.relative_to(PROJECT_ROOT)
            except ValueError:
                raise ValueError(f"Path must be within {PROJECT_ROOT}")

    return path


# =============================================================================
# Tool Definitions
# =============================================================================


@tool
def read_file(path: str) -> str:
    """Read the contents of a file."""
    try:
        safe_path = validate_path(path, allow_write=False)
        if not safe_path.exists():
            return f"Error: File not found: {safe_path}"
        if not safe_path.is_file():
            return f"Error: Not a file: {safe_path}"

        # Read at most 100001 characters: a huge file must not be loaded into memory just to be truncated.
        with safe_path.open("r", encoding="utf-8") as handle:
            content = handle.read(100001)
        if len(content) > 100000:
            return (
                content[:100000]
                + f"\n\n... [TRUNCATED: file is {safe_path.stat().st_size} bytes; showing the first 100000 characters]"
            )
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        safe_path = validate_path(path, allow_write=True)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {safe_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


_LIST_LIMIT = 100
_SEARCH_LIMIT = 50
_SCAN_LIMIT = 20000  # entries one search will examine before giving up


def _walk_allowed(root: Path, budget: Optional[dict] = None):
    """Depth-first, name-sorted walk below `root` that never enters or lists forbidden folders / secret files.

    (The old recursive listing built the complete rglob() of the tree first -- node_modules included --
    and only THEN filtered and cut to 100, so the visible 100 could all be forbidden entries.)
    `budget` ({"left": n, "exhausted": False}) bounds how many entries one call may examine.
    """
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name)
    except OSError:
        return
    for entry in entries:
        if budget is not None:
            if budget["left"] <= 0:
                budget["exhausted"] = True
                return
            budget["left"] -= 1
        if _forbidden_reason(entry) is not None:
            continue
        yield entry
        if entry.is_dir() and not entry.is_symlink():
            yield from _walk_allowed(entry, budget)
            if budget is not None and budget["exhausted"]:
                return


def _iter_matches(root: Path, pattern: str, budget: dict):
    """Paths below `root` matching a glob `pattern`, searching only folders the model may enter.

    rglob() cannot skip folders: a pattern with no matches walked all of node_modules / .git before
    returning. Here every ALLOWED folder is globbed on its own, so forbidden trees are never entered
    and the walk is bounded by `budget`. (A pattern containing '**' keeps the plain rglob behaviour.)
    """
    if "**" in pattern:
        for item in root.rglob(pattern):
            if budget["left"] <= 0:
                budget["exhausted"] = True
                return
            budget["left"] -= 1
            yield item
        return
    folders = itertools.chain(
        [root],
        (e for e in _walk_allowed(root, budget) if e.is_dir() and not e.is_symlink()),
    )
    for folder in folders:
        yield from folder.glob(pattern)


@tool
def list_directory(path: str = ".", recursive: bool = False) -> str:
    """List files and directories."""
    try:
        safe_path = WORKSPACE if path == "." else validate_path(path, allow_write=False)

        if not safe_path.exists():
            return f"Error: Directory not found: {safe_path}"
        if not safe_path.is_dir():
            return f"Error: Not a directory: {safe_path}"

        if recursive:
            candidates = _walk_allowed(safe_path)
        else:
            candidates = (
                item
                for item in sorted(safe_path.iterdir(), key=lambda p: p.name)
                if _forbidden_reason(item) is None
            )
        items = list(itertools.islice(candidates, _LIST_LIMIT + 1))

        result: List[str] = []
        # Limit number of items to prevent overwhelming output
        if len(items) > _LIST_LIMIT:
            items = items[:_LIST_LIMIT]
            result.append("[... showing first 100 items ...]")

        for item in items:
            rel_path = item.relative_to(safe_path)
            prefix = "[DIR] " if item.is_dir() else "[FILE] "
            result.append(f"{prefix}{rel_path}")

        return "\n".join(result) if result else "Directory is empty"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def search_files(pattern: str, path: str = ".") -> str:
    """Search for files matching a pattern."""
    try:
        safe_path = WORKSPACE if path == "." else validate_path(path, allow_write=False)
        matches: List[str] = []
        budget = {"left": _SCAN_LIMIT, "exhausted": False}
        for item in _iter_matches(safe_path, pattern, budget):
            if _forbidden_reason(item) is not None:
                continue
            matches.append(str(item.relative_to(PROJECT_ROOT)))
            if len(matches) > _SEARCH_LIMIT:
                break

        note = (
            f"\n[search stopped after examining {_SCAN_LIMIT} entries; use a narrower path]"
            if budget["exhausted"]
            else ""
        )

        # Limit results
        if len(matches) > _SEARCH_LIMIT:
            matches = matches[:_SEARCH_LIMIT]
            return f"Found {len(matches)}+ files (showing first 50):\n" + "\n".join(
                matches
            )

        return (
            f"Found {len(matches)} files:\n" + "\n".join(matches) + note
            if matches
            else f"No files matching '{pattern}' found{note}"
        )
    except Exception as e:
        return f"Error searching files: {str(e)}"


@tool
def search_knowledge_base(query: str, top_k: int = 3) -> str:
    """Search the RAG knowledge base with descriptive source attribution."""
    try:
        results = retriever.retrieve_advanced(query, top_k=top_k)

        if not results:
            if not retriever.qdrant_available:
                return "Knowledge base (Qdrant) is not currently available."
            return f"No relevant information found for: {query}"

        formatted: List[str] = []
        for i, result in enumerate(results, 1):
            payload = result.get("payload", {}) or {}
            content = payload.get("content", payload.get("text", str(result)))

            collection = payload.get("collection", "Unknown Collection")
            filename = payload.get("source", payload.get("filename", "Unknown"))
            page = payload.get("page", "")
            chapter = payload.get("chapter", "")
            line_ref = payload.get("line_reference", "")

            source_parts = [collection, filename]
            if chapter:
                source_parts.append(chapter)
            if page:
                source_parts.append(f"p.{page}")
            if line_ref:
                source_parts.append(line_ref)

            source_desc = ", ".join(filter(None, source_parts))
            score = float(result.get("score", 0.0))

            formatted.append(
                f"[Source {i}: {source_desc} (relevance: {score:.2f})]\n{content}"
            )

        return "\n\n---\n\n".join(formatted)
    except Exception as e:
        logger.error("Knowledge base search failed: %s", e, exc_info=True)
        return f"Error searching knowledge base: {str(e)}"


@tool
def get_user_profile(key: str) -> str:
    """Get a specific user preference from short-term memory."""
    try:
        with _db() as conn:
            row = conn.execute(
                "SELECT value FROM user_profile WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row and row[0] else f"No information found for key: '{key}'"
    except Exception as e:
        return f"Error retrieving user profile: {str(e)}"


@tool
def save_user_profile(key: str, value: str) -> str:
    """Save a user preference to short-term memory."""
    try:
        # Through the manager (shared lock, 30 s lock timeout, connection closed) instead of a raw connection.
        if not get_sqlite_manager().save_user_profile(key, value):
            return "Error saving user profile: the database write failed (see the log)"
        return f"Successfully saved {key} = {value}"
    except Exception as e:
        return f"Error saving user profile: {str(e)}"


TOOLS = [
    read_file,
    write_file,
    list_directory,
    search_files,
    search_knowledge_base,
    get_user_profile,
    save_user_profile,
]

# Role tools are supplied dynamically by app.agents.role_registry.tools_for_role().


# =============================================================================
# Helper Functions
# =============================================================================


def create_file_with_verification(
    filename: str,
    description: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a file with verification pipeline."""
    from app.agents.verifier import verify_content

    llm = _get_llm(model)
    prompt = (
        f"Create a file named '{filename}' based on this description:\n{description}\n\n"
        "Return ONLY the file content."
    )

    response = llm.invoke(prompt)
    content = _strip_markdown_fences(response.content.strip())

    is_valid, error = verify_content(filename, content)

    if not is_valid:
        retry_prompt = (
            f"Previous error: {error}\n\nFix and create '{filename}' based on:\n"
            f"{description}\n\nReturn ONLY corrected content."
        )
        response = llm.invoke(retry_prompt)
        content = _strip_markdown_fences(response.content.strip())
        is_valid, error = verify_content(filename, content)

        if not is_valid:
            return {
                "status": "failed",
                "error": f"Verification failed after retry: {error}",
            }

    file_path = WORKSPACE / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    return {"status": "success", "filename": filename, "path": str(file_path)}


def execute_tool_call(
    tool_name: str, tool_args: Dict[str, Any], tools: Optional[List[Any]] = None
) -> str:
    """Execute a tool call and return the result.

    `tools` is the tool set of the REQUEST being served. Without it the shared module-level set is
    used (kept for older callers); that set is global, so concurrent requests with different roles
    must pass their own -- agent_loop does.
    """
    active = tools if tools is not None else (_ACTIVE_TOOLS or TOOLS)
    tool_map = {t.name: t for t in active}
    if tool_name not in tool_map:
        return f"Error: Unknown tool '{tool_name}'"
    try:
        return str(tool_map[tool_name].invoke(tool_args))
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


def extract_user_facts(chat_history: List[Dict[str, Any]]) -> List[str]:
    """Extract user facts from recent chat using lightweight LLM."""
    try:
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in chat_history[-10:]
        )
        extraction_prompt = (
            "Analyze conversation and extract NEW specific facts about user. "
            "Return ONLY JSON list of strings.\n\n"
            f"Conversation:\n{history_text}\n\nJSON Output:"
        )

        llm = _get_llm(model_name="qwen2.5:7b", temperature=0.1)
        response = llm.invoke(extraction_prompt)

        json_match = re.search(r"\[.*?\]", response.content, re.DOTALL)
        return json.loads(json_match.group(0)) if json_match else []
    except Exception as e:
        logger.error("Failed to extract user facts: %s", e, exc_info=True)
        return []


def save_extracted_facts(facts: List[str], role_id: Optional[str] = None) -> None:
    """Save new facts to SQLite, avoiding duplicates. Optionally scoped to a role."""
    mgr = get_sqlite_manager()
    with mgr.get_cursor() as cur:
        for fact in facts:
            if role_id:
                cur.execute(
                    "SELECT id FROM user_facts WHERE fact = ? AND role_id = ?",
                    (fact, role_id),
                )
            else:
                cur.execute(
                    "SELECT id FROM user_facts WHERE fact = ? AND role_id IS NULL",
                    (fact,),
                )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO user_facts (fact, category, role_id) VALUES (?, 'extracted', ?)",
                    (fact, role_id),
                )
                logger.info(
                    "Learned new user fact (role=%s): %s", role_id or "global", fact
                )


def get_user_profile_context(role_id: Optional[str] = None) -> str:
    """
    Fetch user profile and recent facts for system prompt injection.

    role_id scoping:
      - role_id = None  → only global facts (role_id IS NULL)
      - role_id = 'x'   → global facts + facts tagged with role 'x'
    """
    mgr = get_sqlite_manager()
    profile = mgr.get_user_profile() or {}
    name = profile.get("name", "User")
    tone = profile.get("preferred_tone", "friendly and professional")

    with mgr.get_cursor() as cur:
        if role_id:
            cur.execute(
                "SELECT fact FROM user_facts "
                "WHERE is_active = TRUE AND (role_id IS NULL OR role_id = ?) "
                "ORDER BY created_at DESC LIMIT 15",
                (role_id,),
            )
        else:
            cur.execute(
                "SELECT fact FROM user_facts "
                "WHERE is_active = TRUE AND role_id IS NULL "
                "ORDER BY created_at DESC LIMIT 15"
            )
        facts = [row[0] for row in cur.fetchall()]

    context = (
        "\n## USER PARTNERSHIP CONTEXT\n"
        f"- **User Name**: {name}\n"
        f"- **Interaction Style**: {tone}\n"
    )
    if facts:
        context += "- **Known User Context & Facts**:\n" + "".join(
            f"  - {fact}\n" for fact in facts
        )
    else:
        context += "- **Known User Context**: None yet.\n"
    context += "Guideline: Use this context to build rapport naturally."
    return context


# =============================================================================
# Chat-Only Fallback
# =============================================================================


_ACTIVE_TOOLS: List[Any] = []


def _get_role_ctx(role_id: Optional[str]) -> Optional[RoleContext]:
    """
    Resolve role context from either:
      1. a Python role package in app/agents/role_tools/
      2. a DB-only role created by the built-in Role applet

    This keeps the framework role-agnostic while supporting both
    packaged external roles and applet-created roles.
    """

    if not role_id:
        return None

    # 1. Packaged/plugin role.
    try:
        ctx = get_registry().get(role_id)
        if ctx is not None:
            return ctx
    except Exception as exc:
        logger.warning("Role registry lookup failed for %s: %s", role_id, exc)

    # 2. DB-only role fallback.
    try:
        import sqlite3

        root = Path(__file__).resolve().parents[2]
        db = root / "memory" / "memory_store.db"

        if not db.exists():
            return None

        conn = sqlite3.connect(db, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM roles WHERE id = ?",
                (role_id,),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            return None

        data = dict(row)

        collection = (
            data.get("collection_name")
            or data.get("rag_collection")
            or data.get("qdrant_collection")
        )
        rag_collections = [str(collection)] if collection else []

        runtime_profile = data.get("runtime_profile") or None
        citation_mode = data.get("citation_mode")
        if not citation_mode:
            citations_enabled = data.get("citations_enabled")
            if citations_enabled is not None:
                citation_mode = "rag" if bool(citations_enabled) else "none"
            else:
                citation_mode = "rag"

        try:
            rag_top_k = int(data.get("rag_top_k") or 12)
        except Exception:
            rag_top_k = 12

        memory_policy = {
            "scope": "isolated",
            "include_global": False,
            "include_default_role": False,
            "allow_learning": True,
        }

        return RoleContext(
            role_id=str(data.get("id", role_id)),
            name=str(data.get("name", role_id)),
            system_prompt=str(data.get("system_prompt", "") or ""),
            citation_mode=str(citation_mode),
            model_override=data.get("model_override") or None,
            runtime_profile=str(runtime_profile) if runtime_profile else None,
            memory_policy=memory_policy,
            tools=[],
            rag_collections=rag_collections,
            rag_top_k=rag_top_k,
            output_subdir=data.get("output_subdir") or None,
            metadata={},
            hooks={},
            module_name=None,
            package_dir=None,
        )

    except Exception as exc:
        logger.warning("DB role fallback failed for %s: %s", role_id, exc)
        return None


def _is_temporal_strict_role(role_id: Optional[str]) -> bool:
    ctx = _get_role_ctx(role_id)
    return bool(ctx and getattr(ctx, "runtime_profile", None) == "temporal_strict")


def _get_role_model_override(
    role_id: Optional[str], role_ctx: Any = None
) -> Optional[str]:
    """
    Read role model override from role context and/or framework SQLite DB.

    This is generic framework behavior. It does not know any role by name.
    """

    if not role_id:
        return None

    override = None

    try:
        if role_ctx is not None:
            override = getattr(role_ctx, "model_override", None)
    except Exception:
        override = None

    if not override:
        try:
            row = _fetch_role(role_id)
            if row:
                try:
                    override = row.get("model_override")
                except Exception:
                    override = row["model_override"]
        except Exception as exc:
            logger.warning(
                "Could not read role model override for %s: %s", role_id, exc
            )
            override = None

    return str(override) if override else None


def _apply_role_model_override(
    model: Optional[str],
    role_id: Optional[str],
    role_ctx: Any = None,
) -> Optional[str]:
    """
    Role-settings model override wins over WebUI dropdown selection.

    This restores the intended independent role behavior.
    """
    _mai_print(f"_apply_role_model_override entered model={model} role_id={role_id}")

    override = _get_role_model_override(role_id, role_ctx)
    if override:
        logger.info(
            "Role model override applied: requested=%s override=%s",
            model,
            override,
        )
        return override

    return model


def _has_verified_temporal_data(content: Optional[str]) -> bool:
    """
    Generic detection for role hooks that inject deterministic temporal data.

    This is intentionally framework-generic.
    It only recognizes the contract emitted by role hooks.
    """

    if not content:
        return False

    return "VERIFIED TEMPORAL DATA" in content and "REQUESTED YEARS:" in content


def _get_llm_for_request(
    model_name: Optional[str],
    role_ctx: Optional[RoleContext] = None,
    verified_temporal: bool = False,
    needs_tools: bool = True,
):
    _mai_print(
        f"_get_llm_for_request entered model={model_name} verified_temporal={verified_temporal} needs_tools={needs_tools}"
    )
    target_model = model_name or get_default_model()

    opts = _resolve_llm_options(
        model_name=target_model,
        role_ctx=role_ctx,
        verified_temporal=verified_temporal,
        needs_tools=needs_tools,
    )

    kwargs = _supported_llm_kwargs(opts)

    _mai_print(
        f"LLM profile: model={target_model} profile={opts.get('_profile')} verified_temporal={verified_temporal} needs_tools={needs_tools} kwargs={kwargs}"
    )
    logger.info(
        "LLM profile: model=%s profile=%s verified_temporal=%s needs_tools=%s kwargs=%s",
        target_model,
        opts.get("_profile"),
        verified_temporal,
        needs_tools,
        kwargs,
    )

    return _get_llm(target_model, **kwargs)


def _simple_chat_fallback(
    llm: ChatOllama,
    query: str,
    rag_context: str,
    model_name: str,
    citation_mode: str = "rag",
    role_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Simple chat mode with adequate generation budget for reasoning models."""
    logger.info(
        "Using simple chat mode for %s (citation_mode=%s)", model_name, citation_mode
    )

    model_name = _apply_role_model_override(model_name, role_id)
    limited_llm = _get_llm_for_request(
        model_name,
        role_ctx=_get_role_ctx(role_id),
        verified_temporal=_is_temporal_strict_role(role_id),
        needs_tools=False,
    )

    system_prompt = get_system_prompt(
        model_name,
        needs_tools=not _is_temporal_strict_role(role_id),
        role_id=role_id,
        citation_mode=citation_mode,
    )
    user_profile_context = (
        ""
        if role_id and role_id != "default"
        else get_user_profile_context(role_id=role_id)
    )
    full_prompt = f"{system_prompt}{user_profile_context}\n\n"

    if citation_mode == "rag" and rag_context:
        user_message = f"""You are an Analytical Engine. Answer the user's question using the Knowledge Base Context as your PRIMARY source.
You MAY supplement with training data, but you MUST follow the citation rules in the system prompt.

=== KNOWLEDGE BASE CONTEXT ===
{rag_context}
=== END CONTEXT ===

User query: {query}
"""
    elif rag_context:
        user_message = rag_context
    else:
        user_message = query

    full_prompt += f"User: {user_message}\n\nAssistant:"

    try:
        response = limited_llm.invoke(full_prompt)
        final_content = (
            response.content.strip()
            if response and hasattr(response, "content") and response.content
            else ""
        )

        if not final_content:
            reasoning = getattr(response, "additional_kwargs", {}).get(
                "reasoning_content"
            ) or getattr(response, "response_metadata", {}).get("reasoning_content", "")
            if reasoning:
                final_content = reasoning.strip()

        if not final_content:
            final_content = _empty_response_message(model_name)

        return {
            "status": "success",
            "response": final_content,
            "tool_calls": [],
            "iterations": 1,
            "model": model_name,
            "tools_available": False,
            "chat_mode_notice": "",
        }
    except Exception as e:
        logger.error("Chat fallback failed: %s", e, exc_info=True)
        return {
            "status": "error",
            "message": f"Chat error: {str(e)}",
            "model": model_name,
            "tools_available": False,
        }


# =============================================================================
# ReAct Loop
# =============================================================================


def agent_loop(
    query: str,
    rag_context: str = "",
    model: Optional[str] = None,
    max_iterations: int = 10,
    citation_mode: str = "rag",
    role_id: Optional[str] = None,
) -> Dict[str, Any]:
    logger.info(
        "Agent loop started (model=%s, citation_mode=%s, role_id=%s)",
        model,
        citation_mode,
        role_id,
    )

    role_ctx = _get_role_ctx(role_id)
    model = _apply_role_model_override(model, role_id, role_ctx)
    _initial_temporal_strict = _is_temporal_strict_role(role_id)
    llm = _get_llm_for_request(
        model,
        role_ctx=role_ctx,
        verified_temporal=_initial_temporal_strict,
        needs_tools=not _initial_temporal_strict,
    )
    model_name = model or get_default_model() or llm.model

    # Reasoning models → simple chat path
    if "deepseek-r1" in model_name.lower() or "qwq" in model_name.lower():
        logger.info("Reasoning model detected — direct chat mode for %s", model_name)
        return _simple_chat_fallback(
            llm,
            query,
            rag_context,
            model_name,
            citation_mode=citation_mode,
            role_id=role_id,
        )

    # ── Role-aware tool detection ──────────────────────────────────────
    # If the active role has registered tools (e.g., role-specific tools),
    # ALWAYS use the full tool-enabled loop. This ensures role-specific tools
    # are callable regardless of whether the query contains "file" keywords.
    # If no role tools exist, behavior is identical to before.
    role_ctx = _get_role_ctx(role_id)
    active_tools = tools_for_role(role_ctx, TOOLS)
    # (no write to the shared _ACTIVE_TOOLS: concurrent requests overwrote each other's tools)
    role_has_tools = bool(role_ctx and role_ctx.tools)

    # Simple chat detection
    tool_keywords = [
        "create file",
        "write file",
        "save",
        "calendar",
        "event",
        "reminder",
        "todo",
        "read",
        "fix",
        "diagnose",
        "sandbox",
        "error",
        "search",
        "backup",
    ]
    is_simple_chat = not any(kw in query.lower() for kw in tool_keywords)

    # CRITICAL FIX: If a role is active, NEVER use the simple chat fallback.
    # The fallback bypasses the role hook injection (augment_user_content),
    # which means the LLM would never receive VERIFIED TEMPORAL DATA or the RESPONSE CONTRACT.
    if is_simple_chat and not role_has_tools and not role_id:
        logger.info("Simple chat detected — direct chat mode for %s", model_name)
        return _simple_chat_fallback(
            llm,
            query,
            rag_context,
            model_name,
            citation_mode=citation_mode,
            role_id=role_id,
        )

    supports_tools = _model_tool_support.get(model_name)
    if supports_tools is False:
        return _simple_chat_fallback(
            llm,
            query,
            rag_context,
            model_name,
            citation_mode=citation_mode,
            role_id=role_id,
        )

    logger.info("Attempting to bind tools for: %s", model_name)
    try:
        llm_with_tools = llm.bind_tools(active_tools)
        logger.info("Tool binding successful for %s", model_name)
    except Exception as e:
        logger.warning("Tool binding failed for %s: %s", model_name, e)
        _model_tool_support[model_name] = False
        return _simple_chat_fallback(
            llm,
            query,
            rag_context,
            model_name,
            citation_mode=citation_mode,
            role_id=role_id,
        )

    system_prompt = get_system_prompt(
        model_name,
        needs_tools=not _is_temporal_strict_role(role_id),
        role_id=role_id,
        citation_mode=citation_mode,
    )
    user_profile_context = (
        ""
        if role_id and role_id != "default"
        else get_user_profile_context(role_id=role_id)
    )
    messages: List[Any] = [SystemMessage(content=system_prompt + user_profile_context)]

    if citation_mode == "rag" and rag_context:
        user_content = f"""You are an Analytical Engine. Answer the user's question using the Knowledge Base Context as your PRIMARY source.
You MAY supplement with training data, but you MUST follow the citation rules in the system prompt.

=== KNOWLEDGE BASE CONTEXT ===
{rag_context}
=== END CONTEXT ===

User query: {query}
"""
    elif rag_context:
        user_content = rag_context
    else:
        user_content = query

    # ── Generic role hook (role-packaged) ──
    if role_id:
        try:
            import importlib

            _slug = re.sub(r"[^a-z0-9_]", "_", str(role_id).lower().replace("-", "_"))
            if not _slug or _slug[0].isdigit():
                _slug = "role_" + _slug

            _module_name = f"app.agents.role_tools.{_slug}_hooks"

            try:
                _hook_mod = importlib.import_module(_module_name)
            except ModuleNotFoundError as _exc:
                # No hook module for this role is normal. A hook that exists but cannot be imported because
                # ITS OWN dependency is missing is a real problem and must not look like "no hook".
                if (
                    _exc.name
                    and _exc.name != _module_name
                    and not _module_name.startswith(_exc.name + ".")
                ):
                    raise
                _hook_mod = None

            if _hook_mod is not None:
                _augment = getattr(_hook_mod, "augment_user_content", None)
                if callable(_augment):
                    user_content = _augment(user_content, role_id)

                if _has_verified_temporal_data(user_content):
                    _mai_print(
                        "Verified temporal data detected; suppressing tools for this turn."
                    )
                    logger.info(
                        "Verified temporal data detected; suppressing tools for this turn."
                    )
                    llm = _get_llm_for_request(
                        model_name,
                        role_ctx=role_ctx,
                        verified_temporal=True,
                        needs_tools=False,
                    )
                    if messages and isinstance(messages[0], SystemMessage):
                        messages[0] = SystemMessage(
                            content=get_system_prompt(
                                model_name=model_name,
                                needs_tools=False,
                                role_id=role_id,
                                citation_mode=citation_mode,
                            )
                            + user_profile_context
                        )
                    llm_with_tools = llm
        except Exception as _e:
            logger.warning("Role hook skipped for %s: %s", role_id, _e)
    messages.append(HumanMessage(content=user_content))
    tool_calls_history: List[Dict[str, Any]] = []

    for iteration in range(1, max_iterations + 1):
        logger.info("Agent iteration %s/%s", iteration, max_iterations)

        try:
            response = llm_with_tools.invoke(messages)
        except Exception as e:
            if "does not support" in str(e).lower() and "tool" in str(e).lower():
                _model_tool_support[model_name] = False
                return _simple_chat_fallback(
                    llm,
                    query,
                    rag_context,
                    model_name,
                    citation_mode=citation_mode,
                    role_id=role_id,
                )
            logger.error("LLM invocation failed: %s", e, exc_info=True)
            return {
                "status": "error",
                "message": f"LLM error: {str(e)}",
                "iterations": iteration,
                "model": model_name,
            }

        if hasattr(response, "tool_calls") and response.tool_calls:
            messages.append(
                AIMessage(
                    content=response.content or "", tool_calls=response.tool_calls
                )
            )
            for tc in response.tool_calls:
                result = execute_tool_call(tc["name"], tc["args"], tools=active_tools)
                tool_calls_history.append(
                    {
                        "tool": tc["name"],
                        "args": tc["args"],
                        "result": result[:500],
                        "iteration": iteration,
                    }
                )
                messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

        elif response.content:
            clean_content = _strip_markdown_fences(response.content.strip())
            is_json_tool_call = False

            try:
                parsed = json.loads(clean_content)
                # Only a JSON OBJECT with name + arguments is a tool call. A plain answer such as 42, null,
                # true or [1, 2] is valid JSON too, and `"name" in 42` raised TypeError.
                if (
                    isinstance(parsed, dict)
                    and "name" in parsed
                    and "arguments" in parsed
                ):
                    tool_name = parsed["name"]
                    tool_args = parsed["arguments"]
                    if isinstance(
                        tool_args, str
                    ):  # some models JSON-encode the arguments
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            pass
                    logger.info("Intercepted JSON tool call: %s", tool_name)
                    result = execute_tool_call(tool_name, tool_args, tools=active_tools)
                    messages.append(AIMessage(content=response.content))
                    messages.append(
                        ToolMessage(content=str(result), tool_call_id="json_fallback_1")
                    )
                    is_json_tool_call = True
                    continue
            except json.JSONDecodeError:
                pass

            if not is_json_tool_call:
                final_response = clean_content

                if not final_response:
                    reasoning = getattr(response, "additional_kwargs", {}).get(
                        "reasoning_content"
                    ) or getattr(response, "response_metadata", {}).get(
                        "reasoning_content", ""
                    )
                    if reasoning:
                        final_response = reasoning.strip()

                if not final_response:
                    final_response = (
                        str(response)
                        if response and str(response).strip()
                        else _empty_response_message(model_name)
                    )

                return {
                    "status": "success",
                    "response": final_response,
                    "tool_calls": tool_calls_history,
                    "iterations": iteration,
                    "model": model_name,
                    "tools_available": True,
                }

        else:
            _model_tool_support[model_name] = True
            final_response = response.content.strip() if response.content else ""

            if not final_response:
                reasoning = getattr(response, "additional_kwargs", {}).get(
                    "reasoning_content"
                ) or getattr(response, "response_metadata", {}).get(
                    "reasoning_content", ""
                )
                if reasoning:
                    final_response = reasoning.strip()

            if not final_response:
                rm = getattr(response, "response_metadata", {})
                if isinstance(rm, dict):
                    msg = rm.get("message", {})
                    if isinstance(msg, dict):
                        final_response = msg.get("content", "").strip()

            if not final_response:
                final_response = (
                    str(response)
                    if response and str(response).strip()
                    else _empty_response_message(model_name)
                )

            return {
                "status": "success",
                "response": final_response,
                "tool_calls": tool_calls_history,
                "iterations": iteration,
                "model": model_name,
                "tools_available": True,
            }

    return {
        "status": "error",
        "message": f"Max iterations ({max_iterations}) reached",
        "tool_calls": tool_calls_history,
        "iterations": max_iterations,
        "model": model_name,
    }


# =============================================================================
# Agentic File Creation
# =============================================================================


def agentic_create_file(
    filename: str,
    description: str,
    model: Optional[str] = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Create a file with built-in verification and self-correction."""
    sanitized = re.sub(r"-+", "-", re.sub(r"[^\w\-_\.]", "-", filename)).strip("-")
    if sanitized != filename:
        logger.info("Sanitized filename: '%s' → '%s'", filename, sanitized)
        filename = sanitized

    output_path = WORKSPACE / filename
    if output_path.exists():
        base_name = output_path.stem
        extension = output_path.suffix
        counter = 1
        while output_path.exists():
            output_path = WORKSPACE / f"{base_name}_{counter}{extension}"
            counter += 1
        filename = output_path.name
        logger.info("File exists, using new name: %s", filename)

    # Use lower num_predict for creative writing, higher for code
    is_code = filename.endswith((".py", ".ts", ".tsx", ".js", ".jsx"))
    predict_tokens = 2048 if is_code else 4096

    llm = _get_llm(model, num_predict=predict_tokens)
    last_error = ""

    for attempt in range(max_retries):
        prompt = (
            f"Create file: {filename}\n\nRequirements:\n{description}\n\n"
            "Output ONLY file content."
        )

        try:
            response = llm.invoke(prompt)
            if not response or not response.content:
                last_error = "LLM returned empty response"
                continue

            current_content = _strip_markdown_fences(response.content.strip())
            if len(current_content) < 10:
                last_error = f"Content too short: {current_content}"
                continue
        except Exception as e:
            last_error = f"Generation error: {e}"
            continue

        # Skip verification for non-code files (poems, stories, notes)
        if is_code:
            result = verifier.verify_file(filename, current_content)
            if not result["valid"]:
                last_error = result["message"]
                description += (
                    f"\n\n[VERIFICATION FEEDBACK] {last_error}. Regenerate with fix."
                )
                continue

        # Success - write file
        output_path = WORKSPACE / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(current_content, encoding="utf-8")

        # Return WITH content and message
        return {
            "status": "success",
            "message": f"File created successfully: {_home_relative(output_path)} ({len(current_content)} characters)",
            "content": f"File created: `{filename}`\n\nLocation: `{_home_relative(output_path)}`\nSize: {len(current_content)} characters\n\n---\n\n{current_content[:500]}{'...' if len(current_content) > 500 else ''}",
            "filename": str(output_path),
            "model": llm.model,
        }

    return {
        "status": "failed",
        "message": f"Failed after {max_retries} attempts. Last error: {last_error}",
        "content": f"File creation failed after {max_retries} attempts.\n\nLast error: {last_error}",
        "model": llm.model,
    }


# =============================================================================
# RAG Context Fetching
# =============================================================================


def fetch_rag_context(
    query: str,
    top_k: int = 5,
    collection_name: Optional[str] = None,
) -> Tuple[str, bool]:
    """Fetch RAG context with descriptive source attribution."""
    if not retriever.qdrant_available:
        return "", False

    try:
        results = retriever.retrieve_advanced(
            query, top_k=top_k, collection_name=collection_name
        )
        logger.info(
            "RAG retrieval returned %s results (collection=%s) for query: %s...",
            len(results),
            collection_name or "auto",
            query[:50],
        )
        if not results:
            logger.warning(
                "No RAG results found – check Qdrant connection and collection."
            )
            return "", False

        context_parts: List[str] = []
        for i, result in enumerate(results, 1):
            payload = result.get("payload", {}) or {}
            content = payload.get("content", payload.get("text", str(result)))
            collection = payload.get("collection", "Unknown Collection")
            filename = payload.get("source", payload.get("filename", "Unknown"))
            page = payload.get("page", "")
            chapter = payload.get("chapter", "")

            source_parts = [collection, filename]
            if chapter:
                source_parts.append(chapter)
            if page:
                source_parts.append(f"p.{page}")

            source_desc = ", ".join(filter(None, source_parts))
            score = float(result.get("score", 0.0))

            context_parts.append(
                f"[Source {i}: {source_desc} (relevance: {score:.2f})]\n{content}"
            )

        context = "\n\n---\n\n".join(context_parts)
        formatted_context = (
            "## KNOWLEDGE BASE CONTEXT (PRIMARY SOURCE)\n"
            "The following excerpts are from the user's knowledge base. Use them as your primary reference. "
            "You may supplement with training data for comprehensive answers, but you MUST cite KB sources using numbered markers (e.g., [1]) and include a '### References' section at the end.\n\n"
            f"{context}"
        )
        return formatted_context, True

    except Exception as e:
        logger.warning("RAG retrieval failed: %s", e)
        return "", False


# =============================================================================
# General Agent Request Handler
# =============================================================================


def _fetch_role(role_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch a role row by id. Returns dict or None."""
    if not role_id:
        return None
    db_path = PROJECT_ROOT / "memory" / "memory_store.db"
    if not db_path.exists():
        return None
    try:
        with _db() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM roles WHERE id = ?", (role_id,)
            ).fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.warning("Failed to fetch role '%s': %s", role_id, e)
        return None


def process_request(
    user_query: str,
    filename: Optional[str] = None,
    model: Optional[str] = None,
    file_context: Optional[str] = None,
    ltm_enabled: bool = False,
    ltm_collection: Optional[str] = None,
    citations_enabled: bool = True,
    role_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Main agent entry point with mode routing."""
    _mai_print("process_request entered")
    logger.info(
        "process_request: filename=%s file_context=%s ltm_enabled=%s ltm_collection=%s citations=%s role_id=%s",
        filename,
        bool(file_context),
        ltm_enabled,
        ltm_collection,
        citations_enabled,
        role_id,
    )

    # ── Role overrides ───────────────────────────────────────────
    role = _fetch_role(role_id)
    if role:
        logger.info("Role active: '%s' (id=%s)", role.get("name"), role.get("id"))
        if role.get("collection_name"):
            ltm_collection = role["collection_name"]
            ltm_enabled = True
        if role.get("citations_enabled") is not None:
            citations_enabled = bool(role["citations_enabled"])
        if role.get("model_override"):
            model = role["model_override"]

    rag_context: Optional[str] = None
    rag_used: bool = False
    citation_mode: str = "none"

    # ── MODE 1: FILE MODE ────────────────────────────────────────
    if file_context:
        parts = file_context.split("\n\n", 1)
        file_text = parts[1] if len(parts) > 1 else file_context
        filename_display = "the attached file"
        if parts[0].startswith("### User uploaded file:"):
            filename_display = parts[0].split(":", 1)[1].strip()

        rag_context = f"""You have an attached file: **{filename_display}**

**INSTRUCTIONS — FOLLOW THESE FOR THE ENTIRE CONVERSATION:**

1. Treat the attached file as your **primary reference**.
2. You MAY draw on your general training to add context, examples, and explanation.
3. When you cite a specific passage, use the page number inline: `(p. 42)`.
4. **DO NOT** invent citations.
5. **DO NOT** add a "### References" section or footnote list.
6. **DO NOT** claim the file says something it doesn't.
7. If the file doesn't cover the topic, answer from training — just make it clear which is which.
8. Be conversational and helpful — not mechanical.

--- FILE CONTENT START ---
{file_text}
--- FILE CONTENT END ---

User query: {user_query}
"""
        rag_used = True
        citation_mode = "file"

    # ── MODE 2: RAG MODE ─────────────────────────────────────────
    elif ltm_enabled:
        rag_context, rag_used = fetch_rag_context(
            user_query, top_k=12, collection_name=ltm_collection
        )
        if rag_context and citations_enabled:
            citation_mode = "rag"
        elif rag_context:
            rag_context = f"""Here is relevant context from your knowledge base:

--- CONTEXT START ---
{rag_context}
--- CONTEXT END ---

Use this context to inform your answer. Do not add a References section or footnotes.

User query: {user_query}
"""
            citation_mode = "file"
        else:
            logger.info("RAG enabled but no results — falling back to chat mode.")
            rag_context = None
            rag_used = False
            citation_mode = "none"

    # ── MODE 3: CHAT MODE ────────────────────────────────────────
    else:
        rag_context = None
        rag_used = False
        citation_mode = "none"

    # ── File creation shortcut ──────────────────────────────────
    if filename:
        result = agentic_create_file(filename, user_query, model)
        result["rag_used"] = rag_used
        return result

    # ── Run agent ────────────────────────────────────────────────
    try:
        result = agent_loop(
            user_query,
            rag_context or "",
            model,
            citation_mode=citation_mode,
            role_id=role_id,
        )

        if result["status"] == "success":
            final_content = (
                result.get("response", "")
                or "I've processed your request, but the response was empty."
            )
            return {
                "status": "success",
                "message": "Response generated",
                "content": final_content,
                "tool_calls": result.get("tool_calls", []),
                "iterations": result.get("iterations", 0),
                "model": result.get("model", model or get_default_model()),
                "rag_used": rag_used,
                "tools_available": result.get("tools_available", True),
            }
        return {
            "status": "failed",
            "message": result.get("message", "Unknown error"),
            "tool_calls": result.get("tool_calls", []),
            "model": model or get_default_model(),
            "rag_used": rag_used,
        }
    except Exception as e:
        logger.error("Agent loop failed: %s", e, exc_info=True)
        return {
            "status": "failed",
            "message": f"Agent error: {str(e)}",
            "model": model or get_default_model(),
            "rag_used": rag_used,
        }


# =============================================================================
# RAG Status Endpoint Helper
# =============================================================================


def get_rag_status() -> Dict[str, Any]:
    """Get the current status of the RAG system for API endpoints."""
    return retriever.get_status()
