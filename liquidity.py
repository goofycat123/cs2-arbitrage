"""
CS2 Arbitrage Engine — Updated Spec
Buy on CSGOEmpire below CSFloat true value, sell on CSFloat.
CSFloat = 100% true market value.
"""

import time
from datetime import datetime

import httpx

from config import (
    FLOAT_API_KEY,
    CSGOEMPIRE_API_KEY,
    MIN_PRICE,
    MAX_PRICE,
    MIN_NET_PROFIT_PCT,
    MIN_SALES_7D,
    TARGET_WEAPONS,
)
from fees import net_profit_pct
from trend import analyze_trend, fetch_float_price
from rate_limiter import wait_if_needed

FLOAT_BASE = "https://csfloat.com/api/v1"
FLOAT_HEADERS = {"Authorization": FLOAT_API_KEY}
EMPIRE_HEADERS = {"Authorization": f"Bearer {CSGOEMPIRE_API_KEY}"}
CLIENT = httpx.Client(timeout=15)

# ---------------------------------------------------------------------------
# Caches
# ---------------------------------------------------------------------------

_empire_cache = None
_float_price_cache = {}
_trend_cache = {}


def clear_caches():
    global _empire_cache, _float_price_cache, _trend_cache
    _empire_cache = None
    _float_price_cache = {}
    _trend_cache = {}


# ---------------------------------------------------------------------------
# CSGOEmpire — buy source
# ---------------------------------------------------------------------------

def fetch_empire_listings(min_price=MIN_PRICE, max_price=MAX_PRICE) -> list[dict]:
    """Fetch all Empire listings in price range. Returns [{name, empire_price, ...}]."""
    global _empire_cache
    if _empire_cache is not None:
        return _empire_cache
    _empire_cache = []
    page = 1
    while page <= 20:
        wait_if_needed("empire")
        try:
            resp = CLIENT.get(
            "https://csgoempire.com/api/v2/trading/items",
            headers=EMPIRE_HEADERS,
            params={
                "per_page": 100,
                "page": page,
                "sort": "asc",
                "price_min": int(min_price * 100),
                "price_max": int(max_price * 100),
            },
        )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                print(f"  Empire rate limited at page {page}, waiting 30s...")
                import time; time.sleep(30)
                continue
            raise
        items = resp.json().get("data", [])
        if not items:
            break
        for item in items:
            name = item.get("market_name", "")
            val = item.get("market_value", 0)
            if name and val:
                _empire_cache.append({
                    "name": name,
                    "empire_price": val / 100,
                    "suggested_price": item.get("suggested_price", 0) / 100,
                    "above_recommended": item.get("above_recommended_price", 0),
                })
        page += 1
    return _empire_cache


# ---------------------------------------------------------------------------
# CSFloat — price reference (true value)
# ---------------------------------------------------------------------------

def get_float_price(market_hash_name: str) -> float | None:
    """Cached CSFloat true value lookup."""
    if market_hash_name in _float_price_cache:
        return _float_price_cache[market_hash_name]
    price = fetch_float_price(market_hash_name)
    _float_price_cache[market_hash_name] = price
    return price


def get_trend(market_hash_name: str) -> dict:
    """Cached trend analysis."""
    if market_hash_name in _trend_cache:
        return _trend_cache[market_hash_name]
    t = analyze_trend(market_hash_name)
    _trend_cache[market_hash_name] = t
    return t


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------

def listing_url(market: str, item_name: str, listing_id: str = "") -> str:
    encoded = item_name.replace(" ", "%20")
    if market == "float":
        if listing_id:
            return f"https://csfloat.com/item/{listing_id}"
        return f"https://csfloat.com/search?market_hash_name={encoded}"
    elif market == "empire":
        return f"https://csgoempire.com/withdraw?search={encoded}"
    return "#"


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

def passes_blacklist(name: str, blacklist: list[str]) -> bool:
    name_lower = name.lower()
    return not any(b in name_lower for b in blacklist)


def passes_weapon_filter(name: str) -> bool:
    return any(w.lower() in name.lower() for w in TARGET_WEAPONS)


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------

DEFAULT_FILTERS = {
    "min_price": MIN_PRICE,
    "max_price": MAX_PRICE,
    "min_roi": 2.0,
    "max_roi": 1000.0,
    "min_volume": MIN_SALES_7D,
    "min_liquidity": 0,
    "blacklist": ["battle-scarred", "sticker", "capsule", "case", "graffiti", "patch"],
}


def rank_items(filters: dict = None):
    f = {**DEFAULT_FILTERS, **(filters or {})}
    min_price = f["min_price"]
    max_price = f["max_price"]
    min_roi = f["min_roi"]
    max_roi = f["max_roi"]
    min_volume = f["min_volume"]
    blacklist = [b.lower() for b in f["blacklist"]]

    # Step 1: Pull Empire listings
    print("Fetching Empire listings...")
    empire_items = fetch_empire_listings(min_price, max_price)
    print(f"  {len(empire_items)} items")

    results = []

    for item in empire_items:
        name = item["name"]
        empire_price = item["empire_price"]

        # Blacklist + weapon filter
        if not passes_blacklist(name, blacklist):
            continue
        if not passes_weapon_filter(name):
            continue

        # Step 2: Get CSFloat true value
        csfloat_price = get_float_price(name)
        if not csfloat_price:
            continue

        # Step 3: Calculate margin (buy Empire, sell CSFloat)
        pct = net_profit_pct(empire_price, csfloat_price) * 100

        if pct < min_roi or pct > max_roi:
            continue

        # Step 4: Trend + liquidity check
        trend = get_trend(name)

        if not trend["safe"]:
            print(f"  SKIP {name}: {trend['reason']}")
            continue

        if min_volume > 0 and trend["sales_7d"] < min_volume:
            continue

        # Calculate score: profit * liquidity
        sales_7d = trend["sales_7d"]
        score = round(pct * (sales_7d / max(MIN_SALES_7D, 1)), 2)

        profit_dollar = round(csfloat_price * 0.98 - empire_price, 2)

        results.append({
            "name": name,
            "buy_price": round(empire_price, 2),
            "buy_market": "empire",
            "sell_price": round(csfloat_price, 2),
            "sell_market": "float",
            "net_profit_pct": round(pct, 2),
            "net_profit_dollar": profit_dollar,
            "avg_7d": trend["avg_7d"],
            "avg_30d": trend["avg_30d"],
            "trend": trend["trend"],
            "pump_pct": trend["pump_pct"],
            "sales_7d": sales_7d,
            "sales_30d": trend["sales_30d"],
            "score": score,
            "float_value": None,
            "wear": "",
            "stickers": 0,
            "buy_url": listing_url("empire", name),
            "sell_url": listing_url("float", name),
        })

        print(f"  HIT {name}: buy ${empire_price} -> sell ${csfloat_price} = {pct:.1f}% net (${profit_dollar})")

    results.sort(key=lambda x: x["score"], reverse=True)
    print(f"\nFound {len(results)} opportunities")
    return results
