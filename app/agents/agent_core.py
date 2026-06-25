# ~/MAi-RAG/app/agents/agent_core.py
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
from typing import Optional, List, Dict, Any

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

DEFAULT_SYSTEM_PROMPT = """You are MAi-RAG, a strategic AI assistant with tool-calling and RAG capabilities.

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

## CITATION & REFERENCE PROTOCOL (CRITICAL)
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

## TOOL-CALLING PROTOCOL
File creation workflow:
1. Parse: Extract filename + requirements
2. Plan: Outline structure
3. Generate: Complete content, no truncation
4. Verify: Mental syntax check
5. Save: Write to ~/MAi-RAG/workspace/
6. Confirm: Report path + summary

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
- Read/write: ~/MAi-RAG/workspace/ and ~/MAi-RAG/
- Forbidden: venv/, node_modules/, .git/, __pycache__/, .env
- Use read_file tool before modifying
- All paths must resolve within ~/MAi-RAG/

## VERIFICATION BEFORE SAVE
- Python: Mentally simulate py_compile
- TypeScript: Check imports (case-sensitive), closed JSX tags, unique keys
- JSON/YAML: Validate structure, quoted keys, no trailing commas

## RESPONSE FORMATS
Technical: Problem → Root Cause → Solution → Explanation → Prevention
Creative: Objectives → Options (min 3) → Trade-offs → Recommendation → Next Steps
File Creation: Requirements → Structure → Complete Content → Verification → Success
Research: Question → Sources Consulted → Findings (with citations) → Gaps → Recommendations

## PROHIBITED BEHAVIORS
- Filler phrases, excessive apologies
- Incomplete code, "..." placeholders, TODO without explanation
- Hallucinated sources, uncited claims when KB context available
- Silent exceptions (except: pass)
- Mutated state, missing cleanup functions
- Truncated responses, partial context
- Tunnel vision, oversimplification
- Repeating user's question back

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
# Configuration
# =============================================================================

WORKSPACE = Path.home() / "MAi-RAG" / "workspace"
PROJECT_ROOT = Path.home() / "MAi-RAG"
os.makedirs(WORKSPACE, exist_ok=True)

verifier = ContentVerifier(WORKSPACE)
retriever = AdvancedRetriever()

FORBIDDEN_DIRS = ['venv', 'node_modules', '.git', '__pycache__', '.env', 'dist', 'public']

# Add a lazy loader for the manager
_sqlite_manager: Optional[SQLiteMemoryManager] = None

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

def detect_hardware_capabilities() -> dict:
    """Detect system hardware and recommend appropriate settings."""
    import psutil
    
    ram_gb = psutil.virtual_memory().total / (1024**3)
    cpu_cores = psutil.cpu_count(logical=True)
    
    # Determine model size and context window based on hardware
    if ram_gb >= 32:
        return {
            "recommended_model_size": "35b+",
            "num_predict": 16384,
            "context_length": 8192,
            "tier": "high"
        }
    elif ram_gb >= 16:
        return {
            "recommended_model_size": "14b",
            "num_predict": 8192,
            "context_length": 4096,
            "tier": "medium"
        }
    elif ram_gb >= 8:
        return {
            "recommended_model_size": "7b",
            "num_predict": 4096,
            "context_length": 2048,
            "tier": "low"
        }
    else:
        return {
            "recommended_model_size": "3b",
            "num_predict": 2048,
            "context_length": 1024,
            "tier": "minimal"
        }

def _get_llm(model_name: Optional[str] = None, temperature: float = 0.1, num_predict: Optional[int] = None) -> ChatOllama:
    """Get or create a ChatOllama instance with hardware-appropriate settings."""
    target_model = model_name or get_default_model()
    
    # Auto-detect hardware if num_predict not specified
    if num_predict is None:
        hw_caps = detect_hardware_capabilities()
        num_predict = hw_caps["num_predict"]
        logger.info(f"🔧 Auto-detected hardware: {hw_caps['tier']} tier, using num_predict={num_predict}")
    
    cache_key = f"{target_model}_{num_predict}"
    
    if cache_key not in _model_cache:
        logger.info(f"Loading model: {target_model} with num_predict={num_predict}")
        _model_cache[cache_key] = ChatOllama(
            model=target_model,
            temperature=temperature,
            num_predict=num_predict,
        )
    return _model_cache[cache_key]


# =============================================================================
# Dynamic Default Model Management
# =============================================================================

def get_default_model() -> str:
    """
    Intelligently detect and select the best available model.
    Uses metadata-based heuristics without hardcoding specific model names.
    """
    # 1. Check user's explicit preference first
    db_path = PROJECT_ROOT / "memory" / "memory_store.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM short_term_memory WHERE key = 'default_model'")
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                logger.info(f"✅ Using user-preferred model: {row[0].strip()}")
                return row[0].strip()
        except Exception as e:
            logger.warning(f"Failed to load default model from SQLite: {e}")
    
    # 2. Check environment variable
    env_model = os.getenv("MAI_RAG_DEFAULT_MODEL")
    if env_model:
        logger.info(f"✅ Using environment variable model: {env_model}")
        return env_model
    
    # 3. Auto-detect from Ollama using metadata
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            models = data.get("models", [])
            
            if not models:
                logger.error("❌ No models found in Ollama. Please pull a model first.")
                return None
            
            # Filter out embedding and vision-only models
            chat_models = []
            for model in models:
                name = model.get("name", "").lower()
                details = model.get("details", {})
                family = details.get("families", [])
                
                # Skip embedding models
                if "embed" in name or any("embed" in f.lower() for f in family):
                    continue
                
                # Skip vision-only models (if they don't support text)
                if "vision" in name.lower() and "chat" not in details.get("capabilities", []):
                    continue
                
                chat_models.append(model)
            
            if not chat_models:
                logger.error("❌ No chat-capable models found in Ollama")
                return None
            
            # Score models based on metadata
            scored_models = []
            for model in chat_models:
                name = model.get("name", "")
                size_bytes = model.get("size", 0)
                details = model.get("details", {})
                
                score = 0
                
                # Size-based scoring (prefer mid-range for CPU inference)
                size_gb = size_bytes / (1024**3) if size_bytes > 0 else 0
                
                if 4 <= size_gb <= 20:  # Sweet spot for most systems
                    score += 100
                elif 2 <= size_gb < 4:
                    score += 80
                elif 20 < size_gb <= 50:
                    score += 60
                elif size_gb > 50:
                    score += 40  # Large models
                else:
                    score += 20  # Very small models
                
                # Bonus for MoE models (indicated by parameter patterns)
                param_size = details.get("parameter_size", "")
                if any(x in param_size.lower() for x in ["a3b", "a1b", "a22b", "a14b", "moe"]):
                    score += 30
                
                # Bonus for models with tool-calling capability
                capabilities = details.get("capabilities", [])
                if "tools" in capabilities or "function-calling" in capabilities:
                    score += 50
                
                scored_models.append((score, name, size_gb))
            
            # Sort by score descending
            scored_models.sort(key=lambda x: x[0], reverse=True)
            
            if scored_models:
                best_score, best_model, best_size = scored_models[0]
                logger.info(f"✅ Auto-detected best model: {best_model} ({best_size:.1f}GB, score: {best_score})")
                
                # Save as default for future use
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT OR REPLACE INTO short_term_memory (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                        ("default_model", best_model)
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.warning(f"Failed to save auto-detected model: {e}")
                
                return best_model
            
            # Ultimate fallback: return first available model
            fallback = chat_models[0].get("name", "")
            logger.warning(f"⚠️  Using first available model: {fallback}")
            return fallback
            
    except Exception as e:
        logger.error(f"Failed to detect available models: {e}")
        return None

# =============================================================================
# System Prompt Management
# =============================================================================

def get_system_prompt() -> str:
    """Fetch the current system prompt dynamically from SQLite storage."""
    db_path = PROJECT_ROOT / "memory" / "memory_store.db"
    
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM short_term_memory WHERE key = 'system_prompt'")
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] and row[0].strip():
                return row[0].strip()
        except Exception as e:
            logger.warning(f"Failed to load system prompt from SQLite: {e}")
    
    return DEFAULT_SYSTEM_PROMPT

# =============================================================================
# Dynamic LLM Model Management
# =============================================================================

_model_cache: dict[str, ChatOllama] = {}
_model_tool_support: dict[str, bool] = {}

def _get_llm(model_name: Optional[str] = None, temperature: float = 0.1, num_predict: int = 32768) -> ChatOllama:
    """Get or create a ChatOllama instance for the given model."""
    target_model = model_name or get_default_model()
    
    if target_model not in _model_cache:
        logger.info(f"Loading model: {target_model}")
        _model_cache[target_model] = ChatOllama(
            model=target_model,
            temperature=temperature,
            num_predict=num_predict,
        )
    return _model_cache[target_model]

def clear_model_cache(model_name: Optional[str] = None) -> None:
    """Clear cached LLM instances to free memory."""
    if model_name:
        _model_cache.pop(model_name, None)
        logger.info(f"Cleared cache for model: {model_name}")
    else:
        _model_cache.clear()
        logger.info("Cleared all model caches")

# =============================================================================
# Helper: Strip Markdown Fences
# =============================================================================

def _strip_markdown_fences(content: str) -> str:
    """Remove markdown code fences from LLM output."""
    content = re.sub(r'^```(?:\w+\s*)?\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'\n?```$', '', content, flags=re.MULTILINE)
    return content.strip()

# =============================================================================
# Security Helpers for Tool-Calling
# =============================================================================

def validate_path(path_str: str, allow_write: bool = True) -> Path:
    """Validate and resolve path within safe boundaries."""
    path = Path(path_str)
    
    if allow_write and not path.is_absolute():
        path = WORKSPACE / path
    
    path = path.expanduser().resolve()
    
    for forbidden in FORBIDDEN_DIRS:
        if forbidden in path.parts:
            raise ValueError(f"Access to '{forbidden}' directory is forbidden for safety")
    
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
    """Read the contents of a file.
    
    Args:
        path: Path to the file to read (relative to project root or absolute)
    
    Returns:
        File contents as string
    """
    try:
        safe_path = validate_path(path, allow_write=False)
        if not safe_path.exists():
            return f"Error: File not found: {safe_path}"
        if not safe_path.is_file():
            return f"Error: Not a file: {safe_path}"
        
        content = safe_path.read_text(encoding='utf-8')
        
        if len(content) > 100000:
            return content[:100000] + f"\n\n... [TRUNCATED: File is {len(content)} characters]"
        
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories if needed.
    
    Args:
        path: Path to the file to write (must be within workspace)
        content: Content to write to the file
    
    Returns:
        Success message or error
    """
    try:
        safe_path = validate_path(path, allow_write=True)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content, encoding='utf-8')
        return f"Successfully wrote {len(content)} characters to {safe_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@tool
