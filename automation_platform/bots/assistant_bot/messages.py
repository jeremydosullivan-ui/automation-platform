"""Messages for Jeremy Assistant."""

from __future__ import annotations


def build_start_message() -> str:
    return (
        "✅ Jeremy Assistant is alive.\n\n"
        "Available commands:\n"
        "/help - show all commands\n"
        "/morning - send the morning briefing\n"
        "/gold - show XAUUSD placeholder status\n"
        "/london - London session watch placeholder\n"
        "/newyork - New York session watch placeholder\n"
        "/status - assistant status\n"
        "/health - platform health check"
    )


def build_help_message() -> str:
    return (
        "🤖 Jeremy Assistant Commands\n\n"
        "/start - confirm Jeremy Assistant is alive\n"
        "/help - list commands and what they do\n"
        "/morning - send the existing morning briefing now\n"
        "/gold - show current XAUUSD module placeholder status\n"
        "/london - placeholder for London session watch\n"
        "/newyork - placeholder for New York session watch\n"
        "/status - show assistant-level status\n"
        "/health - show platform-level diagnostics"
    )


def build_gold_message() -> str:
    return (
        "🥇 XAUUSD module status\n\n"
        "Enabled through Jeremy Assistant, but trading-alert features are not implemented yet.\n\n"
        "This does not provide trading signals or financial advice."
    )


def build_london_message() -> str:
    return (
        "🇬🇧 London Session Watch\n\n"
        "Placeholder active.\n\n"
        "London session logic has not been implemented yet."
    )


def build_newyork_message() -> str:
    return (
        "🇺🇸 New York Session Watch\n\n"
        "Placeholder active.\n\n"
        "New York session logic has not been implemented yet."
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
        "Version:\n"
        "automation-platform v1"
    )

