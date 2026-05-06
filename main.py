import logging
import time

import requests
import yaml

from bot import TelegramBot
from llm import GeminiLLM, GroqLLM
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
    token = config["telegram"]["bot_token"]
    allowed = set(config["telegram"].get("allowed_user_ids", []))

    provider = config.get("provider", "gemini")
    if provider == "groq":
        llm = GroqLLM(
            api_key=config["groq"]["api_key"],
            model=config["groq"].get("model", "openai/gpt-oss-20b"),
            timezone=timezone,
        )
    else:
        llm = GeminiLLM(
            api_key=config["gemini"]["api_key"],
            model=config["gemini"].get("model", "gemini-1.5-flash"),
            timezone=timezone,
        )

    max_turns = config.get("max_history_turns", 20)
    bot = TelegramBot(token, max_turns=max_turns)
    scheduler = ReminderScheduler(timezone=timezone, bot_token=token)
    scheduler.start()

    logger.info("Jarvis is running")

    offset = 0
    while True:
        try:
            updates = bot.get_updates(offset=offset, timeout=30)
            for update in updates:
                offset = update["update_id"] + 1
                bot.process_update(update, scheduler, llm, allowed)
        except requests.RequestException as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Shutting down")
            scheduler.shutdown()
            break


if __name__ == "__main__":
    main()
