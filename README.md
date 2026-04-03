# CS2 Skin Analyzer / Arbitrage

FastAPI app: item analysis, arbitrage scan, Pricempire search. **No database** — it calls external APIs (CSFloat, CSGO Empire, Pricempire, Steam). **You do not need Supabase** unless you add your own persistence later.

## Run locally

```bash
cd cs2-arbitrage
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env    # then fill in keys
uvicorn server:app --host 127.0.0.1 --port 3001
```

Open http://127.0.0.1:3001 — API docs at `/docs`.

## Deploy on Railway

1. Push this folder to a **GitHub** repo (do not commit `.env`).
2. [Railway](https://railway.app) → **New project** → **Deploy from GitHub** → select the repo.
3. After the first deploy, open the service → **Variables** → add the same names as in `.env.example` with your real values:
   - `FLOAT_API_KEY` (or `CSFLOAT_API_KEY`)
   - `CSGOEMPIRE_API_KEY` (or `EMPIRE_API_KEY`)
   - `PRICEMPIRE_API_KEY` (optional)
   - `STEAM_API_KEY` (optional)
4. Railway sets `PORT` automatically; `railway.json` already runs:

   `uvicorn server:app --host 0.0.0.0 --port $PORT`

5. **Generate domain**: service → **Settings** → **Networking** → **Generate domain**.

**“Free” on Railway:** Railway is mostly **usage-based** (trial credits, then pay-as-you-go). It is not a guaranteed forever-free host for always-on Python. For **$0 sustained** options, use Render’s free tier (below) or similar.

## Deploy on Render (free tier)

Good fit if you want **no card / free web service** (with **cold starts** after idle).

1. Push repo to GitHub.
2. [Render](https://render.com) → **New** → **Web Service** → connect repo.
3. **Runtime:** Python  
4. **Build command:** `pip install -r requirements.txt`  
5. **Start command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`  
6. Add the same environment variables as on Railway.

Free instances **sleep** when idle; first request after sleep can take ~30–60s.

## Environment variables (full list)

| Variable | Purpose |
|----------|---------|
| `FLOAT_API_KEY` | CSFloat API |
| `CSFLOAT_API_KEY` | Alias for CSFloat (used in `server.py` if `FLOAT_API_KEY` unset) |
| `CSGOEMPIRE_API_KEY` | CSGO Empire |
| `EMPIRE_API_KEY` | Alias for Empire |
| `PRICEMPIRE_API_KEY` | Item search |
| `STEAM_API_KEY` | Optional Steam usage |

Missing Empire + Float keys → arbitrage endpoints return empty results with `keys_present: false` in meta.

## Why not Supabase?

This service does not read/write Postgres. Everything is computed from live API calls. Add Supabase only if you want saved scans, users, or caching.
