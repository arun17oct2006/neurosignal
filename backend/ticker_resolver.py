"""
ticker_resolver.py — maps user input to a yfinance symbol, currency and market hours.

Accepted input (case-insensitive):
    AAPL            → AAPL        (US, USD)   — unchanged existing behaviour
    RELIANCE.NS     → RELIANCE.NS (NSE, INR)
    500325.BO       → 500325.BO   (BSE, INR)
    NSE:RELIANCE    → RELIANCE.NS (NSE, INR)
    BSE:500325      → 500325.BO   (BSE, INR)
    ^NSEI           → ^NSEI       (index, treated as NSE hours, INR)

Use the returned `symbol` as the cache key so "TCS" and "TCS.NS" never collide.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

_SYMBOL_RE = re.compile(r"^[A-Z0-9.\-^]{1,20}$")

_PREFIX_TO_SUFFIX = {"NSE": ".NS", "BSE": ".BO"}
_SUFFIX_TO_EXCHANGE = {".NS": "NSE", ".BO": "BSE"}

_EXCHANGES = {
    "US":  {"currency": "USD", "symbol": "$", "tz": "America/New_York", "open": time(9, 30), "close": time(16, 0)},
    "NSE": {"currency": "INR", "symbol": "₹", "tz": "Asia/Kolkata",     "open": time(9, 15), "close": time(15, 30)},
    "BSE": {"currency": "INR", "symbol": "₹", "tz": "Asia/Kolkata",     "open": time(9, 15), "close": time(15, 30)},
}


@dataclass(frozen=True)
class Listing:
    symbol: str      # yfinance symbol and cache key, e.g. "RELIANCE.NS"
    exchange: str    # "US", "NSE", or "BSE"
    currency: str    # "USD" or "INR"
    currency_symbol: str


def resolve(raw: str) -> Listing:
    """Normalise user input. Raises ValueError for malformed input."""
    s = (raw or "").strip().upper()

    for prefix, suffix in _PREFIX_TO_SUFFIX.items():
        if s.startswith(prefix + ":"):
            s = s[len(prefix) + 1:] + suffix
            break

    if not _SYMBOL_RE.match(s):
        raise ValueError(f"Invalid ticker: {raw!r}")

    exchange = next((_SUFFIX_TO_EXCHANGE[sfx] for sfx in _SUFFIX_TO_EXCHANGE if s.endswith(sfx)), "US")
    info = _EXCHANGES[exchange]
    return Listing(symbol=s, exchange=exchange, currency=info["currency"], currency_symbol=info["symbol"])


def is_market_open(listing: Listing, now: datetime | None = None) -> bool:
    """
    True during regular trading hours for the listing's exchange, Mon–Fri.
    Exchange holidays are NOT handled; add a holiday calendar if needed.
    """
    info = _EXCHANGES[listing.exchange]
    tz = ZoneInfo(info["tz"])
    local = now.astimezone(tz) if now else datetime.now(tz)
    if local.weekday() >= 5:
        return False
    return info["open"] <= local.time() < info["close"]
