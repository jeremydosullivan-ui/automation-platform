"""Environment variable loading for the automation platform."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BotConfig:
    """Settings for one Telegram bot."""

    name: str
    token: str | None
    chat_id: int | None

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)


@dataclass(frozen=True)
class PlatformConfig:
    """Settings shared by the whole platform."""

    timezone_name: str
    assistant_bot: BotConfig
    morning_bot: BotConfig
    xauusd_bot: BotConfig
    xauusd: "XauusdConfig"

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    @property
    def assistant_mode_enabled(self) -> bool:
        return self.assistant_bot.enabled


@dataclass(frozen=True)
class XauusdConfig:
    """Settings for the XAUUSD awareness module."""

    price_level_alert_distance_usd: float
    rsi_oversold: float
    rsi_overbought: float
    level_alert_cooldown_minutes: int
    rsi_alert_cooldown_minutes: int
    ema_alert_cooldown_minutes: int
    volatility_alert_cooldown_minutes: int
    choppy_alert_cooldown_minutes: int
    gold_api_key: str | None
    news_api_key: str | None
    economic_calendar_api_key: str | None


def load_config() -> PlatformConfig:
    """Load settings from environment variables.

    Railway injects environment variables directly. For local development we
    also load `.env` from either the platform folder or the project root.
    """

    logger.info("Loading environment variables...")
    platform_dir = Path(__file__).resolve().parents[1]
    project_root = platform_dir.parent

    load_dotenv(project_root / ".env")
    load_dotenv(platform_dir / ".env")

    return PlatformConfig(
        timezone_name=os.getenv("TIMEZONE", "Asia/Bangkok").strip(),
        assistant_bot=BotConfig(
            name="assistant",
            token=_env("ASSISTANT_BOT_TOKEN"),
            chat_id=_int_env("ASSISTANT_CHAT_ID"),
        ),
        morning_bot=BotConfig(
            name="morning",
            token=_env("MORNING_BOT_TOKEN", fallback="TELEGRAM_BOT_TOKEN"),
            chat_id=_int_env("MORNING_CHAT_ID", fallback="TELEGRAM_CHAT_ID"),
        ),
        xauusd_bot=BotConfig(
            name="xauusd",
            token=_env("XAUUSD_BOT_TOKEN"),
            chat_id=_int_env("XAUUSD_CHAT_ID"),
        ),
        xauusd=XauusdConfig(
            price_level_alert_distance_usd=_float_env("PRICE_LEVEL_ALERT_DISTANCE_USD", 5),
            rsi_oversold=_float_env("RSI_OVERSOLD", 30),
            rsi_overbought=_float_env("RSI_OVERBOUGHT", 70),
            level_alert_cooldown_minutes=_int_setting("LEVEL_ALERT_COOLDOWN_MINUTES", 60),
            rsi_alert_cooldown_minutes=_int_setting("RSI_ALERT_COOLDOWN_MINUTES", 60),
            ema_alert_cooldown_minutes=_int_setting("EMA_ALERT_COOLDOWN_MINUTES", 120),
            volatility_alert_cooldown_minutes=_int_setting("VOLATILITY_ALERT_COOLDOWN_MINUTES", 120),
            choppy_alert_cooldown_minutes=_int_setting("CHOPPY_ALERT_COOLDOWN_MINUTES", 180),
            gold_api_key=_env("GOLD_API_KEY"),
            news_api_key=_env("NEWS_API_KEY"),
            economic_calendar_api_key=_env("ECONOMIC_CALENDAR_API_KEY"),
        ),
    )


def _env(name: str, fallback: str | None = None) -> str | None:
    value = os.getenv(name)
    if not value and fallback:
        value = os.getenv(fallback)
    return value.strip() if value else None


def _int_env(name: str, fallback: str | None = None) -> int | None:
    raw = _env(name, fallback=fallback)
    if not raw:
        return None

    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"{name} must be a number.") from None


def _int_setting(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default

    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"{name} must be a whole number.") from None


def _float_env(name: str, default: float) -> float:
    raw = _env(name)
    if not raw:
        return default

    try:
        return float(raw)
    except ValueError:
        raise RuntimeError(f"{name} must be a number.") from None
