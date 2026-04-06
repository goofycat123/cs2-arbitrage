"""Flip analyze endpoint logic — separated from server.py."""

import statistics
import time
from datetime import datetime, timezone

import httpx
from config import SELL_VENUES
from flip_analyzer import get_history, liquidity_score, CSFLOAT_FEE
from trend import fetch_float_price, parse_sales


def _verdict_eli5(verdict: str, sell_label: str, live_pct: float | None, live_price: float | None) -> str:
    if verdict == "INFO":
        return (
            f"Like a price tag with no yesterday: we only know what {sell_label} asks today — "
            "there is no float/history graph for this type of item here."
        )
    if verdict == "BUY":
        return (
            f"Simple version: if you sell on {sell_label} for about what we show today, you can make a little extra "
            "after fees — and enough people trade this that you are not stuck holding it forever."
        )
    if verdict == "RISKY":
        return (
            f"Simple version: the math can work on {sell_label}, but the price has been jumpy or dipped near what "
            "you pay — like a bouncy ball, it might land lower when you need to sell."
        )
    return (
        "Simple version: after fees you do not get enough extra money vs what you pay, or the price looks too hype-y — "
        "like paying full price for candy that usually goes on sale."
    )


def _liquidity_eli5(liq: dict | None) -> str:
    if not liq or liq.get("score") is None:
        return ""
    g, s = liq.get("grade", "?"), liq.get("score", 0)
    tail = {
        "A": "So many sales lately that you should find a buyer quickly.",
        "B": "Pretty popular — you might wait a couple days, not weeks.",
        "C": "Okay, but you might wait a while like standing in a slow line.",
        "D": "Few buyers — you could be stuck past a trade lock.",
        "F": "Almost nobody buying — easy to get stuck with it.",
    }.get(g, "Check sales speed before you buy.")
    return f"The big number ({s}) is how easy it is to resell. Grade {g}: {tail}"


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


def _fetch_live_listed_for_venue(
    search_name: str,
    venue: str,
    float_min,
    float_max,
    live_price_override: float | None,
) -> tuple[float | None, str | None]:
    """Returns (gross_listed_price, error_reason). Price is before marketplace sell fee."""
    if live_price_override is not None:
        return live_price_override, None
    v = (venue or "csfloat").lower()
    if v == "empire":
        emp = _fetch_empire_listings(search_name)
        return (float(emp["floor"]), None) if emp else (None, "No Empire listings found")
    from config import FLOAT_API_KEY
    if not FLOAT_API_KEY:
        return None, "FLOAT_API_KEY not configured - set it in Railway Variables"
    try:
        price = fetch_float_price(search_name, float_min=float_min, float_max=float_max)
        if price is None:
            return None, "No CSFloat buy-now listings for this item/float range"
        return price, None
    except Exception as e:
        err = str(e)
        if "429" in err or "too many" in err.lower():
            return None, "CSFloat rate limited (429) - wait 60s and retry"
        if "401" in err or "403" in err or "unauthorized" in err.lower():
            return None, "CSFloat API key invalid or expired (401/403)"
        if "timeout" in err.lower():
            return None, "CSFloat API timed out"
        return None, f"CSFloat error: {err[:120]}"


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
            params={"market_hash_name": market_hash_name, "limit": 1000},
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


