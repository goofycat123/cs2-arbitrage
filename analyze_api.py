"""Flip analyze endpoint logic — separated from server.py."""

import statistics
import time
from datetime import datetime, timezone

import httpx
from flip_analyzer import get_history, liquidity_score, CSFLOAT_FEE
from trend import fetch_float_price, parse_sales

# Collection metadata: name -> (type, year, volatile, note)
# type: "operation" = operation drop, "case" = case collection, "rare" = discontinued/rare pool
COLLECTIONS = {
    # Active operations / recent drops (volatile)
    "Anubis Collection": ("operation", 2023, True, "Operation Riptide+"),
    "Revolution Collection": ("case", 2023, True, "Revolution Case, active drop"),
    "Recoil Collection": ("case", 2022, True, "Recoil Case, active drop"),
    "Dreams & Nightmares Collection": ("case", 2022, True, "D&N Case, active drop"),
    "Snakebite Collection": ("case", 2021, True, "Snakebite Case, active drop"),
    "Fracture Collection": ("case", 2020, True, "Fracture Case, active drop"),
    "Prisma 2 Collection": ("case", 2020, True, "Prisma 2 Case, active drop"),
    "Prisma Collection": ("case", 2019, True, "Prisma Case, active drop"),
    "Danger Zone Collection": ("case", 2018, True, "Danger Zone Case, active drop"),
    "Horizon Collection": ("case", 2018, True, "Horizon Case, active drop"),
    "Clutch Collection": ("case", 2018, True, "Clutch Case, active drop"),
    "Spectrum 2 Collection": ("case", 2017, True, "Spectrum 2, active drop"),
    "Spectrum Collection": ("case", 2017, True, "Spectrum Case, active drop"),
    "Glove Collection": ("case", 2016, True, "Glove Case, active drop"),
    "Gamma 2 Collection": ("case", 2016, True, "Gamma 2, active drop"),
    "Gamma Collection": ("case", 2016, True, "Gamma Case, active drop"),
    "Chroma 3 Collection": ("case", 2016, True, "Chroma 3, active drop"),
    "Kilowatt Collection": ("case", 2024, True, "Kilowatt Case, very recent"),
    "Gallery Collection": ("case", 2025, True, "Gallery Case, newest drop"),
    # Terminals / new operation collections
    "Terminals Collection": ("operation", 2025, True, "Operation Overdrive, newest — high supply, prices dropping"),
    "Overdrive Collection": ("operation", 2025, True, "Operation Overdrive, newest"),
    # Semi-rare (cases discontinued but not ancient)
    "Chroma 2 Collection": ("case", 2015, False, "Chroma 2, discontinued case"),
    "Chroma Collection": ("case", 2015, False, "Chroma Case, discontinued"),
    "Phoenix Collection": ("case", 2014, False, "Operation Phoenix, discontinued"),
    "Breakout Collection": ("case", 2014, False, "Operation Breakout, discontinued"),
    "Huntsman Collection": ("case", 2014, False, "Huntsman Case, discontinued"),
    "Winter Offensive Collection": ("case", 2013, False, "Winter Offensive, discontinued"),
    "CS:GO Weapon Case 3 Collection": ("case", 2014, False, "Weapon Case 3, discontinued"),
    "CS:GO Weapon Case 2 Collection": ("case", 2013, False, "Weapon Case 2, discontinued"),
    "CS:GO Weapon Case Collection": ("case", 2013, False, "Weapon Case 1, OG discontinued"),
    "eSports 2013 Collection": ("case", 2013, False, "eSports 2013, rare"),
    "Bravo Collection": ("operation", 2013, False, "Operation Bravo, rare discontinued"),
    # Rare map collections (no longer dropping)
    "Cobblestone Collection": ("rare", 2014, False, "Cobblestone — discontinued souvenir pool, rare"),
    "Overpass Collection": ("rare", 2014, False, "Overpass collection"),
    "Cache Collection": ("rare", 2015, False, "Cache collection, discontinued"),
    "Gods and Monsters Collection": ("rare", 2015, False, "Gods & Monsters, discontinued"),
    "The Rising Sun Collection": ("rare", 2015, False, "Rising Sun, discontinued"),
    "Canals Collection": ("rare", 2017, False, "Canals, rare drop pool"),
    "St. Marc Collection": ("rare", 2017, False, "St. Marc, limited drop pool"),
    "Bank Collection": ("rare", 2013, False, "Bank, very old rare pool"),
    "Dust Collection": ("rare", 2013, False, "Dust, OG rare pool"),
    "Assault Collection": ("rare", 2018, False, "Assault, rare pool"),
    "Office Collection": ("rare", 2018, False, "Office, rare pool"),
    "Italy Collection": ("rare", 2013, False, "Italy, OG rare pool"),
    "Militia Collection": ("rare", 2018, False, "Militia, rare pool"),
    "Norse Collection": ("rare", 2021, False, "Norse, limited drop pool"),
    "Havoc Collection": ("rare", 2021, False, "Havoc, limited pool"),
    "Control Collection": ("rare", 2021, False, "Control, limited pool"),
    "Ancient Collection": ("rare", 2021, False, "Ancient, limited pool"),
    "Vertigo Collection": ("rare", 2019, False, "Vertigo, semi-rare pool"),
}


