"""Shared Telegram command handlers."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from automation_platform.shared.config import BotConfig, PlatformConfig
from automation_platform.shared.health import build_health_message
from automation_platform.shared.telegram import allowed_chat


logger = logging.getLogger(__name__)


def health_handler() -> CommandHandler:
    """Return the shared /health command handler."""

    return CommandHandler("health", health_command)


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_config: BotConfig = context.application.bot_data["bot_config"]
    platform_config: PlatformConfig = context.application.bot_data["platform_config"]
    if not await allowed_chat(update, bot_config):
        return

    logger.info("%s bot received /health from chat %s.", bot_config.name, update.effective_chat.id)
    await update.effective_chat.send_message(build_health_message(context, platform_config))
    logger.info("%s bot sent /health response.", bot_config.name)

