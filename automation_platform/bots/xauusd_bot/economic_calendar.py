"""Economic calendar support for XAUUSD awareness.

Version 1 uses Finnhub's economic calendar endpoint when
`ECONOMIC_CALENDAR_API_KEY` is configured. Without a key, the module returns a
clear fallback and the rest of the bot keeps working.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from automation_platform.shared.config import PlatformConfig


logger = logging.getLogger(__name__)

CALENDAR_PROVIDER_LABEL = "Finnhub Economic Calendar"
FINNHUB_CALENDAR_URL = "https://finnhub.io/api/v1/calendar/economic"

RELEVANT_COUNTRIES = {"US", "United States"}
HIGH_MEDIUM_IMPACTS = {"high", "medium"}
XAUUSD_EVENT_KEYWORDS = [
    "cpi",
    "consumer price",
    "ppi",
    "producer price",
    "non farm",
    "nonfarm",
    "nfp",
    "unemployment",
    "jobless claims",
    "initial claims",
    "ism",
    "pmi",
    "gdp",
    "retail sales",
    "fomc",
    "federal reserve",
    "fed",
    "powell",
    "treasury",
    "yield",
    "personal consumption",
    "pce",
]


@dataclass(frozen=True)
class EconomicEvent:
    """One economic calendar event relevant to gold."""

    local_time: datetime
    country: str
    event: str
    impact: str
    actual: str | None = None
    estimate: str | None = None
    previous: str | None = None


@dataclass(frozen=True)
class EconomicCalendarResult:
    """Calendar lookup result with enough detail for graceful messages."""

    events: list[EconomicEvent]
    available: bool
    provider: str


def get_todays_xauusd_events(platform_config: PlatformConfig) -> EconomicCalendarResult:
    """Fetch and filter today's high/medium impact gold-relevant events."""

    token = platform_config.xauusd.economic_calendar_api_key
    if not token:
        logger.info("Economic calendar fallback used: ECONOMIC_CALENDAR_API_KEY is not configured.")
        return EconomicCalendarResult(events=[], available=False, provider=CALENDAR_PROVIDER_LABEL)

    logger.info("Fetching economic calendar from %s.", CALENDAR_PROVIDER_LABEL)
    try:
        events = _fetch_finnhub_events(platform_config, token)
    except requests.RequestException as exc:
        logger.warning("Economic calendar unavailable: %s", exc)
        return EconomicCalendarResult(events=[], available=False, provider=CALENDAR_PROVIDER_LABEL)
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Economic calendar parsing failed: %s", exc)
        return EconomicCalendarResult(events=[], available=False, provider=CALENDAR_PROVIDER_LABEL)

    logger.info("Economic calendar events fetched: %s.", len(events))
    filtered = _filter_relevant_events(events, platform_config.timezone)
    logger.info("Economic calendar events filtered for XAUUSD relevance: %s.", len(filtered))
    return EconomicCalendarResult(events=filtered, available=True, provider=CALENDAR_PROVIDER_LABEL)


def format_events_for_message(result: EconomicCalendarResult) -> str:
    """Format events for Telegram messages."""

    if not result.available:
        return "Market events unavailable."
    if not result.events:
        return "No high/medium XAUUSD-relevant US events found today."

    lines: list[str] = []
    for event in result.events[:6]:
        lines.append(
            "\n".join(
                [
                    f"{event.local_time.strftime('%H:%M')} Bangkok",
                    f"{event.event}",
                    f"{_impact_stars(event.impact)} {_impact_label(event.impact)} Impact",
                ]
            )
        )
    return "\n\n".join(lines)


def _fetch_finnhub_events(platform_config: PlatformConfig, token: str) -> list[EconomicEvent]:
    local_day = datetime.now(platform_config.timezone).date()
    start_day = local_day - timedelta(days=1)
    end_day = local_day + timedelta(days=1)
    params = {
        "from": start_day.isoformat(),
        "to": end_day.isoformat(),
        "token": token,
    }

    response = _session().get(FINNHUB_CALENDAR_URL, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()
    raw_events = payload.get("economicCalendar") or []
    return [_event_from_payload(item, platform_config.timezone) for item in raw_events]


def _event_from_payload(item: dict, timezone: ZoneInfo) -> EconomicEvent:
    event_time = _parse_event_time(str(item.get("time") or ""), timezone)
    return EconomicEvent(
        local_time=event_time.astimezone(timezone),
        country=str(item.get("country") or ""),
        event=str(item.get("event") or "Unknown event"),
        impact=str(item.get("impact") or "").lower(),
        actual=_optional_text(item.get("actual")),
        estimate=_optional_text(item.get("estimate")),
        previous=_optional_text(item.get("prev")),
    )


def _parse_event_time(raw: str, timezone: ZoneInfo) -> datetime:
    if not raw:
        return datetime.combine(date.today(), time.min, tzinfo=timezone)

    cleaned = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        if len(raw) == 10:
            parsed = datetime.strptime(raw, "%Y-%m-%d")
        else:
            parsed = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")

    if parsed.tzinfo is None:
        # Finnhub calendar times are treated as UTC when no timezone is present.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _filter_relevant_events(events: list[EconomicEvent], timezone: ZoneInfo) -> list[EconomicEvent]:
    today = datetime.now(timezone).date()
    filtered: list[EconomicEvent] = []
    for event in events:
        if event.local_time.date() != today:
            continue
        if event.country not in RELEVANT_COUNTRIES:
            continue
        if event.impact.lower() not in HIGH_MEDIUM_IMPACTS:
            continue
        if not _is_gold_relevant(event.event):
            continue
        filtered.append(event)

    return sorted(filtered, key=lambda item: item.local_time)


def _is_gold_relevant(name: str) -> bool:
    lowered = name.lower()
    return any(keyword in lowered for keyword in XAUUSD_EVENT_KEYWORDS)


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


def _impact_stars(impact: str) -> str:
    if impact.lower() == "high":
        return "⭐⭐⭐"
    if impact.lower() == "medium":
        return "⭐⭐"
    return "⭐"


def _impact_label(impact: str) -> str:
    return impact.capitalize() if impact else "Unknown"


def _optional_text(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
