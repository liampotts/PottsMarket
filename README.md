# PottsMarket

A Polymarket/Kalshi-style prediction market clone.

## Vision
Build a clean, fast web app where users can browse markets, see live prices, and trade shares on outcomes.

## Planned features
- Market discovery (categories, search, trending)
- Market detail page with order book + price chart
- Trading flow (buy/sell, positions)
- User accounts + portfolio
- Admin tooling for market creation

## Stack
- Frontend: React (Vite)
- Backend: Django
- Database: Postgres

## Getting started
### Backend
1. Create a Postgres database and user (or use your existing setup).
2. Copy `.env.example` to `.env` and update values.
3. Install deps and run the server:

```sh
./backend/.venv/bin/pip install -r backend/requirements.txt
./backend/.venv/bin/python backend/manage.py migrate
./backend/.venv/bin/python backend/manage.py runserver
```

### Frontend
```sh
cd frontend
npm install
npm run dev
```
