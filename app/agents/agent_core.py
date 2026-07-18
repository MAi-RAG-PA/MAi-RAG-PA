# app/agents/agent_core.py
"""
Agentic Workflow Core: Generate → Verify → Fix → Save
Supports dynamic model selection, system prompt customization, tool-calling, and RAG integration.
"""
import os
import re
import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from app.memory.sqlite_memory import SQLiteMemoryManager
from app.agents.verifier import ContentVerifier
from app.rag.retriever import AdvancedRetriever

logger = logging.getLogger(__name__)

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
1. Prioritize context over training data
2. Cite format: [Source N: filename] where N is sequential number
3. Multiple sources: [Source 1: doc1.pdf], [Source 2: doc2.md]
4. Combine context + training for comprehensive answers
5. No relevant context: "Knowledge base lacks info on this. Based on training..."
6. Never fabricate sources - only cite what was actually provided
7. Check KB for patterns before generating code
8. When making claims, reference specific sources when available
9. If synthesizing multiple sources, cite each: [Source 1], [Source 3]
10. Distinguish between KB information and training knowledge

## CITATION PLACEMENT RULES (MANDATORY)
- NEVER list sources at the beginning of responses
- ALWAYS integrate citations inline: "blue [Source 1: file.txt]"
- If multiple sources support a claim, combine: "blue [Source 1: a.txt], [Source 2: b.txt]"
- Sources are reference material only - do not echo them verbatim as preamble

## END-OF-RESPONSE REFERENCES (MANDATORY)
At the END of every response that uses knowledge base content, you MUST include a References section:

### References
- [Source 1]: filename.pdf, Author (if known), Page X
- [Source 2]: filename.md, Section Y

Source Attribution Rules:
- If information is from knowledge base ONLY: Cite the source(s) as shown above
- If information is from model training ONLY: State "Based on model training data"
- If combining KB and training: Cite KB sources AND state "Combined with model training data"
- If no KB context was provided: State "Based on model training data" at the end

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
5. Save: Write to ~/MAi-RAG-PA/workspace/
6. Confirm: Report path + summary

## FILE CREATION RULES:
- When asked to write content, ALWAYS create the file in ~/MAi-RAG-PA/workspace/
- Use .txt for plain text, .md for markdown, NEVER use .py unless explicitly asked for code
- Do NOT show your internal requirements, verification steps, or reasoning in the response
- Just write the file and confirm it was created
- Example: If asked for a summary, create summary.txt or summary.md, not summary.py

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
# SELF-HEALING PROTOCOL (Only for capable models)
# =============================================================================

