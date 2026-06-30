"""Messages for Jeremy Assistant."""

from __future__ import annotations


def build_start_message() -> str:
    return (
        "✅ Jeremy Assistant is alive.\n\n"
        "Available commands:\n"
        "/help - show all commands\n"
        "/morning - send the morning briefing\n"
        "/gold - show current XAUUSD market snapshot\n"
        "/london - London session watch\n"
        "/newyork - New York session watch\n"
        "/status - assistant status\n"
        "/health - platform health check"
    )


def build_help_message() -> str:
    return (
        "🤖 Jeremy Assistant Commands\n\n"
        "/start - confirm Jeremy Assistant is alive\n"
        "/help - list commands and what they do\n"
        "/morning - send the existing morning briefing now\n"
        "/gold - show current XAUUSD market snapshot\n"
        "/london - show London session watch\n"
        "/newyork - show New York session watch\n"
        "/status - show assistant-level status\n"
        "/health - show platform-level diagnostics"
    )


def build_status_message(timezone_name: str, current_time: str, scheduler_running: bool) -> str:
    scheduler_line = "✅ Scheduler Running" if scheduler_running else "⚠️ Scheduler Not Running"
    return (
        "🟢 Jeremy Assistant Status\n\n"
        "✅ Bot Online\n"
        "✅ Telegram Connected\n"
        f"{scheduler_line}\n\n"
        "Current Time:\n"
        f"{current_time}\n\n"
        "Timezone:\n"
        f"{timezone_name}\n\n"
        "Active Interface:\n"
        "Jeremy Assistant\n\n"
        "XAUUSD Module:\n"
        "✅ Market snapshot enabled\n"
        "✅ London/New York watches enabled\n"
        "✅ 15-minute scanner enabled\n\n"
        "Version:\n"
        "automation-platform v1"
    )