def list_directory(path: str = ".", recursive: bool = False) -> str:
    """List files and directories.
    
    Args:
        path: Directory path to list (default: current workspace)
        recursive: If True, list recursively (default: False)
    
    Returns:
        Directory listing as formatted string
    """
    try:
        if path == ".":
            safe_path = WORKSPACE
        else:
            safe_path = validate_path(path, allow_write=False)
        
        if not safe_path.exists():
            return f"Error: Directory not found: {safe_path}"
        if not safe_path.is_dir():
            return f"Error: Not a directory: {safe_path}"
        
        result = []
        if recursive:
            for item in sorted(safe_path.rglob("*")):
                rel_path = item.relative_to(safe_path)
                if any(forbidden in rel_path.parts for forbidden in FORBIDDEN_DIRS):
                    continue
                prefix = "[DIR] " if item.is_dir() else "[FILE] "
                result.append(f"{prefix}{rel_path}")
        else:
            for item in sorted(safe_path.iterdir()):
                prefix = "[DIR] " if item.is_dir() else "[FILE] "
                result.append(f"{prefix}{item.name}")
        
        if not result:
            return "Directory is empty"
        
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@tool
def search_files(pattern: str, path: str = ".") -> str:
    """Search for files matching a pattern.
    
    Args:
        pattern: Glob pattern to match (e.g., "*.py", "test_*.txt")
        path: Directory to search in (default: workspace)
    
    Returns:
        List of matching files
    """
    try:
        if path == ".":
            safe_path = WORKSPACE
        else:
            safe_path = validate_path(path, allow_write=False)
        
        matches = []
        for item in safe_path.rglob(pattern):
            rel_path = item.relative_to(PROJECT_ROOT)
            if any(forbidden in rel_path.parts for forbidden in FORBIDDEN_DIRS):
                continue
            matches.append(str(rel_path))
        
        if not matches:
            return f"No files matching '{pattern}' found"
        
        return f"Found {len(matches)} files:\n" + "\n".join(matches)
    except Exception as e:
        return f"Error searching files: {str(e)}"

