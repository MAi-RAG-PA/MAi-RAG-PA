from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime
from pathlib import Path

import logging


logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

class ReminderManager:
def __init__(self, db_url=None):
    if db_url is None:
        db_path = Path.home() / "MAi-RAG" / "memory" / "memory_store.db"
        db_url = f"sqlite:///{db_path}"
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_jobstore('sqlalchemy', url=db_url)
        self.scheduler.start()

    def add_reminder(self, reminder_id: str, run_date: datetime, func, args=None):
        """
        Schedule a reminder job.
        reminder_id: unique job id
        run_date: datetime to run the job
        func: callable to execute
        args: list of arguments for func
        """
        self.scheduler.add_job(func, 'date', run_date=run_date, args=args or [], id=reminder_id, replace_existing=True)

    def remove_reminder(self, reminder_id: str):
        self.scheduler.remove_job(reminder_id)

    def shutdown(self):
        self.scheduler.shutdown()

class HeartbeatManager:
    def __init__(self, interval_minutes=15):
        self.scheduler = BackgroundScheduler()
        self.interval = interval_minutes
        self.job = None

    def start(self):
        self.job = self.scheduler.add_job(self.self_check, 'interval', minutes=self.interval)
        self.scheduler.start()

    def self_check(self):
        # Example: fetch memories, analyze, update
        memories = memory_store.get_all()  # Implement get_all() if needed
        # Run summarization or consistency check with LLM here
        print("Heartbeat self-check running...")

    def update_interval(self, new_interval):
        self.interval = new_interval
        if self.job:
            self.job.reschedule(trigger='interval', minutes=new_interval)

    def shutdown(self):
        self.scheduler.shutdown()