def _fetch_empire_listings(item_name: str) -> dict | None:
    """Fetch live Empire listings for the item — floor, avg, high, count, price list."""
    try:
        from config import CSGOEMPIRE_API_KEY
        from rate_limiter import wait_if_needed
        if not CSGOEMPIRE_API_KEY:
            return None
        wait_if_needed("empire")
        resp = httpx.get(
            "https://csgoempire.com/api/v2/trading/items",
            headers={"Authorization": f"Bearer {CSGOEMPIRE_API_KEY}"},
            params={"search": item_name, "auction": "no", "per_page": 30, "sort": "price", "order": "asc"},
            timeout=15
        )
        if resp.status_code != 200:
            return None
        items = resp.json().get("data", [])
        exact = [i for i in items if i.get("market_hash_name", "") == item_name]
        if exact:
            items = exact
        if not items:
            return None
        prices = sorted([i.get("market_value", 0) / 100 for i in items if i.get("market_value")])
        if not prices:
            return None
        return {
            "floor": round(prices[0], 2),
            "avg": round(sum(prices) / len(prices), 2),
            "high": round(prices[-1], 2),
            "count": len(prices),
            "prices": [round(p, 2) for p in prices],
        }
    except Exception:
        return None


def _fetch_parsed_sales(market_hash_name: str) -> list:
    """Individual CSFloat sales (timestamp + USD price). Empty if API fails."""
    try:
        from config import FLOAT_API_KEY
        from rate_limiter import wait_if_needed

        if not FLOAT_API_KEY:
            return []
        wait_if_needed("float")
        resp = httpx.get(
            "https://csfloat.com/api/v1/history/sales",
            headers={"Authorization": FLOAT_API_KEY},
            params={"market_hash_name": market_hash_name},
            timeout=25,
        )
        if resp.status_code != 200:
            return []
        raw = resp.json()
        rows = raw if isinstance(raw, list) else raw.get("data", raw.get("sales", []))
        return parse_sales(rows)
    except Exception:
        return []


def _window_stats_from_raw_sales(parsed: list, days: int) -> dict | None:
    """
    All numbers from individual CSFloat sales in the last `days` calendar days.
    - low / high: actual cheapest & priciest sale
    - median: typical trade (robust vs one-off sales)
    - mean_sale: arithmetic mean of every sale in the window (literal average of trades)
    `avg` is kept as median so profit/net_sell math matches the middle of real trades.
    """
    if not parsed:
        return None
    cutoff = time.time() - days * 86400
    prices = sorted(p["price"] for p in parsed if p["ts"] >= cutoff)
    if not prices:
        return None
    low = round(prices[0], 2)
    high = round(prices[-1], 2)
    med = round(statistics.median(prices), 2)
    mean_s = round(sum(prices) / len(prices), 2)
    return {
        "avg": med,
        "median": med,
        "mean_sale": mean_s,
        "low": low,
        "high": high,
        "sales": len(prices),
        "days": days,
        "basis": "sales",
    }


