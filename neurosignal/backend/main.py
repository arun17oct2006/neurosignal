"""NeuroSignal AI — FastAPI backend.

Run:  pip install -r requirements.txt && uvicorn main:app --reload --port 8000
Market data: Yahoo Finance via yfinance (real daily closes).
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
import uuid
from typing import Literal

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from xgboost import XGBRegressor

app = FastAPI(title="NeuroSignal AI", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

SignalType = Literal["STRONG_BUY", "STRONG_SELL", "NEUTRAL"]


# ---------------- Schemas ----------------
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


class EmailIn(BaseModel):
    email: str
    redirect: str | None = None


class OtpVerifyIn(BaseModel):
    email: str
    code: str


# ---------------- Indicators & model ----------------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sma_20"] = df["close"].rolling(20, min_periods=1).mean()
    delta = df["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = (100 - 100 / (1 + rs)).fillna(50)
    return df


FEATURES = {
    "rsi": "RSI (14)",
    "sma_spread": "SMA-20 Spread",
    "mom_20": "Momentum 20d",
    "vol_20": "Volatility",
    "ret_1": "Return 1d",
}


def analyze(ticker: str, df: pd.DataFrame) -> dict:
    if len(df) < 60:
        raise HTTPException(422, "Need at least 60 rows of price history")
    df = add_indicators(df)
    f = pd.DataFrame(index=df.index)
    f["rsi"] = df["rsi"]
    f["sma_spread"] = (df["close"] - df["sma_20"]) / df["sma_20"]
    f["mom_20"] = df["close"].pct_change(20)
    f["vol_20"] = df["close"].pct_change().rolling(20).std()
    f["ret_1"] = df["close"].pct_change()
    target = df["close"].shift(-5) / df["close"] - 1  # 5-day forward return
    data = f.assign(y=target).dropna()
    split = int(len(data) * 0.8)
    X_tr, X_te = data.iloc[:split][list(FEATURES)], data.iloc[split:][list(FEATURES)]
    y_tr, y_te = data.iloc[:split]["y"], data.iloc[split:]["y"]

    models = {
        "XGBoost": XGBRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, verbosity=0),
        "Random Forest": RandomForestRegressor(n_estimators=200, max_depth=6, random_state=42),
    }
    best_name, best_model, best_rmse, best_pred = None, None, float("inf"), None
    for name, m in models.items():
        m.fit(X_tr, y_tr)
        p = m.predict(X_te)
        rmse = float(np.sqrt(mean_squared_error(y_te, p)))
        if rmse < best_rmse:
            best_name, best_model, best_rmse, best_pred = name, m, rmse, p

    hit_ratio = float((np.sign(best_pred) == np.sign(y_te.values)).mean() * 100)
    latest = f[list(FEATURES)].dropna().iloc[[-1]]
    ret = float(best_model.predict(latest)[0]) * 100
    last = df.iloc[-1]
    rsi_now = float(last["rsi"])
    signal: SignalType = (
        "STRONG_BUY" if ret > 1.5 and rsi_now < 70
        else "STRONG_SELL" if ret < -1.5 and rsi_now > 30
        else "NEUTRAL"
    )
    imp = best_model.feature_importances_
    imp = imp / imp.sum() if imp.sum() else imp
    tail = df.tail(120)
    return {
        "ticker": ticker,
        "live_price": round(float(last["close"]), 2),
        "target_price": round(float(last["close"]) * (1 + ret / 100), 2),
        "predicted_return_pct": round(ret, 2),
        "hit_ratio": round(hit_ratio, 1),
        "rsi_now": round(rsi_now, 2),
        "signal": signal,
        "model_used": best_name,
        "rmse": round(best_rmse * float(last["close"]), 3),  # RMSE in $ terms
        "chart_data": [
            {"date": str(d)[:10], "close": round(float(r.close), 2),
             "sma_20": round(float(r.sma_20), 2), "rsi": round(float(r.rsi), 2)}
            for d, r in tail.iterrows()
        ],
        "feature_importance": sorted(
            [{"feature": FEATURES[k], "weight": round(float(w), 3)} for k, w in zip(FEATURES, imp)],
            key=lambda x: -x["weight"],
        ),
    }


_cache: dict[str, tuple[float, dict]] = {}


@app.get("/analysis/{ticker}")
def analysis(ticker: str):
    t = ticker.upper()
    hit = _cache.get(t)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    hist = yf.Ticker(t).history(period="2y", interval="1d")
    if hist.empty:
        raise HTTPException(404, f"No market data for {t}")
    df = hist[["Close"]].rename(columns={"Close": "close"})
    result = analyze(t, df)
    _cache[t] = (time.time(), result)
    return result


@app.post("/analysis/dataset")
def analysis_dataset(body: DatasetIn):
    df = pd.DataFrame([r.model_dump() for r in body.rows])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna().sort_values("date").set_index("date")
    return analyze(body.label.upper(), df)


# ---------------- Low-power chat (SSE) ----------------
def compose_reply(q: str, c: ChatCtx) -> str:
    zone = "overbought" if c.rsi > 70 else "oversold" if c.rsi < 30 else "neutral-range"
    return (
        f"{c.ticker} → {c.signal.replace('_', ' ')}. RSI {c.rsi:.1f} is {zone}; "
        f"model target ${c.target:.2f}. On \"{q}\": size positions to your risk limits — "
        "this is a quantitative estimate, not financial advice."
    )
    # Swap this for an LLM call (e.g. OpenAI/Gemini) using only `c` as context.


@app.post("/chat/stream")
async def chat_stream(body: ChatIn):
    async def gen():
        for tok in compose_reply(body.q, body.ctx).split(" "):
            yield f"data: {json.dumps(tok + ' ')}\n\n"
            await asyncio.sleep(0.02)
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------------- Passwordless auth (in-memory; swap for DB + email provider) ----------------
_otps: dict[str, tuple[str, float]] = {}


@app.post("/auth/otp/request")
def otp_request(body: EmailIn):
    code = f"{secrets.randbelow(10**6):06d}"
    _otps[body.email.lower()] = (code, time.time() + 600)
    print(f"[NeuroSignal] OTP for {body.email}: {code}")  # TODO: send via email provider
    return {"ok": True}


@app.post("/auth/otp/verify")
def otp_verify(body: OtpVerifyIn):
    rec = _otps.get(body.email.lower())
    if not rec or rec[1] < time.time() or not secrets.compare_digest(rec[0], body.code):
        raise HTTPException(401, "Invalid or expired code")
    del _otps[body.email.lower()]
    return {"user_id": str(uuid.uuid4()), "email": body.email, "authenticated_via": "otp"}


@app.post("/auth/magic-link")
def magic_link(_: EmailIn):
    raise HTTPException(501, "Magic link not configured")


@app.post("/auth/webauthn/options")
def webauthn_options(_: EmailIn):
    raise HTTPException(501, "Passkeys not configured")


@app.post("/auth/webauthn/verify")
def webauthn_verify():
    raise HTTPException(501, "Passkeys not configured")


@app.post("/auth/logout")
def logout():
    return {"ok": True}
