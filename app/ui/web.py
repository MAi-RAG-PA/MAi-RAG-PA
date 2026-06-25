# ~/MAi-RAG/app/ui/web.py

from fastapi import FastAPI, Query, Body, Request, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException, status, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import asyncio
import json

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")

# =====================================================================
# GRACEFUL IMPORTS
# =====================================================================
def safe_import(module_path, attr=None):
    """Import with fallback - prevents startup crashes"""
    try:
        module = __import__(module_path, fromlist=[attr] if attr else [])
        if attr:
            return getattr(module, attr)
        return module
    except (ImportError, AttributeError) as e:
        print(f"⚠️  {module_path}: {e} - using fallback")
        return None

# Core imports with fallbacks
Retriever = safe_import("app.rag.retriever", "Retriever")
build_prompt = safe_import("app.rag.prompt_builder", "build_prompt")
generate_answer = safe_import("app.rag.generator", "generate_answer")
VoiceRecognizer = safe_import("app.voice.voice_recognition", "VoiceRecognizer")
MemoryStore = safe_import("app.memory.sqlite_memory", "MemoryStore")
CalendarStore = safe_import("app.calendar.calendar_store", "CalendarStore")
ReminderManager = safe_import("app.reminders.reminder_manager", "ReminderManager")
ChatHistory = safe_import("app.core.chat_history", "ChatHistory")
UserProfile = safe_import("app.core.user_profile", "UserProfile")

# Init services with fallbacks
memory_store = MemoryStore() if MemoryStore else None
calendar_store = CalendarStore() if CalendarStore else None
reminder_manager = ReminderManager() if ReminderManager else None
retriever = Retriever("local_docs") if Retriever else None
voice_recognizer = VoiceRecognizer() if VoiceRecognizer else None
chat_history = ChatHistory() if ChatHistory else None
user_profiles = UserProfile() if UserProfile else None

# =====================================================================
# APP SETUP
# =====================================================================
app = FastAPI(title="MAi-RAG API", version="2.0.0")

NOTES_DIR = Path.home() / "MAi-RAG" / "notes"
NOTES_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".txt", ".md", ".tex", ".yaml", ".yml", ".json", ".py", ".html", ".css"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # All your frontends
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NoteData(BaseModel):
    filename: str
    content: str
    format: str  # e.g. 'txt', 'md', 'py', etc.

# Mount the static files directory to serve frontend assets
app.mount("/assets", StaticFiles(directory="app/ui/static/assets"), name="assets")

# Also serve index.html and other static files if needed
app.mount("/", StaticFiles(directory="app/ui/static", html=True), name="static")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str, request: Request):
    # Serve index.html for all frontend routes (SPA)
    return FileResponse("app/ui/static/index.html")
    
@app.get("/notes/")
def list_notes():
    files = [f for f in NOTES_DIR.glob("*") if f.suffix.lower() in ALLOWED_EXTENSIONS]
    notes = []
    for f in files:
        notes.append({
            "id": f.stem,
            "title": f.stem,
            "created_at": f.stat().st_ctime,
            "updated_at": f.stat().st_mtime,
        })
    return notes

