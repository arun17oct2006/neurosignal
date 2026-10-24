from __future__ import annotations
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / '.env')

import asyncio
import json
import logging
import os
import time
from typing import Literal

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from xgboost import XGBRegressor


from auth_google import (
    AuthResponse,
    CurrentUser,
    GoogleAuthIn,
    OptionalCurrentUser,
    google_login,
    logout as google_logout,
)
from market_cache import MarketCacheClient, MarketCacheError
from ticker_resolver import Listing, is_market_open, resolve


# --------------------------------------------------
# Application configuration
# --------------------------------------------------

from deep_models import build_models
app = FastAPI(title="NeuroSignal AI", version="3.1")

from ask_neuro import router as ask_router
app.include_router(ask_router)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

SignalType = Literal["STRONG_BUY", "STRONG_SELL", "NEUTRAL"]

# Local in-memory cache: resolved symbol -> (timestamp, result)
_analysis_cache: dict[str, tuple[float, dict]] = {}

_market_cache = MarketCacheClient()
_llm_router = MarketCacheClient(base_url=os.getenv("LLM_ROUTER_URL", ""), api_key=os.getenv("LLM_ROUTER_API_KEY", ""))

# Local analysis cache lifetime: shorter while the exchange is open.
ANALYSIS_TTL_OPEN = 300        # 5 minutes during trading hours
ANALYSIS_TTL_CLOSED = 3600     # 1 hour outside trading hours

# AWS action name for Ask Neuro. Override with ASK_NEURO_ACTION in .env
# if your API Gateway uses a different action name.
ASK_NEURO_ACTION = os.getenv("ASK_NEURO_ACTION", "ask_neuro")
MAX_ANSWER_CHARS = 2000


# --------------------------------------------------
# Authentication
# --------------------------------------------------

@app.post("/auth/google", response_model=AuthResponse, tags=["auth"])
async def route_google_login(body: GoogleAuthIn):
    """Verify a Google ID token and return a signed JWT."""
    return await google_login(body)


@app.post("/auth/logout", tags=["auth"])
async def route_logout():
    """Client should discard its token."""
    return await google_logout()


@app.get("/auth/me", tags=["auth"])
async def route_me(user: CurrentUser):
    """Return the identity encoded in the caller's JWT."""
    return user


# --------------------------------------------------
# Request schemas
# --------------------------------------------------

class Row(BaseModel):
    date: str
    close: float


class DatasetIn(BaseModel):
    label: str
    rows: list[Row]


class ChatCtx(BaseModel):
    ticker: str
    rsi: float
    signal: SignalType
    target: float


class ChatIn(BaseModel):
    q: str
    ctx: ChatCtx


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    ticker: str | None = None


class InteractionIn(BaseModel):
    ticker: str
    interaction_type: Literal["ticker_selected"] = "ticker_selected"


# --------------------------------------------------
# Technical indicators
# --------------------------------------------------

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["sma_20"] = df["close"].rolling(
        window=20, min_periods=1
    ).mean()

    delta = df["close"].diff()

    gain = delta.clip(lower=0).ewm(
        alpha=1 / 14, adjust=False
    ).mean()

    loss = (-delta.clip(upper=0)).ewm(
        alpha=1 / 14, adjust=False
    ).mean()

    rs = gain / loss.replace(0, np.nan)

    df["rsi"] = (
        100 - 100 / (1 + rs)
    ).fillna(50)

    return df


FEATURES = {
    "rsi": "RSI (14)",
    "sma_spread": "SMA-20 Spread",
    "mom_20": "Momentum 20d",
    "vol_20": "Volatility",
    "ret_1": "Return 1d",
}


# --------------------------------------------------
# Stock analysis and prediction
# --------------------------------------------------

