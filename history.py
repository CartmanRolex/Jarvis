import json
from pathlib import Path

HISTORY_FILE = Path("history.json")


def get_history(chat_id: int, max_turns: int) -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    data = json.loads(HISTORY_FILE.read_text())
    return data.get(str(chat_id), [])[-(max_turns * 2):]


def append_turn(chat_id: int, user_message: str, assistant_reply: str, max_turns: int):
    data = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else {}
    key = str(chat_id)
    turns = data.get(key, [])
    turns.append({"role": "user", "content": user_message})
    turns.append({"role": "assistant", "content": assistant_reply})
    data[key] = turns[-(max_turns * 2):]
    HISTORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
