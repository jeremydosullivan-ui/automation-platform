# Personal Telegram Automation Platform

This project is now structured as a scalable Railway-ready automation platform.

The goal is to run one Railway service that can eventually host multiple Telegram bots and personal automations from the same codebase.

## Current Bots

### Morning Bot

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
08:00 Asia/Bangkok - morning briefing
```

### XAUUSD Bot

Prepared as a placeholder for the next build.

Enabled only when both variables are present:

```text
XAUUSD_BOT_TOKEN=
XAUUSD_CHAT_ID=
```

If these are missing, the platform logs that the XAUUSD bot is disabled and keeps running the morning bot.

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

## Test The Morning Bot

Open Telegram and send:

```text
/start
/morning
```

The platform logs should show:

```text
Platform starting...
Morning bot starting...
XAUUSD bot disabled...
Scheduler started.
morning bot Telegram polling started.
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
MORNING_BOT_TOKEN=your_morning_bot_token
MORNING_CHAT_ID=your_telegram_chat_id
TIMEZONE=Asia/Bangkok
```

Optional future XAUUSD bot variables:

```text
XAUUSD_BOT_TOKEN=your_xauusd_bot_token
XAUUSD_CHAT_ID=your_telegram_chat_id
```

If the XAUUSD values are not set, the platform still deploys and runs the morning bot.

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

