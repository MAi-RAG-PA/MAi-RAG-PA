import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / "MAi-RAG" / "memory" / "memory_store.db"

class CalendarStore:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def add_event(self, title: str, start_time: datetime, end_time: datetime = None, description: str = None):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO events (title, description, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, (title, description, start_time.isoformat(), end_time.isoformat() if end_time else None))
        self.conn.commit()
        return cursor.lastrowid

    def get_events(self, start: datetime = None, end: datetime = None):
        cursor = self.conn.cursor()
        query = "SELECT id, title, description, start_time, end_time FROM events WHERE 1=1"
        params = []
        if start:
            query += " AND start_time >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND start_time <= ?"
            params.append(end.isoformat())
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "start_time": datetime.fromisoformat(row[3]),
                "end_time": datetime.fromisoformat(row[4]) if row[4] else None,
            }
            for row in rows
        ]

    def close(self):
        self.conn.close()
