"""Logging setup for the automation platform."""

from __future__ import annotations

import logging


def setup_logging() -> None:
    """Configure readable console logs for Railway and local development."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Telegram's HTTP layer can be noisy and may include long request URLs.
    logging.getLogger("httpx").setLevel(logging.WARNING)