def _raw_sale_volatility_pct(parsed: list, days: int) -> float | None:
    """Robust volatility % from individual sale prices (MAD vs median)."""
    if not parsed or len(parsed) < 4:
        return None
    cutoff = time.time() - days * 86400
    prices = [p["price"] for p in parsed if p["ts"] >= cutoff]
    if len(prices) < 4:
        return None
    med = statistics.median(prices)
    if med <= 0:
        return 0.0
    mad = statistics.median(abs(x - med) for x in prices)
    return round((1.4826 * mad / med) * 100, 1)


def _detect_collection(item_name: str) -> dict | None:
    """Try to detect which collection an item belongs to based on name patterns."""
    # Check if CSFloat API returns collection info — if not, use heuristics
    name_lower = item_name.lower()
    for coll_name, (ctype, year, volatile, note) in COLLECTIONS.items():
        # Can't match by collection name from item name alone, so this is supplementary
        pass
    # We'll fetch from CSFloat listing which includes collection info
    try:
        from config import FLOAT_API_KEY
        from rate_limiter import wait_if_needed
        wait_if_needed("float")
        resp = httpx.get(
            "https://csfloat.com/api/v1/listings",
            headers={"Authorization": FLOAT_API_KEY},
            params={"market_hash_name": item_name, "limit": 1, "type": "buy_now"},
            timeout=15,
        )
        resp.raise_for_status()
        listings = resp.json().get("data", [])
        if not listings:
            return None
        item_data = listings[0].get("item", {})
        collection = item_data.get("collection")
        if not collection:
            return None
        # Match against our database
        for coll_name, (ctype, year, volatile, note) in COLLECTIONS.items():
            if coll_name.lower() in collection.lower() or collection.lower() in coll_name.lower():
                return {"name": collection, "type": ctype, "year": year, "volatile": volatile, "note": note}
        # Unknown collection — check year heuristic
        return {"name": collection, "type": "unknown", "year": None, "volatile": False, "note": f"{collection}"}
    except Exception:
        return None


