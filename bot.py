import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import storage
from llm import GeminiLLM, update_context
from scheduler import ReminderScheduler

logger = logging.getLogger(__name__)


def setup_handlers(app: Application, scheduler: ReminderScheduler, llm: GeminiLLM, config: dict):
    allowed = set(config["telegram"].get("allowed_user_ids", []))

    def _is_allowed(update: Update) -> bool:
        return not allowed or update.effective_user.id in allowed

    async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_allowed(update):
            return

        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        try:
            result = llm.process(update.message.text)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            await update.message.reply_text("Sorry, I couldn't process that. Please try again.")
            return

        await update.message.reply_text(result.get("reply", "Done!"))

        for action in result.get("actions", []):
            atype = action.get("type")

            if atype == "add_reminder":
                try:
                    trigger_at = datetime.fromisoformat(action["trigger_at"])
                except (KeyError, ValueError) as e:
                    logger.error(f"Bad trigger_at: {e}")
                    await update.message.reply_text("⚠️ I couldn't parse the reminder time. Please try again.")
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
                    await update.message.reply_text(f"⚠️ No reminder found with id starting with `{rid[:8]}`.")

            elif atype == "update_context":
                update_context(action.get("content", ""))

            elif atype == "list_reminders":
                reminders = storage.get_all_reminders()
                if not reminders:
                    await update.message.reply_text("You have no scheduled reminders.")
                else:
                    lines = ["📋 *Scheduled reminders:*"]
                    for r in reminders:
                        rec = f" _(recurs {r['recurrence']})_" if r["recurrence"] else ""
                        short_id = r["id"][:8]
                        lines.append(f"• `{short_id}` — {r['message']} @ `{r['trigger_at']}`{rec}")
                    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_allowed(update):
            return
        await update.message.reply_text(
            "👋 Hi, I'm Jarvis. Send me a message and I'll help you set reminders or answer questions."
        )

    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
