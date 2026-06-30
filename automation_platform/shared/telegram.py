"""Small Telegram helpers shared by bot modules."""

from __future__ import annotations

import logging

from telegram.ext import Application, ApplicationBuilder, ContextTypes
from telegram import Update

from automation_platform.shared.config import BotConfig


logger = logging.getLogger(__name__)


def build_application(bot_config: BotConfig) -> Application:
    """Create a Telegram Application for one bot."""

    if not bot_config.token:
        raise RuntimeError(f"{bot_config.name} bot token is missing.")

    return ApplicationBuilder().token(bot_config.token).build()


async def send_text(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> None:
    """Send a Telegram text message."""

    await context.bot.send_message(chat_id=chat_id, text=text)


async def allowed_chat(update: Update, bot_config: BotConfig) -> bool:
    """Return True only for the configured private chat."""

    if update.effective_chat is None:
        return False

    if update.effective_chat.id == bot_config.chat_id:
        return True

    logger.warning(
        "Ignoring command for %s bot from unauthorized chat %s.",
        bot_config.name,
        update.effective_chat.id,
    )
    await update.effective_chat.send_message("This bot is configured for a different chat.")
    return False

