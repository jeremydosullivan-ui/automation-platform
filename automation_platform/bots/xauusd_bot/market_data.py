"""Market data fetching for XAUUSD awareness.

Version 1 uses Yahoo Finance's free chart endpoint with the `GC=F` gold
futures symbol as a practical XAUUSD proxy. It requires no API key.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
DATA_SOURCE_LABEL = "Yahoo Finance GC=F gold futures proxy"


@dataclass(frozen=True)
class Candle:
    """One OHLC candle."""

    time: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class MarketData:
    """All candle data needed by the XAUUSD module."""

    source: str
    current_price: float | None
    previous_close: float | None
    daily_high: float | None
    daily_low: float | None
    daily_change_percent: float | None
    candles_15m: list[Candle]
    candles_1h: list[Candle]
    candles_4h: list[Candle]
    candles_1d: list[Candle]

    @property
    def available(self) -> bool:
        return bool(self.current_price and self.candles_1h and self.candles_1d)


def fetch_market_data() -> MarketData | None:
    """Fetch candles for the XAUUSD module.

    Returns `None` if the source is unavailable. Callers should show a graceful
    fallback instead of crashing.
    """

    logger.info("Fetching XAUUSD data from %s.", DATA_SOURCE_LABEL)

    try:
        candles_15m, price_15m = _fetch_candles(interval="15m", range_value="5d")
        candles_1h, price_1h = _fetch_candles(interval="60m", range_value="3mo")
        candles_1d, price_1d = _fetch_candles(interval="1d", range_value="2y")
    except requests.RequestException as exc:
        logger.warning("XAUUSD data unavailable: %s", exc)
        return None
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("XAUUSD data parsing failed: %s", exc)
        return None

    candles_4h = resample_to_4h(candles_1h)
    current_price = _first_number(price_15m, price_1h, price_1d, _last_close(candles_15m), _last_close(candles_1h))

    previous_close = None
    daily_high = None
    daily_low = None
    daily_change_percent = None
    if len(candles_1d) >= 2:
        latest_daily = candles_1d[-1]
        previous_daily = candles_1d[-2]
        previous_close = previous_daily.close
        daily_high = latest_daily.high
        daily_low = latest_daily.low
        if current_price and previous_close:
            daily_change_percent = ((current_price - previous_close) / previous_close) * 100

    logger.info(
        "Fetched XAUUSD candles: 15m=%s, 1h=%s, 4h=%s, 1d=%s.",
        len(candles_15m),
        len(candles_1h),
        len(candles_4h),
        len(candles_1d),
    )

    return MarketData(
        source=DATA_SOURCE_LABEL,
        current_price=current_price,
        previous_close=previous_close,
        daily_high=daily_high,
        daily_low=daily_low,
        daily_change_percent=daily_change_percent,
        candles_15m=candles_15m,
        candles_1h=candles_1h,
        candles_4h=candles_4h,
        candles_1d=candles_1d,
    )


def resample_to_4h(candles: list[Candle]) -> list[Candle]:
    """Build simple 4H candles from 1H candles."""

    if not candles:
        return []

    groups: dict[datetime, list[Candle]] = {}
    for candle in candles:
        bucket_hour = candle.time.hour - (candle.time.hour % 4)
        bucket_time = candle.time.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
        groups.setdefault(bucket_time, []).append(candle)

    resampled: list[Candle] = []
    for bucket_time in sorted(groups):
        group = groups[bucket_time]
        if not group:
            continue
        resampled.append(
            Candle(
                time=bucket_time,
                open=group[0].open,
                high=max(candle.high for candle in group),
                low=min(candle.low for candle in group),
                close=group[-1].close,
            )
        )

    return resampled


def _fetch_candles(interval: str, range_value: str) -> tuple[list[Candle], float | None]:
    session = _session()
    params = {
        "interval": interval,
        "range": range_value,
        "includePrePost": "false",
    }

    # The adapter retries network/server issues. This loop also covers brief
    # empty responses, which can happen with free public endpoints.
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = session.get(YAHOO_CHART_URL, params=params, timeout=15)
            response.raise_for_status()
            payload = response.json()
            candles, price = _parse_chart(payload)
            if candles:
                return candles, price
            raise ValueError(f"Yahoo returned no {interval} candles.")
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            last_error = exc
            logger.warning("Attempt %s failed for XAUUSD %s candles: %s", attempt, interval, exc)
            time.sleep(attempt)

    if isinstance(last_error, requests.RequestException):
        raise last_error
    raise ValueError(last_error or f"Unable to fetch {interval} candles.")


def _session() -> requests.Session:
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "automation-platform/1.0"})
    return session


def _parse_chart(payload: dict[str, Any]) -> tuple[list[Candle], float | None]:
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    meta = result.get("meta", {})

    candles: list[Candle] = []
    for index, timestamp in enumerate(timestamps):
        open_price = _at(quote.get("open"), index)
        high = _at(quote.get("high"), index)
        low = _at(quote.get("low"), index)
        close = _at(quote.get("close"), index)
        if None in (open_price, high, low, close):
            continue

        candles.append(
            Candle(
                time=datetime.fromtimestamp(timestamp, tz=timezone.utc),
                open=float(open_price),
                high=float(high),
                low=float(low),
                close=float(close),
            )
        )

    return candles, _first_number(meta.get("regularMarketPrice"), meta.get("chartPreviousClose"))


def _at(values: list[float | None] | None, index: int) -> float | None:
    if not values or index >= len(values):
        return None
    return values[index]


def _last_close(candles: list[Candle]) -> float | None:
    return candles[-1].close if candles else None


def _first_number(*values: Any) -> float | None:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None