@tool
def search_knowledge_base(query: str, top_k: int = 3) -> str:
    """Search the RAG knowledge base (Qdrant vector database) for relevant information.
    
    Args:
        query: Search query string
        top_k: Number of results to return (default: 3)
    
    Returns:
        Relevant information from the knowledge base, or a message if unavailable
    """
    try:
        results = retriever.retrieve_advanced(query, top_k=top_k)
        
        if not results:
            if not retriever.qdrant_available:
                return "Knowledge base (Qdrant) is not currently available. Please start Qdrant to enable RAG features."
            return f"No relevant information found in the knowledge base for: {query}"
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            payload = result.get('payload', {})
            content = payload.get('content', payload.get('text', str(result)))
            source = payload.get('source', payload.get('filename', 'Unknown'))
            score = result.get('score', 0.0)
            
            formatted_results.append(
                f"[Source {i}: {source} (relevance: {score:.2f})]\n{content}"
            )
        
        return "\n\n---\n\n".join(formatted_results)
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        return f"Error searching knowledge base: {str(e)}"

@tool
def get_user_profile(key: str) -> str:
    """Get a specific user preference or profile detail (e.g., 'name', 'timezone') from short-term memory.
    
    Args:
        key: The profile key to retrieve (e.g., 'name')
    
    Returns:
        The value associated with the key, or a message if not found.
    """
    try:
        db_path = PROJECT_ROOT / "memory" / "memory_store.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM user_profile WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return row[0]
        return f"No information found for key: '{key}'"
    except Exception as e:
        return f"Error retrieving user profile: {str(e)}"

