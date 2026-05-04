import logging
from pathlib import Path

import yaml
from telegram.ext import Application

from bot import setup_handlers
from llm import GeminiLLM
from scheduler import ReminderScheduler

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    timezone = config.get("timezone", "UTC")

    llm = GeminiLLM(
        api_key=config["gemini"]["api_key"],
        model=config["gemini"].get("model", "gemini-1.5-flash"),
        timezone=timezone,
    )

    scheduler = ReminderScheduler(timezone=timezone)

    app = (
        Application.builder()
        .token(config["telegram"]["bot_token"])
        .build()
    )

    setup_handlers(app, scheduler, llm, config)

    async def post_init(application: Application):
        scheduler.bot = application.bot
        scheduler.start()
        logger.info("Jarvis is running")

    async def post_shutdown(application: Application):
        scheduler.shutdown()

    app.post_init = post_init
    app.post_shutdown = post_shutdown

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
