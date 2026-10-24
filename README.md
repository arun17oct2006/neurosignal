# Welcome to your Lovable project

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Open your project in the [Lovable editor](https://lovable.dev) and keep building.

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: connect the project to GitHub and every change made in Lovable is committed straight to your repository.
- **Full ownership**: this code is yours. Push to your repository and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```

## Built with

- TanStack Start
- TypeScript
- React
- Tailwind CSS

## Stockcache API

The FastAPI backend can use the AWS Stockcache API to cache daily closing-price
history and personalize ticker suggestions. Set these variables in the backend
process; the API key must never be exposed to the frontend:

```text
MARKETCACHE_API_URL=https://<api-id>.execute-api.<region>.amazonaws.com/dev/v1
MARKETCACHE_API_KEY=<api-key>
```

The backend sends HTTPS `POST` requests to `MARKETCACHE_API_URL` with an
`x-api-key` header and a JSON body containing an `action` plus its data:

- `cache_get`: `{ "action": "cache_get", "symbol": "AAPL", "cache_key": "US:AAPL:HISTORY:2Y:1D" }`;
  return `{ "data": null }` for a miss or
  `{ "data": { "rows": [{ "date": "2026-10-19", "close": 250.0 }] } }`
  for a hit. Cache rows must include at least 60 valid daily `date`/`close` rows.
- `cache_put`: same `symbol` and `cache_key`, with `data` as an object
  containing the daily rows, for example
  `{ "data": { "rows": [{ "date": "2026-10-19", "close": 250.0 }] } }`.
- `get_preferences`: include the verified JWT subject as `user_id` and return
  `{ "preferences": { "preferred_tickers": ["AAPL"] } }`.
- `get_history`: include the verified JWT subject as `user_id` and return
  `{ "history": [{ "ticker": "TSLA" }] }`. Preferences are listed before
  history when building the dashboard's personalized quick picks.
- `record_interaction`: include verified `user_id`, selected `ticker`, and
  `interaction_type: "ticker_selected"`.

The API Gateway integration should return JSON objects directly. A Stockcache
read failure falls back to yfinance; a write failure is logged without
discarding analysis results. Personalization and interaction failures are
reported to the caller.
