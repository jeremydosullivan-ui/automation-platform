"""Message builder for the morning briefing bot."""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests


logger = logging.getLogger(__name__)

BANGKOK_LATITUDE = 13.7563
BANGKOK_LONGITUDE = 100.5018
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DUMMYJSON_QUOTE_URL = "https://dummyjson.com/quotes/random"
YAHOO_GOLD_URL = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 PersonalAutomationPlatform/1.0",
}

WEATHER_CODE_SUMMARIES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Heavy rain showers",
    95: "Thunderstorm",
}

FALLBACK_QUOTES = [
    ("The obstacle is the way.", "Marcus Aurelius"),
    ("Do what you can, with what you have, where you are.", "Theodore Roosevelt"),
    ("Small steps every day add up to big results.", None),
]


def build_morning_message(timezone: ZoneInfo) -> str:
    """Build the complete morning briefing.

    Each section has its own fallback so one failed API does not prevent the
    Telegram message from being sent.
    """

    now = datetime.now(timezone)

    return "\n".join(
        [
            "☀️ Good Morning Jeremy!",
            "",
            f"📅 {now.strftime('%A, %d %B %Y')}",
            "",
            "🌤 Weather (Bangkok)",
            _weather_section(timezone),
            "",
            "🧠 Quote of the Day",
            _quote_section(),
            "",
            "🥇 Gold (XAUUSD)",
            _gold_section(),
            "",
            "☕ Have a great day!",
        ]
    )


def _weather_section(timezone: ZoneInfo) -> str:
    try:
        payload = _get_json(
            OPEN_METEO_URL,
            params={
                "latitude": BANGKOK_LATITUDE,
                "longitude": BANGKOK_LONGITUDE,
                "current": "temperature_2m,weather_code",
                "hourly": "precipitation_probability,precipitation,rain",
                "forecast_days": 1,
                "timezone": "Asia/Bangkok",
            },
        )
        current = payload.get("current", {})
        temperature = current.get("temperature_2m")
        weather_code = current.get("weather_code")
        summary = WEATHER_CODE_SUMMARIES.get(weather_code, "Weather summary unavailable")
        rain = _rain_forecast(payload.get("hourly", {}), timezone)

        temperature_line = f"{float(temperature):.0f}°C" if temperature is not None else "Temperature unavailable"
        return "\n".join([temperature_line, summary, rain])
    except Exception:
        logger.exception("Weather section failed.")
        return "Weather data unavailable."


def _quote_section() -> str:
    try:
        payload = _get_json(DUMMYJSON_QUOTE_URL)
        quote = payload.get("quote")
        author = payload.get("author")
        if quote and author:
            return f'"{quote}"\n- {author}'
        if quote:
            return f'"{quote}"'
    except Exception:
        logger.warning("Quote API failed; using fallback quote.")

    quote, author = random.choice(FALLBACK_QUOTES)
    return f'"{quote}"\n- {author}' if author else f'"{quote}"'


def _gold_section() -> str:
    try:
        payload = _get_json(YAHOO_GOLD_URL, params={"range": "2d", "interval": "1d"})
        result = payload.get("chart", {}).get("result", [])
        if not result:
            return "Gold data unavailable."

        meta = result[0].get("meta", {})
        price = _to_float(meta.get("regularMarketPrice"))
        previous_close = _to_float(meta.get("chartPreviousClose"))
        if price is None:
            return "Gold data unavailable."

        lines = [f"Current Price: {price:,.2f}"]
        if previous_close and previous_close > 0:
            change = ((price - previous_close) / previous_close) * 100
            sign = "+" if change >= 0 else ""
            lines.append(f"Daily Change: {sign}{change:.2f}%")
        return "\n".join(lines)
    except Exception:
        logger.warning("Gold section failed.")
        return "Gold data unavailable."


def _rain_forecast(hourly: dict[str, Any], timezone: ZoneInfo) -> str:
    now = datetime.now(timezone)
    times = hourly.get("time", [])
    probabilities = hourly.get("precipitation_probability", [])
    rain_amounts = hourly.get("rain", [])
    precipitation_amounts = hourly.get("precipitation", [])

    for index, raw_time in enumerate(times):
        forecast_time = datetime.fromisoformat(raw_time).replace(tzinfo=timezone)
        if forecast_time < now:
            continue

        probability = _number_at(probabilities, index)
        rain_amount = _number_at(rain_amounts, index)
        precipitation_amount = _number_at(precipitation_amounts, index)
        if probability >= 50 or rain_amount >= 0.2 or precipitation_amount >= 0.2:
            return f"Rain expected after {_format_hour(forecast_time)}"

    return "No significant rain expected today"


def _get_json(url: str, *, params: dict[str, Any] | None = None, attempts: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=12)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            last_error = error
            logger.warning("API request failed on attempt %s/%s: %s", attempt, attempts, error)
            if attempt < attempts:
                time.sleep(attempt)

    raise RuntimeError(f"API request failed after {attempts} attempts: {url}") from last_error


def _number_at(values: list[Any], index: int) -> float:
    try:
        value = values[index]
    except IndexError:
        return 0
    return _to_float(value) or 0


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_hour(value: datetime) -> str:
    suffix = "am" if value.hour < 12 else "pm"
    display_hour = value.hour % 12 or 12
    return f"{display_hour}{suffix}"

