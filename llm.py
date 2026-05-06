import json
import logging
from datetime import datetime
from pathlib import Path

import google.generativeai as genai
from groq import Groq

logger = logging.getLogger(__name__)

CONTEXT_FILE = Path("context.md")

SYSTEM_PROMPT = """\
You are Jarvis, a personal assistant operating through Telegram. You help the user manage reminders and answer questions.

Current date and time: {current_datetime}
Timezone: {timezone}

User's personal context (you can read and update this):
---
{context}
---

You MUST always respond with a valid JSON object and nothing else — no markdown, no code fences.

Response format:
{{
  "reply": "Your message to the user (always required)",
  "actions": [
    {{
      "type": "add_reminder",
      "message": "The text to send as the reminder",
      "trigger_at": "YYYY-MM-DDTHH:MM:SS",
      "recurrence": null
    }}
  ]
}}

Available action types:
- add_reminder    : Schedule a reminder. Fields: message (str), trigger_at (ISO 8601 local datetime, must be future), recurrence (null | "daily" | "weekly" | "monthly" | "weekdays")
- delete_reminder : Cancel a reminder. Fields: reminder_id (str)
- update_context  : Replace the context file with new content. Fields: content (str, full replacement)
- list_reminders  : Trigger display of all scheduled reminders. No extra fields.

Rules:
- trigger_at must always be a future datetime in local timezone
- Vague times: "tonight" → 20:00, "morning" → 09:00, "noon" → 12:00, "afternoon" → 15:00, "evening" → 19:00
- "next Monday" means the coming Monday even if today is Monday
- Confirm the exact time and message in your reply
- Omit "actions" entirely if there is nothing to schedule or update
- Never wrap the JSON in markdown or code blocks\
"""


def _get_context() -> str:
    if CONTEXT_FILE.exists():
        text = CONTEXT_FILE.read_text().strip()
        return text if text else "(empty)"
    return "(empty)"


def update_context(content: str):
    CONTEXT_FILE.write_text(content, encoding="utf-8")


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first and last fence lines
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    return text


class GroqLLM:
    def __init__(self, api_key: str, model: str, timezone: str):
        self._client = Groq(api_key=api_key)
        self._model = model
        self.timezone = timezone

    def process(self, user_message: str, history: list[dict] = None) -> dict:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
        system = SYSTEM_PROMPT.format(
            current_datetime=now,
            timezone=self.timezone,
            context=_get_context(),
        )

        messages = [{"role": "system", "content": system}]
        messages.extend(history or [])
        messages.append({"role": "user", "content": user_message})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        raw = _strip_fences(response.choices[0].message.content)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"LLM returned non-JSON: {raw}")
            raise ValueError("LLM response was not valid JSON")


class GeminiLLM:
    def __init__(self, api_key: str, model: str, timezone: str):
        genai.configure(api_key=api_key)
        self.timezone = timezone
        self._model_name = model

    def process(self, user_message: str, history: list[dict] = None) -> dict:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
        system = SYSTEM_PROMPT.format(
            current_datetime=now,
            timezone=self.timezone,
            context=_get_context(),
        )

        gemini_history = [
            {"role": "model" if t["role"] == "assistant" else t["role"], "parts": [t["content"]]}
            for t in (history or [])
        ]

        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system,
        )

        response = model.start_chat(history=gemini_history).send_message(user_message)
        raw = _strip_fences(response.text)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"LLM returned non-JSON: {raw}")
            raise ValueError("LLM response was not valid JSON")
