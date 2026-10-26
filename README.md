# NeuroSignal

**An ML-driven stock research dashboard with technical indicators, model-generated market signals, worldwide trending-stock discovery, and an AI research assistant.**

[Live Demo](https://ns.neurosignal.workers.dev/) · [Source Code](https://github.com/arun17oct2006/neurosignal)

NeuroSignal brings stock-market data, technical analysis, machine-learning experiments, and conversational company research into one web application. It supports Indian listings and US tickers, uses Google Sign-In for access, and connects to AWS-hosted caching and LLM-routing endpoints.

> **Disclaimer:** NeuroSignal is an educational and research project, not a financial advisory service. Its signals and model outputs are experimental, may be inaccurate or stale, and must not be treated as investment recommendations.

## Features

### Stock Dashboard

* Search for stocks or choose from curated stock shortcuts and worldwide trending lists.
* View the latest available market price, historical price chart, technical indicators, and a model-generated directional signal.
* Resolve ticker formats for Indian exchanges (`.NS` for NSE and `.BO` for BSE) and US symbols.
* Discover active stocks and day gainers through Yahoo Finance screeners, with a fallback list if the screener is unavailable.

### Machine-Learning Analysis

* Uses **XGBoost and Random Forest** regression models to estimate a five-trading-day return from historical daily prices and engineered features.
* Calculates features including RSI, 20-day simple moving-average spread, 20-day momentum, rolling volatility, and one-day return.
* Uses a chronological train/test split and selects the model with the lower test-set RMSE.
* Displays the resulting signal, predicted return, model name, evaluation metrics, chart data, and feature-importance values.

The model pipeline is intended for experimentation. It is not yet supported by walk-forward validation or evidence of consistent profitability.

### Ask Neuro — AI Research Assistant

* Answers stock-related questions using company identification and the latest available stock context where available.
* Adds market-price context to questions so responses can refer to the selected company and its price snapshot.
* Answers simple price-only questions locally when the required market data is available, avoiding an LLM call for those requests.
* Sends other questions to an existing AWS API Gateway endpoint connected to a multi-LLM router and semantic-caching system.
* Uses backend answer caching and request rate limiting to reduce repeated calls and control usage.

### Authentication and API Controls

* Google Sign-In with server-side ID-token verification.
* Short-lived JWT sessions for authenticated API requests.
* Configurable CORS origins.
* API keys for server-to-server calls to the AWS market-cache and LLM-router endpoints. These keys stay on the backend and must never be exposed through frontend environment variables.

## Architecture

```mermaid
flowchart TD
    U[User / Browser] --> FE[React + TypeScript Frontend<br/>Cloudflare Workers]
    FE -->|HTTPS + JWT| API[FastAPI Backend<br/>Render]
    FE -->|Google Sign-In Credential| AUTH[Google Token Verification<br/>JWT Issued by Backend]
    AUTH --> API

    API -->|Historical Price Cache| MC[AWS API Gateway<br/>MarketCache API]
    MC -. Cache Miss or
```
