# Personal Telegram Automation Platform

This folder contains the Railway-ready platform package. Run it from the repository root with:

```bash
python -m automation_platform.main
```

Preferred Railway variables for Jeremy Assistant:

```text
ASSISTANT_BOT_TOKEN=
ASSISTANT_CHAT_ID=
TIMEZONE=Asia/Bangkok
```

Legacy fallback variables:

```text
MORNING_BOT_TOKEN=
MORNING_CHAT_ID=
XAUUSD_BOT_TOKEN=
XAUUSD_CHAT_ID=
```

If Assistant variables are present, only Jeremy Assistant starts. If Assistant variables are missing, the platform falls back to the legacy separate bots.

See the root `README.md` for full setup and deployment instructions.
