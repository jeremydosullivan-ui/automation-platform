"""Shared scheduler helpers."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from automation_platform.shared.config import PlatformConfig


def create_scheduler(config: PlatformConfig) -> AsyncIOScheduler:
    """Create the single scheduler used by all enabled bots."""

    return AsyncIOScheduler(timezone=config.timezone)


def describe_jobs(scheduler: AsyncIOScheduler) -> str:
    """Return a readable list of scheduled jobs."""

    jobs = scheduler.get_jobs()
    if not jobs:
        return "No scheduled jobs registered."

    lines: list[str] = []
    for job in jobs:
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z") if job.next_run_time else "not scheduled yet"
        lines.append(f"- {job.id}: {next_run}")

    return "\n".join(lines)

