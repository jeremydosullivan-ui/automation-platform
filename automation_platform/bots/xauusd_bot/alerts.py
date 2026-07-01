"""Silent-scan alert logic for the XAUUSD module."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from automation_platform.bots.xauusd_bot.indicators import MarketAnalysis
from automation_platform.bots.xauusd_bot.market_data import MarketData
from automation_platform.shared.config import XauusdConfig


logger = logging.getLogger(__name__)

_last_alert_times: dict[str, datetime] = {}
_last_ema_side: str | None = None


@dataclass(frozen=True)
class Alert:
    """One Telegram alert from the silent scanner."""

    alert_type: str
    message: str


def evaluate_alerts(data: MarketData, analysis: MarketAnalysis, settings: XauusdConfig, now: datetime) -> list[Alert]:
    """Return alerts that should be sent now, respecting cooldowns."""

    logger.info("Running 15-minute scanner.")
    alerts: list[Alert] = []
    if not data.alerts_allowed:
        logger.warning(
            "Skipping XAUUSD alerts because price data is not alert-safe. source=%s status=%s stale=%s spot=%s",
            data.source,
            data.data_status,
            data.is_stale,
            data.is_spot_price,
        )
        return alerts

    level_alert = _level_alert(data, analysis, settings)
    if level_alert and _cooldown_ready("level", settings.level_alert_cooldown_minutes, now):
        alerts.append(level_alert)

    rsi_alert = _rsi_alert(data, analysis, settings)
    if rsi_alert and _cooldown_ready("rsi", settings.rsi_alert_cooldown_minutes, now):
        alerts.append(rsi_alert)

    ema_alert = _ema_shift_alert(data, analysis)
    if ema_alert and _cooldown_ready("ema", settings.ema_alert_cooldown_minutes, now):
        alerts.append(ema_alert)

    volatility_alert = _volatility_alert(analysis)
    if volatility_alert and _cooldown_ready("volatility", settings.volatility_alert_cooldown_minutes, now):
        alerts.append(volatility_alert)

    choppy_alert = _choppy_alert(data, analysis)
    if choppy_alert and _cooldown_ready("choppy", settings.choppy_alert_cooldown_minutes, now):
        alerts.append(choppy_alert)

    for alert in alerts:
        _last_alert_times[alert.alert_type] = now
        logger.info("Alert triggered: %s", alert.alert_type)

    if not alerts:
        logger.info("No XAUUSD alerts triggered.")

    return alerts


def _level_alert(data: MarketData, analysis: MarketAnalysis, settings: XauusdConfig) -> Alert | None:
    price = data.current_price
    if price is None:
        return None

    candidates = [("Support", level) for level in analysis.supports] + [("Resistance", level) for level in analysis.resistances]
    if not candidates:
        return None

    label, level = min(candidates, key=lambda item: abs(price - item[1]))
    distance = abs(price - level)
    if distance > settings.price_level_alert_distance_usd:
        return None

    direction = "Support" if label == "Support" else "Resistance"
    return Alert(
        alert_type="level",
        message=(
            f"⚠️ XAUUSD Near {direction}\n\n"
            f"Price: {_money(price)}\n"
            f"{direction}: {_level(level)}\n"
            f"Distance: ${distance:.2f}\n\n"
            "Do not enter blindly.\n"
            "Wait for rejection, breakout, or retest."
        ),
    )


def _rsi_alert(data: MarketData, analysis: MarketAnalysis, settings: XauusdConfig) -> Alert | None:
    price = data.current_price
    if price is None:
        return None

    for label, timeframe in (("15m", analysis.fifteen_minute), ("1H", analysis.one_hour)):
        rsi = timeframe.rsi14
        if rsi is None:
            continue
        if rsi <= settings.rsi_oversold:
            return Alert(
                alert_type="rsi",
                message=(
                    "📉 XAUUSD Oversold Watch\n\n"
                    f"Price: {_money(price)}\n"
                    f"RSI(14) {label}: {rsi:.1f}\n\n"
                    "Oversold does not mean buy.\n"
                    "Wait for confirmation."
                ),
            )
        if rsi >= settings.rsi_overbought:
            return Alert(
                alert_type="rsi",
                message=(
                    "📈 XAUUSD Overbought Watch\n\n"
                    f"Price: {_money(price)}\n"
                    f"RSI(14) {label}: {rsi:.1f}\n\n"
                    "Overbought does not mean sell.\n"
                    "Wait for confirmation."
                ),
            )

    return None


def _ema_shift_alert(data: MarketData, analysis: MarketAnalysis) -> Alert | None:
    global _last_ema_side

    price = data.current_price
    ema200 = analysis.one_hour.ema200
    if price is None or ema200 is None:
        return None

    side = "above" if price > ema200 else "below"
    if _last_ema_side is None:
        _last_ema_side = side
        return None
    if side == _last_ema_side:
        return None

    _last_ema_side = side
    return Alert(
        alert_type="ema",
        message=(
            "📈 XAUUSD Trend Shift Watch\n\n"
            f"Price crossed {side} 200 EMA on 1H.\n\n"
            f"Price: {_money(price)}\n"
            f"EMA 200: {_money(ema200)}\n\n"
            "Possible trend shift.\n"
            "Wait for candle close confirmation."
        ),
    )


def _volatility_alert(analysis: MarketAnalysis) -> Alert | None:
    atr14 = analysis.one_hour.atr14
    average = analysis.one_hour.recent_atr_average
    if atr14 is None or average is None or atr14 <= average * 1.5:
        return None

    return Alert(
        alert_type="volatility",
        message=(
            "🚫 High Volatility Warning\n\n"
            "XAUUSD volatility is elevated.\n\n"
            f"ATR(14) 1H: {atr14:.1f}\n"
            f"Recent Average ATR: {average:.1f}\n\n"
            "Reduce position size or consider standing aside."
        ),
    )


def _choppy_alert(data: MarketData, analysis: MarketAnalysis) -> Alert | None:
    price = data.current_price
    ema50 = analysis.one_hour.ema50
    ema200 = analysis.one_hour.ema200
    if price is None or ema50 is None or ema200 is None:
        return None

    lower = min(ema50, ema200)
    upper = max(ema50, ema200)
    if not lower < price < upper:
        return None

    return Alert(
        alert_type="choppy",
        message=(
            "🚫 Choppy Market Warning\n\n"
            "Price is between EMA 50 and EMA 200.\n"
            "Trend is unclear.\n\n"
            "Best action: wait."
        ),
    )


def _cooldown_ready(alert_type: str, cooldown_minutes: int, now: datetime) -> bool:
    previous = _last_alert_times.get(alert_type)
    if previous is None:
        return True

    ready_at = previous + timedelta(minutes=cooldown_minutes)
    if now >= ready_at:
        return True

    logger.info("Alert skipped due to cooldown: %s", alert_type)
    return False


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _level(value: float) -> str:
    return f"${value:,.0f}"
