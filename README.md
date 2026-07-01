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
14:00 Asia/Bangkok - London session watch
20:30 Asia/Bangkok - New York session watch
Every 15 minutes - silent XAUUSD scan, alerts only when conditions trigger
```

## XAUUSD Module

Jeremy Assistant now includes a Version 1 XAUUSD trading-awareness module.

It does:

- show current gold market context with `/gold`
- show London and New York session watch messages
- calculate EMA 50, EMA 200, RSI 14, and ATR 14
- estimate 1H, 4H, and 1D trend
- detect simple support and resistance from recent swing highs/lows
- scan silently every 15 minutes and alert only when configured conditions trigger

It does not:

- provide buy or sell signals
- provide financial advice
- replace your own trading plan or risk management

Market data source:

```text
Current price: TradingView scanner, symbol OANDA:XAUUSD
Historical candles: Yahoo Finance chart API, symbol GC=F
```

The bot uses TradingView `OANDA:XAUUSD` for the current spot-style price so it stays close to the TradingView chart. Yahoo `GC=F` is a COMEX gold futures symbol and is used only for free candle history, adjusted onto the spot-price basis for indicators and levels. No market data API key is required.

News and economic calendar support:

```text
Free calendar: Forex Factory feed + official US sources
```

The bot uses a no-key Forex Factory/Fair Economy weekly calendar feed for USD events, plus official BEA, Census, and Federal Reserve pages where practical. No economic calendar API key is required.

If all free calendar sources are temporarily unavailable, the bot keeps working and shows `Market events unavailable.`

Important disclaimer:

This bot is for education, market awareness, and discipline support only. It does not provide financial advice. It does not issue buy or sell instructions. Trading XAUUSD involves significant risk.

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

PRICE_LEVEL_ALERT_DISTANCE_USD=5
RSI_OVERSOLD=30
RSI_OVERBOUGHT=70

LEVEL_ALERT_COOLDOWN_MINUTES=60
RSI_ALERT_COOLDOWN_MINUTES=60
EMA_ALERT_COOLDOWN_MINUTES=120
VOLATILITY_ALERT_COOLDOWN_MINUTES=120
CHOPPY_ALERT_COOLDOWN_MINUTES=180

GOLD_API_KEY=
NEWS_API_KEY=
ECONOMIC_CALENDAR_API_KEY=
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
assistant_daily_morning_briefing
london_session_watch
newyork_session_watch
silent_market_scan
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
PRICE_LEVEL_ALERT_DISTANCE_USD=5
RSI_OVERSOLD=30
RSI_OVERBOUGHT=70
LEVEL_ALERT_COOLDOWN_MINUTES=60
RSI_ALERT_COOLDOWN_MINUTES=60
EMA_ALERT_COOLDOWN_MINUTES=120
VOLATILITY_ALERT_COOLDOWN_MINUTES=120
CHOPPY_ALERT_COOLDOWN_MINUTES=180
```

No market data API key is required for Version 1. Current price uses TradingView `OANDA:XAUUSD`; candle history uses Yahoo Finance `GC=F`.

Optional future keys are reserved but not required for Version 1:

```text
GOLD_API_KEY=
NEWS_API_KEY=
ECONOMIC_CALENDAR_API_KEY=
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
