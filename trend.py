"""
Trend Filter — CSFloat price history analysis.
Determines if an item is safe to buy based on 30-120 day price stability.
"""

import time
from datetime import datetime

import httpx

from config import FLOAT_API_KEY, PUMP_THRESHOLD, MIN_SALES_7D
from rate_limiter import wait_if_needed

FLOAT_BASE = "https://csfloat.com/api/v1"
FLOAT_HEADERS = {"Authorization": FLOAT_API_KEY}
CLIENT = httpx.Client(timeout=15)


def fetch_float_sales(market_hash_name: str) -> list[dict]:
    """Fetch recent sales history from CSFloat."""
    wait_if_needed("float")
    resp = CLIENT.get(
        f"{FLOAT_BASE}/history/sales",
        headers=FLOAT_HEADERS,
        params={"market_hash_name": market_hash_name},
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("data", data.get("sales", []))


def fetch_float_price(market_hash_name: str, float_min: float | None = None, float_max: float | None = None) -> float | None:
    """Get current lowest CSFloat buy-now listing price, with optional float range filter."""
    params = {
        "limit": 1,
        "sort_by": "lowest_price",
        "type": "buy_now",
        "market_hash_name": market_hash_name,
    }
    if float_min is not None:
        params["min_float"] = float_min
    if float_max is not None:
        params["max_float"] = float_max

    last_status = None
    for attempt in range(3):
        wait_if_needed("float")
        try:
            resp = CLIENT.get(f"{FLOAT_BASE}/listings", headers=FLOAT_HEADERS, params=params, timeout=15)
            last_status = resp.status_code
            if resp.status_code == 200:
                listings = resp.json().get("data", [])
                if not listings:
                    return None
                p = listings[0].get("price", 0)
                return p / 100 if isinstance(p, int) else float(p)
            if resp.status_code == 429:
                time.sleep(15)
                continue
            if resp.status_code in (401, 403):
                # Transient auth rejection — retry once before giving up
                if attempt < 2:
                    time.sleep(2)
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
        except Exception:
            if attempt < 2:
                time.sleep(1)
                continue
            raise
    # All retries exhausted
    if last_status in (401, 403):
        raise Exception(f"{last_status} Unauthorized")
    return None


def extract_index(item_name: str) -> int:
    """Extract index from special item names. Default to 0 if not found."""
    import re
    match = re.search(r'\((\d+)\)', item_name)
    return int(match.group(1)) if match else 0


def parse_sales(sales: list[dict]) -> list[dict]:
    """Parse sales into [{timestamp, price}] sorted by time."""
    parsed = []
    for s in sales:
        ts = s.get("sold_at") or s.get("created_at") or s.get("timestamp")
        price = s.get("price", 0)
        if isinstance(price, int):
            price = price / 100
        if ts is None:
            continue
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts = dt.timestamp()
            except ValueError:
                continue
        parsed.append({"ts": float(ts), "price": float(price)})
    parsed.sort(key=lambda x: x["ts"])
    return parsed


def analyze_trend(market_hash_name: str) -> dict:
    """
    Analyze price trend for an item. Returns:
    - safe: bool (ok to buy)
    - reason: str (why safe/unsafe)
    - avg_7d, avg_30d, avg_90d: average prices
    - sales_7d: count
    - trend: "stable", "up", "down", "pumped"
    - current_price: CSFloat true value
    """
    result = {
        "name": market_hash_name,
        "safe": False,
        "reason": "",
        "avg_7d": None,
        "avg_30d": None,
        "avg_90d": None,
        "sales_7d": 0,
        "sales_30d": 0,
        "trend": "unknown",
        "current_price": None,
        "pump_pct": 0,
    }

    # Fetch sales history
    try:
        raw_sales = fetch_float_sales(market_hash_name)
    except Exception as e:
        result["reason"] = f"Failed to fetch history: {e}"
        return result

    sales = parse_sales(raw_sales)
    if len(sales) < 5:
        result["reason"] = "Not enough sales history"
        return result

    now = time.time()
    d7 = now - 7 * 86400
    d30 = now - 30 * 86400
    d90 = now - 90 * 86400

    sales_7d = [s for s in sales if s["ts"] >= d7]
    sales_30d = [s for s in sales if s["ts"] >= d30]
    sales_90d = [s for s in sales if s["ts"] >= d90]

    result["sales_7d"] = len(sales_7d)
    result["sales_30d"] = len(sales_30d)

    # Minimum liquidity
    if len(sales_7d) < MIN_SALES_7D:
        result["reason"] = f"Only {len(sales_7d)} sales in 7d (need {MIN_SALES_7D}+)"
        return result

    # Calculate averages
    avg_7d = sum(s["price"] for s in sales_7d) / len(sales_7d) if sales_7d else 0
    avg_30d = sum(s["price"] for s in sales_30d) / len(sales_30d) if sales_30d else 0
    avg_90d = sum(s["price"] for s in sales_90d) / len(sales_90d) if sales_90d else avg_30d

    result["avg_7d"] = round(avg_7d, 2)
    result["avg_30d"] = round(avg_30d, 2)
    result["avg_90d"] = round(avg_90d, 2)

    # Get current CSFloat price
    try:
        current = fetch_float_price(market_hash_name)
        result["current_price"] = current
    except Exception:
        current = avg_7d

    # Pump detection: 7d avg > 30d avg by 15%+
    if avg_30d > 0:
        pump_pct = (avg_7d - avg_30d) / avg_30d
        result["pump_pct"] = round(pump_pct * 100, 1)
        if pump_pct > PUMP_THRESHOLD:
            result["reason"] = f"Pumped: 7d avg ${avg_7d:.2f} is {pump_pct*100:.0f}% above 30d avg ${avg_30d:.2f}"
            result["trend"] = "pumped"
            return result

    # Trend: compare 30d avg to 90d avg
    if avg_90d > 0:
        trend_pct = (avg_30d - avg_90d) / avg_90d
        if trend_pct < -0.10:
            result["trend"] = "down"
            result["reason"] = f"Downtrend: 30d avg ${avg_30d:.2f} is {abs(trend_pct)*100:.0f}% below 90d avg ${avg_90d:.2f}"
            return result
        elif trend_pct > 0.05:
            result["trend"] = "up"
        else:
            result["trend"] = "stable"

    # Check for sharp recent drops (any 3-day window dropping 10%+)
    if len(sales_30d) >= 6:
        for i in range(len(sales_30d) - 3):
            window_start = sales_30d[i]["price"]
            window_end = sales_30d[i + 3]["price"]
            if window_start > 0 and (window_start - window_end) / window_start > 0.10:
                result["reason"] = f"Sharp drop detected: ${window_start:.2f} -> ${window_end:.2f} in recent sales"
                result["trend"] = "down"
                return result

    # All checks passed
    result["safe"] = True
    result["reason"] = f"Trend {result['trend']}, {len(sales_7d)} sales/7d, no pump, no drops"
    return result


if __name__ == "__main__":
    # Test with popular items
    test_items = [
        "AK-47 | Redline (Field-Tested)",
        "AK-47 | Asiimov (Field-Tested)",
        "M4A4 | Desolate Space (Field-Tested)",
        "AWP | Asiimov (Field-Tested)",
        "AK-47 | Vulcan (Minimal Wear)",
    ]

    print("=== CS2 Trend Filter ===\n")
    for item in test_items:
        print(f"Analyzing: {item}")
        r = analyze_trend(item)
        safe = "SAFE" if r["safe"] else "SKIP"
        print(f"  [{safe}] {r['reason']}")
        print(f"  7d: ${r['avg_7d']} ({r['sales_7d']} sales) | 30d: ${r['avg_30d']} ({r['sales_30d']} sales) | 90d: ${r['avg_90d']}")
        print(f"  Trend: {r['trend']} | Pump: {r['pump_pct']}% | CSFloat: ${r['current_price']}")
        print()