def _fetch_cs2_market_context() -> dict | None:
    """Fetch latest official CS2 update headlines to flag fresh-update FOMO windows."""
    try:
        resp = httpx.get(
            "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/",
            params={"appid": 730, "count": 6, "maxlength": 220, "format": "json"},
            timeout=10,
        )
        if resp.status_code != 200:
            return None

        items = resp.json().get("appnews", {}).get("newsitems", [])
        if not items:
            return None

        now_ts = datetime.now(timezone.utc).timestamp()
        latest = items[0]
        latest_age_hours = round((now_ts - latest.get("date", now_ts)) / 3600, 1)
        titles = [str(n.get("title", "")) for n in items]
        joined = " | ".join(titles).lower()

        fomo_terms = [
            "case",
            "capsule",
            "sticker",
            "armory",
            "collection",
            "major",
            "operation",
            "update",
            "release notes",
            "patch notes",
        ]
        has_fomo_catalyst = any(t in joined for t in fomo_terms)

        return {
            "latest_title": latest.get("title", "CS2 update"),
            "latest_age_hours": latest_age_hours,
            "has_fomo_catalyst": has_fomo_catalyst,
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
    sell_venue: str = "csfloat",
) -> dict:
    """Full flip analysis. Returns dict with verdict, windows, chart, trend, liquidity."""
    sell_venue = (sell_venue or "csfloat").lower().strip()
    if sell_venue not in SELL_VENUES:
        sell_venue = "csfloat"
    sell_fee = SELL_VENUES[sell_venue]["fee"]
    sell_label = SELL_VENUES[sell_venue]["label"]

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
    no_float_keywords = ["Charm", "Sticker", "Vanilla", "Skeleton Key", "Agent", "Patch", "Collectible",
                         "Case", "Capsule", "Package", "Souvenir", "Graffiti", "Pin", "Coin",
                         "Music Kit", "Tool"]
    has_float = not any(keyword in item_name for keyword in no_float_keywords)

    if not has_float:
        # Commodity items (cases, stickers, capsules, etc.) — no float, but full price history
        live_price, live_price_error = _fetch_live_listed_for_venue(
            item_name, sell_venue, None, None, live_price_override
        )
        live_net = round(live_price * (1 - sell_fee), 2) if live_price else None
        live_profit = round(live_net - buy_price, 2) if live_net is not None else None
        live_pct = round((live_profit / buy_price) * 100, 1) if live_profit is not None else None

        # Fetch price history (graph + individual sales)
        commodity_chart = []
        w7c = w30c = w60c = w180c = None
        commodity_liq = None
        empire_c = _fetch_empire_listings(item_name)
        try:
            cdata = get_history(item_name)
            if cdata:
                cdata = sorted(cdata, key=lambda x: x["day"], reverse=True)
                parsed_c = _fetch_parsed_sales(item_name)

                def wstats_c(days):
                    raw = _window_stats_from_raw_sales(parsed_c, days)
                    if raw:
                        return raw
                    s = cdata[:days]
                    if not s:
                        return None
                    prices = [d["avg_price"] / 100 for d in s]
                    counts = [d["count"] for d in s]
                    import statistics as _st
                    avg = sum(p * c for p, c in zip(prices, counts)) / max(sum(counts), 1)
                    return {
                        "avg": round(avg, 2),
                        "median": round(avg, 2),
                        "low": round(min(prices), 2),
                        "high": round(max(prices), 2),
                        "sales": sum(counts),
                        "days": len(s),
                        "basis": "graph",
                    }

                w7c = wstats_c(7)
                w30c = wstats_c(30)
                w60c = wstats_c(60)
                w180c = wstats_c(180)
                commodity_liq = liquidity_score(w7c, w30c, w60c)
                commodity_chart = [{"day": d["day"], "avg": round(d["avg_price"] / 100, 2), "sales": d["count"]}
                                    for d in cdata[:400]]
        except Exception:
            pass

        def _window_result_c(w):
            if not w:
                return None
            net_s = w["avg"] * (1 - sell_fee)
            profit = net_s - buy_price
            pct = (profit / buy_price) * 100
            buffer = ((w["low"] - buy_price) / buy_price) * 100
            return {**w, "net_sell": round(net_s, 2), "profit": round(profit, 2), "pct": round(pct, 1), "buffer": round(buffer, 1)}

        # Verdict detail for commodities
        detail_parts = []
        if live_pct is not None:
            sign = "+" if live_pct >= 0 else ""
            detail_parts.append(
                f"Floor ${live_price:.2f} on {sell_label} -> net ${live_net:.2f} after {int(sell_fee*100)}% fee = {sign}{live_pct:.1f}% vs your ${buy_price:.2f} buy."
            )
        elif w30c:
            w30n = round(w30c["avg"] * (1 - sell_fee), 2)
            w30p = round((w30n - buy_price) / buy_price * 100, 1)
            detail_parts.append(
                f"No live floor right now. 30d avg ${w30c['avg']:.2f} -> net ${w30n:.2f} after fee = {'+' if w30p >= 0 else ''}{w30p:.1f}% vs ${buy_price:.2f} buy."
            )
        else:
            detail_parts.append(f"No price data available on {sell_label}.")
        if w30c:
            pump_c = round(((w7c["avg"] / w30c["avg"]) - 1) * 100, 1) if w7c and w30c else 0
            if abs(pump_c) > 10:
                detail_parts.append(f"Price {'up' if pump_c > 0 else 'down'} {abs(pump_c):.0f}% vs 30d avg — {'possible pump' if pump_c > 0 else 'declining'}.")
            elif commodity_liq and isinstance(commodity_liq, dict):
                g = commodity_liq.get("grade", "?")
                spd = commodity_liq.get("spd_7", 0)
                liq_txt = {"A": "sells daily", "B": "1-3 day wait", "C": "up to a week", "D": "slow mover", "F": "illiquid"}.get(g, "")
                detail_parts.append(f"Liquidity {g} ({spd}/day — {liq_txt}).")

        trend_notes_c = [{"text": "Commodity — no float value (case, sticker, capsule, etc.)", "type": "info"}]
        if live_price_error:
            trend_notes_c.append({"text": live_price_error, "type": "danger"})
        if empire_c:
            gap = round((empire_c["floor"] - (w30c["avg"] if w30c else live_price or 0)) / (w30c["avg"] if w30c else live_price or 1) * 100, 1) if w30c or live_price else None
            trend_notes_c.append({"text": f"Empire floor ${empire_c['floor']:.2f} ({empire_c['count']} listings)", "type": "info"})

        return {
            "item": item_name, "buy_price": buy_price, "verdict": "INFO",
            "verdict_detail": " ".join(detail_parts) if detail_parts else f"Commodity — no float value.",
            "verdict_eli5": "", "liquidity_eli5": "",
            "live_price": live_price,
            "live_price_error": live_price_error,
            "live_net": live_net,
            "live_profit": live_profit,
            "live_pct": live_pct,
            "sell_venue": sell_venue,
            "sell_venue_label": sell_label,
            "sell_fee_pct": round(sell_fee * 100, 2),
            "w7": _window_result_c(w7c),
            "w30": _window_result_c(w30c),
            "w60": _window_result_c(w60c),
            "w180": _window_result_c(w180c),
            "liquidity": commodity_liq,
            "chart": commodity_chart,
            "empire": empire_c,
            "trend_notes": trend_notes_c,
        }

    # For float items: normal analysis with wear condition
    if any(w in item_name for w in wear_map.values()):
        search_name = item_name
    else:
        search_name = f"{item_name} ({wear_name})"

    try:
        data = get_history(search_name)
    except Exception:
        data = []

    # If no data with wear appended, retry without it (handles vanilla knives automatically)
    if not data and search_name != item_name:
        try:
            data_bare = get_history(item_name)
            if data_bare:
                data = data_bare
                search_name = item_name
        except Exception:
            pass

    data = sorted(data, key=lambda x: x["day"], reverse=True)

    parsed_sales = _fetch_parsed_sales(search_name)

    # If no graph data but we have individual sales, we can still do analysis
    if not data and not parsed_sales:
        live_price2, live_price_error2 = _fetch_live_listed_for_venue(
            search_name, sell_venue, float_min, float_max, live_price_override
        )
        empire2 = _fetch_empire_listings(search_name)
        live_net2 = round(live_price2 * (1 - sell_fee), 2) if live_price2 else None
        live_profit2 = round(live_net2 - buy_price, 2) if live_net2 is not None else None
        live_pct2 = round((live_profit2 / buy_price) * 100, 1) if live_profit2 is not None else None
        detail2 = []
        if live_pct2 is not None:
            detail2.append(f"Floor ${live_price2:.2f} on {sell_label} -> net ${live_net2:.2f} after {int(sell_fee*100)}% fee = {'+' if live_pct2 >= 0 else ''}{live_pct2:.1f}% vs your ${buy_price:.2f} buy.")
        else:
            detail2.append(f"No CSFloat listing or sales history found for this item.")
        if empire2:
            detail2.append(f"Empire floor ${empire2['floor']:.2f} ({empire2['count']} listings).")
        return {
            "item": item_name, "buy_price": buy_price, "verdict": "INFO",
            "verdict_detail": " ".join(detail2),
            "verdict_eli5": "", "liquidity_eli5": "",
            "live_price": live_price2, "live_price_error": live_price_error2,
            "live_net": live_net2, "live_profit": live_profit2, "live_pct": live_pct2,
            "sell_venue": sell_venue, "sell_venue_label": sell_label,
            "sell_fee_pct": round(sell_fee * 100, 2),
            "w7": None, "w30": None, "w60": None, "w180": None,
            "liquidity": None, "chart": [], "empire": empire2,
            "trend_notes": [{"text": "No price graph history on CSFloat for this item", "type": "info"}],
        }

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
    w180 = wstats(180)
    liq = liquidity_score(w7, w30, w60)

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

    cs2_ctx = _fetch_cs2_market_context()

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

    # Live sell-side quote (listed/floor before that site’s fee)
    live_price, live_price_error = _fetch_live_listed_for_venue(
        search_name, sell_venue, float_min, float_max, live_price_override
    )
    live_net = round(live_price * (1 - sell_fee), 2) if live_price else None
    live_profit = round(live_net - buy_price, 2) if live_net is not None else None
    live_pct = round((live_profit / buy_price) * 100, 1) if live_profit is not None else None

    pump = round(((w7["avg"] / w30["avg"]) - 1) * 100, 1) if w7 and w30 else 0
    drop_60to7 = round(((w7["avg"] / w60["avg"]) - 1) * 100, 1) if w7 and w60 else None
    spd = w7["sales"] / 7 if w7 else 0
    low7 = w7["low"] if w7 else 0

    # --- Mathematical risk scoring ---
    # Count dips using robust filtered days to avoid premium-print distortion.
    def _count_dips(days: int) -> int:
        subset = data[:days]
        if not subset:
            return 0
        prices = [d["avg_price"] / 100 for d in subset]
        counts = [d["count"] for d in subset]
        robust = _robust_sales_days(prices, counts)
        if not robust:
            return 0
        return sum(1 for p, _ in robust if p < buy_price)

    dips_7d = _count_dips(7)
    dips_30d = _count_dips(30)
    days_30 = min(len(data), 30)

    # Price volatility (robust MAD-based % over filtered 30d sales)
    if w30 and days_30 > 1:
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
            # Convert MAD to robust sigma-equivalent and normalize as percent.
            robust_sigma = 1.4826 * mad
            volatility = round((robust_sigma / med) * 100, 1) if med > 0 else 0
        else:
            volatility = 0
    else:
        volatility = 0

    # Drop probability: % of days in last 30d where price was below buy
    drop_prob = round((dips_30d / days_30) * 100, 1) if days_30 > 0 else 0

    hist_pcts: list[float] = []
    w7_pct = w30_pct = None
    if w7:
        w7_pct = round((w7["avg"] * (1 - CSFLOAT_FEE) - buy_price) / buy_price * 100, 1)
        hist_pcts.append(w7_pct)
    if w30:
        w30_pct = round((w30["avg"] * (1 - CSFLOAT_FEE) - buy_price) / buy_price * 100, 1)
        hist_pcts.append(w30_pct)
    avg_hist = round(sum(hist_pcts) / len(hist_pcts), 1) if hist_pcts else 0.0

    profit_scores: list[tuple[str, float]] = []
    if live_pct is not None:
        profit_scores.append((f"live_{sell_venue}", live_pct))
    if w7_pct is not None:
        profit_scores.append(("csfloat_7d", w7_pct))
    if w30_pct is not None:
        profit_scores.append(("csfloat_30d", w30_pct))

    all_pcts = [p for _, p in profit_scores]
    best_pct = max(all_pcts) if all_pcts else 0
    worst_pct = min(all_pcts) if all_pcts else 0
    avg_pct = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else 0

    if live_pct is not None and avg_hist:
        real_pct = round(0.55 * live_pct + 0.45 * avg_hist, 1)
    elif live_pct is not None:
        real_pct = live_pct
    else:
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

    # --- Narrative verdict_detail: lead with numbers, then one key signal ---
    lines = []
    fee_pct_disp = int(sell_fee * 100) if sell_fee * 100 == int(sell_fee * 100) else round(sell_fee * 100, 2)

    # Sentence 1: live floor → net → profit vs buy
    if live_pct is not None:
        if live_pct < 0:
            lines.append(
                f"Floor ${live_price:.2f} on {sell_label} → net ${live_net:.2f} after {fee_pct_disp}% fee = {live_pct:+.1f}% vs your ${buy_price:.2f} buy — underwater right now."
            )
        elif live_pct < 2:
            lines.append(
                f"Floor ${live_price:.2f} on {sell_label} → net ${live_net:.2f} after {fee_pct_disp}% fee = {live_pct:+.1f}% vs your ${buy_price:.2f} buy — barely any margin."
            )
        else:
            lines.append(
                f"Floor ${live_price:.2f} on {sell_label} → net ${live_net:.2f} after {fee_pct_disp}% fee = {live_pct:+.1f}% vs your ${buy_price:.2f} buy."
            )
    elif w30:
        w30_net = round(w30["avg"] * (1 - CSFLOAT_FEE), 2)
        w30_pct_r2 = round((w30_net - buy_price) / buy_price * 100, 1)
        lines.append(
            f"No live floor on {sell_label} right now. 30d avg ${w30['avg']:.2f} → net ${w30_net:.2f} after fee = {w30_pct_r2:+.1f}% vs your ${buy_price:.2f} buy."
        )
    else:
        lines.append(f"No live or historical price data available for this item on {sell_label}.")

    # Sentence 2: key risk or confirmation + entry target
    if verdict == "BUY":
        parts = []
        if dips_7d == 0 and volatility < 8:
            parts.append("Price is stable — no dips below your entry this week")
        elif dips_7d == 0:
            parts.append(f"No dips below entry this week")
        else:
            parts.append(f"Dipped below entry {dips_7d}x this week — some risk")
        if liq and isinstance(liq, dict):
            spd_v = liq.get("spd_7", 0)
            grade = liq.get("grade", "?")
            grade_text = {"A": "sells daily", "B": "1-3 day wait", "C": "up to a week", "D": "slow mover", "F": "very illiquid"}.get(grade, "")
            parts.append(f"liquidity {grade} ({spd_v}/day — {grade_text})")
        if live_net:
            max_safe = round(live_net / 1.02, 2)
            parts.append(f"pay up to ${max_safe:.2f} to keep 2%+")
        elif w30:
            max_safe = round(w30["avg"] * (1 - CSFLOAT_FEE) / 1.02, 2)
            parts.append(f"based on 30d history, pay up to ${max_safe:.2f} to keep 2%+")
        lines.append(". ".join(p[0].upper() + p[1:] for p in parts) + ".")
    elif verdict == "RISKY":
        parts = []
        if dips_7d > 0:
            parts.append(f"Dipped below your buy price {dips_7d}x in the last 7 days")
        if pump > 15:
            parts.append(f"price pumped {pump:.0f}% above 30d avg — likely to correct")
        if volatility > 8:
            parts.append(f"volatile ({volatility}%) — hard to predict where it lands after the 7d trade lock")
        if not parts:
            parts.append("Profitable on paper but signals are mixed — check the chart before buying")
        lines.append(". ".join(p[0].upper() + p[1:] for p in parts) + ".")
    elif verdict == "SKIP":
        if pump > 15:
            if w30:
                lines.append(f"Price pumped {pump:.0f}% above 30d avg — wait for it to cool near ${w30['avg']:.2f} before buying.")
            else:
                lines.append(f"Price pumped {pump:.0f}% above 30d avg — wait for correction.")
        elif w30:
            w30_net2 = round(w30["avg"] * (1 - CSFLOAT_FEE), 2)
            target = round(w30_net2 / 1.03, 2)
            lines.append(f"Not worth it at ${buy_price:.2f}. Based on 30d avg you'd need to pay under ${target:.2f} to clear 3%.")
        else:
            lines.append(f"Margins don't clear the minimum threshold at ${buy_price:.2f}.")
    verdict_detail = " ".join(lines) if lines else f"Blend {real_pct}% ({sources_str})."
    verdict_eli5 = _verdict_eli5(verdict, sell_label, live_pct, live_price)
    liquidity_eli5 = _liquidity_eli5(liq)

    # Trend analysis
    trend_notes = []

    # 7d vs 30d momentum
    if pump > 15:
        trend_notes.append({"text": f"7d avg is +{pump}% above 30d avg — PUMPED, price inflated", "type": "danger"})
    elif pump > 5:
        trend_notes.append({"text": f"7d avg is +{pump}% above 30d avg — rising, watch for correction", "type": "warn"})
    elif pump < -10:
        trend_notes.append({"text": f"7d avg is {pump}% below 30d avg — DROPPING fast", "type": "danger"})
    elif pump < -3:
        trend_notes.append({"text": f"7d avg is {pump}% below 30d avg — declining slowly", "type": "warn"})
    else:
        trend_notes.append({"text": f"7d vs 30d: {'+' if pump > 0 else ''}{pump}% — price stable", "type": "safe"})

    # 60d long-term direction
    if drop_60to7 is not None:
        if drop_60to7 < -15:
            trend_notes.append({"text": f"60d trend: {drop_60to7}% — major decline, possible new supply or case drop", "type": "danger"})
        elif drop_60to7 < -5:
            trend_notes.append({"text": f"60d trend: {drop_60to7}% — downward over 2 months", "type": "warn"})
        elif drop_60to7 > 10:
            trend_notes.append({"text": f"60d trend: +{drop_60to7}% — strong uptrend over 2 months", "type": "safe"})
        else:
            trend_notes.append({"text": f"60d trend: {'+' if drop_60to7 > 0 else ''}{drop_60to7}% — flat long-term", "type": "safe"})

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

    # Official CS2 update context (possible FOMO catalyst window).
    if cs2_ctx:
        age_h = cs2_ctx.get("latest_age_hours")
        title = cs2_ctx.get("latest_title", "Recent CS2 update")
        fomo = cs2_ctx.get("has_fomo_catalyst")
        if age_h is not None and age_h <= 72 and fomo:
            trend_notes.append({
                "text": f"Recent official CS2 update ({age_h}h): \"{title}\" — elevated hype/FOMO risk on affected items",
                "type": "warn",
            })
        elif age_h is not None and age_h <= 72:
            trend_notes.append({
                "text": f"Recent official CS2 post ({age_h}h): \"{title}\" — monitor short-term volatility",
                "type": "info",
            })

    cap = min(len(data), 400)
    chart_data = [{"day": d["day"], "avg": round(d["avg_price"] / 100, 2), "sales": d["count"]} for d in data[:cap]]

    return {
        "item": item_name, "buy_price": buy_price,
        "live_price": live_price, "live_price_error": live_price_error, "live_net": live_net, "live_profit": live_profit, "live_pct": live_pct,
        "sell_venue": sell_venue,
        "sell_venue_label": sell_label,
        "sell_fee_pct": round(sell_fee * 100, 2),
        "w7": window_result(w7), "w30": window_result(w30), "w60": window_result(w60),
        "w180": window_result(w180),
        "liquidity": liq, "pump_pct": pump, "trend_notes": trend_notes,
        "chart": chart_data,
        "volatility": volatility, "drop_prob": drop_prob,
        "dips_7d": dips_7d, "dips_30d": dips_30d,
        "verdict": verdict, "verdict_detail": verdict_detail,
        "verdict_eli5": verdict_eli5,
        "liquidity_eli5": liquidity_eli5,
        "empire": empire,
    }
