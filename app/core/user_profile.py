"""User preferences & settings"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path
import json

class UserPreferences(BaseModel):
    response_style: str = "balanced"  # brief, balanced, detailed
    response_length: int = 200       # words
    preferred_format: str = "plain"   # plain, bullet, table
    voice_output: bool = False
    expertise_level: str = "general"

class UserProfile:
    def __init__(self):
        self.profiles_file = Path("data/user_profiles.json")
        self.profiles_file.parent.mkdir(exist_ok=True)
        self.profiles: Dict[str, UserPreferences] = {}
        self.load()
    
    def load(self):
        if self.profiles_file.exists():
            data = json.loads(self.profiles_file.read_text())
            self.profiles = {k: UserPreferences(**v) for k, v in data.items()}
    
    def save(self):
        data = {k: v.dict() for k, v in self.profiles.items()}
        self.profiles_file.write_text(json.dumps(data, indent=2))
    
    def get_profile(self, user_id: str = "default") -> UserPreferences:
        return self.profiles.get(user_id, UserPreferences())
    
    def update_profile(self, user_id: str, preferences: UserPreferences):
        self.profiles[user_id] = preferences
        self.save()