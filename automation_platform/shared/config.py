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
    morning_bot: BotConfig
    xauusd_bot: BotConfig

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


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

