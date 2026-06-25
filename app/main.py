# ~/MAi-RAG/app/main.py
"""
MAi-RAG API - Main Application
Production-ready FastAPI backend with comprehensive endpoint coverage.
"""

# CRITICAL: Set offline mode for HuggingFace BEFORE any other imports
import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/models")

# Now import everything else
from typing import Any, Optional, List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

import logging
import json
import uuid
import urllib.request
import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

# Memory managers
from app.memory.qdrant_manager import QdrantMemoryManager
from app.memory.sqlite_memory import SQLiteMemoryManager
from app.documents.processor import process_directory
from app.rag.vector_store import get_vector_store

# Import the router here, but don't attach it yet
from app.rag.rag_server import router as rag_router

# Agent logic
from app.agents.agent_core import (
    agentic_create_file,
    process_request,
    _get_llm,
    get_system_prompt,
    get_default_model,
    clear_model_cache,
    get_rag_status
)

# =============================================================================
# Configuration
# =============================================================================
PROJECT_ROOT = Path.home() / "MAi-RAG"
WORKSPACE_PATH = PROJECT_ROOT / "workspace"
WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)
DB_PATH = PROJECT_ROOT / "memory" / "memory_store.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Logging Setup
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Environment Checker
# =============================================================================

class EnvironmentChecker:
    """Check if required services are available."""
    
    def __init__(self):
        self.ollama_available = False
        self.qdrant_available = False
        self.ollama_url = "http://127.0.0.1:11434"
        self.qdrant_url = "http://127.0.0.1:6333"
        
    def check_ollama(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                models = data.get("models", [])
                self.ollama_available = True
                logger.info(f"Ollama is running with {len(models)} models")
                return True
        except Exception as e:
            self.ollama_available = False
            logger.warning(f"Ollama not available: {e}")
            return False
    
    def check_qdrant(self) -> bool:
        """Check if Qdrant is running and accessible."""
        try:
            req = urllib.request.Request(f"{self.qdrant_url}/collections", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                collections = data.get("result", {}).get("collections", [])
                self.qdrant_available = True
                logger.info(f"Qdrant is running with {len(collections)} collections")
                return True
        except Exception as e:
            self.qdrant_available = False
            logger.warning(f"Qdrant not available: {e}")
            return False
    
    def check_all(self) -> dict:
        """Run all environment checks."""
        self.check_ollama()
        self.check_qdrant()
        
        return {
            "ollama": {
                "available": self.ollama_available,
                "url": self.ollama_url,
                "download_url": "https://ollama.com/download"
            },
            "qdrant": {
                "available": self.qdrant_available,
                "url": self.qdrant_url,
                "download_url": "https://qdrant.tech/documentation/quick-start/"
            },
            "all_services_available": self.ollama_available and self.qdrant_available
        }

# Global environment checker instance
env_checker = EnvironmentChecker()

# =============================================================================
# FastAPI App Setup
# =============================================================================
executor = ThreadPoolExecutor(max_workers=4)

app = FastAPI(
    title="MAi-RAG API",
    version="2.0.0",
    description="Personal AI Assistant with RAG, Tool-Calling, and Agentic Workflows"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rag_router, prefix="/api/rag", tags=["RAG"])

# =============================================================================
# Initialize Managers (Lazy initialization to avoid startup crashes)
# =============================================================================
sqlite_manager: Optional[SQLiteMemoryManager] = None
qdrant_manager: Optional[QdrantMemoryManager] = None

heartbeat_task: Optional[asyncio.Task] = None
shutdown_flag = False

def get_sqlite_manager() -> SQLiteMemoryManager:
    """Lazy initialization of SQLite manager."""
    global sqlite_manager
    if sqlite_manager is None:
        sqlite_manager = SQLiteMemoryManager(db_path=DB_PATH)
        logger.info(f"SQLite manager initialized at: {sqlite_manager.db_path}")
    return sqlite_manager

def get_qdrant_manager() -> QdrantMemoryManager:
    """Lazy initialization of Qdrant manager."""
    global qdrant_manager
    if qdrant_manager is None:
        qdrant_manager = QdrantMemoryManager()
    return qdrant_manager

# =============================================================================
# Pydantic Models
# =============================================================================

class AgentRequest(BaseModel):
    query: str
    filename: Optional[str] = None
    model: Optional[str] = None

class FileCreationRequest(BaseModel):
    filename: str
    description: str
    model: Optional[str] = None

class DirectoryCreationRequest(BaseModel):
    path: str

class NoteSaveRequest(BaseModel):
    filename: str
    content: str

class CollectionRequest(BaseModel):
    name: str
    action: str

class IngestRequest(BaseModel):
    collection: str
    documents: List[dict]

class SearchRequest(BaseModel):
    collection: str
    query: str
    top_k: int = 5

class EventRequest(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    location: Optional[str] = None
    category: str = "general"
    is_recurring: bool = False
    recurrence_type: Optional[str] = None
    recurrence_days: Optional[List[str]] = None
    recurrence_end_date: Optional[str] = None

class ReminderRequest(BaseModel):
    id: Optional[str] = None
    text: str
    due_time: str
    priority: str = "medium"
    completed: bool = False

class TodoRequest(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    completed: bool = False
    due_date: Optional[str] = None

class UserProfileRequest(BaseModel):
    key: str
    value: Any

class ChatMessageRequest(BaseModel):
    thread_id: str
    role: str
    content: str
    message_id: Optional[str] = None

class ChatThreadRequest(BaseModel):
    id: str
    title: str

class SettingsRequest(BaseModel):
    key: str
    value: Any

class DirectoryIngestRequest(BaseModel):
    directory: str
    collection: str
    chunk_size: int = 1000
    chunk_overlap: int = 200
    file_extensions: Optional[List[str]] = None

class SyntheticDataRequest(BaseModel):
    collection: str
    topic: str
    num_samples: int = 10
    purpose: str = "constraint_validation"  # NEW: adversarial, error_recovery, edge_cases, constraint_validation
    compliance_threshold: int = 95  # NEW: minimum compliance score (0-100)

class DeleteDocumentRequest(BaseModel):
    collection: str
    document_ids: List[str]  # List of document IDs to delete


# =============================================================================
# Security Helpers
# =============================================================================

def resolve_project_path(user_path: str) -> Path:
    """Securely resolve a path within the project root."""
    expanded = Path(user_path).expanduser().resolve()
    project_abs = PROJECT_ROOT.resolve()
    
    forbidden = ['venv', 'node_modules', '.git', '__pycache__', '.env']
    for forbidden_dir in forbidden:
        if forbidden_dir in expanded.parts:
            raise ValueError(f"Access to '{forbidden_dir}' is strictly forbidden.")
    
    try:
        expanded.relative_to(project_abs)
        return expanded
    except ValueError:
        raise ValueError(f"Path traversal detected: '{user_path}' resolves outside project root")

def resolve_workspace_path(user_path: str) -> Path:
    """Securely resolve a path, anchoring relative paths to the workspace."""
    path = Path(user_path)
    
    if not path.is_absolute():
        path = WORKSPACE_PATH / path
    
    expanded = path.expanduser().resolve()
    workspace_abs = WORKSPACE_PATH.resolve()
    
    try:
        expanded.relative_to(workspace_abs)
        return expanded
    except ValueError:
        raise ValueError(f"Path traversal detected: '{user_path}' resolves outside workspace")

# =============================================================================
# Health & System Endpoints
# =============================================================================

@app.get("/api/system/environment")
async def check_environment():
    """Check if required services (Ollama, Qdrant) are available."""
    try:
        status = env_checker.check_all()
        return status
    except Exception as e:
        logger.error(f"Environment check failed: {e}", exc_info=True)
        return {
            "ollama": {"available": False, "error": str(e)},
            "qdrant": {"available": False, "error": str(e)},
            "all_services_available": False
        }

@app.get("/api/health")
async def health_check():
    """Comprehensive health check."""
    try:
        mgr = get_sqlite_manager()
        return {
            "status": "ok",
            "last_heartbeat": mgr.get("last_heartbeat"),
            "default_model": get_default_model(),
            "workspace_writable": os.access(WORKSPACE_PATH, os.W_OK),
            "database_path": str(mgr.db_path)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/system/status")
async def get_system_status():
    """Check if MAi-RAG services are running."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'uvicorn app.main:app'],
            capture_output=True,
            text=True
        )
        is_running = result.returncode == 0
        
        return {
            "status": "running" if is_running else "stopped",
            "pid": result.stdout.strip().split('\n')[0] if is_running else None
        }
    except Exception as e:
        logger.error(f"Failed to check system status: {e}")
        return {"status": "unknown", "error": str(e)}

@app.post("/api/system/stop")
async def stop_system():
    """Stop MAi-RAG services gracefully."""
    try:
        stop_script = PROJECT_ROOT / "stop.sh"
        if stop_script.exists():
            subprocess.Popen(['bash', str(stop_script)], start_new_session=True)
            return {"status": "stopping", "message": "MAi-RAG is shutting down..."}
        else:
            return {"status": "error", "message": "stop.sh not found"}
    except Exception as e:
        logger.error(f"Failed to stop system: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/system/start")
async def start_system():
    """Signal the watchdog to start MAi-RAG."""
    try:
        flag_file = PROJECT_ROOT / "restart.flag"
        flag_file.touch()
        return {"status": "starting", "message": "Restart signal sent to watchdog."}
    except Exception as e:
        logger.error(f"Failed to create restart flag: {e}")
        return {"status": "error", "message": str(e)}

# =============================================================================
# Ollama Model Management
# =============================================================================

@app.get("/api/ollama/models")
async def get_ollama_models():
    """Fetch available models from Ollama."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            models = [model["name"] for model in data.get("models", [])]
            return {"models": models}
    except Exception as e:
        logger.error(f"Failed to fetch Ollama models: {e}")
        return {"models": [], "error": str(e)}

# =============================================================================
# Settings Endpoints
# =============================================================================

@app.get("/api/settings/system-prompt")
async def get_system_prompt_setting():
    """Get the current system prompt."""
    try:
        mgr = get_sqlite_manager()
        prompt = mgr.get("system_prompt")
        if not prompt:
            from app.agents.agent_core import DEFAULT_SYSTEM_PROMPT
            prompt = DEFAULT_SYSTEM_PROMPT
        return {"prompt": prompt}
    except Exception as e:
        logger.error(f"Failed to get system prompt: {e}")
        return {"prompt": ""}

@app.post("/api/settings/system-prompt")
async def save_system_prompt(request: dict):
    """Save the system prompt."""
    try:
        content = request.get("content", "")
        if not content.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        mgr = get_sqlite_manager()
        success = mgr.set("system_prompt", content)
        if success:
            logger.info(f"System prompt saved ({len(content)} chars)")
            return {"status": "saved"}
        else:
            raise RuntimeError("sqlite_manager.set() returned False")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save system prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/heartbeat")
async def get_heartbeat_settings():
    """Get heartbeat interval settings (returns minutes)."""
    try:
        mgr = get_sqlite_manager()
        interval_seconds = mgr.get("heartbeat_interval")
        if interval_seconds:
            interval_minutes = int(interval_seconds) / 60
            return {"interval": interval_minutes, "interval_seconds": int(interval_seconds)}
        return {"interval": 5, "interval_seconds": 300}
    except Exception as e:
        logger.error(f"Failed to get heartbeat settings: {e}")
        return {"interval": 5, "interval_seconds": 300}

@app.post("/api/settings/heartbeat")
async def save_heartbeat_settings(request: dict):
    """Save heartbeat interval settings (in minutes)."""
    try:
        interval = request.get("interval", 5)
        if not isinstance(interval, (int, float)) or interval < 1:
            raise HTTPException(status_code=400, detail="Interval must be a number >= 1 minute")
        
        interval_seconds = int(interval * 60)
        
        mgr = get_sqlite_manager()
        success = mgr.set("heartbeat_interval", str(interval_seconds))
        if success:
            logger.info(f"Heartbeat interval saved: {interval} minutes ({interval_seconds}s)")
            return {"status": "saved", "interval": interval, "interval_seconds": interval_seconds}
        else:
            raise RuntimeError("sqlite_manager.set() returned False")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save heartbeat settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/heartbeat-prompt")
async def get_heartbeat_prompt():
    """Get the heartbeat system prompt."""
    try:
        mgr = get_sqlite_manager()
        prompt = mgr.get("heartbeat_prompt")
        if not prompt:
            prompt = """Quick system check. Respond with ONLY one of these:
- "OK" if everything is fine
- "ERROR: [brief description]" if something needs attention

Keep response under 20 words."""
        return {"prompt": prompt}
    except Exception as e:
        logger.error(f"Failed to get heartbeat prompt: {e}")
        return {"prompt": ""}

@app.post("/api/settings/heartbeat-prompt")
async def save_heartbeat_prompt(request: dict):
    """Save the heartbeat system prompt."""
    try:
        prompt = request.get("prompt", "")
        if not prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        mgr = get_sqlite_manager()
        success = mgr.set("heartbeat_prompt", prompt)
        if success:
            logger.info(f"Heartbeat prompt saved ({len(prompt)} chars)")
            return {"status": "saved"}
        else:
            raise RuntimeError("sqlite_manager.set() returned False")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save heartbeat prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/notifications")
async def get_notification_settings():
    """Get notification preferences."""
    try:
        mgr = get_sqlite_manager()
        intervals_json = mgr.get("notification_intervals")
        if intervals_json:
            return {"intervals": json.loads(intervals_json)}
        
        return {
            "intervals": [
                {"label": "24h", "minutes": 1440, "enabled": True},
                {"label": "1h", "minutes": 60, "enabled": True},
                {"label": "30m", "minutes": 30, "enabled": True},
                {"label": "15m", "minutes": 15, "enabled": True},
                {"label": "5m", "minutes": 5, "enabled": True},
                {"label": "0m", "minutes": 0, "enabled": True},
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get notification settings: {e}")
        return {"intervals": []}

@app.post("/api/settings/notifications")
async def save_notification_settings(request: dict):
    """Save notification preferences."""
    try:
        intervals = request.get("intervals", [])
        mgr = get_sqlite_manager()
        mgr.set("notification_intervals", json.dumps(intervals))
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Failed to save notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/default-model")
async def get_default_model_setting():
    """Get the current default model."""
    try:
        mgr = get_sqlite_manager()
        model = mgr.get("default_model")
        return {"model": model or get_default_model()}
    except Exception as e:
        logger.error(f"Failed to get default model: {e}")
        return {"model": get_default_model()}

@app.post("/api/settings/default-model")
async def save_default_model_setting(request: dict):
    """Save the default model preference."""
    try:
        model = request.get("model", "")
        if not model:
            raise HTTPException(status_code=400, detail="Model name is required")
        
        mgr = get_sqlite_manager()
        success = mgr.set("default_model", model)
        if success:
            clear_model_cache()
            logger.info(f"Default model saved: {model}")
            return {"status": "saved", "model": model}
        else:
            raise RuntimeError("sqlite_manager.set() returned False")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save default model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Heartbeat System
# =============================================================================

@app.post("/api/heartbeat/trigger")
async def trigger_heartbeat():
    """Manually trigger a quick heartbeat check."""
    try:
        logger.info("Manual heartbeat trigger requested")
        await run_heartbeat_check()
        return {
            "status": "success" if heartbeat_state["last_status"] == "OK" else "failed",
            "last_status": heartbeat_state["last_status"],
            "last_message": heartbeat_state["last_message"],
            "last_check": heartbeat_state["last_check"],
            "next_check": heartbeat_state.get("next_check")
        }
    except Exception as e:
        logger.error(f"Manual heartbeat trigger error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

heartbeat_state = {
    "last_check": None,
    "last_status": "UNKNOWN",
    "last_message": "Not yet run",
    "next_check": None,
    "is_running": False
}

async def run_heartbeat_check():
    """Execute a quick heartbeat check - SQLite connectivity only."""
    global heartbeat_state
    
    if heartbeat_state["is_running"]:
        logger.warning("Heartbeat already running, skipping")
        return
    
    if shutdown_flag:
        logger.info("Shutdown in progress, skipping heartbeat")
        return
    
    heartbeat_state["is_running"] = True
    heartbeat_state["last_status"] = "RUNNING"
    heartbeat_state["last_message"] = "Checking database..."
    logger.info("Starting quick heartbeat check...")
    
    try:
        mgr = get_sqlite_manager()
        test_read = mgr.get("last_heartbeat")
        test_key = f"__heartbeat_test_{datetime.now().timestamp()}"
        mgr.set(test_key, "ok")
        mgr.delete(test_key)
        test_events = mgr.get_upcoming_events(limit=1)
        test_todos = mgr.get_pending_todos(limit=1)
        
        heartbeat_state["last_check"] = datetime.now().isoformat()
        heartbeat_state["last_status"] = "OK"
        heartbeat_state["last_message"] = f"Database healthy (checked at {datetime.now().strftime('%H:%M:%S')})"
        logger.info(f"Heartbeat check completed (SQLite OK) at {datetime.now().strftime('%H:%M:%S')}")
        
        mgr.set("last_heartbeat", heartbeat_state["last_check"])
        mgr.set("last_heartbeat_status", heartbeat_state["last_status"])
        mgr.set("last_heartbeat_message", heartbeat_state["last_message"])
        
    except Exception as e:
        heartbeat_state["last_check"] = datetime.now().isoformat()
        heartbeat_state["last_status"] = "ERROR"
        heartbeat_state["last_message"] = f"Database error: {str(e)}"
        logger.error(f"Heartbeat check failed: {e}", exc_info=True)
        
        try:
            mgr = get_sqlite_manager()
            mgr.set("last_heartbeat", heartbeat_state["last_check"])
            mgr.set("last_heartbeat_status", heartbeat_state["last_status"])
            mgr.set("last_heartbeat_message", heartbeat_state["last_message"])
        except:
            pass
    finally:
        heartbeat_state["is_running"] = False
        await update_next_check_time()
        logger.debug(f"Next check scheduled for: {heartbeat_state.get('next_check', 'unknown')}")

async def update_next_check_time():
    """Calculate and store the next check time."""
    global heartbeat_state
    
    if heartbeat_state["is_running"]:
        heartbeat_state["next_check"] = None
        return
    
    try:
        mgr = get_sqlite_manager()
        interval_seconds = mgr.get("heartbeat_interval")
        
        if interval_seconds:
            interval_seconds = int(interval_seconds)
            if heartbeat_state["last_check"]:
                last_check = datetime.fromisoformat(heartbeat_state["last_check"])
                next_check = last_check + timedelta(seconds=interval_seconds)
                heartbeat_state["next_check"] = next_check.isoformat()
            else:
                next_check = datetime.now() + timedelta(seconds=interval_seconds)
                heartbeat_state["next_check"] = next_check.isoformat()
        else:
            next_check = datetime.now() + timedelta(seconds=300)
            heartbeat_state["next_check"] = next_check.isoformat()
    except Exception as e:
        logger.warning(f"Failed to update next check time: {e}")

async def heartbeat_scheduler():
    """Background task that runs heartbeat checks at configured intervals."""
    global shutdown_flag
    logger.info("Heartbeat scheduler started")
    
    await run_heartbeat_check()
    
    while not shutdown_flag:
        try:
            mgr = get_sqlite_manager()
            interval_seconds = mgr.get("heartbeat_interval")
            
            if not interval_seconds:
                interval_seconds = 300
            
            interval_seconds = int(interval_seconds)
            
            for _ in range(interval_seconds):
                if shutdown_flag:
                    logger.info("Heartbeat scheduler received shutdown signal")
                    return
                await asyncio.sleep(1)
            
            if not shutdown_flag:
                await run_heartbeat_check()
            
        except asyncio.CancelledError:
            logger.info("Heartbeat scheduler cancelled")
            return
        except Exception as e:
            logger.error(f"Heartbeat scheduler error: {e}", exc_info=True)
            await asyncio.sleep(60)

@app.get("/api/heartbeat/status")
async def get_heartbeat_status():
    """Get current heartbeat state."""
    global heartbeat_state
    return heartbeat_state

# =============================================================================
# Agent Endpoints
# =============================================================================

@app.post("/api/agent")
async def agent_endpoint(request: AgentRequest):
    """Main agent endpoint with file creation support."""
    try:
        model = request.model or get_default_model()
        
        # Check if this is a file creation request
        if request.filename:
            from app.agents.agent_core import create_file_with_verification
            result = create_file_with_verification(
                filename=request.filename,
                description=request.query,
                model=model
            )
            return result
        
        # Regular chat request
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: process_request(request.query, request.filename, model=model)
        )
        
        return result
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_endpoint(request: AgentRequest):
    """Simple chat endpoint."""
    try:
        loop = asyncio.get_event_loop()
        
        def run_chat():
            llm = _get_llm(request.model)
            prompt = get_system_prompt()
            prompt_text = f"{prompt}\n\nUser: {request.query}\nAssistant:"
            response = llm.invoke(prompt_text)
            return {"content": response.content, "model": request.model or get_default_model()}
        
        return await loop.run_in_executor(executor, run_chat)
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agent/read-file")
async def read_file_endpoint(request: dict):
    """Allow the agent to securely read a file."""
    file_path = request.get("path", "")
    if not file_path:
        raise HTTPException(status_code=400, detail="Path is required")
    
    try:
        safe_path = resolve_project_path(file_path)
        if not safe_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        content = safe_path.read_text(encoding='utf-8')
        if len(content) > 50000:
            return {
                "status": "success",
                "path": str(safe_path.relative_to(PROJECT_ROOT)),
                "content": content[:50000] + "\n\n...[TRUNCATED]..."
            }
        
        return {
            "status": "success",
            "path": str(safe_path.relative_to(PROJECT_ROOT)),
            "content": content
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

@app.post("/api/agent/create-file")
async def create_file_endpoint(request: FileCreationRequest):
    """Simple file creation."""
    try:
        safe_path = resolve_workspace_path(request.filename)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(request.description or "", encoding='utf-8')
        return {
            "status": "success",
            "path": str(safe_path.relative_to(WORKSPACE_PATH)),
            "filename": request.filename
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create file: {str(e)}")

@app.post("/api/agent/create-dir")
async def create_directory_endpoint(request: DirectoryCreationRequest):
    """Create a directory."""
    try:
        safe_path = resolve_workspace_path(request.path)
        safe_path.mkdir(parents=True, exist_ok=True)
        return {
            "status": "success",
            "path": str(safe_path.relative_to(WORKSPACE_PATH)),
            "message": f"Directory created: {request.path}"
        }
    except Exception as e:
        logger.error(f"Failed to create directory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create directory: {str(e)}")

# =============================================================================
# SQLite Memory Endpoints
# =============================================================================

@app.get("/api/memory/sqlite/chat/threads")
async def get_chat_threads():
    try:
        mgr = get_sqlite_manager()
        with mgr.get_cursor() as cur:
            cur.execute("SELECT id, title, created_at, last_message_at FROM chat_threads ORDER BY created_at DESC")
            threads = [
                {
                    "id": row[0],
                    "title": row[1],
                    "created_at": row[2],
                    "last_message_at": row[3]
                }
                for row in cur.fetchall()
            ]
        return {"threads": threads}
    except Exception as e:
        logger.error(f"Failed to get chat threads: {e}", exc_info=True)
        return {"threads": []}

@app.get("/api/memory/sqlite/chat/messages/{thread_id}")
async def get_chat_messages(thread_id: str):
    try:
        mgr = get_sqlite_manager()
        with mgr.get_cursor() as cur:
            # Note: using 'timestamp' as per your schema check
            cur.execute("""
                SELECT id, role, content, timestamp 
                FROM chat_messages 
                WHERE thread_id = ? 
                ORDER BY timestamp ASC
            """, (thread_id,))
            messages = []
            for row in cur.fetchall():
                timestamp = 0
                if row[3]:
                    try:
                        from datetime import datetime
                        # Handle both 'YYYY-MM-DD HH:MM:SS' and ISO formats
                        dt_str = str(row[3]).replace(' ', 'T')
                        dt = datetime.fromisoformat(dt_str)
                        timestamp = int(dt.timestamp() * 1000)
                    except Exception:
                        pass
                
                messages.append({
                    "id": row[0],
                    "from": "ai" if row[1] == "assistant" else row[1],
                    "text": row[2],
                    "timestamp": timestamp
                })
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Failed to get chat messages: {e}", exc_info=True)
        return {"messages": []}

@app.get("/api/memory/sqlite/notifications/due-soon")
async def get_due_soon_notifications():
    """Fetch upcoming events and pending reminders."""
    try:
        mgr = get_sqlite_manager()
        events = mgr.get_upcoming_events(limit=15)
        reminders = mgr.get_pending_reminders(limit=15)
        
        logger.info(f"Notification check: {len(events)} events, {len(reminders)} reminders")
        
        return {
            "events": events or [],
            "reminders": reminders or [],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Critical error in notifications endpoint: {e}", exc_info=True)
        return {
            "events": [],
            "reminders": [],
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/memory/sqlite/events/upcoming")
async def get_upcoming_events(limit: int = 20):
    """Get upcoming events."""
    try:
        mgr = get_sqlite_manager()
        events = mgr.get_upcoming_events(limit=limit)
        return {"events": events or []}
    except Exception as e:
        logger.error(f"Failed to get upcoming events: {e}")
        return {"events": []}

@app.post("/api/memory/sqlite/events")
async def create_or_update_event(request: EventRequest):
    """Create or update an event."""
    try:
        mgr = get_sqlite_manager()
        event_data = request.dict(exclude_none=True)
        event_id = mgr.save_event(event_data)
        return {"status": "saved", "id": event_id}
    except Exception as e:
        logger.error(f"Failed to save event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/memory/sqlite/events/{event_id}")
async def delete_event(event_id: str):
    """Delete an event."""
    try:
        mgr = get_sqlite_manager()
        mgr.delete_event(event_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/sqlite/reminders/upcoming")
async def get_upcoming_reminders(limit: int = 20):
    """Get upcoming reminders."""
    try:
        mgr = get_sqlite_manager()
        reminders = mgr.get_pending_reminders(limit=limit)
        return {"reminders": reminders or []}
    except Exception as e:
        logger.error(f"Failed to get reminders: {e}")
        return {"reminders": []}

@app.post("/api/memory/sqlite/reminders")
async def create_or_update_reminder(request: ReminderRequest):
    """Create or update a reminder."""
    try:
        mgr = get_sqlite_manager()
        reminder_data = request.dict(exclude_none=True)
        reminder_id = mgr.save_reminder(reminder_data)
        return {"status": "saved", "id": reminder_id}
    except Exception as e:
        logger.error(f"Failed to save reminder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/memory/sqlite/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    """Delete a reminder."""
    try:
        mgr = get_sqlite_manager()
        mgr.delete_reminder(reminder_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete reminder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/sqlite/todos")
async def get_todos(limit: int = 50):
    """Get all todos."""
    try:
        mgr = get_sqlite_manager()
        todos = mgr.get_pending_todos(limit=limit)
        return {"todos": todos or []}
    except Exception as e:
        logger.error(f"Failed to get todos: {e}")
        return {"todos": []}

@app.post("/api/memory/sqlite/todos")
async def create_or_update_todo(request: TodoRequest):
    """Create or update a todo."""
    try:
        mgr = get_sqlite_manager()
        todo_data = request.dict(exclude_none=True)
        todo_id = mgr.save_todo(todo_data)
        return {"status": "saved", "id": todo_id}
    except Exception as e:
        logger.error(f"Failed to save todo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/memory/sqlite/todos/{todo_id}")
async def delete_todo(todo_id: str):
    """Delete a todo."""
    try:
        mgr = get_sqlite_manager()
        mgr.delete_todo(todo_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete todo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/sqlite/chat/thread")
async def save_chat_thread(request: ChatThreadRequest):
    """Save or update a chat thread."""
    try:
        mgr = get_sqlite_manager()
        mgr.save_chat_thread(request.id, request.title)
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Failed to save chat thread: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/sqlite/chat/message")
async def save_chat_message(request: ChatMessageRequest):
    """Save a chat message."""
    try:
        mgr = get_sqlite_manager()
        mgr.save_chat_message(
            thread_id=request.thread_id,
            role=request.role,
            content=request.content,
            message_id=request.message_id
        )
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Failed to save chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/extract-facts")
async def extract_facts_from_chat(request: dict):
    """Extract user facts from recent chat messages."""
    try:
        from app.agents.agent_core import extract_user_facts, save_extracted_facts
        
        thread_id = request.get("thread_id")
        if not thread_id:
            raise HTTPException(status_code=400, detail="thread_id is required")
        
        mgr = get_sqlite_manager()
        recent_msgs = mgr.get_chat_messages(thread_id, limit=10)
        
        if not recent_msgs:
            return {"status": "no_messages", "facts_extracted": 0}
        
        # Convert to dict format for extraction
        chat_history = [{"role": msg["role"], "content": msg["content"]} for msg in recent_msgs]
        
        new_facts = extract_user_facts(chat_history)
        
        if new_facts:
            save_extracted_facts(new_facts)
        
        return {
            "status": "success",
            "facts_extracted": len(new_facts),
            "facts": new_facts
        }
    except Exception as e:
        logger.error(f"Failed to extract facts: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@app.get("/api/memory/sqlite/user-profile")
async def get_user_profile():
    """Get all user profile data."""
    try:
        mgr = get_sqlite_manager()
        profile = mgr.get_user_profile()
        return {"profile": profile or {}}
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        return {"profile": {}}

@app.post("/api/memory/sqlite/user-profile")
async def save_user_profile(request: UserProfileRequest):
    """Save a user profile entry."""
    try:
        mgr = get_sqlite_manager()
        mgr.save_user_profile(request.key, str(request.value))
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Failed to save user profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/analytics/stm-size")
async def get_stm_size():
    """Get SQLite database file size."""
    try:
        if DB_PATH.exists():
            return {"size": DB_PATH.stat().st_size}
        return {"size": 0}
    except Exception as e:
        logger.error(f"Failed to get STM size: {e}")
        return {"size": 0}

@app.get("/api/system/cpu")
async def get_system_cpu():
    """Get CPU usage percentage."""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        return {"percent": cpu_percent}
    except Exception as e:
        logger.error(f"Failed to get CPU usage: {e}")
        return {"percent": 0, "error": str(e)}

@app.get("/api/system/ram")
async def get_system_ram():
    """Get system RAM and swap usage (cross-platform)."""
    try:
        import psutil
        
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "used": mem.used // (1024 * 1024),
            "total": mem.total // (1024 * 1024),
            "percent": mem.percent,
            "swap_used": swap.used // (1024 * 1024),
            "swap_total": swap.total // (1024 * 1024),
            "swap_percent": swap.percent
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}", exc_info=True)
        return {"used": 0, "total": 0, "percent": 0, "swap_used": 0, "swap_total": 0, "swap_percent": 0}

@app.get("/api/memory/sqlite/events/all")
async def get_all_events(limit: int = 1000):
    """Get all events including past recurring instances."""
    try:
        mgr = get_sqlite_manager()
        events = mgr.get_all_events(limit=limit)
        return {"events": events or []}
    except Exception as e:
        logger.error(f"Failed to get all events: {e}")
        return {"events": []}

@app.delete("/api/memory/sqlite/events/recurring/{base_event_id}")
async def delete_recurring_events(base_event_id: str):
    """Delete a recurring event and all its instances."""
    try:
        mgr = get_sqlite_manager()
        
        # Get the base event to check if it's recurring
        with mgr.get_cursor() as cur:
            cur.execute("SELECT id, is_recurring FROM events WHERE id = ?", (base_event_id,))
            base_event = cur.fetchone()
            
            if not base_event:
                raise HTTPException(status_code=404, detail="Event not found")
            
            # Delete all instances (IDs that start with base_event_id)
            cur.execute("DELETE FROM events WHERE id LIKE ?", (f"{base_event_id}%",))
            deleted_count = cur.rowcount
        
        return {
            "status": "deleted",
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} event instances"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete recurring events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Qdrant Endpoints
# =============================================================================
@app.post("/api/memory/qdrant/chunk-files")
async def chunk_files_endpoint(request: DirectoryIngestRequest):
    """Chunk files from documents_storage and save to storage/chunks."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")
        
        # Create chunks directory
        chunks_dir = PROJECT_ROOT / "storage" / "chunks" / request.collection
        chunks_dir.mkdir(parents=True, exist_ok=True)
        
        # Get files from documents_storage
        docs_dir = PROJECT_ROOT / "documents_storage"
        if not docs_dir.exists():
            docs_dir.mkdir(parents=True, exist_ok=True)
            return {"status": "no_files", "message": "documents_storage directory is empty"}
        
        extensions = request.file_extensions or ['.txt', '.md', '.py', '.js', '.ts', '.json', '.yaml', '.yml']
        files_to_chunk = []
        for ext in extensions:
            files_to_chunk.extend(docs_dir.rglob(f"*{ext}"))
        
        if not files_to_chunk:
            return {"status": "no_files", "message": f"No files found with extensions: {extensions}"}
        
        total_chunks = 0
        metadata = {
            "collection": request.collection,
            "chunk_size": request.chunk_size,
            "chunk_overlap": request.chunk_overlap,
            "files": [],
            "created_at": datetime.now().isoformat()
        }
        
        for file_path in files_to_chunk:
            try:
                content = file_path.read_text(encoding='utf-8')
                chunks = chunk_text(content, request.chunk_size, request.chunk_overlap)
                
                file_metadata = {
                    "source": str(file_path.relative_to(docs_dir)),
                    "chunks_count": len(chunks),
                    "chunk_indices": []
                }
                
                for i, chunk in enumerate(chunks):
                    chunk_file = chunks_dir / f"{file_path.stem}_chunk_{i:04d}.txt"
                    chunk_file.write_text(chunk, encoding='utf-8')
                    file_metadata["chunk_indices"].append(i)
                    total_chunks += 1
                
                metadata["files"].append(file_metadata)
                logger.info(f"Chunked {file_path.name}: {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Failed to chunk {file_path}: {e}")
                continue
        
        # Save metadata
        metadata_file = chunks_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        
        return {
            "status": "success",
            "collection": request.collection,
            "total_chunks": total_chunks,
            "files_processed": len(files_to_chunk),
            "chunks_directory": str(chunks_dir)
        }
        
    except Exception as e:
        logger.error(f"Failed to chunk files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/qdrant/list-chunks/{collection}")
async def list_chunks(collection: str):
    """List all chunks for a collection."""
    try:
        chunks_dir = PROJECT_ROOT / "storage" / "chunks" / collection
        if not chunks_dir.exists():
            return {"status": "no_chunks", "chunks": [], "metadata": None}
        
        # Read metadata
        metadata_file = chunks_dir / "metadata.json"
        metadata = None
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
        
        # List chunk files
        chunk_files = [f.name for f in chunks_dir.glob("*.txt")]
        
        return {
            "status": "success",
            "chunks": chunk_files,
            "metadata": metadata,
            "total_chunks": len(chunk_files)
        }
    except Exception as e:
        logger.error(f"Failed to list chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/search")
async def search_knowledge_base(request: dict):
    """Search the knowledge base"""
    try:
        query = request.get("query")
        collection = request.get("collection", "local_docs")
        top_k = request.get("top_k", 5)
        
        vector_store = get_vector_store(collection)
        results = vector_store.search(query, top_k=top_k)
        
        return {"results": results}
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/qdrant/ingest-chunks/{collection}")
async def ingest_chunks(collection: str):
    """Ingest pre-chunked files into Qdrant."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")
        
        chunks_dir = PROJECT_ROOT / "storage" / "chunks" / collection
        if not chunks_dir.exists():
            raise HTTPException(status_code=404, detail=f"No chunks found for collection: {collection}")
        
        # Read metadata
        metadata_file = chunks_dir / "metadata.json"
        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail="Metadata file not found")
        
        metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
        
        documents = []
        for chunk_file in chunks_dir.glob("*.txt"):
            content = chunk_file.read_text(encoding='utf-8')
            # Extract source from filename
            source = chunk_file.stem.rsplit('_chunk_', 1)[0]
            
            documents.append({
                "content": content,
                "source": source,
                "chunk_file": chunk_file.name
            })
        
        if not documents:
            raise HTTPException(status_code=400, detail="No chunk files found")
        
        # Ingest into Qdrant
        qm.ingest_documents(collection, documents)
        
        return {
            "status": "success",
            "collection": collection,
            "documents_ingested": len(documents),
            "message": f"Successfully ingested {len(documents)} chunks into Qdrant"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest chunks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/memory/qdrant/cleanup-chunks/{collection}")
async def cleanup_chunks(collection: str):
    """Delete chunk files after successful ingestion."""
    try:
        chunks_dir = PROJECT_ROOT / "storage" / "chunks" / collection
        if not chunks_dir.exists():
            return {"status": "not_found", "message": "No chunks to cleanup"}
        
        # Count files before deletion
        chunk_files = list(chunks_dir.glob("*.txt"))
        metadata_file = chunks_dir / "metadata.json"
        
        # Delete chunk files
        deleted_count = 0
        for chunk_file in chunk_files:
            chunk_file.unlink()
            deleted_count += 1
        
        # Delete metadata
        if metadata_file.exists():
            metadata_file.unlink()
        
        # Delete directory if empty
        try:
            chunks_dir.rmdir()
        except OSError:
            pass  # Directory not empty
        
        return {
            "status": "success",
            "deleted_files": deleted_count,
            "message": f"Cleaned up {deleted_count} chunk files"
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/qdrant/delete")
async def delete_qdrant_documents(request: DeleteDocumentRequest):
    """Delete specific documents from Qdrant collection."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")
        
        deleted_count = qm.delete_documents(request.collection, request.document_ids)
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "collection": request.collection
        }
    except Exception as e:
        logger.error(f"Failed to delete documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/analytics/ltm-size")
async def get_ltm_size():
    """Get Qdrant storage size (approximate)."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            return {"size": 0}
        
        # Qdrant doesn't expose size directly, estimate from collections
        collections = qm.list_collections()
        # Rough estimate: 1MB per collection as baseline
        estimated_size = len(collections) * 1024 * 1024
        return {"size": estimated_size}
    except Exception as e:
        logger.error(f"Failed to get LTM size: {e}")
        return {"size": 0}

@app.get("/api/memory/qdrant/collections")
async def get_qdrant_collections():
    """List all Qdrant collections."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            return {"collections": [], "available": False}
        
        collections = qm.list_collections()
        return {"collections": collections, "available": True}
    except Exception as e:
        logger.error(f"Failed to get Qdrant collections: {e}")
        return {"collections": [], "available": False, "error": str(e)}

@app.post("/api/memory/qdrant/collection")
async def manage_qdrant_collection(request: CollectionRequest):
    """Create or delete a Qdrant collection."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")
        
        if request.action == "create":
            qm.create_collection(request.name)
            return {"status": "created", "collection": request.name}
        elif request.action == "delete":
            qm.delete_collection(request.name)
            return {"status": "deleted", "collection": request.name}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to manage Qdrant collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/qdrant/ingest-directory")
async def ingest_directory(request: DirectoryIngestRequest):
    """Ingest all files from a directory into Qdrant with chunking."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")
        
        dir_path = Path(request.directory).expanduser().resolve()
        
        if not dir_path.exists() or not dir_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Directory not found: {dir_path}")
        
        extensions = request.file_extensions or ['.txt', '.md', '.py', '.js', '.ts', '.json', '.yaml', '.yml']
        
        files_to_ingest = []
        for ext in extensions:
            files_to_ingest.extend(dir_path.rglob(f"*{ext}"))
        
        if not files_to_ingest:
            return {"status": "no_files", "message": f"No files found with extensions: {extensions}"}
        
        logger.info(f"Found {len(files_to_ingest)} files to ingest from {dir_path}")
        
        total_chunks = 0
        for file_path in files_to_ingest:
            try:
                content = file_path.read_text(encoding='utf-8')
                chunks = chunk_text(content, request.chunk_size, request.chunk_overlap)
                
                documents = []
                for i, chunk in enumerate(chunks):
                    documents.append({
                        "content": chunk,
                        "source": str(file_path.relative_to(dir_path)),
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "file_path": str(file_path)
                    })
                
                if documents:
                    qm.ingest_documents(request.collection, documents)
                    total_chunks += len(documents)
                    logger.info(f"Ingested {len(documents)} chunks from {file_path.name}")
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue
        
        return {
            "status": "success",
            "files_processed": len(files_to_ingest),
            "total_chunks": total_chunks,
            "collection": request.collection
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest directory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks

@app.post("/api/memory/qdrant/ingest")
async def ingest_documents(request: IngestRequest):
    """Ingest documents into a Qdrant collection."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")
        
        result = qm.ingest_documents(request.collection, request.documents)
        return {"status": "ingested", "count": len(request.documents)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/qdrant/search")
async def search_qdrant(request: SearchRequest):
    """Search a Qdrant collection."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")
        
        results = qm.search(request.collection, request.query, top_k=request.top_k)
        return {"results": results, "count": len(results)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search Qdrant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/qdrant/status")
async def get_qdrant_status():
    """Get Qdrant system status."""
    try:
        return get_rag_status()
    except Exception as e:
        logger.error(f"Failed to get Qdrant status: {e}")
        return {"available": False, "error": str(e)}

@app.post("/api/memory/qdrant/generate-synthetic")
async def generate_synthetic_data(request: SyntheticDataRequest):
    """Generate constraint-seeded synthetic data with verification."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")
        
        model = get_default_model()
        llm = _get_llm(model)
        
        # Build purpose-specific prompt
        purpose_prompts = {
            "adversarial": f"""Generate {request.num_samples} adversarial prompts designed to test system prompt security.

Attack Vector: {request.topic}

Each prompt should:
- Attempt to bypass system instructions
- Use techniques like prompt injection, jailbreaking, or role manipulation
- Be realistic and varied
- Include both subtle and obvious attacks

Format each prompt on a new line starting with "PROMPT:"

Begin:""",
            
            "error_recovery": f"""Generate {request.num_samples} synthetic tool-use error scenarios and recovery steps.

Error Type: {request.topic}

Each scenario should include:
1. The user request that triggered the error
2. The error that occurred
3. The correct recovery action
4. The final successful outcome

Format as:
REQUEST: [user request]
ERROR: [what went wrong]
RECOVERY: [how to fix it]
OUTCOME: [successful result]

Begin:""",
            
            "edge_cases": f"""Generate {request.num_samples} edge case scenarios for testing.

Edge Case Type: {request.topic}

Each scenario should:
- Represent a rare but possible situation
- Test system boundaries
- Include conflicting or unusual parameters
- Have a clear correct behavior

Format as:
SCENARIO: [description]
PARAMETERS: [unusual inputs]
EXPECTED_BEHAVIOR: [correct response]

Begin:""",
            
            "constraint_validation": f"""Generate {request.num_samples} test cases to validate system constraints.

Constraint to Test: {request.topic}

Each test case should:
- Present a scenario where the constraint must be enforced
- Include both compliant and non-compliant examples
- Clearly show the expected behavior

Format as:
TEST_CASE: [scenario description]
INPUT: [user request]
EXPECTED_OUTPUT: [correct response showing constraint adherence]
CONSTRAINT_VERIFIED: [which constraint is being tested]

Begin:"""
        }
        
        prompt = purpose_prompts.get(request.purpose, purpose_prompts["constraint_validation"])
        
        logger.info(f"Generating {request.num_samples} {request.purpose} synthetic documents")
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            executor,
            lambda: llm.invoke(prompt)
        )
        
        # Parse response into documents
        documents = parse_synthetic_response(response.content, request)
        
        # Verification gate - score compliance
        verified_docs = []
        for doc in documents:
            compliance_score = await verify_compliance(doc, request)
            if compliance_score >= request.compliance_threshold:
                doc['metadata']['compliance_score'] = compliance_score
                verified_docs.append(doc)
            else:
                logger.warning(f"Document failed compliance check: {compliance_score}% < {request.compliance_threshold}%")
        
        if verified_docs:
            qm.ingest_documents(request.collection, verified_docs)
            logger.info(f"Ingested {len(verified_docs)}/{len(documents)} verified documents")
        
        return {
            "status": "success",
            "documents_generated": len(documents),
            "documents_verified": len(verified_docs),
            "compliance_rate": round((len(verified_docs) / len(documents)) * 100, 1) if documents else 0,
            "collection": request.collection,
            "purpose": request.purpose
        }
        
    except Exception as e:
        logger.error(f"Failed to generate synthetic data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def verify_compliance(document: dict, request: SyntheticDataRequest) -> float:
    """Verify that generated document meets compliance threshold."""
    # This is a simplified verification - in production, you'd use a separate LLM call
    # to score the document against the system prompt constraints
    
    content = document.get('content', '')
    
    # Basic checks based on purpose
    if request.purpose == "adversarial":
        # Check if it actually contains attack patterns
        attack_indicators = ['ignore', 'forget', 'bypass', 'DAN', 'jailbreak', 'override']
        score = sum(10 for indicator in attack_indicators if indicator.lower() in content.lower())
        return min(score, 100)
    
    elif request.purpose == "error_recovery":
        # Check if it has all required sections
        required_sections = ['REQUEST:', 'ERROR:', 'RECOVERY:', 'OUTCOME:']
        score = sum(25 for section in required_sections if section in content)
        return score
    
    elif request.purpose == "edge_cases":
        # Check if it has scenario, parameters, and expected behavior
        required_sections = ['SCENARIO:', 'PARAMETERS:', 'EXPECTED_BEHAVIOR:']
        score = sum(33 for section in required_sections if section in content)
        return min(score, 100)
    
    elif request.purpose == "constraint_validation":
        # Check if it has test case structure
        required_sections = ['TEST_CASE:', 'INPUT:', 'EXPECTED_OUTPUT:', 'CONSTRAINT_VERIFIED:']
        score = sum(25 for section in required_sections if section in content)
        return score
    
    return 50.0  # Default if unknown purpose

def parse_synthetic_response(content: str, request: SyntheticDataRequest) -> list[dict]:
    """Parse LLM response into structured documents."""
    documents = []
    
    # Split by common delimiters
    if request.purpose == "adversarial":
        prompts = [line.strip() for line in content.split('\n') if line.strip().startswith('PROMPT:')]
        for i, prompt in enumerate(prompts):
            documents.append({
                "content": prompt.replace('PROMPT:', '').strip(),
                "source": f"synthetic_{request.purpose}_{i+1}",
                "type": "synthetic",
                "purpose": request.purpose,
                "topic": request.topic,
                "generated_at": datetime.now().isoformat()
            })
    else:
        # For other purposes, split by double newlines
        sections = content.split('\n\n')
        for i, section in enumerate(sections):
            if section.strip() and len(section.strip()) > 50:  # Minimum length check
                documents.append({
                    "content": section.strip(),
                    "source": f"synthetic_{request.purpose}_{i+1}",
                    "type": "synthetic",
                    "purpose": request.purpose,
                    "topic": request.topic,
                    "generated_at": datetime.now().isoformat()
                })
    
    return documents

# =============================================================================
# Notes Endpoints
# =============================================================================

@app.get("/api/notes")
async def get_notes():
    """Get all notes from workspace."""
    try:
        notes_dir = WORKSPACE_PATH / "notes"
        if not notes_dir.exists():
            return {"notes": []}
        
        notes = []
        for note_file in sorted(notes_dir.glob("*.md")):
            content = note_file.read_text(encoding='utf-8')
            notes.append({
                "filename": note_file.name,
                "content": content,
                "size": len(content),
                "modified": datetime.fromtimestamp(note_file.stat().st_mtime).isoformat()
            })
        
        return {"notes": notes}
    except Exception as e:
        logger.error(f"Failed to get notes: {e}")
        return {"notes": []}

@app.post("/api/notes")
async def save_note(request: NoteSaveRequest):
    """Save a note to workspace."""
    try:
        notes_dir = WORKSPACE_PATH / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        
        safe_filename = "".join(c for c in request.filename if c.isalnum() or c in '.-_ ').strip()
        if not safe_filename.endswith('.md'):
            safe_filename += '.md'
        
        note_path = notes_dir / safe_filename
        note_path.write_text(request.content, encoding='utf-8')
        
        return {
            "status": "saved",
            "filename": safe_filename,
            "path": str(note_path.relative_to(WORKSPACE_PATH))
        }
    except Exception as e:
        logger.error(f"Failed to save note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/notes/{filename}")
async def delete_note(filename: str):
    """Delete a note from workspace."""
    try:
        note_path = WORKSPACE_PATH / "notes" / filename
        if note_path.exists():
            note_path.unlink()
            return {"status": "deleted"}
        else:
            raise HTTPException(status_code=404, detail="Note not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# File Save Endpoint for Text Editor
# =============================================================================

@app.post("/api/notes/save")
async def save_to_workspace(request: dict):
    """Save file content to workspace directory."""
    try:
        filename = request.get("filename")
        content = request.get("content")
        
        if not filename or content is None:
            raise HTTPException(status_code=400, detail="Filename and content are required")
        
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in '.-_ ').strip()
        if not safe_filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        file_path = WORKSPACE_PATH / safe_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_text(content, encoding='utf-8')
        
        return {
            "status": "success",
            "path": str(file_path.relative_to(WORKSPACE_PATH)),
            "filename": safe_filename
        }
    except Exception as e:
        logger.error(f"Failed to save file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Voice Recognition Endpoint
# =============================================================================

@app.post("/api/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio file to text using faster-whisper or Vosk."""
    import tempfile
    
    try:
        logger.info(f"📥 Received audio file: {file.filename}, size: {file.size} bytes")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        logger.info(f"💾 Saved temporary file: {tmp_path}")
        
        try:
            # Transcribe
            from app.voice.voice_recognition import transcribe_audio_file
            text = transcribe_audio_file(tmp_path)
            
            if not text:
                logger.warning("⚠️ Transcription returned empty result")
                raise HTTPException(status_code=400, detail="No speech detected or transcription failed")
            
            logger.info(f"✅ Transcription successful: {len(text)} characters")
            return {"text": text, "status": "success"}
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                logger.info(f"🗑️ Cleaned up temporary file: {tmp_path}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Transcription endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# =============================================================================
# System Doctor Endpoint
# =============================================================================

@app.post("/api/system/doctor")
async def run_system_doctor():
    """Run comprehensive system diagnostics and auto-fix common issues."""
    import subprocess
    import shutil
    from datetime import datetime
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "checks": [],
        "fixes_applied": [],
        "warnings": [],
        "errors": []
    }
    
    try:
        # Check 1: Ollama connectivity
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                model_count = len(data.get("models", []))
                report["checks"].append({
                    "name": "Ollama Connection",
                    "status": "pass",
                    "details": f"Connected with {model_count} models"
                })
        except Exception as e:
            report["checks"].append({
                "name": "Ollama Connection",
                "status": "fail",
                "details": str(e)
            })
            report["errors"].append("Ollama is not running. Start with: ollama serve")
        
        # Check 2: Qdrant connectivity
        try:
            req = urllib.request.Request("http://127.0.0.1:6333/", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                report["checks"].append({
                    "name": "Qdrant Connection",
                    "status": "pass",
                    "details": "Connected successfully"
                })
        except Exception as e:
            report["checks"].append({
                "name": "Qdrant Connection",
                "status": "fail",
                "details": str(e)
            })
            report["errors"].append("Qdrant is not running. Start with: ./qdrant")
        
        # Check 3: SQLite database integrity
        try:
            mgr = get_sqlite_manager()
            with mgr.get_cursor() as cur:
                cur.execute("PRAGMA integrity_check")
                result = cur.fetchone()[0]
                if result == "ok":
                    report["checks"].append({
                        "name": "SQLite Database",
                        "status": "pass",
                        "details": "Integrity check passed"
                    })
                else:
                    report["checks"].append({
                        "name": "SQLite Database",
                        "status": "fail",
                        "details": f"Integrity check failed: {result}"
                    })
                    report["errors"].append("Database integrity issue detected")
        except Exception as e:
            report["checks"].append({
                "name": "SQLite Database",
                "status": "fail",
                "details": str(e)
            })
            report["errors"].append(f"Database error: {str(e)}")
        
        # Check 4: Workspace directory permissions
        try:
            if os.access(WORKSPACE_PATH, os.W_OK):
                report["checks"].append({
                    "name": "Workspace Permissions",
                    "status": "pass",
                    "details": "Writable"
                })
            else:
                report["checks"].append({
                    "name": "Workspace Permissions",
                    "status": "fail",
                    "details": "Not writable"
                })
                report["errors"].append("Workspace directory is not writable")
        except Exception as e:
            report["checks"].append({
                "name": "Workspace Permissions",
                "status": "fail",
                "details": str(e)
            })
        
        # Check 5: Frontend build exists
        try:
            frontend_dist = PROJECT_ROOT / "frontend" / "dist" / "index.html"
            if frontend_dist.exists():
                report["checks"].append({
                    "name": "Frontend Build",
                    "status": "pass",
                    "details": "Build exists"
                })
            else:
                report["checks"].append({
                    "name": "Frontend Build",
                    "status": "fail",
                    "details": "Missing"
                })
                report["warnings"].append("Frontend not built. Run: cd frontend && npm run build")
        except Exception as e:
            report["checks"].append({
                "name": "Frontend Build",
                "status": "fail",
                "details": str(e)
            })
        
        # Check 6: Disk space
        try:
            total, used, free = shutil.disk_usage(str(PROJECT_ROOT))
            free_gb = free // (1024**3)
            if free_gb > 5:
                report["checks"].append({
                    "name": "Disk Space",
                    "status": "pass",
                    "details": f"{free_gb} GB free"
                })
            else:
                report["checks"].append({
                    "name": "Disk Space",
                    "status": "warn",
                    "details": f"Only {free_gb} GB free"
                })
                report["warnings"].append(f"Low disk space: {free_gb} GB remaining")
        except Exception as e:
            report["checks"].append({
                "name": "Disk Space",
                "status": "fail",
                "details": str(e)
            })
        
        # Check 7: Python dependencies
        try:
            result = subprocess.run(
                ["python3", "-c", "import fastapi, uvicorn, qdrant_client, sentence_transformers"],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                report["checks"].append({
                    "name": "Python Dependencies",
                    "status": "pass",
                    "details": "All critical packages installed"
                })
            else:
                report["checks"].append({
                    "name": "Python Dependencies",
                    "status": "fail",
                    "details": "Missing packages"
                })
                report["errors"].append("Missing Python dependencies. Run: pip install -r requirements.txt")
        except Exception as e:
            report["checks"].append({
                "name": "Python Dependencies",
                "status": "fail",
                "details": str(e)
            })
        
        # Summary
        pass_count = sum(1 for c in report["checks"] if c["status"] == "pass")
        total_count = len(report["checks"])
        report["summary"] = {
            "total_checks": total_count,
            "passed": pass_count,
            "failed": total_count - pass_count,
            "health_score": round((pass_count / total_count) * 100) if total_count > 0 else 0
        }
        
        # Save report to file
        report_file = PROJECT_ROOT / f"doctor-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        report["report_file"] = str(report_file)
        
        return report
        
    except Exception as e:
        logger.error(f"System doctor failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Frontend Serving (MUST BE LAST)
# =============================================================================

@app.get("/")
async def serve_frontend():
    """Serve the frontend application."""
    frontend_path = PROJECT_ROOT / "frontend" / "dist" / "index.html"
    if frontend_path.exists():
        return FileResponse(str(frontend_path), headers={"Cache-Control": "no-cache"})
    return JSONResponse(
        status_code=404,
        content={"message": "MAi-RAG API running. Frontend not built. Run: cd frontend && npm run build"}
    )

@app.get("/sounds/{filename}")
async def serve_sound(filename: str):
    """Serve sound files."""
    sound_path = PROJECT_ROOT / "frontend" / "public" / "sounds" / filename
    if sound_path.exists():
        return FileResponse(str(sound_path))
    raise HTTPException(status_code=404, detail="Sound file not found")

@app.get("/fonts/{path:path}")
async def serve_font(path: str):
    """Serve font files."""
    font_path = PROJECT_ROOT / "frontend" / "public" / "fonts" / path
    if font_path.exists():
        return FileResponse(str(font_path))
    raise HTTPException(status_code=404, detail="Font file not found")

@app.get("/{full_path:path}")
async def serve_static_files(full_path: str):
    """Serve static frontend files."""
    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    file_path = frontend_dist / full_path
    
    if file_path.is_dir() or not file_path.exists():
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), headers={"Cache-Control": "no-cache"})
        raise HTTPException(status_code=404, detail="Frontend not found")
    
    if full_path.startswith("assets/"):
        return FileResponse(str(file_path), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    
    return FileResponse(str(file_path))

# =============================================================================
# Startup/Shutdown Events
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global shutdown_flag
    shutdown_flag = False
    
    logger.info("MAi-RAG API starting up...")
    
    # Check environment
    env_status = env_checker.check_all()
    if not env_status["all_services_available"]:
        logger.warning("⚠️ Not all required services are available. Some features will be disabled.")
    
    if not os.access(WORKSPACE_PATH, os.W_OK):
        logger.warning(f"Workspace not writable: {WORKSPACE_PATH}")
    
    try:
        mgr = get_sqlite_manager()
        test_key = "__startup_test__"
        mgr.set(test_key, "ok")
        mgr.delete(test_key)
        logger.info(f"SQLite connection OK: {mgr.db_path}")
    except Exception as e:
        logger.error(f"SQLite connection failed: {e}")
    
    try:
        qm = get_qdrant_manager()
        if qm.qdrant_available:
            logger.info("Qdrant connection OK")
        else:
            logger.warning("Qdrant not available - RAG features disabled")
    except Exception as e:
        logger.warning(f"Qdrant initialization failed: {e}")
    
    global heartbeat_task
    heartbeat_task = asyncio.create_task(heartbeat_scheduler())
    logger.info("Heartbeat scheduler task created")
    
    logger.info(f"MAi-RAG API started. Workspace: {WORKSPACE_PATH}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global shutdown_flag, heartbeat_task
    
    logger.info("MAi-RAG API shutting down...")
    
    shutdown_flag = True
    
    if heartbeat_task and not heartbeat_task.done():
        logger.info("Cancelling heartbeat scheduler...")
        heartbeat_task.cancel()
        try:
            await asyncio.wait_for(heartbeat_task, timeout=5.0)
        except asyncio.CancelledError:
            logger.info("Heartbeat scheduler cancelled successfully")
        except asyncio.TimeoutError:
            logger.warning("Heartbeat scheduler didn't stop in time")
        except Exception as e:
            logger.warning(f"Error stopping heartbeat: {e}")
    
    try:
        if qdrant_manager and hasattr(qdrant_manager, 'close'):
            qdrant_manager.close()
    except Exception as e:
        logger.warning(f"Qdrant close failed: {e}")
    
    try:
        if sqlite_manager and hasattr(sqlite_manager, 'close'):
            sqlite_manager.close()
    except Exception as e:
        logger.warning(f"SQLite close failed: {e}")
    
    logger.info("MAi-RAG API shutdown complete")