@tool
def save_user_profile(key: str, value: str) -> str:
    """Save a user preference or profile detail (e.g., 'name') to short-term memory.
    
    Args:
        key: The profile key to save (e.g., 'name')
        value: The value to associate with the key
    
    Returns:
        Success or error message.
    """
    try:
        db_path = PROJECT_ROOT / "memory" / "memory_store.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_profile (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
        conn.commit()
        conn.close()
        return f"Successfully saved {key} = {value}"
    except Exception as e:
        return f"Error saving user profile: {str(e)}"

# =============================================================================
# Tool Registry
# =============================================================================

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

def create_file_with_verification(filename: str, description: str, model: str = None) -> dict:
    """Create a file with verification pipeline."""
    from app.agents.verifier import verify_content
    
    # Generate content using LLM
    llm = _get_llm(model)
    prompt = f"""Create a file named '{filename}' based on this description:
{description}

Return ONLY the file content, no explanations or markdown code blocks."""
    
    response = llm.invoke(prompt)
    content = response.content.strip()
    
    # Remove markdown code blocks if present
    if content.startswith('```'):
        lines = content.split('\n')
        content = '\n'.join(lines[1:-1]) if lines[-1].startswith('```') else '\n'.join(lines[1:])
    
    # Verify content
    is_valid, error = verify_content(filename, content)
    
    if not is_valid:
        # Retry with error feedback
        retry_prompt = f"""The previous attempt had this error: {error}

Please fix it and create the file '{filename}' based on:
{description}

Return ONLY the corrected file content."""
        
        response = llm.invoke(retry_prompt)
        content = response.content.strip()
        
        if content.startswith('```'):
            lines = content.split('\n')
            content = '\n'.join(lines[1:-1]) if lines[-1].startswith('```') else '\n'.join(lines[1:])
        
        is_valid, error = verify_content(filename, content)
        
        if not is_valid:
            return {"status": "failed", "error": f"Verification failed after retry: {error}"}
    
    # Save to workspace
    file_path = Path.home() / "MAi-RAG" / "workspace" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')
    
    return {
        "status": "success",
        "filename": filename,
        "path": str(file_path)
    }

