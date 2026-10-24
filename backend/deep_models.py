"""LSTM and TFT-style models, plus the combined 4-model summary."""
import math

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    TORCH_OK = True
except ImportError:  # backend still starts without torch; deep models are skipped
    TORCH_OK = False

LOOKBACK = 30
EPOCHS = 150
MIN_SAMPLES = 40


if TORCH_OK:
    class LSTMNet(nn.Module):
        def __init__(self, n_features, hidden=32):
            super().__init__()
            self.lstm = nn.LSTM(n_features, hidden, batch_first=True)
            self.head = nn.Linear(hidden, 1)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :]).squeeze(-1)


    class TFTLite(nn.Module):
        """TFT-style: learned feature gating, LSTM encoder, self-attention, linear head."""
        def __init__(self, n_features, hidden=32, heads=4):
            super().__init__()
            self.gate = nn.Sequential(nn.Linear(n_features, n_features), nn.Sigmoid())
            self.encoder = nn.LSTM(n_features, hidden, batch_first=True)
            self.attn = nn.MultiheadAttention(hidden, heads, batch_first=True)
            self.norm = nn.LayerNorm(hidden)
            self.head = nn.Linear(hidden, 1)

        def forward(self, x):
            weights = self.gate(x.mean(dim=1))      # per-feature importance, shape (B, F)
            x = x * weights.unsqueeze(1)
            h, _ = self.encoder(x)
            a, _ = self.attn(h, h, h)
            h = self.norm(h + a)
            return self.head(h[:, -1, :]).squeeze(-1)


def _close(rec):
    v = rec.get("Close", rec.get("close"))
    if v is None:
        return None
    v = float(v)
    return None if math.isnan(v) else v


def _prepare(closes):
    s = pd.Series(closes, dtype=float)
    r = np.log(s).diff()
    feats = pd.DataFrame({"ret": r, "mom5": s.pct_change(5), "vol10": r.rolling(10).std()}).dropna()
    target = r.shift(-1).loc[feats.index]          # next-day log return
    X_all = feats.values.astype(np.float32)
    y_all = target.values.astype(np.float32)
    mu, sd = X_all.mean(axis=0), X_all.std(axis=0) + 1e-8
    Xs = (X_all - mu) / sd
    ystd = float(np.nanstd(y_all)) + 1e-8
    Xw, yw = [], []
    for t in range(LOOKBACK - 1, len(Xs)):
        if np.isnan(y_all[t]):
            continue
        Xw.append(Xs[t - LOOKBACK + 1 : t + 1])
        yw.append(y_all[t] / ystd)
    if len(Xw) < MIN_SAMPLES:
        return None
    return {
        "X": torch.tensor(np.stack(Xw)),
        "y": torch.tensor(np.array(yw, dtype=np.float32)),
        "last": torch.tensor(Xs[-LOOKBACK:]).unsqueeze(0),
        "n_features": Xs.shape[1],
        "ystd": ystd,
        "last_close": float(s.iloc[-1]),
    }


def _train(model, X, y):
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()
    model.train()
    for _ in range(EPOCHS):
        opt.zero_grad()
        loss = loss_fn(model(X), y)
        loss.backward()
        opt.step()
    model.eval()


def _summary(label, pred_ret, last_close):
    return {
        "label": label,
        "direction": "UP" if pred_ret > 0 else "DOWN",
        "predicted_change_pct": round(pred_ret * 100, 2),
        "predicted_price": round(last_close * math.exp(pred_ret), 2),
    }


def run_deep_models(history):
    if not TORCH_OK or not history:
        return {}
    closes = [c for c in (_close(r) for r in history) if c is not None]
    prep = _prepare(closes)
    if prep is None:
        return {}
    results = {}
    specs = (
        ("lstm", "LSTM", lambda: LSTMNet(prep["n_features"])),
        ("tft", "Temporal Fusion Transformer (TFT-style)", lambda: TFTLite(prep["n_features"])),
    )
    for key, label, build in specs:
        torch.manual_seed(42)
        model = build()
        _train(model, prep["X"], prep["y"])
        with torch.no_grad():
            pred = float(model(prep["last"]).item()) * prep["ystd"]
        results[key] = _summary(label, pred, prep["last_close"])
    return results


def _legacy_card(result):
    """Wrap the existing XGBoost + Random Forest output as one card."""
    sig = str(result.get("signal", "")).upper()
    if not sig and result.get("target_price") is None:
        return {}
    direction = "UP" if sig in ("BUY", "UP") else "DOWN" if sig in ("SELL", "DOWN") else "HOLD"
    return {
        "xgboost_rf": {
            "label": "XGBoost + Random Forest",
            "direction": direction,
            "predicted_change_pct": None,
            "predicted_price": result.get("target_price"),
        }
    }


def build_models(result, history):
    """Returns models, consensus, and model_count for the analysis response."""
    models = {**_legacy_card(result), **run_deep_models(history)}
    if not models:
        return {}
    total = len(models)
    up = sum(1 for m in models.values() if m["direction"] == "UP")
    down = sum(1 for m in models.values() if m["direction"] == "DOWN")
    consensus = "UP" if up * 2 > total else "DOWN" if down * 2 > total else "MIXED"
    return {"models": models, "consensus": consensus, "model_count": total}