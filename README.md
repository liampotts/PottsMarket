# PottsMarket 🎯

A full-stack prediction markets platform inspired by Polymarket and Kalshi. Users can create markets, trade on outcomes, and discuss predictions in real-time.

**Live Demo**: [potts-market.vercel.app](https://potts-market.vercel.app)

---

## Features

### Core Trading
- **Market Creation** — Create prediction markets with custom titles, descriptions, and YES/NO outcomes
- **Real-time Pricing** — Prices update dynamically based on trading activity using CPMM
- **Position Tracking** — View your shares, current value, and P&L across all markets
- **Market Resolution** — Owners can resolve markets, triggering automatic payouts

### Social Features
- **Public Ledger** — See who bet on what and how much for each market
- **Comments** — Discuss predictions and share insights on any market
- **User Dashboard** — Track your portfolio, positions, and created markets

### Admin Features
- **Staff Privileges** — Admins can edit/delete any market
- **Django Admin** — Full backend management via `/admin/`

---

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│    Frontend     │   ←→    │     Backend     │   ←→    │    Database     │
│   React/Vite    │         │     Django      │         │   PostgreSQL    │
│   (Vercel)      │         │   (Railway)     │         │   (Railway)     │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

### Tech Stack
| Layer | Technology | Why |
|-------|------------|-----|
| Frontend | React + Vite | Fast HMR, modern tooling, simple setup |
| Styling | Vanilla CSS | Maximum control, no framework lock-in |
| Backend | Django | Batteries-included, excellent ORM, admin panel |
| API | Django Views (no DRF) | Lightweight, direct JSON responses |
| Database | PostgreSQL | Reliable, scalable, Railway-native |
| Auth | Django Sessions | Secure, built-in, cross-origin cookies |
| Hosting | Vercel + Railway | Free tier, easy CI/CD, separate scaling |

---

## Design Decisions

### 1. CPMM Pricing Model (Constant Product Market Maker)

We use a simplified CPMM inspired by Uniswap for price discovery:

```python
# Price = Other_Outcome_Pool / Total_Pool
# Example: If YES pool has $40 and NO pool has $60:
# Price(YES) = 60 / (40 + 60) = 0.60 (60%)
# Price(NO)  = 40 / (40 + 60) = 0.40 (40%)
```

**Why CPMM?**
- Self-correcting prices based on supply/demand
- No order book complexity
- Guaranteed liquidity (no stuck orders)
- Intuitive: buying an outcome raises its price

### 2. Session-Based Authentication (Not JWT)

We chose Django sessions with `SameSite=None; Secure` cookies over JWTs:

**Why Sessions?**
- Built-in Django support, no extra libraries
- Automatic CSRF protection
- Server-side session invalidation (log out everywhere)
- No token refresh complexity

**Cross-Origin Setup:**
```python
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True
```

### 3. No REST Framework

We use plain Django views returning `JsonResponse` instead of DRF:

**Why?**
- Fewer dependencies
- Direct control over response format
- Simpler debugging
- ~3x less boilerplate for our use case

### 4. Monorepo Structure

```
PottsMarket/
├── backend/          # Django project
│   ├── config/       # Settings, URLs
│   └── markets/      # Main app (models, views, api)
└── frontend/         # React/Vite project
    └── src/
        ├── components/
        ├── context/
        └── pages/
```

**Why Monorepo?**
- Single git history
- Atomic commits across stack
- Easier local development
- Shared deployment workflows

### 5. Feature Organization

All trading, comments, ledger, and resolution logic lives in `markets/views.py` as function-based views:

**Why FBVs over CBVs?**
- Explicit request handling
- Easier to read and debug
- No hidden inheritance magic
- Direct mapping: 1 URL = 1 function

---

## Data Model

```
Market
├── title, slug, description, status
├── created_by → User
├── winning_outcome → Outcome (nullable)
└── outcomes[]
    └── Outcome
        ├── name (e.g., "YES", "NO")
        ├── current_price
        └── pool_balance

Position
├── user → User
├── outcome → Outcome
└── shares

Comment
├── market → Market
├── user → User
├── text, created_at

UserProfile
├── user → User (1:1)
└── balance
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/markets/` | List all markets |
| POST | `/api/markets/` | Create market (auth) |
| GET/PUT | `/api/markets/<slug>/` | Get/update market |
| POST | `/api/markets/<slug>/trade/` | Buy/sell shares |
| POST | `/api/markets/<slug>/resolve/` | Resolve market |
| POST | `/api/markets/<slug>/redeem/` | Redeem winnings |
| DELETE | `/api/markets/<slug>/delete/` | Delete market |
| GET | `/api/markets/<slug>/ledger/` | Public trading ledger |
| GET/POST | `/api/markets/<slug>/comments/` | Get/post comments |
| GET | `/api/portfolio/` | User's positions + stats |
| POST | `/api/auth/login/` | Login |
| POST | `/api/auth/logout/` | Logout |
| POST | `/api/auth/signup/` | Register |
| GET | `/api/auth/me/` | Current user |

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (or use SQLite for local dev)

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

**Backend (.env or Railway):**
```
DEBUG=False
DATABASE_URL=postgres://...
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
CSRF_TRUSTED_ORIGINS=https://your-backend.railway.app
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=your-password
```

**Frontend (.env or Vercel):**
```
VITE_API_URL=https://your-backend.railway.app/api
```

---

## Deployment

### Railway (Backend)
1. Connect GitHub repo
2. Set root directory to `backend/`
3. Add environment variables
4. Add PostgreSQL plugin
5. Deploy triggers automatically on push

### Vercel (Frontend)
1. Connect GitHub repo
2. Set root directory to `frontend/`
3. Add `VITE_API_URL` environment variable
4. Deploy triggers automatically on push

---

## Project Stats

- **~3,400 lines** of custom code
- **595 lines** in main App.jsx
- **445 lines** in views.py
- **12 API endpoints**
- **5 database models**

---

## Future Ideas

- [ ] Leaderboard (rank users by net worth)
- [ ] Trading history with timestamps
- [ ] Market categories and search
- [ ] Price charts over time
- [ ] Mobile app (React Native)
- [ ] Real money integration

---

## Issues Solved

### 1. Cross-Origin Authentication (Cookie Blocking)
**Problem:**
Deploying the frontend on Vercel (`vercel.app`) and backend on Railway (`railway.app`) created a cross-origin scenario. Browsers block `SameSite=Lax` cookies (Django's default) from third-party domains in POST requests, causing "Authentication required" errors despite being logged in.

**Solution:**
We updated Django's `settings.py` to explicitly allow cross-site cookies, even when `DEBUG=True`:
```python
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True
```

### 2. Mobile Authentication (ITP / 3rd-Party Blocking)
**Problem:**
Even with the above settings, mobile browsers (especially Safari on iOS) enforce **Intelligent Tracking Prevention (ITP)**. This blocks *all* third-party cookies by default to prevent tracking. Since our API (`railway.app`) is a different domain from our frontend (`vercel.app`), the session cookie was blocked entirely on mobile, breaking login.

**Solution:**
We implemented **Vercel Rewrites** to proxy API requests.
1. Added `vercel.json` to front the API.
2. Used **Regex-based Rewrites** (`source: "/api/(.*)"`, `destination: ".../api/$1"`) because standard wildcards (`/api/:path*`) failed to correctly forward paths on Vercel.
3. Frontend now makes requests to its *own* domain (`/api/...`).
4. The browser sees this as a **first-party** request and allows the cookie.
5. Vercel forwards the cookie to the backend invisibly.

---

## License

MIT
