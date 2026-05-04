import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

import storage

logger = logging.getLogger(__name__)


class ReminderScheduler:
    def __init__(self, timezone: str):
        self.timezone = timezone
        self.bot = None  # set after Application is built
        self.scheduler = AsyncIOScheduler(timezone=timezone)

    def start(self):
        self.scheduler.start()
        self._load_persisted()

    def shutdown(self):
        self.scheduler.shutdown(wait=False)

    def _load_persisted(self):
        now = datetime.now()
        for r in storage.get_all_reminders():
            trigger_at = datetime.fromisoformat(r["trigger_at"])
            if r["recurrence"] or trigger_at > now:
                self._schedule(r)
            else:
                storage.delete_reminder(r["id"])

    def _schedule(self, reminder: dict):
        dt = datetime.fromisoformat(reminder["trigger_at"])
        recurrence = reminder["recurrence"]

        if recurrence == "daily":
            trigger = CronTrigger(hour=dt.hour, minute=dt.minute, timezone=self.timezone)
        elif recurrence == "weekly":
            trigger = CronTrigger(
                day_of_week=dt.strftime("%a").lower(),
                hour=dt.hour,
                minute=dt.minute,
                timezone=self.timezone,
            )
        elif recurrence == "monthly":
            trigger = CronTrigger(day=dt.day, hour=dt.hour, minute=dt.minute, timezone=self.timezone)
        elif recurrence == "weekdays":
            trigger = CronTrigger(
                day_of_week="mon-fri", hour=dt.hour, minute=dt.minute, timezone=self.timezone
            )
        else:
            trigger = DateTrigger(run_date=dt, timezone=self.timezone)

        self.scheduler.add_job(
            self._fire,
            trigger=trigger,
            args=[reminder["chat_id"], reminder["message"], reminder["id"], recurrence],
            id=reminder["id"],
            replace_existing=True,
        )

    async def _fire(self, chat_id: int, message: str, reminder_id: str, recurrence: Optional[str]):
        try:
            await self.bot.send_message(chat_id=chat_id, text=f"⏰ {message}")
        except Exception as e:
            logger.error(f"Failed to send reminder {reminder_id}: {e}")
        if not recurrence:
            storage.delete_reminder(reminder_id)

    def add(self, reminder: dict):
        self._schedule(reminder)

    def remove(self, reminder_id: str) -> bool:
        try:
            self.scheduler.remove_job(reminder_id)
        except Exception:
            pass
        return storage.delete_reminder(reminder_id)
