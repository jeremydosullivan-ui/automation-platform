"""Scheduled jobs for the morning briefing bot."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application

from automation_platform.bots.morning_bot.messages import build_morning_message
from automation_platform.shared.config import BotConfig, PlatformConfig


logger = logging.getLogger(__name__)


def register_jobs(scheduler: AsyncIOScheduler, application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    """Schedule the daily 08:00 Bangkok morning briefing."""

    scheduler.add_job(
        send_scheduled_morning,
        CronTrigger(hour=8, minute=0, timezone=platform_config.timezone),
        args=[application, platform_config, bot_config],
        id="morning_bot_daily_briefing",
        replace_existing=True,
    )
    logger.info("Morning bot daily job registered for 08:00 %s.", platform_config.timezone_name)


async def send_scheduled_morning(application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    if not bot_config.chat_id:
        logger.warning("Morning bot chat ID missing; skipping scheduled message.")
        return

    message = await asyncio.to_thread(build_morning_message, platform_config.timezone)
    await application.bot.send_message(chat_id=bot_config.chat_id, text=message)
    logger.info("Morning bot scheduled briefing sent.")