SELF_HEALING_PROTOCOL = """
## PROJECT SELF-HEALING & ARCHITECTURE AWARENESS

You have read/write access to ~/MAi-RAG-PA/workspace/MAi-RAG-DEV/ (staging sandbox).

### ARCHITECTURE CONTEXT
Before modifying any file, you MUST:
1. Read ARCHITECTURE.md to understand the project structure
2. Identify which layer the issue is in (backend/frontend/database)
3. Check related files for dependencies

### SELF-HEALING PROTOCOL

When fixing errors:
1. **Diagnose**: Read the error message and relevant files
2. **Locate**: Identify the exact file and line causing the issue
3. **Verify**: Check if the fix breaks dependencies
4. **Backup**: Provide a `cp` command to backup the original file
5. **Fix**: Output the complete corrected file (no truncation)
6. **Test**: Suggest a command to verify the fix (e.g., `python -m py_compile <file>`)

### CRITICAL SAFETY RULES (NON-NEGOTIABLE)

1. **WORKING DIRECTORY**: You are STRICTLY CONFINED to ~/MAi-RAG-PA/workspace/MAi-RAG-DEV/
   - NEVER read, write, or reference files outside this directory
   - NEVER create subdirectories containing "workspace" or "MAi-RAG-DEV"
   
2. **INFINITE LOOP PREVENTION**:
   - NEVER recursively copy or move directories
   - NEVER create symbolic links
   - Maximum directory depth: 10 levels
   - Maximum files per operation: 50 files
   - If you need to process more than 50 files, ask for explicit approval
   
3. **FORBIDDEN PATHS** (NEVER access these):
   - ~/MAi-RAG-PA/workspace/MAi-RAG-DEV/workspace/
   - ~/MAi-RAG-PA/workspace/MAi-RAG-DEV/venv/
   - ~/MAi-RAG-PA/workspace/MAi-RAG-DEV/node_modules/
   - ~/MAi-RAG-PA/workspace/MAi-RAG-DEV/.git/
   - ~/MAi-RAG-PA/workspace/MAi-RAG-DEV/__pycache__/
   - Any path containing "workspace/workspace"
   
4. **FILESYSTEM TRAVERSAL LIMITS**:
   - Maximum recursive depth: 5 levels
   - Maximum files to read in single operation: 20 files
   - Maximum files to write in single operation: 10 files
   - If you exceed these limits, STOP and request approval
   
5. **OPERATION VALIDATION**:
   - Before any file operation, verify the target path is within allowed boundaries
   - Use `pathlib.Path.resolve()` to get absolute paths
   - Verify path starts with ~/MAi-RAG-PA/workspace/MAi-RAG-DEV/
   - Verify path does NOT contain forbidden patterns

### VERIFICATION CHECKLIST

Before providing code:
- [ ] Python: `python -m py_compile <filepath>` will pass
- [ ] TypeScript: All imports are valid, hooks are at top level
- [ ] Database: Schema matches queries, uses parameterized arguments
- [ ] API: Pydantic models match request/response structure
- [ ] Frontend: No infinite loops in useEffect, proper cleanup
- [ ] Path validation: All file operations use validated paths
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
    "qwen3-235b-a22b",      # Large MoE, excellent if hardware supports
    "qwen3-30b-a3b",        # Consumer-friendly MoE
    "qwen3.6-35b-a3b",      # Decent fast model
    "mixtral-8x7b",         # Excellent MoE coder
    "mixtral-8x22b",        # Large MoE, very capable
    "deepseek-v2",          # Strong MoE coder
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
        "critical": True
    }
]

def get_protected_models_status() -> List[Dict[str, Any]]:
    """Get status of protected system models using Ollama HTTP API (PATH-independent)."""
    import urllib.request
    import json
    
    installed_models = []
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            # Extract just the model names in lowercase
            installed_models = [m.get("name", "").lower() for m in data.get("models", [])]
    except Exception as e:
        logger.warning(f"Failed to fetch Ollama models for protected status: {e}")
    
    model_status = []
    for model in PROTECTED_SYSTEM_MODELS:
        model_name_lower = model["name"].lower()
        # Check if the protected model name is in any of the installed model names
        is_installed = any(model_name_lower in m for m in installed_models)
        
        model_status.append({
            **model,
            "installed": is_installed,
            "warning": None if is_installed else f"{model['name']} is not installed. {model['reason']}"
        })
    
    return model_status

# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.resolve()
WORKSPACE: Path = PROJECT_ROOT / "workspace"
DEV_SANDBOX: Path = PROJECT_ROOT / "dev-sandbox"
SANDBOX_ROOT: Path = DEV_SANDBOX / "MAi-RAG-DEV"  # Self-healing workspace
os.makedirs(WORKSPACE, exist_ok=True)
os.makedirs(DEV_SANDBOX, exist_ok=True)

verifier = ContentVerifier(WORKSPACE)
retriever = AdvancedRetriever()

FORBIDDEN_DIRS: List[str] = [
    # Environments & Dependencies (Prevent AI from deleting dependencies)
    "venv", "env", ".venv", "node_modules",
    
    # Version Control & Cache
    ".git", "__pycache__", ".env",
    
    # Build Artifacts
    "dist", "build", "public",
    
    # CRITICAL SYSTEM DIRECTORIES (AI must NEVER touch these directly)
    "memory",      # SQLite databases (prevent direct AI SQL manipulation)
    "storage",     # Chunk cache
    "models",      # Binary ML models (prevent accidental deletion of .gguf files)
    "logs",        # Log files
    "alembic",     # Database migrations
    
    # DEVELOPMENT & TESTING (Prevent AI from breaking your test suite or scripts)
    "tests",       # Pytest suites
    "scripts",     # Your audit and runtime scripts
    "dev-sandbox", # Prevent the MAIN agent from altering the sandbox directly
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
            "message": "Sandbox already exists"
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
                        '__pycache__', 'node_modules', 'venv', '.git', '*.pyc'
                    )
                )
                copied_files.append(f"{src_rel}/")
            else:
                # Copy file
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(src_path, dst_path)
                copied_files.append(src_rel)
        
        logger.info(f"Created dev sandbox at {SANDBOX_ROOT} with {len(copied_files)} items")
        
        return {
            "status": "success",
            "path": str(SANDBOX_ROOT),
            "copied_items": copied_files,
            "message": f"Sandbox created with {len(copied_files)} items"
        }
        
    except Exception as e:
        logger.error(f"Failed to create dev sandbox: {e}", exc_info=True)
        return {
            "status": "error",
            "path": str(SANDBOX_ROOT),
            "message": f"Failed to create sandbox: {str(e)}"
        }

_sqlite_manager: Optional[SQLiteMemoryManager] = None
_model_tool_support: Dict[str, bool] = {}

def get_sqlite_manager() -> SQLiteMemoryManager:
    """Lazy initialization of SQLite manager."""
    global _sqlite_manager
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
    
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    cpu_cores = psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True)
    
    # Determine tier based on RAM and CPU
    if ram_gb >= 32 and cpu_cores >= 8:
        return {
            "recommended_model_size": "35b+",
            "recommended_model_type": "MoE",  # NEW
            "recommended_models": [  # NEW
                "Qwen3.6-35b-a3b-Claude4.7-Opus-uncensored-mtp:latest",
                "Mixtral-8x7B-Instruct-v0.1",
                "DeepSeek-V2"
            ],
            "num_predict": 16384,
            "context_length": 8192,
            "tier": "high",
            "max_concurrent_requests": 3
        }
    elif ram_gb >= 16 and cpu_cores >= 4:
        return {
            "recommended_model_size": "14b",
            "recommended_model_type": "MoE",  # NEW
            "recommended_models": [  # NEW
                "Mixtral-8x7B-Instruct-v0.1",
                "Qwen2.5-Coder-14B",
                "DeepSeek-Coder-V2-Lite"
            ],
            "num_predict": 8192,
            "context_length": 4096,
            "tier": "medium",
            "max_concurrent_requests": 2
        }
    elif ram_gb >= 8:
        return {
            "recommended_model_size": "7b",
            "recommended_model_type": "MoE",  # NEW
            "recommended_models": [  # NEW
                "Qwen2.5-Coder-7B",
                "DeepSeek-Coder-V2-Lite",
                "CodeQwen-7B"
            ],
            "num_predict": 4096,
            "context_length": 2048,
            "tier": "low",
            "max_concurrent_requests": 1
        }
    else:
        return {
            "recommended_model_size": "3b",
            "recommended_model_type": "Dense",  # NEW
            "recommended_models": [  # NEW
                "Qwen2.5-3B",
                "Phi-3-mini"
            ],
            "num_predict": 2048,
            "context_length": 1024,
            "tier": "minimal",
            "max_concurrent_requests": 1
        }

# =============================================================================
# LLM Instance Management
# =============================================================================

_llm_cache: Dict[str, ChatOllama] = {}

def _get_llm(
    model_name: str,
    temperature: float = 0.7,
    repeat_penalty: float = 1.1,
    num_predict: int = 2048,
    timeout: int = 300,
    num_ctx: int = 4096
) -> ChatOllama:
    """
    Get or create a cached ChatOllama instance.
    
    Args:
        model_name: Name of the Ollama model to use
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

    cache_key = f"{model_name}_{temperature}_{repeat_penalty}_{num_predict}_{timeout}_{num_ctx}"
    
    if cache_key not in _llm_cache:
        _llm_cache[cache_key] = ChatOllama(
            model=model_name,
            temperature=temperature,
            repeat_penalty=repeat_penalty,
            num_predict=num_predict,
            timeout=timeout,
            num_ctx=num_ctx,
        )
        logger.debug("Created new ChatOllama instance for: %s", model_name)
    
    return _llm_cache[cache_key]

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
        logger.info("Cleared %d cached instances for model: %s", len(keys_to_remove), model_name)
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
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM short_term_memory WHERE key = 'default_model'")
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

        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
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
                size_gb = size_bytes / (1024 ** 3) if size_bytes > 0 else 0.0

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
                if any(x in param_size.lower() for x in ["a3b", "a1b", "a22b", "a14b", "moe"]):
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

                try:
                    with sqlite3.connect(str(db_path)) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT OR REPLACE INTO short_term_memory (key, value, updated_at) "
                            "VALUES (?, ?, CURRENT_TIMESTAMP)",
                            ("default_model", best_model),
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
                    if isinstance(fact_data, dict) and fact_data.get("type") == "user_fact":
                        fact_lines.append(f"- {fact_data['raw']}")
                        continue
                except (json.JSONDecodeError, TypeError):
                    pass
            fact_lines.append(f"- {value}")
        if fact_lines:
            sections.append("### Personal Facts & Preferences\n" + "\n".join(fact_lines[:10]))
    except Exception as e:
        logger.debug("Failed to load user profile for STM context: %s", e)

    if not sections:
        return ""

    header = (
        "## USER'S PERSONAL CONTEXT (Reference Only - Do Not Output Verbatim)\n"
        "Use this information to personalize responses naturally. "
        "Cite sources inline using [Source N: filename] format ONLY when directly referencing specific facts."
    )
    return header + "\n\n" + "\n".join(sections)

