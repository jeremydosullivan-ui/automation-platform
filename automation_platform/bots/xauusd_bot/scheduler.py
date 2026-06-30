"""Scheduled jobs for the placeholder XAUUSD bot."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from automation_platform.shared.config import BotConfig, PlatformConfig


logger = logging.getLogger(__name__)


def register_jobs(scheduler: AsyncIOScheduler, application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    """Register future XAUUSD jobs.

    Version 1 of the platform keeps this empty so missing or unfinished trading
    logic cannot affect the working morning bot.
    """

    logger.info("XAUUSD bot has no scheduled jobs yet.")

