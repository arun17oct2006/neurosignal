"""Worldwide trending stocks.

Pulls Yahoo's most-active and top-gainer screener lists and ranks each stock by
a score: (volume vs 3-month average) x (1 + |price move| / 10). The screener is
unofficial and may change, so a fixed fallback list is returned if it fails.
"""
import time

import yfinance as yf
from fastapi import APIRouter

router = APIRouter(prefix="/trending", tags=["trending"])

CACHE_TTL = 900
SCREENS = ["most_actives", "day_gainers"]
FALLBACK_SYMBOLS = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META"]

NAME_OVERRIDES = {"GOOGL": "Google"}

_cache: dict = {"ts": 0.0, "items": None}


def _quotes(screen_name: str) -> list[dict]:
    try:
        res = yf.screen(screen_name, size=25)
        return res.get("quotes", []) if isinstance(res, dict) else []
    except Exception:
        return []


def _score(q: dict) -> tuple[float, float]:
    vol = q.get("regularMarketVolume") or 0
    avg = q.get("averageDailyVolume3Month") or 0
    change = q.get("regularMarketChangePercent") or 0.0
    ratio = (vol / avg) if avg else 1.0
    return ratio * (1 + abs(change) / 10), ratio


def _fallback() -> list[dict]:
    return [
        {"symbol": s, "name": s, "price": None, "change_pct": None,
         "volume_ratio": None, "currency": "USD", "reasons": ["fallback"]}
        for s in FALLBACK_SYMBOLS
    ]


def _build() -> list[dict]:
    pool: dict[str, dict] = {}
    for screen in SCREENS:
        for q in _quotes(screen):
            sym = q.get("symbol")
            if not sym or q.get("quoteType", "EQUITY") != "EQUITY":
                continue
            score, ratio = _score(q)
            entry = pool.get(sym)
            if entry is None:
                pool[sym] = {
                    "symbol": sym,
                    "name": NAME_OVERRIDES.get(sym) or q.get("shortName") or q.get("longName") or sym,
                    "price": q.get("regularMarketPrice"),
                    "change_pct": q.get("regularMarketChangePercent"),
                    "volume_ratio": round(ratio, 2),
                    "currency": q.get("currency", "USD"),
                    "reasons": [screen],
                    "score": score,
                }
            else:
                entry["reasons"].append(screen)
                entry["score"] = max(entry["score"], score)

    if not pool:
        return _fallback()

    ranked = sorted(pool.values(), key=lambda x: x["score"], reverse=True)[:6]
    items = []
    for r in ranked:
        r.pop("score", None)
        if r["price"] is not None:
            r["price"] = round(float(r["price"]), 2)
        if r["change_pct"] is not None:
            r["change_pct"] = round(float(r["change_pct"]), 2)
        items.append(r)
    return items


@router.get("/worldwide")
def worldwide():
    now = time.time()
    if _cache["items"] and now - _cache["ts"] < CACHE_TTL:
        return {"items": _cache["items"], "cached": True}
    items = _build()
    _cache.update(ts=now, items=items)
    return {"items": items, "cached": False}