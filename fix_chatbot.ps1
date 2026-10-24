$backend = "E:\neurosignal\neurosignal\backend"
$utf8    = New-Object System.Text.UTF8Encoding($false)
$stamp   = Get-Date -Format "yyyyMMdd-HHmmss"

# ---------- 1. stock_context.py: any-company lookup via Yahoo search ----------
$sc = "$backend\stock_context.py"
Copy-Item $sc "$sc.$stamp.bak"
$t = [System.IO.File]::ReadAllText($sc)

# Add Jio and a few common names to the built-in list
$t = $t.Replace('"itc": "ITC.NS",', '"itc": "ITC.NS", "jio": "JIOFIN.NS", "jio financial": "JIOFIN.NS", "adani": "ADANIENT.NS", "wipro": "WIPRO.NS", "maruti": "MARUTI.NS", "tata motors": "TATAMOTORS.NS", "amd": "AMD", "netflix": "NFLX", "intel": "INTC", "oracle": "ORCL", "uber": "UBER",')

$resolver = @'


STOPWORDS = {
    "explain", "about", "stock", "stocks", "share", "shares", "price", "current", "rate",
    "what", "tell", "news", "outlook", "should", "buy", "sell", "analysis", "analyze",
    "company", "doing", "lately", "today", "how", "much", "the", "and", "for", "its",
    "with", "from", "give", "me", "please", "latest", "value", "this", "that", "why",
    "who", "when", "where", "does", "are", "you", "will", "can", "future", "forecast",
    "trading", "worth", "overview", "history", "risk", "compare", "is", "of", "in",
    "on", "to", "a", "an", "my", "i", "do", "any", "some", "good", "bad", "best",
}
_search_cache: dict[str, tuple[float, str | None]] = {}


def _search_symbol(name: str) -> str | None:
    key = name.lower()
    hit = _search_cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    symbol = None
    try:
        if hasattr(yf, "Search"):
            quotes = yf.Search(name, max_results=5).quotes or []
            for q in quotes:
                if q.get("quoteType") == "EQUITY" and q.get("symbol"):
                    symbol = q["symbol"].upper()
                    break
    except Exception:
        symbol = None
    _search_cache[key] = (time.time(), symbol)
    return symbol


def resolve_company(question: str) -> str | None:
    """For any company not in ALIASES: searches Yahoo by each candidate word."""
    words = re.findall(r"[A-Za-z][A-Za-z&]{2,}", question)
    seen = []
    for w in words:
        lw = w.lower()
        if lw in STOPWORDS or lw in seen:
            continue
        seen.append(lw)
    for name in seen[:4]:
        symbol = _search_symbol(name)
        if symbol:
            return symbol
    return None
'@
$t = $t.TrimEnd() + "`r`n" + $resolver
[System.IO.File]::WriteAllText($sc, $t, $utf8)
Write-Host "stock_context.py: any-company lookup added" -ForegroundColor Green

# ---------- 2. ask_neuro.py: use the resolver and keep answers on the stock ----------
$ask = "$backend\ask_neuro.py"
Copy-Item $ask "$ask.$stamp.bak"
$t = [System.IO.File]::ReadAllText($ask)

$t = $t.Replace('from stock_context import detect_ticker, stock_snapshot',
                'from stock_context import detect_ticker, resolve_company, stock_snapshot')
$t = $t.Replace('ticker = detect_ticker(question) or (body.ticker or "").strip().upper() or None',
                'ticker = detect_ticker(question) or resolve_company(question) or (body.ticker or "").strip().upper() or None')
$t = $t.Replace('"You are Neuro, a stock research analyst. Answer only about the company asked.",',
                '"You are Neuro, a stock research analyst. Answer only about the company or stock in the live data below. If the question is about a different company or topic, say in one sentence that you only cover the stock shown, then give that stock\'s overview.",')
[System.IO.File]::WriteAllText($ask, $t, $utf8)
Write-Host "ask_neuro.py: stock-focused prompt and resolver applied" -ForegroundColor Green

# ---------- 3. market_cache.py: 20 second timeout ----------
$mc = "$backend\market_cache.py"
Copy-Item $mc "$mc.$stamp.bak"
$t = [System.IO.File]::ReadAllText($mc)
$new = [regex]::Replace($t, '(timeout\s*=\s*)[\d.]+', '${1}20')
if ($new -eq $t) { Write-Host "No timeout found in market_cache.py. Paste the httpx/requests call and I'll adjust it." -ForegroundColor Yellow }
else { [System.IO.File]::WriteAllText($mc, $new, $utf8); Write-Host "market_cache.py: timeout set to 20s" -ForegroundColor Green }

# ---------- 4. main.py: degrade preferences and interactions quietly ----------
$main = "$backend\main.py"
Copy-Item $main "$main.$stamp.bak"
$t = [System.IO.File]::ReadAllText($main)
if ($t -notmatch "degrade_optional_routes") {
    $soft = @'


# ---- Optional routes degrade quietly when MarketCache is slow or down ----
from fastapi import Request as _Request
from fastapi.responses import JSONResponse as _JSONResponse

_OPTIONAL_FALLBACKS = {
    "/personalization": {"recommended_tickers": [], "preferences": [], "history": [], "degraded": True},
    "/interactions": {"ok": False, "degraded": True},
}


@app.middleware("http")
async def degrade_optional_routes(request: _Request, call_next):
    response = await call_next(request)
    fallback = _OPTIONAL_FALLBACKS.get(request.url.path)
    if fallback and response.status_code in (500, 502, 503, 504):
        return _JSONResponse(status_code=200, content=fallback)
    return response
'@
    $t = $t.TrimEnd() + "`r`n" + $soft + "`r`n"
    [System.IO.File]::WriteAllText($main, $t, $utf8)
    Write-Host "main.py: optional routes degrade quietly" -ForegroundColor Green
} else {
    Write-Host "main.py already patched" -ForegroundColor Yellow
}

Write-Host "`nDone. Restart the backend." -ForegroundColor Cyan