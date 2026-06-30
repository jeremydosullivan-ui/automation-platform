# Personal Telegram Automation Platform

This project is now structured as a scalable Railway-ready automation platform.

The goal is to run one Railway service that can eventually host multiple Telegram bots and personal automations from the same codebase.

## Current Bot Interface

### Jeremy Assistant

Jeremy Assistant is the preferred single-bot interface.

Enabled when these environment variables are present:

```text
ASSISTANT_BOT_TOKEN=
ASSISTANT_CHAT_ID=
```

When `ASSISTANT_BOT_TOKEN` and `ASSISTANT_CHAT_ID` are set, the platform starts only Jeremy Assistant and does not start the legacy separate Morning/XAUUSD bot pollers.

Commands:

```text
/start
/help
/morning
/gold
/london
/newyork
/status
/health
```

Schedule:

```text
07:30 Asia/Bangkok - morning briefing
```

## Legacy Bots

### Morning Bot

The legacy Morning Bot remains available for compatibility.

Enabled when these environment variables are present:

```text
MORNING_BOT_TOKEN=
MORNING_CHAT_ID=
```

Commands:

```text
/start
/morning
```

Schedule:

```text
07:30 Asia/Bangkok - morning briefing
```

### XAUUSD Bot

Prepared as a placeholder for the next build.

Enabled only when both variables are present:

```text
XAUUSD_BOT_TOKEN=
XAUUSD_CHAT_ID=
```

If these are missing, the platform logs that the XAUUSD bot is disabled and keeps running the morning bot.

After Jeremy Assistant is tested successfully, you can remove these legacy Railway variables:

```text
MORNING_BOT_TOKEN
MORNING_CHAT_ID
XAUUSD_BOT_TOKEN
XAUUSD_CHAT_ID
```

## Project Structure

```text
automation_platform/
├── main.py
├── requirements.txt
├── Procfile
├── railway.json
├── .env.example
├── bots/
│   ├── morning_bot/
│   ├── xauusd_bot/
│   └── __init__.py
├── shared/
│   ├── config.py
│   ├── telegram.py
│   ├── logging_config.py
│   └── scheduler.py
└── README.md
```

Root-level `Procfile`, `railway.json`, and `requirements.txt` are also present so Railway can deploy directly from this repository root.

## Local Setup

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env`:

```bash
cp .env.example .env
```

Add your values:

```text
ASSISTANT_BOT_TOKEN=your_jeremy_assistant_bot_token
ASSISTANT_CHAT_ID=your_telegram_chat_id

# Legacy fallback variables. Optional once Jeremy Assistant is working.
MORNING_BOT_TOKEN=your_morning_bot_token
MORNING_CHAT_ID=your_telegram_chat_id

XAUUSD_BOT_TOKEN=
XAUUSD_CHAT_ID=

TIMEZONE=Asia/Bangkok
```

## Run Locally

From the repository root:

```bash
python -m automation_platform.main
```

For a short startup test:

```bash
python -m automation_platform.main --run-seconds 10
```

For a non-polling startup check:

```bash
python -m automation_platform.main --check-startup
```

## Test Jeremy Assistant

Open Telegram and send:

```text
/start
/help
/morning
/gold
/london
/newyork
/status
/health
```

The platform logs should show:

```text
Platform starting...
Jeremy Assistant starting...
Scheduler started.
assistant bot Telegram polling started.
```

## Railway Deployment

1. Push this project to GitHub.
2. Create a new Railway project.
3. Add a service from your GitHub repository.
4. Railway should use `railway.json` and start with:

```bash
python -m automation_platform.main
```

5. Add these Railway environment variables:

```text
ASSISTANT_BOT_TOKEN=your_jeremy_assistant_bot_token
ASSISTANT_CHAT_ID=your_telegram_chat_id
TIMEZONE=Asia/Bangkok
```

Legacy variables can stay during testing:

```text
MORNING_BOT_TOKEN=your_morning_bot_token
MORNING_CHAT_ID=your_telegram_chat_id
XAUUSD_BOT_TOKEN=your_legacy_xauusd_bot_token
XAUUSD_CHAT_ID=your_telegram_chat_id
```

If the Assistant values are not set, the platform falls back to the legacy Morning/XAUUSD bot setup.

## Railway Notes

This is a worker-style service. It uses Telegram polling and does not need to expose a web port.

The included `Procfile` says:

```text
worker: python -m automation_platform.main
```

The included `railway.json` sets the same start command and restarts the service on failure.

## Adding More Bots Later

Add a new folder under:

```text
automation_platform/bots/
```

Each bot should have:

```text
handlers.py
scheduler.py
messages.py
```

Reusable code should go in:

```text
automation_platform/shared/
```

This keeps one Railway service flexible without turning the project into a complicated framework.
