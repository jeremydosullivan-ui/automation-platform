"""Telegram command handlers for the placeholder XAUUSD bot."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from automation_platform.bots.xauusd_bot.messages import build_start_message, build_status_message
from automation_platform.shared.config import BotConfig, PlatformConfig
from automation_platform.shared.telegram import allowed_chat


logger = logging.getLogger(__name__)


def register_handlers(application: Application, platform_config: PlatformConfig, bot_config: BotConfig) -> None:
    application.bot_data["platform_config"] = platform_config
    application.bot_data["bot_config"] = bot_config
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("XAUUSD bot received /start from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message(build_start_message())
    logger.info("XAUUSD bot responded to /start.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("XAUUSD bot received /status from chat %s.", update.effective_chat.id)
    await update.effective_chat.send_message(build_status_message())
    logger.info("XAUUSD bot responded to /status.")
