"""Railway-ready entrypoint for the personal automation platform."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from dataclasses import dataclass

from telegram.ext import Application

from automation_platform.bots.assistant_bot.handlers import register_handlers as register_assistant_handlers
from automation_platform.bots.assistant_bot.scheduler import register_jobs as register_assistant_jobs
from automation_platform.bots.morning_bot.handlers import register_handlers as register_morning_handlers
from automation_platform.bots.morning_bot.scheduler import register_jobs as register_morning_jobs
from automation_platform.bots.xauusd_bot.handlers import register_handlers as register_xauusd_handlers
from automation_platform.bots.xauusd_bot.scheduler import register_jobs as register_xauusd_jobs
from automation_platform.shared.config import BotConfig, PlatformConfig, load_config
from automation_platform.shared.logging_config import setup_logging
from automation_platform.shared.scheduler import create_scheduler, describe_jobs
from automation_platform.shared.telegram import build_application


logger = logging.getLogger(__name__)


@dataclass
class BotRuntime:
    """A running Telegram bot application."""

    name: str
    application: Application
    runtime_state: dict[str, bool]

    async def start(self) -> None:
        await self.application.initialize()

        if self.application.updater is None:
            raise RuntimeError(f"{self.name} bot was created without a Telegram updater.")

        await self.application.updater.start_polling(drop_pending_updates=True)
        await self.application.start()
        self.runtime_state[f"{self.name}_polling"] = True
        logger.info("%s bot Telegram polling started.", self.name)

    async def stop(self) -> None:
        if self.application.updater and self.application.updater.running:
            await self.application.updater.stop()

        if self.application.running:
            await self.application.stop()

        await self.application.shutdown()
        self.runtime_state[f"{self.name}_polling"] = False
        logger.info("%s bot stopped.", self.name)


async def run_platform(config: PlatformConfig, *, run_seconds: int | None = None) -> None:
    """Start all enabled bots and the shared scheduler."""

    logger.info("Platform starting...")
    scheduler = create_scheduler(config)
    runtime_state = {
        "assistant_polling": False,
        "morning_polling": False,
        "xauusd_polling": False,
    }
    runtimes: list[BotRuntime] = []

    if config.assistant_mode_enabled:
        assistant_runtime = _build_assistant_runtime(config, scheduler, runtime_state)
        if assistant_runtime:
            runtimes.append(assistant_runtime)
    else:
        logger.info("Assistant bot disabled. Falling back to legacy bot setup.")
        morning_runtime = _build_morning_runtime(config, scheduler, runtime_state)
        if morning_runtime:
            runtimes.append(morning_runtime)

        xauusd_runtime = _build_xauusd_runtime(config, scheduler, runtime_state)
        if xauusd_runtime:
            runtimes.append(xauusd_runtime)

    if not runtimes:
        raise RuntimeError("No bots are enabled. Add ASSISTANT_BOT_TOKEN/ASSISTANT_CHAT_ID or legacy bot credentials.")

    scheduler.start()
    logger.info("Scheduler started.")
    logger.info("Registered jobs:\n%s", describe_jobs(scheduler))

    for runtime in runtimes:
        await runtime.start()

    try:
        if run_seconds is not None:
            await asyncio.sleep(run_seconds)
        else:
            await _wait_for_shutdown_signal()
    finally:
        for runtime in reversed(runtimes):
            await runtime.stop()

        if scheduler.running:
            scheduler.shutdown(wait=False)
        logger.info("Platform stopped.")


def _build_assistant_runtime(config: PlatformConfig, scheduler, runtime_state: dict[str, bool]) -> BotRuntime | None:
    bot_config = config.assistant_bot
    if not bot_config.enabled:
        logger.info("Jeremy Assistant disabled. Add ASSISTANT_BOT_TOKEN and ASSISTANT_CHAT_ID to enable it.")
        return None

    logger.info("Jeremy Assistant starting...")
    application = build_application(bot_config)
    application.bot_data["scheduler"] = scheduler
    application.bot_data["runtime_state"] = runtime_state
    register_assistant_handlers(application, config, bot_config)
    register_assistant_jobs(scheduler, application, config, bot_config)
    return BotRuntime(name="assistant", application=application, runtime_state=runtime_state)


def _build_morning_runtime(config: PlatformConfig, scheduler, runtime_state: dict[str, bool]) -> BotRuntime | None:
    bot_config = config.morning_bot
    if not bot_config.enabled:
        logger.info("Morning bot disabled. Add MORNING_BOT_TOKEN and MORNING_CHAT_ID to enable it.")
        return None

    logger.info("Morning bot starting...")
    application = build_application(bot_config)
    application.bot_data["scheduler"] = scheduler
    application.bot_data["runtime_state"] = runtime_state
    register_morning_handlers(application, config, bot_config)
    register_morning_jobs(scheduler, application, config, bot_config)
    return BotRuntime(name="morning", application=application, runtime_state=runtime_state)


def _build_xauusd_runtime(config: PlatformConfig, scheduler, runtime_state: dict[str, bool]) -> BotRuntime | None:
    bot_config = config.xauusd_bot
    if not bot_config.enabled:
        logger.info("XAUUSD bot disabled. Add XAUUSD_BOT_TOKEN and XAUUSD_CHAT_ID to enable it.")
        return None

    logger.info("XAUUSD bot starting...")
    application = build_application(bot_config)
    application.bot_data["scheduler"] = scheduler
    application.bot_data["runtime_state"] = runtime_state
    register_xauusd_handlers(application, config, bot_config)
    register_xauusd_jobs(scheduler, application, config, bot_config)
    return BotRuntime(name="xauusd", application=application, runtime_state=runtime_state)


async def _wait_for_shutdown_signal() -> None:
    """Wait until Railway or the terminal asks the process to stop."""

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    await stop_event.wait()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Personal Telegram automation platform")
    parser.add_argument(
        "--run-seconds",
        type=int,
        help="run briefly for local startup testing, then stop",
    )
    parser.add_argument(
        "--check-startup",
        action="store_true",
        help="build runtime configuration without starting Telegram polling",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    config = load_config()
    if args.check_startup:
        check_startup(config)
    else:
        asyncio.run(run_platform(config, run_seconds=args.run_seconds))


def check_startup(config: PlatformConfig) -> None:
    """Build the configured bot runtime without connecting to Telegram."""

    logger.info("Platform startup check...")
    scheduler = create_scheduler(config)
    runtime_state = {
        "assistant_polling": False,
        "morning_polling": False,
        "xauusd_polling": False,
    }

    if config.assistant_mode_enabled:
        runtime = _build_assistant_runtime(config, scheduler, runtime_state)
        enabled = [runtime.name] if runtime else []
    else:
        enabled = []
        morning_runtime = _build_morning_runtime(config, scheduler, runtime_state)
        xauusd_runtime = _build_xauusd_runtime(config, scheduler, runtime_state)
        if morning_runtime:
            enabled.append(morning_runtime.name)
        if xauusd_runtime:
            enabled.append(xauusd_runtime.name)

    if not enabled:
        raise RuntimeError("No bots would start with the current configuration.")

    logger.info("Startup check passed. Enabled bot runtimes: %s", ", ".join(enabled))
    logger.info("Registered jobs:\n%s", describe_jobs(scheduler))


if __name__ == "__main__":
    main()