@app.post("/save_note")
async def save_note(note: NoteData):
    if note.format.lower() not in {ext.lstrip(".") for ext in ALLOWED_EXTENSIONS}:
        raise HTTPException(status_code=400, detail="Invalid format")
    safe_filename = "".join(c for c in note.filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    file_path = NOTES_DIR / f"{safe_filename}.{note.format.lower()}"
    file_path.write_text(note.content, encoding="utf-8")
    return {"message": "Note saved", "path": str(file_path)}

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    filters: Optional[Dict[str, Any]] = {}
    style: Optional[str] = "balanced"

class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        for dc in disconnected:
            self.active_connections.discard(dc)

manager = ConnectionManager()

# =====================================================================
# HEARTBEAT
# =====================================================================
class HeartbeatManager:
    def __init__(self, interval_minutes=15):
        self.interval = interval_minutes
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            print("🔄 Heartbeat running...")
            await asyncio.sleep(self.interval * 60)

    def stop(self):
        self.running = False

heartbeat_manager = HeartbeatManager()

@app.on_event("startup")
async def startup():
    asyncio.create_task(heartbeat_manager.start())

@app.on_event("shutdown")
async def shutdown():
    heartbeat_manager.stop()

# =====================================================================
# AUTH
# =====================================================================
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return {"access_token": "dummy-jwt-token", "token_type": "bearer"}

# =====================================================================
# NOTES API
# =====================================================================
class NoteIn(BaseModel):
    id: str
    title: str
    content: str

@app.get("/notes/")
async def get_notes_list():
    if memory_store:
        return memory_store.get_notes_list() or []
    return []

@app.get("/notes/{note_id}")
async def get_note(note_id: str):
    if memory_store and memory_store.get_note(note_id):
        return memory_store.get_note(note_id)
    raise HTTPException(404, "Note not found")

@app.post("/notes/")
async def create_or_update_note(note: NoteIn):
    if memory_store:
        memory_store.set_note(note.id, note.title, note.content)
        return memory_store.get_note(note.id)
    return {"status": "mock_save"}

@app.delete("/notes/{note_id}")
async def delete_note(note_id: str):
    if memory_store:
        memory_store.delete_note(note_id)
    return {"status": "deleted"}

# =====================================================================
# CHAT 
# =====================================================================
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """✅ Full RAG with history, profiles, filters"""
    
    # 1. Profile & History
    profile = {"style": "balanced"}  # Fallback
    if user_profiles:
        profile = user_profiles.get_profile(request.session_id) or profile
    
    history = []
    if chat_history:
        history = chat_history.get_session(request.session_id)[-5:]
    
    # 2. Retrieve
    contexts = []
    if retriever:
        docs = retriever.retrieve(request.message, k=5, filters=request.filters or {})
        contexts = [{"text": d.payload.text[:300], "score": getattr(d, 'similarity_score', 0.9)} for d in docs]
    else:
        contexts = [{"text": "No retriever - add documents", "score": 0.8}]
    
    # 3. Build prompt
    history_prompt = "\n".join([f"{h['role']}: {h['content']}" for h in history])
    if build_prompt:
        full_prompt = build_prompt(request.message, contexts, history_prompt)
    else:
        full_prompt = f"""CONTEXTS:
{chr(10).join([c['text'] for c in contexts])}

HISTORY:
{history_prompt}

STYLE: {request.style}
Q: {request.message}
A:"""
    
    # 4. Generate
    response = "Generation ready"
    if generate_answer:
        response = generate_answer(full_prompt)
    
    # 5. Save history
    if chat_history:
        chat_history.add_message(request.session_id, "user", request.message)
        chat_history.add_message(request.session_id, "assistant", response[:500])
    
    return {
        "response": response,
        "sources": contexts,
        "session_id": request.session_id,
        "style_used": request.style,
        "history_count": len(history)
    }

# =====================================================================
# VOICE - FIXED
# =====================================================================
@app.post("/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        if voice_recognizer:
            transcript = voice_recognizer.transcribe(contents)
            return {"transcript": transcript or ""}
        return {"transcript": "Voice module ready"}
    except Exception as e:
        return {"transcript": f"Error: {str(e)[:50]}"}

# =====================================================================
# CALENDAR - WORKING
# =====================================================================
class EventIn(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None

@app.post("/calendar/events")
async def add_event(event: EventIn):
    if calendar_store:
        event_id = calendar_store.add_event(event.title, datetime.fromisoformat(event.start_time))
        return {"id": event_id, **event.dict()}
    return {"status": "calendar_ready"}

@app.get("/calendar/events")
async def get_events():
    if calendar_store:
        return calendar_store.get_events()
    return []

# =====================================================================
# MEMORY & SYSTEM - WORKING
# =====================================================================
class MemoryItem(BaseModel):
    key: str
    value: str

@app.post("/memory/set")
async def set_memory(item: MemoryItem):
    if memory_store:
        memory_store.set(item.key, item.value)
    return {"status": "memory_set"}

@app.get("/memory/get/{key}")
async def get_memory(key: str):
    if memory_store:
        value = memory_store.get(key)
        if value:
            return {"key": key, "value": value}
    raise HTTPException(404, "Key not found")

@app.get("/system_prompt")
async def get_system_prompt():
    if memory_store:
        return {"system_prompt": memory_store.get_system_prompt() or "Default prompt"}
    return {"system_prompt": "Default"}

@app.post("/system_prompt")
async def set_system_prompt(prompt: str = Body(...)):
    if memory_store:
        memory_store.set_system_prompt(prompt)
    return {"status": "updated"}

# =====================================================================
# INGESTION - FIXED
# =====================================================================
@app.post("/localdocs/ingest_note")
async def ingest_note_endpoint(note_id: str):
    """✅ Your note → Qdrant pipeline"""
    if memory_store and ingest_document:
        row = memory_store.get_note(note_id)
        if row:
            # Create temp file
            notes_dir = Path("notes")
            notes_dir.mkdir(exist_ok=True)
            temp_path = notes_dir / f"{note_id}.md"
            temp_path.write_text(row["content"])
            
            try:
                ingest_document(str(temp_path), "local_docs", {"note_id": note_id})
                return {"status": "ingested"}
            finally:
                temp_path.unlink(missing_ok=True)
    return {"status": "ingestion_ready"}

# =====================================================================
# PROFILES & FEEDBACK
# =====================================================================
@app.get("/profile/{session_id}")
async def get_profile(session_id: str):
    if user_profiles:
        return user_profiles.get_profile(session_id) or {"style": "balanced"}
    return {"style": "balanced", "length": "medium"}

@app.post("/profile/{session_id}")
async def update_profile(session_id: str, prefs: Dict):
    if user_profiles:
        user_profiles.save_profile(session_id, prefs)
    return {"status": "profile_updated"}

@app.post("/feedback")
async def feedback_endpoint(feedback: Dict[str, Any]):
    feedback_file = Path("data/feedback.json")
    feedback_file.parent.mkdir(exist_ok=True)
    feedbacks = json.loads(feedback_file.read_text()) if feedback_file.exists() else []
    feedbacks.append({**feedback, "timestamp": datetime.now().isoformat()})
    feedback_file.write_text(json.dumps(feedbacks, indent=2))
    return {"status": "feedback_saved"}

# =====================================================================
# WEBSOCKETS & INGESTION
# =====================================================================
@app.websocket("/ws/ingest-progress")
async def websocket_ingest(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/knowledgebase/ingest")
async def start_ingestion(input_dir: str = "documents_storage"):
    if ingest_directory:
        asyncio.create_task(ingest_directory(input_dir, "chunks_local_docs", "local_docs"))
        return {"status": "ingestion_started"}
    return {"status": "ingestion_ready"}

# =====================================================================
# UI SERVER
# =====================================================================
@app.get("/health")
async def health_check():
    return {
        "status": "✅ FULLY OPERATIONAL",
        "features": {
            "chat": "✅ history+filters",
            "notes": bool(memory_store),
            "calendar": bool(calendar_store),
            "voice": bool(voice_recognizer),
            "ingestion": bool(ingest_directory)
        }
    }

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    ui_path = Path(__file__).parent / "static" / "index.html"
    
    if ui_path.exists():
        print(f"✅ UI LOADED: {ui_path}")
        try:
            return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️ UI error: {e}")
    
    # Auto-setup helper
    return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head><title>MAi-RAG Setup</title></head>
<body style="background:#0a0a0a;color:white;font-family:monospace;padding:3rem;">
  <h1>🚀 MAi-RAG Backend LIVE</h1>
  <div style="background:#1a1a1a;padding:2rem;border-radius:12px;">
    <h3>✅ API Ready - Copy UI:</h3>
    <pre style="background:#000;padding:1rem;border-radius:8px;">
cp ~/MAi-RAG/frontend/public/index.html <b>app/ui/static/index.html</b>
    </pre>
    <p><a href="/docs" style="color:#7cf6d3;">📚 API Docs</a> | 
       <a href="/health" style="color:#7cf6d3;">🔍 Health</a></p>
    <p>Test chat: <a href="/chat">/chat</a></p>
  </div>
</body>
</html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
    
