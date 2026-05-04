import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

REMINDERS_FILE = Path("reminders.json")


def load_reminders() -> list[dict]:
    if not REMINDERS_FILE.exists():
        return []
    with open(REMINDERS_FILE) as f:
        return json.load(f)


def save_reminders(reminders: list[dict]):
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, indent=2, default=str)


def add_reminder(chat_id: int, message: str, trigger_at: datetime, recurrence: Optional[str]) -> dict:
    reminders = load_reminders()
    reminder = {
        "id": str(uuid.uuid4()),
        "chat_id": chat_id,
        "message": message,
        "trigger_at": trigger_at.isoformat(),
        "recurrence": recurrence,
        "created_at": datetime.now().isoformat(),
    }
    reminders.append(reminder)
    save_reminders(reminders)
    return reminder


def delete_reminder(reminder_id: str) -> bool:
    reminders = load_reminders()
    filtered = [r for r in reminders if r["id"] != reminder_id]
    if len(filtered) < len(reminders):
        save_reminders(filtered)
        return True
    return False


def get_all_reminders() -> list[dict]:
    return load_reminders()
