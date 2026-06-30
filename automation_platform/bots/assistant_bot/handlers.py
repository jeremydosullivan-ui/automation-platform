"""Telegram command handlers for Jeremy Assistant."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from automation_platform.bots.assistant_bot.messages import (
    build_gold_message,
    build_help_message,
    build_london_message,
    build_newyork_message,
    build_start_message,
    build_status_message,
)
from automation_platform.bots.morning_bot.messages import build_morning_message
from automation_platform.shared.config import BotConfig, PlatformConfig
from automation_platform.shared.handlers import health_handler
from automation_platform.shared.telegram import allowed_chat


logger = logging.getLogger(__name__)


def register_handlers(application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    """Register Jeremy Assistant commands."""

    logger.info("Registering assistant commands...")
    application.bot_data["platform_config"] = platform_config
    application.bot_data["bot_config"] = bot_config
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("morning", morning_command))
    application.add_handler(CommandHandler("gold", gold_command))
    application.add_handler(CommandHandler("london", london_command))
    application.add_handler(CommandHandler("newyork", newyork_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(health_handler())


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("/start received by assistant from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message(build_start_message())
    logger.info("Assistant responded to /start.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("/help received by assistant from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message(build_help_message())
    logger.info("Assistant responded to /help.")


async def morning_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    platform_config: PlatformConfig = context.application.bot_data["platform_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("/morning received by assistant from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message("Building your morning briefing...")
    message = await asyncio.to_thread(build_morning_message, platform_config.timezone)
    await update.effective_chat.send_message(message)
    logger.info("Assistant responded to /morning.")


async def gold_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("/gold received by assistant from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message(build_gold_message())
    logger.info("Assistant responded to /gold.")


async def london_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("/london received by assistant from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message(build_london_message())
    logger.info("Assistant responded to /london.")


async def newyork_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("/newyork received by assistant from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message(build_newyork_message())
    logger.info("Assistant responded to /newyork.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    platform_config: PlatformConfig = context.application.bot_data["platform_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("/status received by assistant from chat %s.", update.effective_chat.id)
    scheduler = context.application.bot_data.get("scheduler")
    now = datetime.now(platform_config.timezone).strftime("%A, %d %B %Y %H:%M:%S")
    await update.effective_chat.send_message(
        build_status_message(
            timezone_name=platform_config.timezone_name,
            current_time=now,
            scheduler_running=bool(scheduler and scheduler.running),
        )
    )
    logger.info("Assistant responded to /status.")

