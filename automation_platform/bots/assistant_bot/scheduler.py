"""Scheduled jobs for Jeremy Assistant."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application

from automation_platform.bots.morning_bot.messages import build_morning_message
from automation_platform.bots.morning_bot.scheduler import MORNING_BRIEF_HOUR, MORNING_BRIEF_MINUTE
from automation_platform.shared.config import BotConfig, PlatformConfig


logger = logging.getLogger(__name__)


def register_jobs(scheduler: AsyncIOScheduler, application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    """Schedule the daily morning briefing through Jeremy Assistant."""

    scheduler.add_job(
        send_scheduled_morning,
        CronTrigger(hour=MORNING_BRIEF_HOUR, minute=MORNING_BRIEF_MINUTE, timezone=platform_config.timezone),
        args=[application, platform_config, bot_config],
        id="assistant_daily_morning_briefing",
        replace_existing=True,
    )
    logger.info("Jeremy Assistant daily morning job registered for 07:30 %s.", platform_config.timezone_name)


async def send_scheduled_morning(application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    if not bot_config.chat_id:
        logger.warning("Assistant chat ID missing; skipping scheduled morning briefing.")
        return

    message = await asyncio.to_thread(build_morning_message, platform_config.timezone)
    await application.bot.send_message(chat_id=bot_config.chat_id, text=message)
    logger.info("Jeremy Assistant scheduled morning briefing sent.")

