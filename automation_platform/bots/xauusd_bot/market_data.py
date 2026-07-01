"""Market data fetching for XAUUSD awareness.

Current spot price comes from TradingView's scanner endpoint using
`OANDA:XAUUSD`, which closely matches the XAUUSD spot price shown on
TradingView. Yahoo Finance `GC=F` remains as the free candle source for
indicator history, then those candles are shifted onto the spot basis.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)

TRADINGVIEW_SCAN_URL = "https://scanner.tradingview.com/cfd/scan"
TRADINGVIEW_SPOT_SYMBOLS = ["OANDA:XAUUSD", "FX_IDC:XAUUSD", "TVC:GOLD", "FOREXCOM:XAUUSD"]
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
YAHOO_CANDLE_SYMBOL = "GC=F"
DATA_SOURCE_LABEL = "TradingView OANDA:XAUUSD spot with Yahoo GC=F candle history"
STALE_AFTER_MINUTES = 5


@dataclass(frozen=True)
class Candle:
    """One OHLC candle."""

    time: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class SpotQuote:
    """Current spot price metadata."""

    provider: str
    requested_symbol: str
    returned_symbol: str
    price: float
    bid: float | None
    ask: float | None
    daily_change_percent: float | None
    daily_high: float | None
    daily_low: float | None
    previous_close: float | None
    update_mode: str
    provider_timestamp: datetime | None
    received_at: datetime

    @property
    def is_streaming(self) -> bool:
        return self.update_mode.lower() == "streaming"


@dataclass(frozen=True)
class MarketData:
    """All data needed by the XAUUSD module."""

    source: str
    requested_symbol: str
    candle_symbol: str
    current_price: float | None
    previous_close: float | None
    daily_high: float | None
    daily_low: float | None
    daily_change_percent: float | None
    price_timestamp: datetime | None
    provider_timestamp: datetime | None
    current_utc_time: datetime
    data_status: str
    is_stale: bool
    is_spot_price: bool
    update_mode: str
    candle_timeframe_used: str
    candles_15m: list[Candle]
    candles_1h: list[Candle]
    candles_4h: list[Candle]
    candles_1d: list[Candle]

    @property
    def available(self) -> bool:
        return bool(self.current_price and self.candles_1h and self.candles_1d)

    @property
    def alerts_allowed(self) -> bool:
        return self.available and self.is_spot_price and not self.is_stale


def fetch_market_data() -> MarketData | None:
    """Fetch spot price plus candle history.

    Returns `None` if all price sources are unavailable. Callers should show a
    graceful fallback instead of crashing.
    """

    logger.info("Fetching XAUUSD data. Preferred spot source: TradingView scanner.")
    now = datetime.now(timezone.utc)

    try:
        spot_quote = _fetch_tradingview_spot_quote()
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        logger.warning("TradingView XAUUSD spot quote unavailable: %s", exc)
        spot_quote = None

    try:
        candles_15m, price_15m, ts_15m = _fetch_yahoo_candles(interval="15m", range_value="5d")
        candles_1h, price_1h, _ = _fetch_yahoo_candles(interval="60m", range_value="3mo")
        candles_1d, price_1d, _ = _fetch_yahoo_candles(interval="1d", range_value="2y")
    except requests.RequestException as exc:
        logger.warning("XAUUSD candle data unavailable: %s", exc)
        return None
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("XAUUSD candle data parsing failed: %s", exc)
        return None

    yahoo_current = _first_number(price_15m, price_1h, price_1d, _last_close(candles_15m), _last_close(candles_1h))
    if spot_quote:
        current_price = spot_quote.price
        basis_adjustment = current_price - yahoo_current if yahoo_current is not None else 0
        price_timestamp = spot_quote.received_at
        provider_timestamp = spot_quote.provider_timestamp
        previous_close = spot_quote.previous_close
        daily_high = spot_quote.daily_high
        daily_low = spot_quote.daily_low
        daily_change_percent = spot_quote.daily_change_percent
        source = f"{spot_quote.provider} {spot_quote.returned_symbol} spot"
        requested_symbol = spot_quote.requested_symbol
        update_mode = spot_quote.update_mode
        is_spot_price = True
    else:
        current_price = yahoo_current
        basis_adjustment = 0
        price_timestamp = ts_15m
        provider_timestamp = ts_15m
        previous_close, daily_high, daily_low, daily_change_percent = _daily_stats_from_candles(current_price, candles_1d)
        source = "Yahoo Finance GC=F futures fallback"
        requested_symbol = YAHOO_CANDLE_SYMBOL
        update_mode = "delayed/futures"
        is_spot_price = False

    if current_price is None:
        logger.warning("No XAUUSD current price available.")
        return None

    adjusted_15m = _adjust_candles(candles_15m, basis_adjustment)
    adjusted_1h = _adjust_candles(candles_1h, basis_adjustment)
    adjusted_1d = _adjust_candles(candles_1d, basis_adjustment)
    candles_4h = resample_to_4h(adjusted_1h)

    is_stale = _is_stale(price_timestamp, now)
    data_status = _data_status(is_stale=is_stale, is_spot_price=is_spot_price, update_mode=update_mode)

    logger.info(
        "XAUUSD price provider=%s requested_symbol=%s returned_timestamp=%s current_utc=%s returned_price=%s candle_timeframe=%s status=%s",
        source,
        requested_symbol,
        price_timestamp.isoformat() if price_timestamp else "unavailable",
        now.isoformat(),
        f"{current_price:.2f}",
        "15m/1h/1d Yahoo GC=F adjusted to spot basis",
        data_status,
    )
    if provider_timestamp and provider_timestamp != price_timestamp:
        logger.info("XAUUSD provider bar timestamp=%s.", provider_timestamp.isoformat())
    logger.info(
        "Fetched XAUUSD candles: 15m=%s, 1h=%s, 4h=%s, 1d=%s.",
        len(adjusted_15m),
        len(adjusted_1h),
        len(candles_4h),
        len(adjusted_1d),
    )

    return MarketData(
        source=source,
        requested_symbol=requested_symbol,
        candle_symbol=YAHOO_CANDLE_SYMBOL,
        current_price=current_price,
        previous_close=previous_close,
        daily_high=daily_high,
        daily_low=daily_low,
        daily_change_percent=daily_change_percent,
        price_timestamp=price_timestamp,
        provider_timestamp=provider_timestamp,
        current_utc_time=now,
        data_status=data_status,
        is_stale=is_stale,
        is_spot_price=is_spot_price,
        update_mode=update_mode,
        candle_timeframe_used="15m/1h/1d Yahoo GC=F adjusted to spot basis",
        candles_15m=adjusted_15m,
        candles_1h=adjusted_1h,
        candles_4h=candles_4h,
        candles_1d=adjusted_1d,
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


def _fetch_tradingview_spot_quote() -> SpotQuote:
    columns = [
        "name",
        "close",
        "bid",
        "ask",
        "update_mode",
        "change",
        "high",
        "low",
        "time",
    ]
    payload = {
        "symbols": {"tickers": TRADINGVIEW_SPOT_SYMBOLS, "query": {"types": []}},
        "columns": columns,
    }
    received_at = datetime.now(timezone.utc)
    response = _session(retries=1).post(
        TRADINGVIEW_SCAN_URL,
        json=payload,
        timeout=8,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("data") or []
    if not rows:
        raise ValueError("TradingView returned no XAUUSD rows.")

    row = rows[0]
    returned_symbol = row.get("s") or TRADINGVIEW_SPOT_SYMBOLS[0]
    values = row.get("d") or []
    name, close, bid, ask, update_mode, change, high, low, provider_time = values
    price = _first_number(close, bid, ask)
    if price is None:
        raise ValueError("TradingView returned no current XAUUSD price.")

    provider_timestamp = _timestamp_from_seconds(provider_time)
    previous_close = price / (1 + (float(change) / 100)) if change not in (None, 0) else None

    return SpotQuote(
        provider="TradingView scanner",
        requested_symbol=TRADINGVIEW_SPOT_SYMBOLS[0],
        returned_symbol=str(returned_symbol),
        price=float(price),
        bid=_first_number(bid),
        ask=_first_number(ask),
        daily_change_percent=_first_number(change),
        daily_high=_first_number(high),
        daily_low=_first_number(low),
        previous_close=previous_close,
        update_mode=str(update_mode or "unknown"),
        provider_timestamp=provider_timestamp,
        received_at=received_at,
    )


def _fetch_yahoo_candles(interval: str, range_value: str) -> tuple[list[Candle], float | None, datetime | None]:
    session = _session(retries=2)
    params = {
        "interval": interval,
        "range": range_value,
        "includePrePost": "false",
    }

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = session.get(YAHOO_CHART_URL, params=params, timeout=12)
            response.raise_for_status()
            payload = response.json()
            candles, price = _parse_yahoo_chart(payload)
            if candles:
                return candles, price, candles[-1].time
            raise ValueError(f"Yahoo returned no {interval} candles.")
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            last_error = exc
            logger.warning("Attempt %s failed for Yahoo %s %s candles: %s", attempt, YAHOO_CANDLE_SYMBOL, interval, exc)
            time.sleep(attempt)

    if isinstance(last_error, requests.RequestException):
        raise last_error
    raise ValueError(last_error or f"Unable to fetch {interval} candles.")


def _session(*, retries: int) -> requests.Session:
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        respect_retry_after_header=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "automation-platform/1.0"})
    return session


def _parse_yahoo_chart(payload: dict[str, Any]) -> tuple[list[Candle], float | None]:
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


def _daily_stats_from_candles(current_price: float | None, candles: list[Candle]) -> tuple[float | None, float | None, float | None, float | None]:
    if len(candles) < 2:
        return None, None, None, None

    latest_daily = candles[-1]
    previous_daily = candles[-2]
    previous_close = previous_daily.close
    daily_high = latest_daily.high
    daily_low = latest_daily.low
    daily_change_percent = None
    if current_price and previous_close:
        daily_change_percent = ((current_price - previous_close) / previous_close) * 100
    return previous_close, daily_high, daily_low, daily_change_percent


def _adjust_candles(candles: list[Candle], adjustment: float) -> list[Candle]:
    if adjustment == 0:
        return candles
    return [
        Candle(
            time=candle.time,
            open=candle.open + adjustment,
            high=candle.high + adjustment,
            low=candle.low + adjustment,
            close=candle.close + adjustment,
        )
        for candle in candles
    ]


def _is_stale(price_timestamp: datetime | None, now: datetime) -> bool:
    if price_timestamp is None:
        return True
    return now - price_timestamp > timedelta(minutes=STALE_AFTER_MINUTES)


def _data_status(*, is_stale: bool, is_spot_price: bool, update_mode: str) -> str:
    if is_stale:
        return "stale"
    if not is_spot_price:
        return "futures fallback"
    if update_mode.lower() == "streaming":
        return "live"
    return "delayed"


def _timestamp_from_seconds(value: Any) -> datetime | None:
    numeric = _first_number(value)
    if numeric is None:
        return None
    try:
        return datetime.fromtimestamp(numeric, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


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
