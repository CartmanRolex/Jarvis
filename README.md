# Jarvis

A personal Telegram assistant that manages reminders and answers questions, powered by Google Gemini.

## Features

- **Natural language reminders** — set one-off or recurring reminders by just describing them
- **AI responses** — powered by Gemini, understands context and conversational follow-ups
- **Persistent reminders** — survive restarts, stored locally in `reminders.json`
- **Personal context** — Jarvis remembers information about you across conversations via `context.md`
- **Whitelist** — restrict access to specific Telegram user IDs

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd Jarvis
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Get your credentials

- **Telegram bot token** — message [@BotFather](https://t.me/BotFather) on Telegram, create a new bot, copy the token
- **Your Telegram user ID** — message [@userinfobot](https://t.me/userinfobot) to get your numeric ID
- **Gemini API key** — get one at [aistudio.google.com](https://aistudio.google.com)

### 3. Create `config.yaml`

```yaml
telegram:
  bot_token: "YOUR_TELEGRAM_BOT_TOKEN"
  allowed_user_ids:
    - 123456789  # your Telegram user ID

gemini:
  api_key: "YOUR_GEMINI_API_KEY"
  model: "gemini-2.0-flash"  # or gemini-1.5-flash

timezone: "Europe/Paris"  # your local timezone (IANA format)
```

### 4. Run

```bash
python main.py
```

## Usage

Send any message to your bot in Telegram:

| Example message | What happens |
|---|---|
| `Remind me to call John tomorrow at 3pm` | Sets a one-off reminder |
| `Every morning at 9 remind me to check emails` | Sets a daily recurring reminder |
| `What reminders do I have?` | Lists all scheduled reminders |
| `Cancel the call John reminder` | Deletes a reminder |
| `My name is Gal and I live in Paris` | Updates your personal context |

## Project structure

```
Jarvis/
├── main.py        # Entry point, polling loop
├── bot.py         # TelegramBot class, message handling
├── llm.py         # Gemini integration
├── scheduler.py   # APScheduler-based reminder firing
├── storage.py     # JSON persistence for reminders
├── config.yaml    # Your credentials (not committed)
└── context.md     # Your personal context (auto-managed by Jarvis)
```

## Recurring reminder options

`daily` · `weekly` · `monthly` · `weekdays`

## Running as a systemd service

This is the recommended way to run the bot on a Linux server — it starts automatically on boot and restarts itself if it crashes.

This uses a **user-level systemd service** (no `sudo` needed), which starts automatically on login and restarts on crash.

### 1. Create the service file

```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/jarvis.service
```

Paste the following, adjusting the paths to match your setup:

```ini
[Unit]
Description=Jarvis Telegram assistant
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/path/to/Jarvis
ExecStart=/path/to/Jarvis/.venv/bin/python /path/to/Jarvis/main.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
```

> If you're not using a virtual environment, replace `ExecStart` with:
> ```
> ExecStart=/usr/bin/python3 /path/to/Jarvis/main.py
> ```

### 2. Enable and start the service

```bash
# Reload systemd to pick up the new file
systemctl --user daemon-reload

# Enable it so it starts automatically on login
systemctl --user enable jarvis

# Start it now
systemctl --user start jarvis
```

### Useful commands

```bash
# Check if the bot is running
systemctl --user status jarvis

# View live logs
journalctl --user -u jarvis -f

# View last 100 lines of logs
journalctl --user -u jarvis -n 100

# Restart the bot (e.g. after editing config.yaml)
systemctl --user restart jarvis

# Stop the bot
systemctl --user stop jarvis

# Disable auto-start on boot
systemctl --user disable jarvis
```

> **After editing `config.yaml`**, always restart the service for changes to take effect:
> ```bash
> systemctl --user restart jarvis
> ```
