import json
import os
import re
import time

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from stock_context import detect_ticker, resolve_company, stock_snapshot

router = APIRouter()

LLM_ROUTER_URL = os.getenv("LLM_ROUTER_URL", "")
LLM_ROUTER_API_KEY = os.getenv("LLM_ROUTER_API_KEY", "")
ASK_NEURO_ACTION = os.getenv("ASK_NEURO_ACTION", "ask_neuro")
ASK_NEURO_TIMEOUT = float(os.getenv("ASK_NEURO_TIMEOUT", "25"))
ANSWER_TTL = int(os.getenv("ANSWER_CACHE_TTL", "1800"))
RATE_LIMIT_PER_MIN = int(os.getenv("ASK_RATE_LIMIT", "12"))

_answers: dict[str, tuple[float, dict]] = {}
_calls: list[float] = []
PRICE_WORDS = ("price", "rate", "trading", "quote", "worth", "how much")
DEEP_WORDS = ("explain", "why", "outlook", "should", "buy", "sell", "analy", "about",
              "overview", "news", "future", "predict", "forecast", "history", "risk")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    ticker: str | None = None


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[\*\-]\s+", "• ", text, flags=re.M)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(raw) -> str:
    data = None
    if isinstance(raw, dict):
        data = raw
    elif isinstance(raw, str) and raw.strip().startswith(("{", "[")):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
    if isinstance(data, dict):
        for key in ("answer", "text", "content", "response", "message"):
            if key in data and data[key]:
                return extract_text(data[key])
        raw = json.dumps(data, indent=2)
    elif isinstance(data, list):
        raw = "\n".join(extract_text(item) for item in data)
    elif not isinstance(raw, str):
        raw = str(raw)
    return clean_text(raw)


def build_query(question: str, snap: dict | None) -> str:
    lines = [
        "You are Neuro, a stock research analyst.",
        "Answer only about the company or stock in the live data below.",
        "If the question names a different company or topic, say in one sentence that you only cover the stock shown, then give the overview of the stock shown.",
        "Plain text only. No markdown, asterisks, headings or bullets.",
        "Keep the reply under 80 words.",
    ]
    if snap:
        cur = snap["currency_symbol"]
        lines.append("Live data (use these exact figures):")
        lines.append(f"Company: {snap['name']} ({snap['ticker']})")
        if snap.get("sector"):
            lines.append(f"Sector: {snap['sector']}")
        if snap.get("price") is not None:
            move = f" ({snap['change_pct']:+}% today)" if snap.get("change_pct") is not None else ""
            lines.append(f"Current price: {cur}{snap['price']}{move}")
            if snap.get("price_inr"):
                lines.append(f"Approximate price in INR: ₹{snap['price_inr']} (USD to INR rate {snap['fx_rate']})")
        if snap.get("summary"):
            lines.append(f"Business summary: {snap['summary']}")
    else:
        lines.append("No live data is available. Answer from general knowledge in one short paragraph.")
    lines.append("Structure: direct answer, then a 2 to 3 sentence overview, then the price in one sentence.")
    lines.append("Question: " + question)
    return "\n".join(lines)


def price_only_reply(question: str, snap: dict) -> str | None:
    q = question.lower()
    if len(q) > 60 or not any(w in q for w in PRICE_WORDS):
        return None
    if any(w in q for w in DEEP_WORDS) or snap.get("price") is None:
        return None
    cur = snap["currency_symbol"]
    move = f", {snap['change_pct']:+}% today" if snap.get("change_pct") is not None else ""
    inr = f" (about ₹{snap['price_inr']} at the live USD to INR rate)" if snap.get("price_inr") else ""
    return f"{snap['name']} ({snap['ticker']}) is trading at {cur}{snap['price']}{move}{inr}."


def rate_limit_ok() -> bool:
    now = time.time()
    _calls[:] = [t for t in _calls if now - t < 60]
    if len(_calls) >= RATE_LIMIT_PER_MIN:
        return False
    _calls.append(now)
    return True


@router.post("/chat/ask")
def chat_ask(body: AskRequest):
    if not LLM_ROUTER_URL or not LLM_ROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="LLM router is not configured")
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question is required")

    ticker = (detect_ticker(question) or resolve_company(question)
              or (body.ticker or "").strip().upper() or None)
    snap = stock_snapshot(ticker) if ticker else None

    cache_key = f"{ticker or ''}|{question.lower()}"
    hit = _answers.get(cache_key)
    if hit and time.time() - hit[0] < ANSWER_TTL:
        return {**hit[1], "cache_hit": True, "cache_source": "backend"}

    if snap:
        direct = price_only_reply(question, snap)
        if direct:
            result = {"answer": direct, "ticker": ticker, "stock": snap, "provider": "local",
                      "model": "live-price", "cache_hit": False, "request_id": None}
            _answers[cache_key] = (time.time(), result)
            return result

    if not rate_limit_ok():
        raise HTTPException(status_code=429, detail="Too many questions right now. Wait a minute and try again.")

    payload = {"action": ASK_NEURO_ACTION, "query": build_query(question, snap)}
    headers = {"x-api-key": LLM_ROUTER_API_KEY, "Content-Type": "application/json"}
    try:
        resp = httpx.post(LLM_ROUTER_URL, json=payload, headers=headers, timeout=ASK_NEURO_TIMEOUT)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ask Neuro timed out, please try again")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="LLM router is unreachable")

    if resp.status_code == 504:
        raise HTTPException(status_code=504, detail="Ask Neuro is taking too long. Try a shorter question.")
    if resp.status_code != 200:
        print(f"ASK NEURO FAILED: status={resp.status_code}")
        raise HTTPException(status_code=502, detail="LLM router returned an error")

    try:
        data = resp.json()
    except ValueError:
        data = {"answer": resp.text}
    if isinstance(data, dict) and data.get("error"):
        raise HTTPException(status_code=502, detail=f"Router: {data['error']}")

    answer = extract_text(data.get("answer", data) if isinstance(data, dict) else data)
    if not answer:
        answer = "I couldn't generate an answer for that. Try rephrasing."
    meta = data if isinstance(data, dict) else {}
    result = {
        "answer": answer,
        "ticker": ticker,
        "stock": snap,
        "provider": meta.get("provider"),
        "model": meta.get("model"),
        "cache_hit": meta.get("cache_hit", False),
        "request_id": meta.get("request_id"),
    }
    _answers[cache_key] = (time.time(), result)
    return result