"""Free economic calendar support for XAUUSD awareness.

The primary no-key source is the public Forex Factory/Fair Economy weekly JSON
feed. Official BEA, Census, and Federal Reserve pages are used as supplemental
sources for US releases that are easy to parse reliably.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from automation_platform.shared.config import PlatformConfig


logger = logging.getLogger(__name__)

CALENDAR_PROVIDER_LABEL = "Free calendar: Forex Factory feed + official US sources"
FAIR_ECONOMY_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
BEA_SCHEDULE_URL = "https://www.bea.gov/news/schedule"
CENSUS_CALENDAR_URL = "https://www.census.gov/economic-indicators/calendar-listview.html"
FED_FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

NEW_YORK_TZ = ZoneInfo("America/New_York")
HIGH_MEDIUM_IMPACTS = {"high", "medium"}
CALENDAR_CACHE_MINUTES = 15

XAUUSD_EVENT_KEYWORDS = [
    "cpi",
    "consumer price",
    "ppi",
    "producer price",
    "non farm",
    "nonfarm",
    "nfp",
    "employment change",
    "employment situation",
    "unemployment",
    "jobless claims",
    "initial claims",
    "ism",
    "pmi",
    "gdp",
    "gross domestic",
    "retail sales",
    "fomc",
    "federal reserve",
    "fed",
    "powell",
    "treasury",
    "yield",
    "personal consumption",
    "pce",
    "personal income",
    "durable goods",
]

_calendar_cache: tuple[datetime, EconomicCalendarResult] | None = None


@dataclass(frozen=True)
class EconomicEvent:
    """One economic calendar event relevant to gold."""

    local_time: datetime
    country: str
    event: str
    impact: str
    source: str
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

    global _calendar_cache

    now = datetime.now(platform_config.timezone)
    if _calendar_cache:
        cached_at, cached_result = _calendar_cache
        if cached_at.date() == now.date() and now - cached_at < timedelta(minutes=CALENDAR_CACHE_MINUTES):
            logger.info("Using cached economic calendar result.")
            return cached_result

    logger.info("Fetching economic calendar from %s.", CALENDAR_PROVIDER_LABEL)
    all_events: list[EconomicEvent] = []
    successful_sources = 0

    for source_name, fetcher in (
        ("Forex Factory/Fair Economy", _fetch_fair_economy_events),
        ("BEA release schedule", _fetch_bea_events),
        ("Census economic indicators", _fetch_census_events),
        ("Federal Reserve FOMC calendar", _fetch_fomc_events),
    ):
        try:
            events = fetcher(platform_config)
        except requests.RequestException as exc:
            logger.warning("%s calendar unavailable: %s", source_name, exc)
            continue
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            logger.warning("%s calendar parsing failed: %s", source_name, exc)
            continue

        successful_sources += 1
        logger.info("%s events fetched: %s.", source_name, len(events))
        all_events.extend(events)

    if successful_sources == 0:
        logger.warning("Economic calendar fallback used: no free providers were available.")
        return EconomicCalendarResult(events=[], available=False, provider=CALENDAR_PROVIDER_LABEL)

    filtered = _filter_relevant_events(all_events, platform_config.timezone)
    filtered = _dedupe_events(filtered)
    logger.info("Economic calendar events filtered for XAUUSD relevance: %s.", len(filtered))
    result = EconomicCalendarResult(events=filtered, available=True, provider=CALENDAR_PROVIDER_LABEL)
    _calendar_cache = (now, result)
    return result


def format_events_for_message(result: EconomicCalendarResult) -> str:
    """Format events for Telegram messages."""

    if not result.available:
        return "Market events unavailable."
    if not result.events:
        return "No high/medium XAUUSD-relevant US events found today."

    lines: list[str] = []
    for event in result.events[:8]:
        lines.append(
            "\n".join(
                [
                    f"{event.local_time.strftime('%H:%M')} Bangkok",
                    event.event,
                    f"{_impact_stars(event.impact)} {_impact_label(event.impact)} Impact",
                ]
            )
        )
    return "\n\n".join(lines)


def _fetch_fair_economy_events(platform_config: PlatformConfig) -> list[EconomicEvent]:
    response = _session().get(FAIR_ECONOMY_URL, timeout=6)
    response.raise_for_status()
    payload = response.json()

    events: list[EconomicEvent] = []
    for item in payload:
        if str(item.get("country") or "").upper() != "USD":
            continue
        title = str(item.get("title") or "")
        event_time = datetime.fromisoformat(str(item.get("date")).replace("Z", "+00:00"))
        impact = str(item.get("impact") or "").lower()
        events.append(
            EconomicEvent(
                local_time=event_time.astimezone(platform_config.timezone),
                country="US",
                event=title,
                impact=impact,
                source="Forex Factory/Fair Economy",
                estimate=_optional_text(item.get("forecast")),
                previous=_optional_text(item.get("previous")),
            )
        )

    return events


def _fetch_bea_events(platform_config: PlatformConfig) -> list[EconomicEvent]:
    response = _session().get(BEA_SCHEDULE_URL, timeout=6)
    response.raise_for_status()
    text = response.text
    current_year = datetime.now(platform_config.timezone).year

    rows = re.findall(r"<tr[^>]*scheduled-releases[^>]*>(.*?)</tr>", text, flags=re.IGNORECASE | re.DOTALL)
    events: list[EconomicEvent] = []
    for row in rows:
        date_match = re.search(r'<div class="release-date">([^<]+)</div>', row, flags=re.IGNORECASE)
        time_match = re.search(r'<small[^>]*>([^<]+)</small>', row, flags=re.IGNORECASE)
        title_match = re.search(r'<td class="release-title[^"]*"[^>]*>(.*?)</td>', row, flags=re.IGNORECASE | re.DOTALL)
        if not (date_match and time_match and title_match):
            continue

        title = _clean_html(title_match.group(1))
        try:
            event_time = _parse_month_day_time(date_match.group(1), time_match.group(1), current_year, NEW_YORK_TZ)
        except ValueError:
            logger.info("Skipping BEA row with unparseable date/time: %s", title)
            continue
        events.append(
            EconomicEvent(
                local_time=event_time.astimezone(platform_config.timezone),
                country="US",
                event=title,
                impact=_impact_for_title(title),
                source="BEA",
            )
        )

    return events


def _fetch_census_events(platform_config: PlatformConfig) -> list[EconomicEvent]:
    response = _session().get(CENSUS_CALENDAR_URL, timeout=6)
    response.raise_for_status()
    text = response.text

    rows = re.findall(r"<tr[^>]*height=\"20\"[^>]*>(.*?)</tr>", text, flags=re.IGNORECASE | re.DOTALL)
    events: list[EconomicEvent] = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
        if len(cells) < 3:
            continue

        title = _clean_html(cells[0])
        date_text = _clean_html(cells[1])
        time_text = _clean_html(cells[2])
        try:
            event_time = _parse_full_date_time(date_text, time_text, NEW_YORK_TZ)
        except ValueError:
            logger.info("Skipping Census row with unparseable date/time: %s", title)
            continue
        events.append(
            EconomicEvent(
                local_time=event_time.astimezone(platform_config.timezone),
                country="US",
                event=title,
                impact=_impact_for_title(title),
                source="Census",
            )
        )

    return events


def _fetch_fomc_events(platform_config: PlatformConfig) -> list[EconomicEvent]:
    response = _session().get(FED_FOMC_URL, timeout=6)
    response.raise_for_status()
    text = response.text
    year = datetime.now(platform_config.timezone).year

    section_match = re.search(
        rf"{year} FOMC Meetings</a></h4></div>(.*?)(?:<div class=\"panel panel-default\"><div class=\"panel-heading\"><h4>|</body>)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not section_match:
        return []

    rows = re.findall(r'<div class="[^"]*row fomc-meeting[^"]*"[^>]*>(.*?)(?=<div class="[^"]*row fomc-meeting|</div>\s*</div>)', section_match.group(1), flags=re.IGNORECASE | re.DOTALL)
    events: list[EconomicEvent] = []
    current_month: str | None = None
    for row in rows:
        month_match = re.search(r'fomc-meeting__month[^>]*><strong>([^<]+)</strong>', row, flags=re.IGNORECASE)
        if month_match:
            current_month = _clean_html(month_match.group(1))

        date_match = re.search(r'fomc-meeting__date[^>]*>([^<]+)</div>', row, flags=re.IGNORECASE)
        if not current_month or not date_match:
            continue

        day = _last_day_from_range(date_match.group(1))
        try:
            event_time = _parse_month_day_time(f"{current_month} {day}", "2:00 PM", year, NEW_YORK_TZ)
        except ValueError:
            logger.info("Skipping FOMC row with unparseable date/time: %s %s", current_month, date_match.group(1))
            continue
        events.append(
            EconomicEvent(
                local_time=event_time.astimezone(platform_config.timezone),
                country="US",
                event="FOMC Statement / Rate Decision",
                impact="high",
                source="Federal Reserve",
            )
        )

    return events


def _filter_relevant_events(events: list[EconomicEvent], timezone: ZoneInfo) -> list[EconomicEvent]:
    today = datetime.now(timezone).date()
    filtered: list[EconomicEvent] = []
    for event in events:
        if event.local_time.date() != today:
            continue
        if event.impact.lower() not in HIGH_MEDIUM_IMPACTS:
            continue
        if not _is_gold_relevant(event.event):
            continue
        filtered.append(event)

    return sorted(filtered, key=lambda item: item.local_time)


def _dedupe_events(events: list[EconomicEvent]) -> list[EconomicEvent]:
    seen: set[tuple[str, str]] = set()
    unique: list[EconomicEvent] = []
    for event in events:
        key = (event.local_time.strftime("%Y-%m-%d %H:%M"), _normalize_title(event.event))
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return unique


def _is_gold_relevant(name: str) -> bool:
    lowered = name.lower()
    return any(keyword in lowered for keyword in XAUUSD_EVENT_KEYWORDS)


def _impact_for_title(title: str) -> str:
    lowered = title.lower()
    high_keywords = ["gdp", "gross domestic", "personal income", "pce", "retail sales", "fomc"]
    if any(keyword in lowered for keyword in high_keywords):
        return "high"
    medium_keywords = ["durable goods", "trade", "inventories", "construction", "housing", "new residential"]
    if any(keyword in lowered for keyword in medium_keywords):
        return "medium"
    return "low"


def _parse_month_day_time(month_day: str, time_text: str, year: int, timezone: ZoneInfo) -> datetime:
    cleaned = f"{month_day.strip()}, {year} {time_text.strip()}"
    return datetime.strptime(cleaned, "%B %d, %Y %I:%M %p").replace(tzinfo=timezone)


def _parse_full_date_time(date_text: str, time_text: str, timezone: ZoneInfo) -> datetime:
    cleaned = f"{date_text.strip()} {time_text.strip()}"
    return datetime.strptime(cleaned, "%B %d, %Y %I:%M %p").replace(tzinfo=timezone)


def _last_day_from_range(raw: str) -> int:
    cleaned = re.sub(r"[^0-9\\-]", "", raw)
    if "-" in cleaned:
        return int(cleaned.split("-")[-1])
    return int(cleaned)


def _session() -> requests.Session:
    retry = Retry(
        total=1,
        connect=1,
        read=1,
        backoff_factor=0.2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "automation-platform/1.0"})
    return session


def _clean_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _impact_stars(impact: str) -> str:
    if impact.lower() == "high":
        return "⭐⭐⭐"
    if impact.lower() == "medium":
        return "⭐⭐"
    return "⭐"


def _impact_label(impact: str) -> str:
    return impact.capitalize() if impact else "Unknown"


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.lower()).strip()


def _optional_text(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
