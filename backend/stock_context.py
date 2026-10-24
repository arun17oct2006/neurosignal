"""Stock detection (built-in names, Yahoo search for any company) and live snapshots."""
import difflib
import re
import time

import yfinance as yf
import socket
socket.setdefaulttimeout(5)

ALIASES = {
    "nvidia": "NVDA", "apple": "AAPL", "microsoft": "MSFT", "tesla": "TSLA",
    "google": "GOOGL", "alphabet": "GOOGL", "amazon": "AMZN", "meta": "META",
    "netflix": "NFLX", "amd": "AMD", "intel": "INTC", "oracle": "ORCL", "uber": "UBER",
    "reliance": "RELIANCE.NS", "tcs": "TCS.NS", "infosys": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS", "hdfc": "HDFCBANK.NS", "icici": "ICICIBANK.NS",
    "sbi": "SBIN.NS", "state bank": "SBIN.NS", "airtel": "BHARTIARTL.NS",
    "itc": "ITC.NS", "larsen": "LT.NS", "hindustan unilever": "HINDUNILVR.NS",
    "jio": "JIOFIN.NS", "jio financial": "JIOFIN.NS", "adani": "ADANIENT.NS",
    "wipro": "WIPRO.NS", "maruti": "MARUTI.NS", "tata motors": "TATAMOTORS.NS",
}
KNOWN_TICKERS = set(ALIASES.values())
CACHE_TTL = 300
FX_TTL = 900
STOPWORDS = {
    "explain", "about", "stock", "stocks", "share", "shares", "price", "current", "rate",
    "what", "tell", "news", "outlook", "should", "buy", "sell", "analysis", "analyze",
    "company", "doing", "lately", "today", "how", "much", "the", "and", "for", "its",
    "with", "from", "give", "me", "please", "latest", "value", "this", "that", "why",
    "who", "when", "where", "does", "are", "you", "will", "can", "future", "forecast",
    "trading", "worth", "overview", "history", "risk", "compare", "is", "of", "in",
    "on", "to", "a", "an", "my", "i", "do", "any", "some", "good", "bad", "best",
}
_cache: dict[str, tuple[float, dict | None]] = {}
_fx: dict = {"ts": 0.0, "rate": None}
_search_cache: dict[str, tuple[float, str | None]] = {}


def detect_ticker(question: str) -> str | None:
    m = re.search(r"\b([A-Za-z]{1,10}\.(?:NS|BO))\b", question)
    if m:
        return m.group(1).upper()
    q = question.lower()
    for name, symbol in sorted(ALIASES.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(name)}\b", q):
            return symbol
    tokens = re.findall(r"[a-z]+", q)
    for tok in tokens:
        if len(tok) >= 2 and tok.upper() in KNOWN_TICKERS:
            return tok.upper()
    single_names = [n for n in ALIASES if " " not in n]
    for tok in tokens:
        if len(tok) >= 4:
            match = difflib.get_close_matches(tok, single_names, n=1, cutoff=0.7)
            if match:
                return ALIASES[match[0]]
    return None


def _search_symbol(name: str) -> str | None:
    key = name.lower()
    hit = _search_cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    symbol = None
    try:
        if hasattr(yf, "Search"):
            for q in (yf.Search(name, max_results=5).quotes or []):
                if q.get("quoteType") == "EQUITY" and q.get("symbol"):
                    symbol = q["symbol"].upper()
                    break
    except Exception:
        symbol = None
    _search_cache[key] = (time.time(), symbol)
    return symbol


def resolve_company(question: str) -> str | None:
    """For companies not in ALIASES: searches Yahoo using each candidate word."""
    seen = []
    for w in re.findall(r"[A-Za-z][A-Za-z&]{2,}", question):
        lw = w.lower()
        if lw not in STOPWORDS and lw not in seen:
            seen.append(lw)
    for name in seen[:4]:
        symbol = _search_symbol(name)
        if symbol:
            return symbol
    return None


def usd_inr_rate() -> float | None:
    if _fx["rate"] and time.time() - _fx["ts"] < FX_TTL:
        return _fx["rate"]
    try:
        rate = float(yf.Ticker("USDINR=X").fast_info.last_price)
        _fx.update(ts=time.time(), rate=round(rate, 4))
        return _fx["rate"]
    except Exception:
        return _fx["rate"]


def stock_snapshot(ticker: str) -> dict | None:
    key = ticker.upper()
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    snap = None
    try:
        t = yf.Ticker(key)
        fi = t.fast_info
        price = float(fi.last_price) if fi.last_price else None
        prev = float(fi.previous_close) if fi.previous_close else None
        try:
            info = t.info or {}
        except Exception:
            info = {}
        change = round((price - prev) / prev * 100, 2) if price and prev else None
        is_indian = key.endswith((".NS", ".BO"))
        price_inr, rate = None, None
        if price and not is_indian:
            rate = usd_inr_rate()
            if rate:
                price_inr = round(price * rate, 2)
        snap = {
            "ticker": key,
            "name": info.get("longName") or info.get("shortName") or key,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "price": round(price, 2) if price else None,
            "change_pct": change,
            "currency": "INR" if is_indian else "USD",
            "currency_symbol": "₹" if is_indian else "$",
            "price_inr": price_inr,
            "fx_rate": rate,
            "summary": (info.get("longBusinessSummary") or "")[:150],
        }
    except Exception:
        snap = None
    _cache[key] = (time.time(), snap)
    return snap