def analyze(ticker: str, df: pd.DataFrame) -> dict:
    if len(df) < 60:
        raise HTTPException(
            status_code=422,
            detail="Need at least 60 rows of price history",
        )

    df = add_indicators(df)

    features = pd.DataFrame(index=df.index)

    features["rsi"] = df["rsi"]
    features["sma_spread"] = (
        df["close"] - df["sma_20"]
    ) / df["sma_20"]

    features["mom_20"] = df["close"].pct_change(20)

    features["vol_20"] = (
        df["close"].pct_change().rolling(20).std()
    )

    features["ret_1"] = df["close"].pct_change()

    target = df["close"].shift(-5) / df["close"] - 1

    data = features.assign(y=target).dropna()

    split = int(len(data) * 0.8)

    X_train = data.iloc[:split][list(FEATURES)]
    X_test = data.iloc[split:][list(FEATURES)]

    y_train = data.iloc[:split]["y"]
    y_test = data.iloc[split:]["y"]

    if X_train.empty or X_test.empty:
        raise HTTPException(
            status_code=422,
            detail="Insufficient usable data for model evaluation",
        )

    models = {
        "XGBoost": XGBRegressor(
            n_estimators=200,
            max_depth=3,
            learning_rate=0.05,
            verbosity=0,
            random_state=42,
            objective="reg:squarederror",
            n_jobs=1,
        ),
        "Random Forest": RandomForestRegressor(
            n_estimators=200,
            max_depth=6,
            random_state=42,
            n_jobs=1,
        ),
    }

    best_name = None
    best_model = None
    best_rmse = float("inf")
    best_predictions = None

    for name, model in models.items():
        model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        rmse = float(
            np.sqrt(mean_squared_error(y_test, predictions))
        )

        if rmse < best_rmse:
            best_name = name
            best_model = model
            best_rmse = rmse
            best_predictions = predictions

    if best_model is None or best_predictions is None:
        raise HTTPException(
            status_code=500,
            detail="Unable to train a prediction model",
        )

    hit_ratio = float(
        (
            np.sign(best_predictions)
            == np.sign(y_test.to_numpy())
        ).mean() * 100
    )

    latest_features = features[list(FEATURES)].dropna()

    if latest_features.empty:
        raise HTTPException(
            status_code=422,
            detail="Insufficient data to calculate the latest prediction",
        )

    latest = latest_features.iloc[[-1]]

    predicted_return = float(
        best_model.predict(latest)[0]
    ) * 100

    last = df.iloc[-1]

    latest_price = float(last["close"])
    rsi_now = float(last["rsi"])

    signal: SignalType = (
        "STRONG_BUY"
        if predicted_return > 1.5 and rsi_now < 70
        else "STRONG_SELL"
        if predicted_return < -1.5 and rsi_now > 30
        else "NEUTRAL"
    )

    importances = best_model.feature_importances_

    if importances.sum():
        importances = importances / importances.sum()

    tail = df.tail(120)

    return {
        "ticker": ticker,
        "live_price": round(latest_price, 2),
        "target_price": round(
            latest_price * (1 + predicted_return / 100), 2
        ),
        "predicted_return_pct": round(predicted_return, 2),
        "hit_ratio": round(hit_ratio, 1),
        "rsi_now": round(rsi_now, 2),
        "signal": signal,
        "model_used": best_name,
        "rmse": round(best_rmse * latest_price, 3),
        "chart_data": [
            {
                "date": str(date)[:10],
                "close": round(float(row["close"]), 2),
                "sma_20": round(float(row["sma_20"]), 2),
                "rsi": round(float(row["rsi"]), 2),
            }
            for date, row in tail.iterrows()
        ],
        "feature_importance": sorted(
            [
                {
                    "feature": FEATURES[key],
                    "weight": round(float(weight), 3),
                }
                for key, weight in zip(FEATURES, importances)
            ],
            key=lambda item: -item["weight"],
        ),
    }


# --------------------------------------------------
# Stockcache helpers
# --------------------------------------------------

def _history_cache_key(listing: Listing) -> str:
    """
    Cache key per listing, e.g. 'US:AAPL:HISTORY:2Y:1D' or
    'NSE:RELIANCE.NS:HISTORY:2Y:1D'. The US format matches the
    keys already stored in your cache.
    """
    return f"{listing.exchange}:{listing.symbol}:HISTORY:2Y:1D"


def _analysis_ttl(listing: Listing) -> int:
    return ANALYSIS_TTL_OPEN if is_market_open(listing) else ANALYSIS_TTL_CLOSED


