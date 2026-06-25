"""Multi-turn conversation memory"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class ChatHistory:
    def __init__(self):
        self.history_file = Path("data/chat_history.json")
        self.history_file.parent.mkdir(exist_ok=True)
        self.sessions: Dict[str, List[Dict]] = {}
        self.load()
    
    def load(self):
        if self.history_file.exists():
            self.sessions = json.loads(self.history_file.read_text())
    
    def save(self):
        self.history_file.write_text(json.dumps(self.sessions, indent=2))
    
    def get_session(self, user_id: str = "default") -> List[Dict]:
        return self.sessions.get(user_id, [])
    
    def add_message(self, user_id: str, role: str, content: str):
        if user_id not in self.sessions:
            self.sessions[user_id] = []
        
        self.sessions[user_id].append({
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep last 20 messages
        self.sessions[user_id] = self.sessions[user_id][-20:]
        self.save()
