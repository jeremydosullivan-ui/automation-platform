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
        "/inspection - XAUUSD inspection checklist\n"
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
        "/inspection - send the XAUUSD inspection checklist\n"
        "/status - show assistant-level status\n"
        "/health - show platform-level diagnostics"
    )


def build_inspection_message() -> str:
    return (
        "🔔 XAUUSD Inspection\n\n"
        "Maximum inspection time: 15 minutes\n\n"
        "TREND\n"
        "☐ Daily candle agrees\n"
        "☐ 4H candle agrees\n"
        "☐ 1H candle agrees\n"
        "☐ 15M candle agrees\n\n"
        "If any trend box fails:\n"
        "❌ No trade. Close the chart.\n\n"
        "ENTRY\n"
        "☐ 1M pullback against trend\n"
        "☐ Continuation back in trend direction\n\n"
        "TIMING\n"
        "☐ First 15 minutes of the hour\n"
        "☐ New 4H candle? Bonus confidence\n\n"
        "DECISION\n"
        "✅ All checks = Trade allowed\n"
        "❌ Any missing check = No trade\n\n"
        "Golden Rule:\n"
        "Trade the process, not the money."
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
        "✅ 15-minute scanner enabled\n"
        "✅ Hourly inspection reminders 08:00-23:00\n\n"
        "Version:\n"
        "automation-platform v1"
    )