def _history_from_cache(listing: Listing) -> pd.DataFrame | None:
    """
    Read and validate historical prices from AWS Marketcache.

    Expected cache_get response:
        {"data": [{"date": "YYYY-MM-DD", "close": 123.45}]}

    A null or empty data value is treated as a cache miss.
    """
    cache_key = _history_cache_key(listing)
    logger.info("AWS CACHE READ: ticker=%s key=%s", listing.symbol, cache_key)

    response = _market_cache.action(
        "cache_get",
        symbol=listing.symbol,
        cache_key=cache_key,
    )

    if not isinstance(response, dict):
        raise MarketCacheError(
            "Stockcache cache_get response must be an object"
        )

    if "data" not in response:
        raise MarketCacheError(
            "Stockcache cache_get response is missing 'data'"
        )

    rows = response["data"]

    if isinstance(rows, dict):
        rows = rows.get("rows")

    if rows is None or rows == []:
        logger.info("AWS CACHE MISS: ticker=%s (empty entry)", listing.symbol)
        return None

    if not isinstance(rows, list):
        raise MarketCacheError(
            "Stockcache cache_get 'data' must contain a list of rows"
        )

    try:
        df = pd.DataFrame(rows)

        if not {"date", "close"}.issubset(df.columns):
            raise ValueError("Cached rows must contain date and close")

        df = df[["date", "close"]].copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")

        df = (
            df.dropna()
            .sort_values("date")
            .drop_duplicates("date", keep="last")
        )

    except (TypeError, ValueError, KeyError) as exc:
        raise MarketCacheError(
            "Stockcache returned invalid market data"
        ) from exc

    if len(df) < 60:
        logger.info(
            "AWS CACHE MISS: ticker=%s valid_rows=%d (minimum=60)",
            listing.symbol,
            len(df),
        )
        return None

    logger.info("AWS CACHE HIT: ticker=%s rows=%d", listing.symbol, len(df))
    return df.set_index("date")


def _to_cache_rows(df: pd.DataFrame) -> list[dict[str, str | float]]:
    """Convert a price DataFrame to serializable cache rows."""
    return [
        {
            "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
            "close": float(row["close"]),
        }
        for date, row in df.iterrows()
    ]


def _ticker_values(value: object) -> list[str]:
    """Extract ticker symbols from common preference/history shapes."""
    if isinstance(value, dict):
        for key in (
            "preferred_tickers",
            "tickers",
            "favorites",
            "symbols",
            "history",
        ):
            if key in value:
                return _ticker_values(value[key])

        ticker = value.get("ticker") or value.get("symbol")

        if isinstance(ticker, str) and ticker.strip():
            return [ticker.strip().upper()]

        return []

    if isinstance(value, list):
        tickers: list[str] = []

        for item in value:
            tickers.extend(_ticker_values(item))

        return tickers

    if isinstance(value, str) and value.strip():
        return [value.strip().upper()]

    return []


def _fetch_history_from_yahoo(symbol: str) -> pd.DataFrame:
    """Fetch daily historical prices from Yahoo Finance (works for .NS and .BO too)."""
    try:
        hist = yf.Ticker(symbol).history(
            period="2y",
            interval="1d",
        )
    except Exception as exc:
        logger.exception("Yahoo Finance history request failed for %s", symbol)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to retrieve market data for {symbol}",
        ) from exc

    if hist.empty or "Close" not in hist.columns:
        raise HTTPException(
            status_code=404,
            detail=f"No market data for {symbol}",
        )

    df = hist[["Close"]].rename(columns={"Close": "close"})

    df = df.dropna().sort_index()
    df = df[~df.index.duplicated(keep="last")]

    if len(df) < 60:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient historical data for {symbol}",
        )

    return df


def _write_history_to_cache(listing: Listing, df: pd.DataFrame) -> None:
    """Write historical prices to AWS Marketcache."""
    cache_key = _history_cache_key(listing)
    rows = _to_cache_rows(df)

    logger.info(
        "AWS CACHE WRITE START: ticker=%s key=%s rows=%d",
        listing.symbol,
        cache_key,
        len(rows),
    )
    _market_cache.action(
        "cache_put",
        symbol=listing.symbol,
        cache_key=cache_key,
        data={"rows": rows},
    )
    logger.info(
        "AWS CACHE WRITE ACKNOWLEDGED: ticker=%s rows=%d",
        listing.symbol,
        len(rows),
    )


