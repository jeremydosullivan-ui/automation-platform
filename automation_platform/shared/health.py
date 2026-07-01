"""Shared platform health-check message builder."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from automation_platform.bots.xauusd_bot.economic_calendar import CALENDAR_PROVIDER_LABEL
from automation_platform.bots.xauusd_bot.market_data import DATA_SOURCE_LABEL
from automation_platform.shared.config import PlatformConfig


APP_VERSION = "automation-platform v1"


def build_health_message(context: Any, platform_config: PlatformConfig) -> str:
    """Build one health message that can be used by any bot."""

    scheduler = context.application.bot_data.get("scheduler")
    runtime_state = context.application.bot_data.get("runtime_state", {})
    now = datetime.now(platform_config.timezone)

    return "\n".join(
        [
            "🟢 Automation Platform Health",
            "",
            "Platform:",
            "✅ Online",
            "",
            "Environment:",
            f"Timezone: {platform_config.timezone_name}",
            f"Railway: {_railway_status()}",
            f"Environment: {_environment_label()}",
            "",
            "Bots:",
            *_bot_lines(platform_config),
            "",
            "Telegram:",
            *_polling_lines(platform_config, runtime_state),
            "",
            "Scheduler:",
            _scheduler_status(scheduler),
            "",
            "XAUUSD:",
            f"Data Source: {DATA_SOURCE_LABEL}",
            f"Calendar Source: {_calendar_source_status(platform_config)}",
            f"Scanner: {_job_registered(scheduler, 'silent_market_scan')}",
            "",
            "Next Scheduled Jobs:",
            _scheduled_jobs(scheduler),
            "",
            "Current Time:",
            now.strftime("%A, %d %B %Y %H:%M:%S"),
            "",
            "Version:",
            _version_label(),
        ]
    )


def _bot_status(name: str, enabled: bool, *, placeholder: bool) -> str:
    if not enabled:
        return f"⚪ {name}: Disabled"
    if placeholder:
        return f"✅ {name}: Enabled / Placeholder"
    return f"✅ {name}: Enabled"


def _bot_lines(platform_config: PlatformConfig) -> list[str]:
    if platform_config.assistant_mode_enabled:
        return [
            _bot_status("Jeremy Assistant", platform_config.assistant_bot.enabled, placeholder=False),
            "✅ Morning Module: Enabled",
            "✅ XAUUSD Module: Enabled",
        ]

    return [
        _bot_status("Morning Bot", platform_config.morning_bot.enabled, placeholder=False),
        _bot_status("XAUUSD Bot", platform_config.xauusd_bot.enabled, placeholder=True),
    ]


def _polling_lines(platform_config: PlatformConfig, runtime_state: dict[str, bool]) -> list[str]:
    if platform_config.assistant_mode_enabled:
        return [_polling_status("Jeremy Assistant", runtime_state.get("assistant_polling"))]

    return [
        _polling_status("Morning Bot", runtime_state.get("morning_polling")),
        _polling_status("XAUUSD Bot", runtime_state.get("xauusd_polling")),
    ]


def _polling_status(name: str, active: bool | None) -> str:
    if active is True:
        return f"✅ {name} polling active"
    if active is False:
        return f"⚠️ {name} polling not active"
    return f"⚪ {name} polling unavailable"


def _scheduler_status(scheduler: AsyncIOScheduler | None) -> str:
    if scheduler is None:
        return "⚠️ Scheduler unavailable"
    return "✅ Running" if scheduler.running else "⚠️ Not running"


def _job_registered(scheduler: AsyncIOScheduler | None, job_id: str) -> str:
    if scheduler is None:
        return "Unavailable"
    return "Registered" if scheduler.get_job(job_id) else "Not registered"


def _calendar_source_status(platform_config: PlatformConfig) -> str:
    return f"{CALENDAR_PROVIDER_LABEL} enabled"


def _scheduled_jobs(scheduler: AsyncIOScheduler | None) -> str:
    if scheduler is None:
        return "• Scheduler data unavailable"

    jobs = scheduler.get_jobs()
    if not jobs:
        return "• No jobs registered"

    lines = []
    for job in sorted(jobs, key=lambda item: item.id):
        lines.append(f"• {_job_label(job.id)}")

    return "\n".join(lines)


def _job_label(job_id: str) -> str:
    labels = {
        "assistant_daily_morning_briefing": "07:30 — Morning Briefing",
        "morning_bot_daily_briefing": "07:30 — Morning Briefing",
        "london_session_watch": "14:00 — London Watch",
        "newyork_session_watch": "20:30 — New York Watch",
        "silent_market_scan": "Every 15 min — XAUUSD scan",
        "xauusd_hourly_inspection_reminder": "08:00-23:00 hourly — XAUUSD Inspection",
    }
    return labels.get(job_id, job_id.replace("_", " "))


def _railway_status() -> str:
    return "Detected" if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_SERVICE_NAME") else "Not detected"


def _environment_label() -> str:
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return "Production"
    return os.getenv("APP_ENV", "Local")


def _version_label() -> str:
    commit = os.getenv("RAILWAY_GIT_COMMIT_SHA") or _git_commit()
    if commit:
        return f"{APP_VERSION} ({commit[:7]})"
    return APP_VERSION


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (subprocess.SubprocessError, OSError):
        return None

    return result.stdout.strip() or None