def _check_pricempire_status() -> dict | None:
    """Check Pricempire API status and marketplace health."""
    try:
        from config import PRICEMPIRE_API_KEY
        if not PRICEMPIRE_API_KEY:
            return None

        resp = httpx.get(
            "https://api.pricempire.com/v4/free/service-status",
            params={"api_key": PRICEMPIRE_API_KEY},
            timeout=10
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        providers = data.get("providers", {})

        # Flag degraded marketplaces
        degraded = [k for k, v in providers.items() if v.get("status") == "degraded"]
        return {"operational": data.get("api", {}).get("operational"), "degraded": degraded}
    except Exception:
        return None


def _fetch_pricempire_context(item_name: str) -> dict | None:
    """Get marketplace diversity + health from Pricempire (only on analyze click)."""
    try:
        from config import PRICEMPIRE_API_KEY
        from rate_limiter import wait_if_needed

        if not PRICEMPIRE_API_KEY:
            return None

        # Call 1: Search (marketplace diversity)
        wait_if_needed("pricempire_free")
        search_resp = httpx.get(
            "https://api.pricempire.com/v4/free/search",
            params={"q": item_name[:50], "api_key": PRICEMPIRE_API_KEY},
            timeout=10
        )
        marketplace_count = 0
        if search_resp.status_code == 200:
            results = search_resp.json().get("results", [])
            marketplace_count = len(results)

        # Call 2: Service status (check for stale/degraded markets)
        wait_if_needed("pricempire_free")
        status_resp = httpx.get(
            "https://api.pricempire.com/v4/free/service-status",
            params={"api_key": PRICEMPIRE_API_KEY},
            timeout=10
        )
        degraded_markets = []
        csfloat_stale = False
        csfloat_last_updated_hours = None
        if status_resp.status_code == 200:
            data = status_resp.json()
            providers = data.get("providers", {})
            degraded_markets = [k for k, v in providers.items() if v.get("status") == "degraded"]
            # Check if CSFloat status feed looks stale by timestamp age.
            if "csfloat" in providers:
                last_updated = providers["csfloat"].get("last_updated")
                if last_updated:
                    try:
                        dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                        now = datetime.now(timezone.utc)
                        age_hours = (now - dt).total_seconds() / 3600
                        csfloat_last_updated_hours = round(age_hours, 1)
                        if age_hours > 3:
                            csfloat_stale = True
                    except Exception:
                        pass

        return {
            "marketplace_count": marketplace_count,
            "degraded_markets": degraded_markets,
            "csfloat_stale": csfloat_stale,
            "csfloat_last_updated_hours": csfloat_last_updated_hours,
        }
    except Exception:
        return None


def run_analysis(
    item_name: str,
    buy_price: float,
    wear: str = "FN",
    float_min=None,
    float_max=None,
    fade_min_pct=None,
    fade_max_pct=None,
    live_price_override: float | None = None,
) -> dict:
    """Full flip analysis. Returns dict with verdict, windows, chart, trend, liquidity."""
    wear_map = {"FN": "Factory New", "MW": "Minimal Wear", "FT": "Field-Tested", "WW": "Well-Worn", "BS": "Battle-Scarred"}
    wear_name = wear_map.get(wear, "Factory New")

    # Fade % → float range override (100% fade = float 0.00, 90% = float 0.07 for FN)
    if "Fade" in item_name and (fade_min_pct is not None or fade_max_pct is not None):
        max_wear_floats = {"FN": 0.07, "MW": 0.15, "FT": 0.38, "WW": 0.45, "BS": 1.0}
        mwf = max_wear_floats.get(wear, 0.07)
        # float = (100 - fade_pct) * mwf / 10
        if fade_min_pct is not None:
            float_max = round(min(mwf, (100 - fade_min_pct) * mwf / 10), 4)
        if fade_max_pct is not None:
            float_min = round(max(0.0, (100 - fade_max_pct) * mwf / 10), 4)

    # Detect if item has float values (charms, stickers, vanilla knives don't)
    no_float_keywords = ["Charm", "Sticker", "Vanilla", "Skeleton Key", "Agent", "Patch", "Collectible"]
    has_float = not any(keyword in item_name for keyword in no_float_keywords)

    if not has_float:
        # No-float items: return live price only, no history
        if live_price_override is not None:
            live_price = live_price_override
        else:
            try:
                live_price = fetch_float_price(item_name, float_min=None, float_max=None)
            except Exception:
                live_price = None
        return {
            "item": item_name, "buy_price": buy_price, "verdict": "INFO",
            "verdict_detail": "No float value - live price only (no historical data)",
            "live_price": live_price, "live_net": round(live_price * 0.98, 2) if live_price else None,
            "live_profit": round((live_price * 0.98 - buy_price), 2) if live_price else None,
            "live_pct": round(((live_price * 0.98 - buy_price) / buy_price * 100), 1) if live_price else None,
            "w7": None, "w30": None, "w60": None, "liquidity": None, "chart": [],
            "trend_notes": [{"text": "No float value — live price only", "type": "info"}]
        }

    # For float items: normal analysis with wear condition
    if any(w in item_name for w in wear_map.values()):
        search_name = item_name
    else:
        search_name = f"{item_name} ({wear_name})"

    try:
        data = get_history(search_name)
    except Exception as e:
        return {"error": f"CSFloat API error: {e}"}
    if not data:
        return {"error": "No data from CSFloat"}
    data = sorted(data, key=lambda x: x["day"], reverse=True)

    parsed_sales = _fetch_parsed_sales(search_name)

    def _robust_sales_days(prices: list[float], counts: list[int]) -> list[tuple[float, int]]:
        """
        Remove likely premium outlier days (e.g. rare sticker/float prints) so
        liquid-market baseline pricing drives the signal.
        """
        sales_days = [(prices[i], counts[i]) for i in range(len(prices)) if counts[i] > 0]
        if len(sales_days) < 5:
            return sales_days

        vals = [p for p, _ in sales_days]
        med = statistics.median(vals)
        abs_dev = [abs(p - med) for p in vals]
        mad = statistics.median(abs_dev)
        if mad == 0:
            mad = max(med * 0.03, 0.01)

        kept: list[tuple[float, int]] = []
        for p, c in sales_days:
            z = abs(p - med) / (1.4826 * mad)
            # Low-volume extreme prints are usually premium specials.
            if c <= 2 and z > 3:
                continue
            # Very extreme moves are removed even with higher volume.
            if z > 6:
                continue
            kept.append((p, c))

        return kept if len(kept) >= 3 else sales_days

    def wstats(days):
        raw = _window_stats_from_raw_sales(parsed_sales, days)
        if raw:
            return raw
        # Fallback: CSFloat graph is daily buckets only (no per-sale detail).
        s = data[:days]
        if not s:
            return None
        prices = [d["avg_price"] / 100 for d in s]
        counts = [d["count"] for d in s]
        sales_days = _robust_sales_days(prices, counts)
        if sales_days:
            weight_sum = sum(c for _, c in sales_days)
            avg = sum(p * c for p, c in sales_days) / max(weight_sum, 1)
        else:
            avg = sum(prices) / len(prices)
        if sales_days:
            low = round(min(p for p, c in sales_days), 2)
            high = round(max(p for p, c in sales_days), 2)
        else:
            low = round(min(prices), 2)
            high = round(max(prices), 2)
        return {
            "avg": round(avg, 2),
            "median": round(avg, 2),
            "low": low,
            "high": high,
            "sales": sum(counts),
            "days": len(s),
            "basis": "graph",
        }

    w7, w30, w60 = wstats(7), wstats(30), wstats(60)
    liq = liquidity_score(w7, w30, w60)
    sale_based = bool(parsed_sales)
    stat_lbl = "median sale" if sale_based else "daily estimate"

    # Get marketplace listing count (only called on analyze)
    pm_context = _fetch_pricempire_context(search_name)
    marketplace_count = 0
    csfloat_down = False
    csfloat_stale = False
    csfloat_age_h = None
    if pm_context:
        marketplace_count = pm_context.get("marketplace_count", 0)
        csfloat_down = "csfloat" in pm_context.get("degraded_markets", [])
        csfloat_stale = bool(pm_context.get("csfloat_stale"))
        csfloat_age_h = pm_context.get("csfloat_last_updated_hours")

    # Empire live listings for direct comparison
    empire = _fetch_empire_listings(search_name)

    def window_result(w):
        if not w:
            return None
        net_sell = w["avg"] * (1 - CSFLOAT_FEE)
        profit = net_sell - buy_price
        pct = (profit / buy_price) * 100
        buffer = ((w["low"] - buy_price) / buy_price) * 100
        return {**w, "net_sell": round(net_sell, 2), "profit": round(profit, 2), "pct": round(pct, 1), "buffer": round(buffer, 1)}

    # Live CSFloat price (buy-now only)
    if live_price_override is not None:
        live_price = live_price_override
    else:
        try:
            live_price = fetch_float_price(search_name, float_min=float_min, float_max=float_max)
        except Exception:
            live_price = None
    live_net = round(live_price * (1 - CSFLOAT_FEE), 2) if live_price else None
    live_profit = round(live_net - buy_price, 2) if live_net else None
    live_pct = round((live_profit / buy_price) * 100, 1) if live_profit else None

    pump = round(((w7["avg"] / w30["avg"]) - 1) * 100, 1) if w7 and w30 else 0
    drop_60to7 = round(((w7["avg"] / w60["avg"]) - 1) * 100, 1) if w7 and w60 else None
    spd = w7["sales"] / 7 if w7 else 0
    low7 = w7["low"] if w7 else 0

    # --- Mathematical risk scoring ---
    def _count_dips_graph(days: int) -> int:
        subset = data[:days]
        if not subset:
            return 0
        prices = [d["avg_price"] / 100 for d in subset]
        counts = [d["count"] for d in subset]
        robust = _robust_sales_days(prices, counts)
        if not robust:
            return 0
        return sum(1 for p, _ in robust if p < buy_price)

    def _count_dips_sales(days: int) -> int:
        cutoff = time.time() - days * 86400
        return sum(1 for p in parsed_sales if p["ts"] >= cutoff and p["price"] < buy_price)

    if parsed_sales:
        dips_7d = _count_dips_sales(7)
        dips_30d = _count_dips_sales(30)
    else:
        dips_7d = _count_dips_graph(7)
        dips_30d = _count_dips_graph(30)

    days_30 = min(len(data), 30)

    if parsed_sales:
        v = _raw_sale_volatility_pct(parsed_sales, 30)
        volatility = v if v is not None else 0.0
    elif w30 and days_30 > 1:
        prices_30 = [d["avg_price"] / 100 for d in data[:30]]
        counts_30 = [d["count"] for d in data[:30]]
        robust_30 = _robust_sales_days(prices_30, counts_30)
        if robust_30:
            expanded_prices: list[float] = []
            for p, c in robust_30:
                expanded_prices.extend([p] * max(1, min(c, 20)))
            med = statistics.median(expanded_prices)
            abs_dev = [abs(p - med) for p in expanded_prices]
            mad = statistics.median(abs_dev)
            robust_sigma = 1.4826 * mad
            volatility = round((robust_sigma / med) * 100, 1) if med > 0 else 0
        else:
            volatility = 0
    else:
        volatility = 0

    if parsed_sales:
        c30 = time.time() - 30 * 86400
        in_30 = [p for p in parsed_sales if p["ts"] >= c30]
        if in_30:
            below = sum(1 for p in in_30 if p["price"] < buy_price)
            drop_prob = round(100 * below / len(in_30), 1)
        else:
            drop_prob = 0.0
    else:
        drop_prob = round((dips_30d / days_30) * 100, 1) if days_30 > 0 else 0

    # Composite profit score using multiple sources
    profit_scores = []
    if live_pct is not None:
        profit_scores.append(("live", live_pct))
    if w7:
        w7_pct = round((w7["avg"] * (1 - CSFLOAT_FEE) - buy_price) / buy_price * 100, 1)
        profit_scores.append(("7d", w7_pct))
    if w30:
        w30_pct = round((w30["avg"] * (1 - CSFLOAT_FEE) - buy_price) / buy_price * 100, 1)
        profit_scores.append(("30d", w30_pct))

    # Best and worst case
    all_pcts = [p for _, p in profit_scores]
    best_pct = max(all_pcts) if all_pcts else 0
    worst_pct = min(all_pcts) if all_pcts else 0
    avg_pct = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else 0

    # Use avg of all sources for verdict, not just live
    real_pct = avg_pct
    sources_str = " / ".join(f"{s}={p}%" for s, p in profit_scores)

    # --- Verdict label ---
    if real_pct >= 2 and pump <= 15 and dips_7d == 0 and spd >= 2 and volatility < 8:
        verdict = "BUY"
    elif real_pct >= 2 and dips_7d == 0 and dips_30d <= 3 and volatility < 12:
        verdict = "BUY"
    elif real_pct >= 2 and (dips_7d > 0 or dips_30d > 5):
        verdict = "RISKY"
    elif real_pct < 2 and worst_pct < 0:
        verdict = "SKIP"
    elif real_pct < 2:
        verdict = "SKIP"
    elif pump > 15:
        verdict = "SKIP"
    elif spd < 1:
        verdict = "RISKY"
    else:
        verdict = "SKIP"

    # --- Narrative verdict_detail ---
    lines = []

    # 1. Live price situation
    if live_pct is not None:
        if live_pct < 0:
            lines.append(f"Live CSFloat at ${live_price:.0f} is ${buy_price - live_price:.0f} below your buy — you'd lose money selling right now.")
        elif live_pct < 2:
            lines.append(f"Live at ${live_price:.0f} barely covers the 2% fee ({live_pct:+.1f}%).")
        else:
            lines.append(f"Live at ${live_price:.0f} is profitable now ({live_pct:+.1f}% after fee).")

    # 2. Historical context
    if w30:
        w30_pct_r = round((w30["avg"] * 0.98 - buy_price) / buy_price * 100, 1)
        if w30_pct_r >= 5:
            lines.append(f"30d {stat_lbl} ${w30['avg']:.0f} net ~${w30['avg'] * 0.98:.0f} after 2% fee = +{w30_pct_r}% vs buy — market supports this level.")
        elif w30_pct_r >= 2:
            lines.append(f"30d {stat_lbl} ${w30['avg']:.0f} = +{w30_pct_r}% vs buy — thin margin.")
        else:
            lines.append(f"30d {stat_lbl} ${w30['avg']:.0f} = {w30_pct_r:+}% vs buy — tight or negative at this entry.")

    # 3. Risk factors
    if pump > 15:
        lines.append(f"7d vs 30d {stat_lbl}: +{pump:.0f}% — short window trading above the longer norm, correction risk.")
    if dips_7d > 0:
        if sale_based:
            lines.append(f"{dips_7d} individual sales in the last 7d below your buy; {drop_prob}% of last-30d sales also below buy.")
        else:
            lines.append(f"{dips_7d} days in the last 7d had avg below your buy; ~{drop_prob}% of last-30d days below buy (graph estimate).")
    if volatility > 12:
        lines.append(f"Very volatile ({volatility}%) — hard to predict where it lands after 7d lock.")
    elif volatility > 6:
        lines.append(f"Moderate volatility ({volatility}%) — some price risk during lock.")

    # 4. Liquidity
    if liq and isinstance(liq, dict):
        spd_v = liq.get("spd_7", 0)
        grade = liq.get("grade", "?")
        grade_text = {"A": "sells daily — instant flip", "B": "1-3 day wait typical", "C": "may take up to a week", "D": "slow mover, could sit past lock", "F": "illiquid, avoid"}.get(grade, "")
        lines.append(f"Liquidity grade {grade} ({spd_v}/day) — {grade_text}.")

    # 5. Empire spread
    if empire and w30:
        gap = round((w30["avg"] - empire["avg"]) / empire["avg"] * 100, 1)
        if gap > 5:
            lines.append(f"Empire avg ${empire['avg']:.0f} vs CSFloat ${w30['avg']:.0f} = {gap:.0f}% spread — solid arbitrage gap.")
        else:
            lines.append(f"Empire avg ${empire['avg']:.0f} ({empire['count']} live listings).")

    # 6. Bottom line
    if verdict == "BUY":
        max_safe = round(w30["avg"] * 0.98 / 1.02, 0) if w30 else buy_price
        lines.append(f"Buy at or below ${max_safe:.0f} for safe 2%+ margin.")
    elif verdict == "SKIP" and real_pct < 2 and w30:
        target = round(w30["avg"] * 0.98 / 1.03, 0)
        lines.append(f"Need to pay below ${target:.0f} to clear 3% margin — pass at ${buy_price:.0f}.")
    elif verdict == "RISKY" and live_pct is not None and live_pct < 0 and w30:
        target = round(w30["avg"] * 0.98 / 1.04, 0)
        lines.append(f"Wait for live price to rise, or buy below ${target:.0f} for adequate buffer.")
    elif verdict == "SKIP" and pump > 15:
        lines.append(f"Wait for pump to cool — 30d {stat_lbl} ${w30['avg']:.0f} is a saner reference.")

    verdict_detail = " ".join(lines) if lines else f"Avg profit {real_pct}% across {sources_str}."

    # Trend analysis
    trend_notes = []

    # 7d vs 30d momentum (median of real sales when available)
    if pump > 15:
        trend_notes.append({"text": f"7d vs 30d {stat_lbl}: +{pump}% — short window inflated vs longer norm", "type": "danger"})
    elif pump > 5:
        trend_notes.append({"text": f"7d vs 30d {stat_lbl}: +{pump}% — rising, watch for correction", "type": "warn"})
    elif pump < -10:
        trend_notes.append({"text": f"7d vs 30d {stat_lbl}: {pump}% — dropping fast", "type": "danger"})
    elif pump < -3:
        trend_notes.append({"text": f"7d vs 30d {stat_lbl}: {pump}% — drifting down", "type": "warn"})
    else:
        trend_notes.append({"text": f"7d vs 30d {stat_lbl}: {'+' if pump > 0 else ''}{pump}% — stable", "type": "safe"})

    # 60d long-term direction (median sales)
    if drop_60to7 is not None:
        if drop_60to7 < -15:
            trend_notes.append({"text": f"7d vs 60d {stat_lbl}: {drop_60to7}% — major decline vs 2mo norm", "type": "danger"})
        elif drop_60to7 < -5:
            trend_notes.append({"text": f"7d vs 60d {stat_lbl}: {drop_60to7}% — softer than 2mo norm", "type": "warn"})
        elif drop_60to7 > 10:
            trend_notes.append({"text": f"7d vs 60d {stat_lbl}: +{drop_60to7}% — strong vs 2mo norm", "type": "safe"})
        else:
            trend_notes.append({"text": f"7d vs 60d {stat_lbl}: {'+' if drop_60to7 > 0 else ''}{drop_60to7}% — in line long-term", "type": "safe"})

    # Volume change
    if w7 and w30 and w30["sales"] > 0:
        vol_change = round(((w7["sales"] / 7) / (w30["sales"] / 30) - 1) * 100, 1)
        if vol_change > 50:
            trend_notes.append({"text": f"Volume spike: +{vol_change}% vs 30d avg — hype or dump incoming", "type": "warn"})
        elif vol_change < -40:
            trend_notes.append({"text": f"Volume drop: {vol_change}% vs 30d avg — drying up", "type": "warn"})

    if marketplace_count > 0:
        trend_notes.append({"text": f"Listed on {marketplace_count} marketplace variants", "type": "info"})

    if csfloat_down:
        trend_notes.append({"text": "⚠️ CSFloat API degraded — live prices may be unreliable", "type": "danger"})
    elif csfloat_stale:
        age_txt = f"{csfloat_age_h}h ago" if csfloat_age_h is not None else "a while ago"
        trend_notes.append({"text": f"CSFloat status feed may be stale (last update {age_txt})", "type": "warn"})

    # Volatility note
    if volatility > 12:
        trend_notes.append({"text": f"Volatility: {volatility}% — very unstable, high risk during 7d lock", "type": "danger"})
    elif volatility > 6:
        trend_notes.append({"text": f"Volatility: {volatility}% — moderate swings", "type": "warn"})
    else:
        trend_notes.append({"text": f"Volatility: {volatility}% — tight price range, predictable", "type": "safe"})

    # Float filtering note
    if not has_float:
        trend_notes.append({"text": "No float values — prices not filtered by condition/float range", "type": "info"})

    # Collection info
    coll = _detect_collection(search_name)
    if coll:
        if coll["volatile"]:
            trend_notes.append({"text": f"Collection: {coll['name']} ({coll['year']}) — {coll['note']}, expect price drops", "type": "danger"})
        elif coll["type"] == "rare":
            trend_notes.append({"text": f"Collection: {coll['name']} — {coll['note']}, supply limited", "type": "safe"})
        else:
            trend_notes.append({"text": f"Collection: {coll['name']} — {coll['note']}", "type": "info"})

    # Chart: daily CSFloat graph buckets (visual trend only — cards use per-sale stats when available)
    chart_data = [{"day": d["day"], "avg": round(d["avg_price"] / 100, 2), "sales": d["count"]} for d in data[:60]]

    if sale_based:
        trend_notes.insert(0, {
            "text": "7d / 30d / 60d numbers = real CSFloat sales (low, high, median + mean of trades). Chart = daily graph.",
            "type": "info",
        })
    else:
        trend_notes.insert(0, {
            "text": "No per-sale history returned — windows use daily graph buckets (less precise for tight margins).",
            "type": "warn",
        })

    return {
        "item": item_name, "buy_price": buy_price,
        "live_price": live_price, "live_net": live_net, "live_profit": live_profit, "live_pct": live_pct,
        "w7": window_result(w7), "w30": window_result(w30), "w60": window_result(w60),
        "liquidity": liq, "pump_pct": pump, "trend_notes": trend_notes,
        "chart": chart_data, "volatility": volatility, "drop_prob": drop_prob,
        "dips_7d": dips_7d, "dips_30d": dips_30d,
        "verdict": verdict, "verdict_detail": verdict_detail,
        "empire": empire,
        "stats_basis": "sales" if sale_based else "graph",
    }