def get_system_prompt(model_name: Optional[str] = None, needs_tools: bool = False) -> str:
    """
    Fetch the current system prompt and inject STM context.
    
    Args:
        model_name: Optional model name to determine if self-healing should be enabled
        needs_tools: Whether to inject tool-calling instructions
    
    Returns:
        Complete system prompt with appropriate sections
    """
    base_prompt = DEFAULT_SYSTEM_PROMPT

    # Load custom system prompt from database if exists
    db_path = PROJECT_ROOT / "memory" / "memory_store.db"
    if db_path.exists():
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM short_term_memory WHERE key = 'system_prompt'")
                row = cursor.fetchone()
                if row and row[0] and row[0].strip():
                    base_prompt = row[0].strip()
        except Exception as e:
            logger.warning("Failed to load custom system prompt: %s", e)

    # Inject tool-calling instructions only for capable models that need them
    if needs_tools and model_name:
        supports_tools = _model_tool_support.get(model_name, True)
        if supports_tools:
            base_prompt += "\n\n" + TOOL_CALLING_INSTRUCTIONS
            logger.debug("Tool-calling instructions injected for model: %s", model_name)

    # Add self-healing protocol only for capable models
    if model_name and is_self_healing_capable(model_name):
        base_prompt += "\n\n" + SELF_HEALING_PROTOCOL
        logger.debug("Self-healing protocol enabled for model: %s", model_name)

    # Inject STM context
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

