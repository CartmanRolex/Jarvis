import logging
from datetime import datetime

import requests

import storage
from llm import GeminiLLM, update_context
from scheduler import ReminderScheduler

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()

    def get_updates(self, offset: int = None, timeout: int = 30) -> list:
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        resp = self.session.get(
            f"{self.base_url}/getUpdates", params=params, timeout=timeout + 5
        )
        resp.raise_for_status()
        return resp.json().get("result", [])

    def send_message(self, chat_id: int, text: str, parse_mode: str = None):
        data = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        try:
            self.session.post(f"{self.base_url}/sendMessage", json=data, timeout=10)
        except requests.RequestException as e:
            logger.error(f"Failed to send message: {e}")

    def send_chat_action(self, chat_id: int, action: str):
        try:
            self.session.post(
                f"{self.base_url}/sendChatAction",
                json={"chat_id": chat_id, "action": action},
                timeout=10,
            )
        except requests.RequestException:
            pass

    def process_update(self, update: dict, scheduler: ReminderScheduler, llm: GeminiLLM, allowed: set):
        message = update.get("message")
        if not message:
            return

        user_id = message.get("from", {}).get("id")
        if allowed and user_id not in allowed:
            return

        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if text == "/start":
            self.send_message(
                chat_id,
                "👋 Hi, I'm Jarvis. Send me a message and I'll help you set reminders or answer questions.",
            )
            return

        if not text or text.startswith("/"):
            return

        self.send_chat_action(chat_id, "typing")

        try:
            result = llm.process(text)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            self.send_message(chat_id, "Sorry, I couldn't process that. Please try again.")
            return

        self.send_message(chat_id, result.get("reply", "Done!"))

        for action in result.get("actions", []):
            atype = action.get("type")

            if atype == "add_reminder":
                try:
                    trigger_at = datetime.fromisoformat(action["trigger_at"])
                except (KeyError, ValueError) as e:
                    logger.error(f"Bad trigger_at: {e}")
                    self.send_message(chat_id, "⚠️ I couldn't parse the reminder time. Please try again.")
                    continue
                reminder = storage.add_reminder(
                    chat_id=chat_id,
                    message=action["message"],
                    trigger_at=trigger_at,
                    recurrence=action.get("recurrence"),
                )
                scheduler.add(reminder)

            elif atype == "delete_reminder":
                rid = action.get("reminder_id", "")
                removed = scheduler.remove(rid)
                if not removed:
                    self.send_message(chat_id, f"⚠️ No reminder found with id `{rid[:8]}`.")

            elif atype == "update_context":
                update_context(action.get("content", ""))

            elif atype == "list_reminders":
                reminders = storage.get_all_reminders()
                if not reminders:
                    self.send_message(chat_id, "You have no scheduled reminders.")
                else:
                    lines = ["📋 *Scheduled reminders:*"]
                    for r in reminders:
                        rec = f" _(recurs {r['recurrence']})_" if r["recurrence"] else ""
                        short_id = r["id"][:8]
                        lines.append(f"• `{short_id}` — {r['message']} @ `{r['trigger_at']}`{rec}")
                    self.send_message(chat_id, "\n".join(lines), parse_mode="Markdown")
