"""Indicator and market-structure calculations for XAUUSD."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from automation_platform.bots.xauusd_bot.market_data import Candle, MarketData


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimeframeAnalysis:
    """Indicator values for one timeframe."""

    trend: str
    ema50: float | None
    ema200: float | None
    rsi14: float | None
    atr14: float | None
    recent_atr_average: float | None


@dataclass(frozen=True)
class MarketAnalysis:
    """The calculated XAUUSD view used by messages and alerts."""

    one_hour: TimeframeAnalysis
    four_hour: TimeframeAnalysis
    one_day: TimeframeAnalysis
    fifteen_minute: TimeframeAnalysis
    supports: list[float]
    resistances: list[float]
    market_condition: str


def analyze_market(data: MarketData) -> MarketAnalysis:
    """Calculate indicators, trends, and simple support/resistance."""

    logger.info("Calculating indicators.")
    fifteen_minute = analyze_timeframe(data.candles_15m)
    one_hour = analyze_timeframe(data.candles_1h)
    four_hour = analyze_timeframe(data.candles_4h)
    one_day = analyze_timeframe(data.candles_1d)

    logger.info("Detecting support/resistance.")
    supports, resistances = detect_support_resistance(
        current_price=data.current_price,
        candles=data.candles_1h[-150:] + data.candles_4h[-100:],
    )

    condition = market_condition(data.current_price, one_hour, four_hour, one_day)
    return MarketAnalysis(
        one_hour=one_hour,
        four_hour=four_hour,
        one_day=one_day,
        fifteen_minute=fifteen_minute,
        supports=supports,
        resistances=resistances,
        market_condition=condition,
    )


def analyze_timeframe(candles: list[Candle]) -> TimeframeAnalysis:
    closes = [candle.close for candle in candles]
    ema50_values = ema(closes, 50)
    ema200_values = ema(closes, 200)
    rsi_values = rsi(closes, 14)
    atr_values = atr(candles, 14)

    ema50 = _last(ema50_values)
    ema200 = _last(ema200_values)
    current_price = closes[-1] if closes else None
    trend = trend_label(current_price, ema50, ema200)
    recent_atr_average = _average([value for value in atr_values[-50:] if value is not None])

    return TimeframeAnalysis(
        trend=trend,
        ema50=ema50,
        ema200=ema200,
        rsi14=_last(rsi_values),
        atr14=_last(atr_values),
        recent_atr_average=recent_atr_average,
    )


def ema(values: list[float], period: int) -> list[float | None]:
    if not values:
        return []

    output: list[float | None] = [None] * len(values)
    if len(values) < period:
        return output

    multiplier = 2 / (period + 1)
    current = sum(values[:period]) / period
    output[period - 1] = current

    for index in range(period, len(values)):
        current = (values[index] - current) * multiplier + current
        output[index] = current

    return output


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    output: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return output

    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    output[period] = _rsi_from_average(average_gain, average_loss)

    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0)
        loss = abs(min(change, 0))
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
        output[index] = _rsi_from_average(average_gain, average_loss)

    return output


def atr(candles: list[Candle], period: int = 14) -> list[float | None]:
    output: list[float | None] = [None] * len(candles)
    if len(candles) <= period:
        return output

    true_ranges: list[float] = []
    for index, candle in enumerate(candles):
        if index == 0:
            true_ranges.append(candle.high - candle.low)
            continue
        previous_close = candles[index - 1].close
        true_ranges.append(
            max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        )

    current_atr = sum(true_ranges[1 : period + 1]) / period
    output[period] = current_atr
    for index in range(period + 1, len(candles)):
        current_atr = ((current_atr * (period - 1)) + true_ranges[index]) / period
        output[index] = current_atr

    return output


def trend_label(price: float | None, ema50: float | None, ema200: float | None) -> str:
    if price is None or ema50 is None or ema200 is None:
        return "Neutral"
    if price > ema50 > ema200:
        return "Bullish"
    if price < ema50 < ema200:
        return "Bearish"
    return "Neutral"


def detect_support_resistance(current_price: float | None, candles: list[Candle]) -> tuple[list[float], list[float]]:
    if current_price is None or len(candles) < 7:
        return [], []

    swing_lows: list[float] = []
    swing_highs: list[float] = []
    for index in range(2, len(candles) - 2):
        window = candles[index - 2 : index + 3]
        candle = candles[index]
        if candle.low == min(item.low for item in window):
            swing_lows.append(candle.low)
        if candle.high == max(item.high for item in window):
            swing_highs.append(candle.high)

    supports = _nearest_levels([level for level in swing_lows if level < current_price], current_price, below=True)
    resistances = _nearest_levels([level for level in swing_highs if level > current_price], current_price, below=False)
    return supports[:2], resistances[:2]


def market_condition(
    current_price: float | None,
    one_hour: TimeframeAnalysis,
    four_hour: TimeframeAnalysis,
    one_day: TimeframeAnalysis,
) -> str:
    if current_price and one_hour.ema50 and one_hour.ema200:
        lower = min(one_hour.ema50, one_hour.ema200)
        upper = max(one_hour.ema50, one_hour.ema200)
        if lower < current_price < upper:
            return "🔴 High Risk / Choppy"

    if one_hour.atr14 and one_hour.recent_atr_average and one_hour.atr14 > one_hour.recent_atr_average * 1.5:
        return "🔴 High Risk / Choppy"

    trends = [one_hour.trend, four_hour.trend, one_day.trend]
    if trends.count("Bullish") >= 2 or trends.count("Bearish") >= 2:
        return "🟢 Trending"

    return "🟡 Mixed"


def _nearest_levels(levels: list[float], current_price: float, *, below: bool) -> list[float]:
    rounded = sorted({_round_level(level) for level in levels}, reverse=below)
    rounded = [level for level in rounded if (level < current_price if below else level > current_price)]
    rounded.sort(key=lambda level: abs(current_price - level))
    return rounded


def _round_level(value: float) -> float:
    return round(value)


def _rsi_from_average(average_gain: float, average_loss: float) -> float:
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _last(values: list[float | None]) -> float | None:
    for value in reversed(values):
        if value is not None:
            return value
    return None
