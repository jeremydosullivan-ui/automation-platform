"""Scheduled jobs for Jeremy Assistant."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from telegram.ext import Application

from automation_platform.bots.morning_bot.messages import build_morning_message
from automation_platform.bots.morning_bot.scheduler import MORNING_BRIEF_HOUR, MORNING_BRIEF_MINUTE
from automation_platform.bots.xauusd_bot.alerts import evaluate_alerts
from automation_platform.bots.xauusd_bot.indicators import analyze_market
from automation_platform.bots.xauusd_bot.market_data import fetch_market_data
from automation_platform.bots.xauusd_bot.messages import build_london_message, build_newyork_message
from automation_platform.shared.config import BotConfig, PlatformConfig


logger = logging.getLogger(__name__)


def register_jobs(scheduler: AsyncIOScheduler, application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    """Schedule Jeremy Assistant jobs."""

    scheduler.add_job(
        send_scheduled_morning,
        CronTrigger(hour=MORNING_BRIEF_HOUR, minute=MORNING_BRIEF_MINUTE, timezone=platform_config.timezone),
        args=[application, platform_config, bot_config],
        id="assistant_daily_morning_briefing",
        replace_existing=True,
    )
    logger.info("Jeremy Assistant daily morning job registered for 07:30 %s.", platform_config.timezone_name)

    scheduler.add_job(
        send_scheduled_london,
        CronTrigger(hour=14, minute=0, timezone=platform_config.timezone),
        args=[application, platform_config, bot_config],
        id="london_session_watch",
        replace_existing=True,
    )
    logger.info("Jeremy Assistant London session job registered for 14:00 %s.", platform_config.timezone_name)

    scheduler.add_job(
        send_scheduled_newyork,
        CronTrigger(hour=20, minute=30, timezone=platform_config.timezone),
        args=[application, platform_config, bot_config],
        id="newyork_session_watch",
        replace_existing=True,
    )
    logger.info("Jeremy Assistant New York session job registered for 20:30 %s.", platform_config.timezone_name)

    scheduler.add_job(
        run_silent_market_scan,
        IntervalTrigger(minutes=15, timezone=platform_config.timezone),
        args=[application, platform_config, bot_config],
        id="silent_market_scan",
        replace_existing=True,
    )
    logger.info("Jeremy Assistant silent XAUUSD scan registered for every 15 minutes.")


async def send_scheduled_morning(application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    if not bot_config.chat_id:
        logger.warning("Assistant chat ID missing; skipping scheduled morning briefing.")
        return

    message = await asyncio.to_thread(build_morning_message, platform_config.timezone)
    await application.bot.send_message(chat_id=bot_config.chat_id, text=message)
    logger.info("Jeremy Assistant scheduled morning briefing sent.")


async def send_scheduled_london(application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    if not bot_config.chat_id:
        logger.warning("Assistant chat ID missing; skipping London session watch.")
        return

    try:
        message = await asyncio.to_thread(build_london_message, platform_config)
        await application.bot.send_message(chat_id=bot_config.chat_id, text=message)
        logger.info("Jeremy Assistant London session watch sent.")
    except Exception:
        logger.exception("London session watch failed.")


async def send_scheduled_newyork(application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    if not bot_config.chat_id:
        logger.warning("Assistant chat ID missing; skipping New York session watch.")
        return

    try:
        message = await asyncio.to_thread(build_newyork_message, platform_config)
        await application.bot.send_message(chat_id=bot_config.chat_id, text=message)
        logger.info("Jeremy Assistant New York session watch sent.")
    except Exception:
        logger.exception("New York session watch failed.")


async def run_silent_market_scan(application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    if not bot_config.chat_id:
        logger.warning("Assistant chat ID missing; skipping XAUUSD market scan.")
        return

    try:
        data = await asyncio.to_thread(fetch_market_data)
        if data is None or not data.available:
            logger.warning("Data unavailable fallback used during XAUUSD scanner.")
            return

        analysis = await asyncio.to_thread(analyze_market, data)
        now = datetime.now(platform_config.timezone)
        alerts = evaluate_alerts(data, analysis, platform_config.xauusd, now)
        for alert in alerts:
            await application.bot.send_message(chat_id=bot_config.chat_id, text=alert.message)
        if alerts:
            logger.info("Sent %s XAUUSD alert(s).", len(alerts))
    except Exception:
        logger.exception("Silent XAUUSD market scan failed.")
