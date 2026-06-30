"""Shared platform health-check message builder."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
            _bot_status("Morning Bot", platform_config.morning_bot.enabled, placeholder=False),
            _bot_status("XAUUSD Bot", platform_config.xauusd_bot.enabled, placeholder=True),
            "",
            "Telegram:",
            _polling_status("Morning Bot", runtime_state.get("morning_polling")),
            _polling_status("XAUUSD Bot", runtime_state.get("xauusd_polling")),
            "",
            "Scheduler:",
            _scheduler_status(scheduler),
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
        "morning_bot_daily_briefing": "07:30 — Morning Briefing",
        "london_session_watch": "14:00 — London Watch",
        "newyork_session_watch": "20:30 — New York Watch",
        "silent_market_scan": "Every 15 min — XAUUSD scan",
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