# =============================================================================
# Security Helpers for Tool-Calling
# =============================================================================

def validate_path(path_str: str, allow_write: bool = True, sandbox_mode: bool = False) -> Path:
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

    if allow_write and not path.is_absolute():
        if sandbox_mode:
            path = SANDBOX_ROOT / path
        else:
            path = WORKSPACE / path

    path = path.expanduser().resolve()

    # Check forbidden directories
    for forbidden in FORBIDDEN_DIRS:
        if forbidden in path.parts:
            raise ValueError(f"Access to '{forbidden}' directory is forbidden for safety")

    # Sandbox-specific validation
    if sandbox_mode:
        try:
            path.relative_to(SANDBOX_ROOT)
        except ValueError:
            raise ValueError(f"Sandbox mode: Path must be within {SANDBOX_ROOT}")
        
        # Check for infinite loop patterns
        path_str = str(path)
        if "workspace/workspace" in path_str:
            raise ValueError("Infinite loop detected: path contains 'workspace/workspace'")
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

        content = safe_path.read_text(encoding="utf-8")
        if len(content) > 100000:
            return (
                content[:100000]
                + f"\n\n... [TRUNCATED: File is {len(content)} characters]"
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

@tool
def list_directory(path: str = ".", recursive: bool = False) -> str:
    """List files and directories."""
    try:
        safe_path = WORKSPACE if path == "." else validate_path(path, allow_write=False)

        if not safe_path.exists():
            return f"Error: Directory not found: {safe_path}"
        if not safe_path.is_dir():
            return f"Error: Not a directory: {safe_path}"

        result: List[str] = []
        items = sorted(safe_path.rglob("*")) if recursive else sorted(safe_path.iterdir())

        # Limit number of items to prevent overwhelming output
        if len(items) > 100:
            items = items[:100]
            result.append("[... showing first 100 items ...]")

        for item in items:
            rel_path = item.relative_to(safe_path)
            if any(forbidden in rel_path.parts for forbidden in FORBIDDEN_DIRS):
                continue
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
        matches = [
            str(item.relative_to(PROJECT_ROOT))
            for item in safe_path.rglob(pattern)
            if not any(
                forbidden in item.relative_to(PROJECT_ROOT).parts
                for forbidden in FORBIDDEN_DIRS
            )
        ]
        
        # Limit results
        if len(matches) > 50:
            matches = matches[:50]
            return f"Found {len(matches)}+ files (showing first 50):\n" + "\n".join(matches)
        
        return (
            f"Found {len(matches)} files:\n" + "\n".join(matches)
            if matches
            else f"No files matching '{pattern}' found"
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
        db_path = PROJECT_ROOT / "memory" / "memory_store.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_profile WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row and row[0] else f"No information found for key: '{key}'"
    except Exception as e:
        return f"Error retrieving user profile: {str(e)}"

@tool
def save_user_profile(key: str, value: str) -> str:
    """Save a user preference to short-term memory."""
    try:
        db_path = PROJECT_ROOT / "memory" / "memory_store.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_profile (key, value, updated_at) "
                "VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, value),
            )
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

def execute_tool_call(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Execute a tool call and return the result."""
    tool_map = {t.name: t for t in TOOLS}
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

def save_extracted_facts(facts: List[str]) -> None:
    """Save new facts to SQLite, avoiding duplicates."""
    mgr = get_sqlite_manager()
    with mgr.get_cursor() as cur:
        for fact in facts:
            cur.execute("SELECT id FROM user_facts WHERE fact = ?", (fact,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO user_facts (fact, category) VALUES (?, 'extracted')",
                    (fact,),
                )
                logger.info("Learned new user fact: %s", fact)

def get_user_profile_context() -> str:
    """Fetch user profile and recent facts for system prompt injection."""
    mgr = get_sqlite_manager()
    profile = mgr.get_user_profile() or {}
    name = profile.get("name", "User")
    tone = profile.get("preferred_tone", "friendly and professional")

    with mgr.get_cursor() as cur:
        cur.execute(
            "SELECT fact FROM user_facts WHERE is_active = TRUE "
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

def _simple_chat_fallback(
    llm: ChatOllama,
    query: str,
    rag_context: str,
    model_name: str,
) -> Dict[str, Any]:
    """Simple chat mode with reduced generation budget."""
    logger.info("Using simple chat mode for %s", model_name)
    
    # Create a separate instance with limited tokens to avoid mutating the cached instance
    limited_llm = _get_llm(
        model_name=model_name,
        temperature=0.7,
        repeat_penalty=1.1,
        num_predict=1024,
        timeout=300
    )

    # Pass model_name to get_system_prompt for capability-based prompt injection
    system_prompt = get_system_prompt(model_name)
    user_profile_context = get_user_profile_context()
    full_prompt = f"{system_prompt}{user_profile_context}\n\n"
    if rag_context:
        full_prompt += f"## Knowledge Base Context\n{rag_context}\n\n"
    full_prompt += f"User: {query}\n\nAssistant:"

    try:
        response = limited_llm.invoke(full_prompt)
        final_content = (
            response.content.strip()
            if response and hasattr(response, "content") and response.content
            else ""
        )

        if not final_content:
            try:
                msg = (
                    response.response_metadata.get("message")
                    if hasattr(response, "response_metadata")
                    else None
                )
                if msg and hasattr(msg, "thinking") and msg.thinking:
                    final_content = msg.thinking.strip()
            except Exception:
                pass

        if not final_content:
            final_content = "I apologize, but I couldn't generate a response."

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
) -> Dict[str, Any]:
    """Execute ReAct loop with tool-calling, falling back to chat mode if needed."""
    llm = _get_llm(model)
    model_name = model or get_default_model() or llm.model

    tool_keywords = [
        "create file",
        "write file",
        "save",
        "calendar",
        "event",
        "reminder",
        "todo",
    ]
    is_simple_chat = not any(kw in query.lower() for kw in tool_keywords)

    if is_simple_chat:
        logger.info(
            "Simple chat detected - using direct chat mode for %s",
            model_name,
        )
        return _simple_chat_fallback(llm, query, rag_context, model_name)

    supports_tools = _model_tool_support.get(model_name)
    if supports_tools is False:
        return _simple_chat_fallback(llm, query, rag_context, model_name)

    try:
        llm_with_tools = llm.bind_tools(TOOLS)
    except Exception as e:
        logger.warning("Tool binding failed for %s: %s", model_name, e)
        _model_tool_support[model_name] = False
        return _simple_chat_fallback(llm, query, rag_context, model_name)

    # Pass model_name to get_system_prompt for capability-based prompt injection
    system_prompt = get_system_prompt(model_name)
    user_profile_context = get_user_profile_context()
    messages: List[Any] = [
        SystemMessage(content=system_prompt + user_profile_context)
    ]

    if rag_context:
        messages.append(
            SystemMessage(
                content=(
                    "## Relevant Information from Knowledge Base\n\n"
                    f"{rag_context}\n\n"
                    "Use above info to inform response."
                )
            )
        )

    messages.append(HumanMessage(content=query))
    tool_calls_history: List[Dict[str, Any]] = []

    for iteration in range(1, max_iterations + 1):
        logger.info("Agent iteration %s/%s", iteration, max_iterations)

        try:
            response = llm_with_tools.invoke(messages)
        except Exception as e:
            if "does not support" in str(e).lower() and "tool" in str(e).lower():
                _model_tool_support[model_name] = False
                return _simple_chat_fallback(llm, query, rag_context, model_name)
            logger.error("LLM invocation failed: %s", e, exc_info=True)
            return {
                "status": "error",
                "message": f"LLM error: {str(e)}",
                "iterations": iteration,
                "model": model_name,
            }

        if hasattr(response, "tool_calls") and response.tool_calls:
            messages.append(
                AIMessage(content=response.content or "", tool_calls=response.tool_calls)
            )
            for tc in response.tool_calls:
                result = execute_tool_call(tc["name"], tc["args"])
                tool_calls_history.append(
                    {
                        "tool": tc["name"],
                        "args": tc["args"],
                        "result": result[:500],
                        "iteration": iteration,
                    }
                )
                messages.append(
                    ToolMessage(content=result, tool_call_id=tc["id"])
                )
        else:
            _model_tool_support[model_name] = True
            final_response = response.content.strip() if response.content else ""

            if not final_response:
                reasoning = getattr(
                    response, "additional_kwargs", {}
                ).get("reasoning_content") or getattr(
                    response, "response_metadata", {}
                ).get("reasoning_content", "")
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
                    if response
                    else "I apologize, but I couldn't generate a response."
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
    is_code = filename.endswith(('.py', '.ts', '.tsx', '.js', '.jsx'))
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
                description += f"\n\n[VERIFICATION FEEDBACK] {last_error}. Regenerate with fix."
                continue

        # Success - write file
        output_path = WORKSPACE / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(current_content, encoding="utf-8")
        
        # Return WITH content and message
        return {
            "status": "success",
            "message": f"File created successfully: ~/MAi-RAG-PA/workspace/{filename} ({len(current_content)} characters)",
            "content": f"File created: `{filename}`\n\nLocation: `~/MAi-RAG-PA/workspace/{filename}`\nSize: {len(current_content)} characters\n\n---\n\n{current_content[:500]}{'...' if len(current_content) > 500 else ''}",
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

def fetch_rag_context(query: str, top_k: int = 3) -> Tuple[str, bool]:
    """Fetch RAG context with descriptive source attribution."""
    if not retriever.qdrant_available:
        return "", False

    try:
        results = retriever.retrieve_advanced(query, top_k=top_k)
        if not results:
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
            "## KNOWLEDGE BASE CONTEXT (Cite Inline Only)\n"
            "The following information is available for reference. When using specific facts, "
            "cite them inline as [Source N: Collection, Filename, Chapter, p.Page]. "
            "Do NOT list sources at the beginning of your response.\n\n"
            f"{context}"
        )
        return formatted_context, True

    except Exception as e:
        logger.warning("RAG retrieval failed: %s", e)
        return "", False

# =============================================================================
# General Agent Request Handler
# =============================================================================

def process_request(
    user_query: str,
    filename: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Main agent entry point."""
    logger.info(
        "process_request called with filename='%s', model='%s'",
        filename,
        model,
    )

    rag_context, rag_used = fetch_rag_context(user_query, top_k=3)

    if filename:
        result = agentic_create_file(filename, user_query, model)
        result["rag_used"] = rag_used
        return result

    try:
        result = agent_loop(user_query, rag_context, model)

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