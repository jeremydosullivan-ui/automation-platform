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
PRICE_LEVEL_ALERT_DISTANCE_USD=5
RSI_OVERSOLD=30
RSI_OVERBOUGHT=70
LEVEL_ALERT_COOLDOWN_MINUTES=60
RSI_ALERT_COOLDOWN_MINUTES=60
EMA_ALERT_COOLDOWN_MINUTES=120
VOLATILITY_ALERT_COOLDOWN_MINUTES=120
CHOPPY_ALERT_COOLDOWN_MINUTES=180
```

The XAUUSD module uses TradingView `OANDA:XAUUSD` for the current spot-style price. Yahoo Finance `GC=F` is used only for free candle history, adjusted onto the spot-price basis for indicators and levels. No market data API key is required.

Economic calendar support uses a no-key Forex Factory/Fair Economy weekly calendar feed for USD events, plus official BEA, Census, and Federal Reserve pages where practical. No economic calendar API key is required. If all free sources are temporarily unavailable, `/gold` and `/newyork` show `Market events unavailable` and the rest of the message still works.

Optional future provider keys are reserved but not required for Version 1:

```text
GOLD_API_KEY=
NEWS_API_KEY=
ECONOMIC_CALENDAR_API_KEY=
```

Scheduled jobs in Assistant mode:

```text
07:30 Asia/Bangkok - morning briefing
14:00 Asia/Bangkok - London session watch
20:30 Asia/Bangkok - New York session watch
Every 15 minutes - silent XAUUSD scan
```

Legacy fallback variables:

```text
MORNING_BOT_TOKEN=
MORNING_CHAT_ID=
XAUUSD_BOT_TOKEN=
XAUUSD_CHAT_ID=
```

If Assistant variables are present, only Jeremy Assistant starts. If Assistant variables are missing, the platform falls back to the legacy separate bots.

Trading disclaimer: this bot is for education, market awareness, and discipline support only. It does not provide financial advice or buy/sell instructions. Trading XAUUSD involves significant risk.

See the root `README.md` for full setup and deployment instructions.
