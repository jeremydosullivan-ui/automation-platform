# Personal Telegram Automation Platform

This folder contains the Railway-ready platform package. Run it from the repository root with:

```bash
python -m automation_platform.main
```

Required Railway variables for the current working morning bot:

```text
MORNING_BOT_TOKEN=
MORNING_CHAT_ID=
TIMEZONE=Asia/Bangkok
```

Optional future XAUUSD bot variables:

```text
XAUUSD_BOT_TOKEN=
XAUUSD_CHAT_ID=
```

If the XAUUSD variables are missing, the platform logs that the XAUUSD bot is disabled and continues running the morning bot.

See the root `README.md` for full setup and deployment instructions.
