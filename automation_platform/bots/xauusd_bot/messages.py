"""Messages for XAUUSD trading-awareness features.

Educational disclaimer: this module provides market awareness and discipline
support only. It does not provide financial advice or buy/sell instructions.
"""

from __future__ import annotations

import logging

from automation_platform.bots.xauusd_bot.economic_calendar import format_events_for_message, get_todays_xauusd_events
from automation_platform.bots.xauusd_bot.indicators import analyze_market
from automation_platform.bots.xauusd_bot.market_data import DATA_SOURCE_LABEL, MarketData, fetch_market_data
from automation_platform.shared.config import PlatformConfig


logger = logging.getLogger(__name__)


def build_start_message() -> str:
    return (
        "✅ XAUUSD module is alive.\n\n"
        "This is for education, market awareness, and discipline support only.\n"
        "It does not provide trading signals or financial advice."
    )


def build_status_message() -> str:
    return (
        "🥇 XAUUSD module status\n\n"
        "✅ Module enabled\n"
        f"✅ Data source configured: {DATA_SOURCE_LABEL}\n"
        "✅ Alerts require fresh spot data\n"
        "✅ Alerts configured with cooldowns\n\n"
        "This does not provide trading signals or financial advice."
    )


def build_gold_message(platform_config: PlatformConfig) -> str:
    logger.info("Building /gold response.")
    context = _load_context()
    if context is None:
        logger.warning("Data unavailable fallback used for /gold.")
        return _data_unavailable_message("🥇 XAUUSD Market Snapshot")

    data, analysis = context
    events_text = market_events_text(platform_config)
    return (
        "🥇 XAUUSD Market Snapshot\n\n"
        "Price:\n"
        f"{_money(data.current_price)}\n\n"
        "Price Source:\n"
        f"{data.source}\n"
        f"Requested Symbol: {data.requested_symbol}\n"
        f"Last Updated: {_time_label(data.price_timestamp)}\n"
        f"Status: {_status_label(data)}\n\n"
        "Today:\n"
        f"{_percent(data.daily_change_percent)}\n\n"
        "Range:\n"
        f"High: {_money(data.daily_high)}\n"
        f"Low: {_money(data.daily_low)}\n\n"
        "Trend:\n"
        f"1H: {analysis.one_hour.trend}\n"
        f"4H: {analysis.four_hour.trend}\n"
        f"1D: {analysis.one_day.trend}\n\n"
        "Key Levels:\n"
        "Support:\n"
        f"{_levels(analysis.supports)}\n\n"
        "Resistance:\n"
        f"{_levels(analysis.resistances)}\n\n"
        "Indicators:\n"
        f"RSI(14) 1H: {_number(analysis.one_hour.rsi14, 1)}\n"
        f"ATR(14) 1H: {_number(analysis.one_hour.atr14, 1)}\n"
        f"EMA50 1H: {_price_number(analysis.one_hour.ema50)}\n"
        f"EMA200 1H: {_price_number(analysis.one_hour.ema200)}\n\n"
        "Market Conditions:\n"
        f"{analysis.market_condition}\n\n"
        "Today's Market Events:\n"
        f"{events_text}\n\n"
        "Reminder:\n"
        "Wait for confirmation. No chasing. Protect capital first."
    )


def build_london_message(platform_config: PlatformConfig) -> str:
    logger.info("Building London session watch.")
    context = _load_context()
    if context is None:
        logger.warning("Data unavailable fallback used for /london.")
        return _data_unavailable_message("🇬🇧 London Session Watch")

    data, analysis = context
    return (
        "🇬🇧 London Session Watch\n\n"
        f"XAUUSD: {_money(data.current_price)}\n\n"
        "Price Source:\n"
        f"{data.source}\n"
        f"Last Updated: {_time_label(data.price_timestamp)}\n"
        f"Status: {_status_label(data)}\n\n"
        "Trend:\n"
        f"1H: {analysis.one_hour.trend}\n"
        f"4H: {analysis.four_hour.trend}\n\n"
        f"Nearest Support: {_nearest(analysis.supports)}\n"
        f"Nearest Resistance: {_nearest(analysis.resistances)}\n\n"
        f"RSI(14) 1H: {_number(analysis.one_hour.rsi14, 1)}\n"
        f"ATR(14) 1H: {_number(analysis.one_hour.atr14, 1)}\n\n"
        "Session Note:\n"
        "London open can create volatility and false breakouts.\n\n"
        "Reminder:\n"
        "Avoid entering in the first 5-10 minutes unless the setup is clear."
    )


def build_newyork_message(platform_config: PlatformConfig) -> str:
    logger.info("Building New York session watch.")
    context = _load_context()
    if context is None:
        logger.warning("Data unavailable fallback used for /newyork.")
        return _data_unavailable_message("🇺🇸 New York Session Watch")

    data, analysis = context
    events_text = market_events_text(platform_config)
    return (
        "🇺🇸 New York Session Watch\n\n"
        f"XAUUSD: {_money(data.current_price)}\n\n"
        "Price Source:\n"
        f"{data.source}\n"
        f"Last Updated: {_time_label(data.price_timestamp)}\n"
        f"Status: {_status_label(data)}\n\n"
        "Trend:\n"
        f"1H: {analysis.one_hour.trend}\n"
        f"4H: {analysis.four_hour.trend}\n\n"
        f"Nearest Support: {_nearest(analysis.supports)}\n"
        f"Nearest Resistance: {_nearest(analysis.resistances)}\n\n"
        f"RSI(14) 1H: {_number(analysis.one_hour.rsi14, 1)}\n"
        f"ATR(14) 1H: {_number(analysis.one_hour.atr14, 1)}\n\n"
        "Today's US Events:\n"
        f"{events_text}\n\n"
        "Session Note:\n"
        "New York open and US data releases can cause sharp moves in gold.\n\n"
        "Reminder:\n"
        "Wait for candle close confirmation. No chasing."
    )


def market_events_text(platform_config: PlatformConfig) -> str:
    """Return today's XAUUSD-relevant event text."""

    result = get_todays_xauusd_events(platform_config)
    if not result.available:
        logger.warning("Economic calendar fallback used in message.")
    return format_events_for_message(result)


def _load_context() -> tuple[MarketData, MarketAnalysis] | None:
    data = fetch_market_data()
    if data is None or not data.available:
        return None
    return data, analyze_market(data)


def _data_unavailable_message(title: str) -> str:
    return (
        f"{title}\n\n"
        "Gold data unavailable.\n\n"
        "The rest of Jeremy Assistant is still running.\n\n"
        "Reminder:\n"
        "Wait for confirmation. No chasing. Protect capital first."
    )


def _levels(levels: list[float]) -> str:
    if not levels:
        return "• unavailable"
    return "\n".join(f"• {level:,.0f}" for level in levels)


def _nearest(levels: list[float]) -> str:
    if not levels:
        return "unavailable"
    return f"{levels[0]:,.0f}"


def _money(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"${value:,.2f}"


def _percent(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"{value:+.2f}%"


def _price_number(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"{value:,.2f}"


def _number(value: float | None, digits: int) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.{digits}f}"


def _time_label(value) -> str:
    if value is None:
        return "unavailable"
    return value.strftime("%Y-%m-%d %H:%M:%S UTC")


def _status_label(data: MarketData) -> str:
    if data.data_status == "live":
        return "Live spot"
    if data.data_status == "stale":
        return "Stale - alerts disabled"
    if data.data_status == "futures fallback":
        return "Futures fallback - alerts disabled"
    return "Delayed"
