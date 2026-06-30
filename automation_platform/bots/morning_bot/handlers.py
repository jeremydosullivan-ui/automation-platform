"""Telegram command handlers for the morning briefing bot."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from automation_platform.bots.morning_bot.messages import build_morning_message
from automation_platform.bots.morning_bot.scheduler import MORNING_BRIEF_HOUR, MORNING_BRIEF_MINUTE
from automation_platform.shared.config import BotConfig, PlatformConfig
from automation_platform.shared.telegram import allowed_chat


logger = logging.getLogger(__name__)


def register_handlers(application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    """Register morning bot commands."""

    application.bot_data["platform_config"] = platform_config
    application.bot_data["bot_config"] = bot_config
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("morning", morning_command))
    application.add_handler(CommandHandler("status", status_command))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("Morning bot received /start from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message(
        "✅ Morning bot is alive.\n\n"
        "Commands:\n"
        "/morning - send the morning briefing now"
    )
    logger.info("Morning bot responded to /start.")


async def morning_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    platform_config: PlatformConfig = context.application.bot_data["platform_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("Morning bot received /morning from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message("Building your morning briefing...")
    message = await asyncio.to_thread(build_morning_message, platform_config.timezone)
    await update.effective_chat.send_message(message)
    logger.info("Morning bot responded to /morning.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    platform_config: PlatformConfig = context.application.bot_data["platform_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("Morning bot received /status from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message(_build_status_message(context, platform_config))
    logger.info("Morning bot responded to /status.")


def _build_status_message(context: ContextTypes.DEFAULT_TYPE, platform_config: PlatformConfig) -> str:
    scheduler = context.application.bot_data.get("scheduler")
    scheduler_running = bool(scheduler and scheduler.running)
    now = datetime.now(platform_config.timezone)

    return "\n".join(
        [
            "🟢 Morning Bot Status",
            "",
            "✅ Bot Online",
            "✅ Telegram Connected",
            "✅ Scheduler Running" if scheduler_running else "⚠️ Scheduler Not Running",
            "",
            "Current Time:",
            now.strftime("%A, %d %B %Y %H:%M:%S"),
            "",
            "Timezone:",
            platform_config.timezone_name,
            "",
            "Next Scheduled Job:",
            f"{MORNING_BRIEF_HOUR:02d}:{MORNING_BRIEF_MINUTE:02d} Morning Briefing",
            "",
            "Version:",
            "automation-platform v1",
        ]
    )