# --------------------------------------------------
# Analysis routes
# --------------------------------------------------

@app.get("/analysis/{ticker}", tags=["analysis"])
def analysis(
    ticker: str,
    user: OptionalCurrentUser,
):
    try:
        listing = resolve(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    t = listing.symbol
    ttl = _analysis_ttl(listing)

    # Layer 1: local in-memory analysis cache.
    cached_result = _analysis_cache.get(t)

    if cached_result:
        age = time.time() - cached_result[0]
        if age < ttl:
            logger.info(
                "LOCAL ANALYSIS CACHE HIT: ticker=%s age_seconds=%.1f",
                t,
                age,
            )
            return cached_result[1]

        logger.info(
            "LOCAL ANALYSIS CACHE EXPIRED: ticker=%s age_seconds=%.1f",
            t,
            age,
        )
        _analysis_cache.pop(t, None)
    else:
        logger.info("LOCAL ANALYSIS CACHE MISS: ticker=%s", t)

    # Layer 2: shared AWS market history cache, keyed by listing.
    df = None

    try:
        df = _history_from_cache(listing)
    except MarketCacheError as exc:
        logger.warning(
            "AWS CACHE READ FAILED: ticker=%s error=%s",
            t,
            exc,
        )

    # Yahoo Finance remains the fallback on a cache miss or cache error.
    if df is None:
        logger.info("YAHOO FALLBACK: fetching history for ticker=%s", t)
        df = _fetch_history_from_yahoo(t)

        try:
            _write_history_to_cache(listing, df)
        except MarketCacheError as exc:
            logger.warning(
                "AWS CACHE WRITE FAILED: ticker=%s error=%s",
                t,
                exc,
            )

    result = analyze(t, df)
    result.update({
        "exchange": listing.exchange,
        "currency": listing.currency,
        "currency_symbol": listing.currency_symbol,
    })

    _analysis_cache[t] = (time.time(), result)

    return result


# --------------------------------------------------
# Personalization
# --------------------------------------------------

@app.get("/personalization", tags=["personalization"])
def personalization(user: CurrentUser):
    try:
        preferences_response = _market_cache.action(
            "get_preferences",
            user_id=user.sub,
        )

        history_response = _market_cache.action(
            "get_history",
            user_id=user.sub,
        )

    except MarketCacheError as exc:
        logger.exception("Failed to load personalization data")
        raise HTTPException(
            status_code=502,
            detail="Unable to load personalization data",
        ) from exc

    preferences = (
        preferences_response.get("preferences", preferences_response)
        if isinstance(preferences_response, dict)
        else preferences_response
    )

    history = (
        history_response.get("history", history_response)
        if isinstance(history_response, dict)
        else history_response
    )

    recommended = list(
        dict.fromkeys(
            _ticker_values(preferences)
            + _ticker_values(history)
        )
    )

    return {
        "preferences": preferences,
        "history": history,
        "recommended_tickers": recommended,
    }


@app.post("/interactions", tags=["personalization"])
def record_interaction(
    body: InteractionIn,
    user: CurrentUser,
):
    try:
        symbol = resolve(body.ticker).symbol
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        return _market_cache.action(
            "record_interaction",
            user_id=user.sub,
            symbol=symbol,
            interaction_type=body.interaction_type,
        )

    except MarketCacheError as exc:
        logger.exception("Failed to record interaction for %s", symbol)
        raise HTTPException(
            status_code=502,
            detail="Unable to record interaction",
        ) from exc


# --------------------------------------------------
# Custom dataset analysis
# --------------------------------------------------

@app.post("/analysis/dataset", tags=["analysis"])
def analysis_dataset(body: DatasetIn):
    if len(body.rows) < 60:
        raise HTTPException(
            status_code=422,
            detail="Upload at least 60 rows of price history",
        )

    df = pd.DataFrame(
        [row.model_dump() for row in body.rows]
    )

    df["date"] = pd.to_datetime(
        df["date"], errors="coerce"
    )

    df["close"] = pd.to_numeric(
        df["close"], errors="coerce"
    )

    df = (
        df.dropna()
        .sort_values("date")
        .drop_duplicates("date", keep="last")
        .set_index("date")
    )

    if len(df) < 60:
        raise HTTPException(
            status_code=422,
            detail="Need at least 60 valid rows of price history",
        )

    return analyze(body.label.strip().upper(), df)


# --------------------------------------------------
# Ask Neuro (AWS-backed chatbot)
# --------------------------------------------------

def _label(key: object) -> str:
    return str(key).replace("_", " ").strip().capitalize()


def _format_scalar(value: object) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def json_to_text(value: object, depth: int = 0) -> str:
    """
    Render any JSON value as readable plain text.
    Used when AWS returns structured data instead of a ready-made answer.
    """
    pad = "  " * depth
    lines: list[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            if item is None or item == "" or item == [] or item == {}:
                continue
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{_label(key)}:")
                lines.append(json_to_text(item, depth + 1))
            else:
                lines.append(f"{pad}{_label(key)}: {_format_scalar(item)}")

    elif isinstance(value, list):
        if all(not isinstance(item, (dict, list)) for item in value):
            items = [_format_scalar(i) for i in value if i is not None]
            if items:
                lines.append(pad + ", ".join(items))
        else:
            for number, item in enumerate(value, 1):
                if isinstance(item, (dict, list)):
                    lines.append(f"{pad}{number}.")
                    lines.append(json_to_text(item, depth + 1))
                else:
                    lines.append(f"{pad}{number}. {_format_scalar(item)}")

    elif value is not None:
        lines.append(pad + _format_scalar(value))

    return "\n".join(line for line in lines if line.strip())


def _extract_answer(response: dict) -> str:
    """Use a ready-made 'answer' string if AWS provides one; otherwise convert the JSON."""
    answer = response.get("answer")
    if isinstance(answer, str) and answer.strip():
        text = answer.strip()
    else:
        text = json_to_text(response).strip()

    if not text:
        return "No information was found for that question."
    if len(text) > MAX_ANSWER_CHARS:
        text = text[:MAX_ANSWER_CHARS].rstrip() + "â€¦"
    return text


@app.post("/chat/ask", tags=["chat"])
def ask_neuro(body: AskIn, user: OptionalCurrentUser):
    """
    Ask Neuro: forwards the question (and optional ticker) to AWS,
    converts the JSON reply to text, and returns {"answer": "..."}.
    The question text is never logged.
    """
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question is required")

    symbol = None
    if body.ticker and body.ticker.strip():
        try:
            symbol = resolve(body.ticker).symbol
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        response = _llm_router.action(ASK_NEURO_ACTION,
            question=question,
            symbol=symbol,
            user_id=user.sub if user else None,
        )
    except MarketCacheError as exc:
        logger.warning("ASK NEURO FAILED: symbol=%s error=%s", symbol, exc)
        raise HTTPException(
            status_code=502,
            detail="Ask Neuro is unavailable right now",
        ) from exc

    logger.info("ASK NEURO OK: symbol=%s", symbol)
    return {"answer": _extract_answer(response), "ticker": symbol, "provider": response.get("provider"), "model": response.get("model"), "cache_hit": response.get("cache_hit", False), "request_id": response.get("request_id")}


# --------------------------------------------------
# Streaming chat (unchanged fallback)
# --------------------------------------------------

def compose_reply(q: str, c: ChatCtx) -> str:
    zone = (
        "overbought"
        if c.rsi > 70
        else "oversold"
        if c.rsi < 30
        else "neutral-range"
    )

    return (
        f"{c.ticker} â†’ {c.signal.replace('_', ' ')}. "
        f"RSI {c.rsi:.1f} is {zone}; "
        f"model target ${c.target:.2f}. "
        f"On \"{q}\": size positions to your risk limits â€” "
        "this is a quantitative estimate, not financial advice."
    )


@app.post("/chat/stream", tags=["chat"])
async def chat_stream(body: ChatIn):
    async def generate():
        for token in compose_reply(body.q, body.ctx).split(" "):
            yield f"data: {json.dumps(token + ' ')}\n\n"
            await asyncio.sleep(0.02)

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )

from trending import router as trending_router
app.include_router(trending_router)


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