def execute_tool_call(tool_name: str, tool_args: dict) -> str:
    """Execute a tool call and return the result."""
    tool_map = {t.name: t for t in TOOLS}
    
    if tool_name not in tool_map:
        return f"Error: Unknown tool '{tool_name}'"
    
    try:
        tool_func = tool_map[tool_name]
        result = tool_func.invoke(tool_args)
        return str(result)
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"

def extract_user_facts(chat_history: list[dict]) -> list[str]:
    """Use a lightweight LLM call to extract user facts from recent chat."""
    try:
        # Format history for extraction
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history[-10:]])
        
        extraction_prompt = f"""Analyze the following conversation and extract NEW, specific facts about the user (preferences, personal details, work context, goals). 
Ignore generic statements. Return ONLY a JSON list of strings. If no new facts, return [].

Conversation:
{history_text}

JSON Output:"""

        # Use a fast, small model for extraction to save resources
        llm = _get_llm(model_name="qwen2.5:7b", temperature=0.1) 
        response = llm.invoke(extraction_prompt)
        
        # Parse JSON safely
        import json
        import re
        json_match = re.search(r'\[.*?\]', response.content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return []
    except Exception as e:
        logger.error(f"Failed to extract user facts: {e}")
        return []

def save_extracted_facts(facts: list[str]):
    """Save new facts to SQLite, avoiding duplicates."""
    mgr = get_sqlite_manager()
    with mgr.get_cursor() as cur:
        for fact in facts:
            # Check for duplicates
            cur.execute("SELECT id FROM user_facts WHERE fact = ?", (fact,))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO user_facts (fact, category) 
                    VALUES (?, 'extracted')
                """, (fact,))
                logger.info(f"Learned new user fact: {fact}")

def get_user_profile_context() -> str:
    """Fetch user profile and recent facts to inject into the system prompt."""
    mgr = get_sqlite_manager()
    
    # 1. Get static profile
    profile = mgr.get_user_profile()
    name = profile.get("name", "User")
    tone = profile.get("preferred_tone", "friendly and professional")
    
    # 2. Get dynamic facts (limit to last 15 to save tokens)
    with mgr.get_cursor() as cur:
        cur.execute("""
            SELECT fact FROM user_facts 
            WHERE is_active = TRUE 
            ORDER BY created_at DESC 
            LIMIT 15
        """)
        facts = [row[0] for row in cur.fetchall()]
    
    # 3. Format for LLM
    context = f"\n## USER PARTNERSHIP CONTEXT\n"
    context += f"- **User Name**: {name}\n"
    context += f"- **Interaction Style**: {tone}\n"
    
    if facts:
        context += "- **Known User Context & Facts**:\n"
        for fact in facts:
            context += f"  - {fact}\n"
    else:
        context += "- **Known User Context**: None yet. Learn about the user naturally during conversation.\n"
        
    context += "Guideline: Use this context to build rapport. Reference past details naturally. Treat the user as a close partner."
    
    return context

# =============================================================================
# Chat-Only Fallback for Non-Tool Models
# =============================================================================

def _simple_chat_fallback(
    llm: ChatOllama,
    query: str,
    rag_context: str,
    model_name: str
) -> Dict[str, Any]:
    """Simple chat mode - reliable and straightforward."""
    logger.info(f"💬 Using simple chat mode for {model_name}")
    
    system_prompt = get_system_prompt()
    user_profile_context = get_user_profile_context()
    
    full_prompt = f"{system_prompt}{user_profile_context}\n\n"
    
    if rag_context:
        full_prompt += f"## Knowledge Base Context\n{rag_context}\n\n"
    
    full_prompt += f"User: {query}\n\nAssistant:"
    
    try:
        response = llm.invoke(full_prompt)
        
        # Simple extraction - just get the content
        final_content = ""
        
        if response and hasattr(response, 'content') and response.content:
            final_content = response.content.strip()
        
        # If content is empty, try to extract from response_metadata safely
        if not final_content:
            try:
                if hasattr(response, 'response_metadata') and response.response_metadata:
                    msg = response.response_metadata.get('message')
                    if msg and hasattr(msg, 'thinking') and msg.thinking:
                        logger.info(f"🧠 Using thinking content ({len(msg.thinking)} chars)")
                        final_content = msg.thinking.strip()
            except Exception as e:
                logger.warning(f"Could not extract thinking: {e}")
        
        # Final fallback
        if not final_content:
            final_content = "I apologize, but I couldn't generate a response. The model may be experiencing token limits."
            logger.warning("⚠️  No content extracted from response")
        
        return {
            "status": "success",
            "response": final_content,
            "tool_calls": [],
            "iterations": 1,
            "model": model_name,
            "tools_available": False,
            "chat_mode_notice": ""
        }
    except Exception as e:
        logger.error(f"Chat fallback failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Chat error: {str(e)}",
            "model": model_name,
            "tools_available": False
        }

# =============================================================================
# ReAct Loop for General Agent Tasks
# =============================================================================

def agent_loop(
    query: str,
    rag_context: str = "",
    model: Optional[str] = None,
    max_iterations: int = 10
) -> Dict[str, Any]:
    """
    Execute a ReAct loop with tool-calling for general tasks.
    Gracefully falls back to chat-only mode if model doesn't support tools.
    """
    llm = _get_llm(model)
    model_name = model or get_default_model()
    
    # DETECT if this is a simple chat query (no file ops, no calendar, etc.)
    tool_keywords = ['create file', 'write file', 'save', 'calendar', 'event', 'reminder', 'todo']
    is_simple_chat = not any(keyword in query.lower() for keyword in tool_keywords)
    
    # For simple chat, DON'T bind tools - just chat naturally
    if is_simple_chat:
        logger.info(f"💬 Simple chat detected - using direct chat mode for {model_name}")
        return _simple_chat_fallback(llm, query, rag_context, model_name)
    
    # Check cached capability
    supports_tools = _model_tool_support.get(model_name)
    
    # If we know this model doesn't support tools, skip straight to chat mode
    if supports_tools is False:
        logger.info(f"ℹ️  Model {model_name} known to not support tools - using chat mode")
        return _simple_chat_fallback(llm, query, rag_context, model_name)
    
    # Try tool-calling mode
    try:
        llm_with_tools = llm.bind_tools(TOOLS)
    except Exception as e:
        logger.warning(f"⚠️  Tool binding failed for {model_name}: {e}")
        _model_tool_support[model_name] = False
        return _simple_chat_fallback(llm, query, rag_context, model_name)
    
    # Initialize conversation
    system_prompt = get_system_prompt()
    user_profile_context = get_user_profile_context()
    
    messages = [
        SystemMessage(content=system_prompt + user_profile_context),
    ]
    
    if rag_context:
        messages.append(SystemMessage(content=f"""
## Relevant Information from Knowledge Base

{rag_context}

Use the above information to inform your response. Reference sources when appropriate.
"""))
    
    messages.append(HumanMessage(content=query))
    
    tool_calls_history = []
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Agent iteration {iteration}/{max_iterations}")
        
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as e:
            error_msg = str(e).lower()
            
            # CRITICAL: Detect "does not support tools" error and fall back
            if "does not support" in error_msg and "tool" in error_msg:
                logger.warning(f"⚠️  Model {model_name} does not support tools - switching to chat mode")
                _model_tool_support[model_name] = False
                return _simple_chat_fallback(llm, query, rag_context, model_name)
            
            # Other LLM errors
            logger.error(f"LLM invocation failed: {e}")
            return {
                "status": "error",
                "message": f"LLM error: {str(e)}",
                "iterations": iteration,
                "model": model_name
            }
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"LLM requested {len(response.tool_calls)} tool call(s)")
            messages.append(AIMessage(content=response.content or "", tool_calls=response.tool_calls))
            
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                result = execute_tool_call(tool_name, tool_args)
                
                tool_calls_history.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result[:500] + "..." if len(result) > 500 else result,
                    "iteration": iteration
                })
                
                messages.append(ToolMessage(content=result, tool_call_id=tool_call['id']))
        else:
            logger.info("Agent completed - no more tool calls")
            _model_tool_support[model_name] = True
            
            # COMPREHENSIVE RESPONSE EXTRACTION
            final_response = ""
            
            # 1. Try standard content
            if response.content and response.content.strip():
                final_response = response.content
                logger.info(f"Got response from content field ({len(final_response)} chars)")
            
            # 2. Try reasoning_content (Qwen3 thinking)
            if not final_response:
                reasoning = None
                if hasattr(response, 'additional_kwargs'):
                    reasoning = response.additional_kwargs.get('reasoning_content')
                if hasattr(response, 'response_metadata'):
                    if not reasoning:
                        reasoning = response.response_metadata.get('reasoning_content')
                
                if reasoning and reasoning.strip():
                    final_response = reasoning
                    logger.info(f"🧠 Got response from reasoning_content ({len(final_response)} chars)")
            
            # 3. Try to get from response_metadata message
            if not final_response:
                if hasattr(response, 'response_metadata'):
                    msg = response.response_metadata.get('message', {})
                    if isinstance(msg, dict):
                        content = msg.get('content', '')
                        if content and content.strip():
                            final_response = content
                            logger.info(f"Got response from response_metadata.message.content")
            
            # 4. Last resort: stringify the whole response
            if not final_response:
                logger.warning(f"⚠️  All extraction methods failed. Response object: {type(response)}")
                logger.warning(f"⚠️  Response attributes: {dir(response)}")
                final_response = str(response) if response else "I apologize, but I couldn't generate a response."
            
            return {
                "status": "success",
                "response": final_response,
                "tool_calls": tool_calls_history,
                "iterations": iteration,
                "model": model_name,
                "tools_available": True
            }
    
    return {
        "status": "error",
        "message": f"Max iterations ({max_iterations}) reached",
        "tool_calls": tool_calls_history,
        "iterations": iteration,
        "model": model_name
    }

# =============================================================================
# Agentic File Creation
# =============================================================================
def agentic_create_file(
    filename: str,
    description: str,
    model: Optional[str] = None,
    max_retries: int = 3
) -> dict:
    """Create a file with built-in verification and self-correction."""
    
    # AUTO-SANITIZE FILENAME
    import re
    # Replace spaces and special characters with hyphens
    sanitized = re.sub(r'[^\w\-_\.]', '-', filename)
    # Remove multiple consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    
    if sanitized != filename:
        logger.info(f"📝 Sanitized filename: '{filename}' → '{sanitized}'")
        filename = sanitized
    
    llm = _get_llm(model)
    current_content = ""
    last_error = ""
    
    for attempt in range(max_retries):
        prompt = f"""Create a file named: {filename}

Content requirements:
{description}

Generate the complete file content now. Output ONLY the file content, no explanations."""
        
        try:
            logger.info(f"🔄 Attempt {attempt+1}/{max_retries}: Generating content for {filename}...")
            response = llm.invoke(prompt)
            
            if not response or not response.content:
                logger.warning(f"⚠️  Attempt {attempt+1}: LLM returned empty response")
                last_error = "LLM returned empty response"
                continue
            
            raw_content = response.content.strip()
            
            if not raw_content:
                logger.warning(f"⚠️  Attempt {attempt+1}: Generated content is empty after stripping")
                last_error = "Generated content is empty"
                continue
            
            current_content = _strip_markdown_fences(raw_content)
            logger.info(f"✅ Generated {len(raw_content)} chars, processed to {len(current_content)} chars")
            
            if len(current_content) < 10:
                logger.warning(f"⚠️  Attempt {attempt+1}: Content too short ({len(current_content)} chars): {current_content}")
                last_error = f"Content too short: {current_content}"
                continue
            
        except Exception as e:
            logger.error(f"❌ Generation failed (attempt {attempt + 1}): {e}")
            last_error = f"Generation error: {e}"
            continue
        
        result = verifier.verify_file(filename, current_content)
        logger.info(f"🔍 Verification: valid={result['valid']}, msg='{result.get('message', '')}'")
        
        if result["valid"]:
            output_path = WORKSPACE / filename
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(current_content, encoding='utf-8')
                logger.info(f"💾 File saved: {output_path}")
                return {
                    "status": "success",
                    "filename": str(output_path),
                    "model": llm.model
                }
            except Exception as e:
                logger.error(f"❌ Save error: {e}")
                return {"status": "failed", "message": f"Save error: {e}"}
        else:
            last_error = result["message"]
            logger.warning(f"⚠️  Attempt {attempt + 1} failed verification: {last_error}")
            description += f"\n\n[VERIFICATION FEEDBACK] {last_error}. Regenerate with this fix."
    
    logger.error(f"❌ Failed to create {filename} after {max_retries} attempts")
    return {
        "status": "failed",
        "message": f"Failed after {max_retries} attempts. Last error: {last_error}",
        "model": llm.model
    }

# =============================================================================
# RAG Context Fetching
# =============================================================================

def fetch_rag_context(query: str, top_k: int = 3) -> tuple[str, bool]:
    """
    Fetch relevant context from the RAG knowledge base.
    
    Returns:
        Tuple of (formatted_context, rag_was_used)
    """
    if not retriever.qdrant_available:
        logger.debug("Qdrant not available, skipping RAG context")
        return "", False
    
    try:
        results = retriever.retrieve_advanced(query, top_k=top_k)
        
        if not results:
            logger.debug("No RAG results found")
            return "", False
        
        context_parts = []
        for i, result in enumerate(results, 1):
            payload = result.get('payload', {})
            content = payload.get('content', payload.get('text', str(result)))
            source = payload.get('source', payload.get('filename', 'Unknown'))
            score = result.get('score', 0.0)
            
            context_parts.append(f"[Source {i}: {source} (relevance: {score:.2f})]\n{content}")
        
        context = "\n\n---\n\n".join(context_parts)
        logger.info(f"✅ RAG context injected: {len(context)} chars from {len(results)} sources")
        return context, True
        
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return "", False

# =============================================================================
# General Agent Request Handler
# =============================================================================

def process_request(
    user_query: str,
    filename: Optional[str] = None,
    model: Optional[str] = None
) -> dict:
    """
    Main agent entry point - uses RAG context, tool-calling, and verification.
    """
    logger.info(f"🔍 process_request called with filename='{filename}', model='{model}'")
    logger.info(f"🔍 Query preview: {user_query[:100]}...")

    # 1. Fetch RAG context
    rag_context, rag_used = fetch_rag_context(user_query, top_k=3)
    
    # 2. If filename is provided, use file creation workflow
    if filename:
        logger.info(f"✅ ROUTING TO agentic_create_file for: {filename}")
        result = agentic_create_file(filename, user_query, model)
        result['rag_used'] = rag_used
        return result
    
    # 3. Otherwise, use ReAct loop with tool-calling
    logger.info(f"ℹ️ ROUTING TO agent_loop (no filename)")
    
    try:
        result = agent_loop(user_query, rag_context, model)
        
        # ✅ DEBUG: Log what we got back
        logger.info(f"🔍 Agent loop result keys: {result.keys()}")
        logger.info(f"🔍 Agent loop status: {result.get('status')}")
        logger.info(f"🔍 Agent loop response length: {len(result.get('response', ''))}")
        
        if result["status"] == "success":
            # ✅ THE FIX: Extract content from the correct field
            final_content = result.get("response", "")
            
            # Fallback if response is empty
            if not final_content:
                final_content = "I've processed your request, but the response was empty."
                logger.warning("⚠️  Response field was empty in agent_loop result")
            
            return {
                "status": "success",
                "message": "Response generated",
                "content": final_content,  # ← NOW POPULATED
                "tool_calls": result.get("tool_calls", []),
                "iterations": result.get("iterations", 0),
                "model": result.get("model", model or get_default_model()),
                "rag_used": rag_used,
                "tools_available": result.get("tools_available", True),
                "chat_mode_notice": result.get("chat_mode_notice", "")
            }
        else:
            return {
                "status": "failed",
                "message": result.get("message", "Unknown error"),
                "tool_calls": result.get("tool_calls", []),
                "model": model or get_default_model(),
                "rag_used": rag_used
            }
    except Exception as e:
        logger.error(f"Agent loop failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "message": f"Agent error: {str(e)}",
            "model": model or get_default_model(),
            "rag_used": rag_used
        }

# =============================================================================
# RAG Status Endpoint Helper
# =============================================================================

def get_rag_status() -> Dict[str, Any]:
    """Get the current status of the RAG system for API endpoints."""
    return retriever.get_status()
