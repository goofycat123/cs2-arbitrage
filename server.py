"""CS2 Skin Analyzer — Web Server."""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from urllib.parse import quote

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from analyze_api import run_analysis
from config import CSGOEMPIRE_API_KEY, FLOAT_API_KEY, FEES, RATE_LIMITS
from templates import FLIP_HTML

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="CS2 Skin Analyzer", lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/test-csfloat")
def test_csfloat():
    """Quick probe: verify CSFloat API key works and can fetch a live listing."""
    from config import FLOAT_API_KEY
    from rate_limiter import wait_if_needed
    if not FLOAT_API_KEY:
        return {"ok": False, "error": "FLOAT_API_KEY env var not set — add it in Railway Variables"}
    try:
        wait_if_needed("float")
        resp = httpx.get(
            "https://csfloat.com/api/v1/listings",
            headers={"Authorization": FLOAT_API_KEY},
            params={"market_hash_name": "AK-47 | Redline (Field-Tested)", "limit": 1, "sort_by": "lowest_price", "type": "buy_now"},
            timeout=12,
        )
        if resp.status_code == 401:
            return {"ok": False, "error": "API key rejected (401 Unauthorized) — key may be expired or invalid"}
        if resp.status_code == 403:
            return {"ok": False, "error": "API key forbidden (403) — check CSFloat API key permissions"}
        if resp.status_code == 429:
            return {"ok": False, "error": "Rate limited (429) — too many requests, wait 60s"}
        if resp.status_code != 200:
            return {"ok": False, "error": f"CSFloat returned HTTP {resp.status_code}", "body": resp.text[:200]}
        data = resp.json().get("data", [])
        if data:
            price = data[0].get("price", 0)
            return {"ok": True, "floor_price": round(price / 100, 2), "key_prefix": FLOAT_API_KEY[:6] + "..."}
        return {"ok": True, "floor_price": None, "note": "No listings found for test item (key works)", "key_prefix": FLOAT_API_KEY[:6] + "..."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/search")
def search_items(q: str = ""):
    if len(q) < 2:
        return {"results": []}

    from config import PRICEMPIRE_API_KEY
    from rate_limiter import wait_if_needed

    if not PRICEMPIRE_API_KEY:
        return {"results": []}

    try:
        wait_if_needed("pricempire_free")
        resp = httpx.get(
            "https://api.pricempire.com/v4/free/search",
            params={"q": q, "api_key": PRICEMPIRE_API_KEY},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            # Convert to our format - Pricempire uses market_hash_name
            matches = [{"name": r.get("market_hash_name", ""), "price": 0} for r in results[:15] if r.get("market_hash_name")]
            return {"results": matches}
    except Exception as e:
        pass

    return {"results": []}


@app.post("/api/analyze")
def analyze_item(body: dict):
    item_name = body.get("item", "")
    buy_price = float(body.get("price", 0))
    wear = body.get("wear", "FN")
    float_min = body.get("float_min")
    float_max = body.get("float_max")
    fade_min_pct = body.get("fade_min_pct")
    fade_max_pct = body.get("fade_max_pct")
    live_price_override = body.get("live_price_override")
    vanilla = bool(body.get("vanilla", False))
    sell_venue = body.get("sell_venue") or "csfloat"
    if not item_name or buy_price <= 0:
        return {"error": "Need item name and buy price"}
    if live_price_override is not None:
        live_price_override = float(live_price_override)
    # Vanilla knives: strip wear condition from name if present
    if vanilla:
        for w in ["(Factory New)", "(Minimal Wear)", "(Field-Tested)", "(Well-Worn)", "(Battle-Scarred)"]:
            item_name = item_name.replace(w, "").strip()
    return run_analysis(
        item_name,
        buy_price,
        wear=wear,
        float_min=float_min,
        float_max=float_max,
        fade_min_pct=fade_min_pct,
        fade_max_pct=fade_max_pct,
        live_price_override=live_price_override,
        sell_venue=sell_venue,
    )


@app.get("/", response_class=HTMLResponse)
def flip_page():
    return FLIP_HTML


@app.get("/api/arbitrage")
async def arbitrage_scan(
    # Money filters are in USD (we convert to cents for the Empire API).
    min_price: float = 0.0,
    max_price: float = 200.0,
    # Float filters are for CSFloat listings. If either is empty, it is ignored.
    float_min: float | None = None,
    float_max: float | None = None,
    # Scan source for CSGOEmpire: listed (withdrawals), auctions, or both.
    source: str = "listed",
    # Rate-limit-friendly scan size.
    pages: int = 1,
    per_page: int = 200,
    # Extra CSFloat history calls to determine volatility.
    check_volatile: bool = False,
    # Hard cap on how many Empire items we will query CSFloat for in a single scan.
    # This is how we stay usable under CSFloat rate limits.
    max_items: int = 25,
    # Arbitrage direction.
    direction: str = "empire_to_float",
):
    # Prefer config env var names, but keep backward compatibility with older env var names.
    empire_api_key = CSGOEMPIRE_API_KEY or os.getenv("EMPIRE_API_KEY")
    csfloat_api_key = FLOAT_API_KEY or os.getenv("CSFLOAT_API_KEY")

    meta = {
        "keys_present": bool(empire_api_key and csfloat_api_key),
        "source": source,
        "direction": direction,
        "pages": pages,
        "per_page": per_page,
        "min_price": min_price,
        "max_price": max_price,
        "float_min": float_min,
        "float_max": float_max,
        "check_volatile": check_volatile,
        "empire_items_fetched": 0,
        "csfloat_listings_found": 0,
        "csfloat_items_enqueued": 0,
        "profitable_pre_margin": 0,
        "volatile_true": 0,
    }

    if not meta["keys_present"]:
        return {"results": [], "meta": meta}

    from rate_limiter import wait_if_needed

    def _empire_price_to_usd(v: int | float) -> float:
        # Empire API price fields are integer cents; convert to USD.
        return v / 100.0 if isinstance(v, int) else float(v)

    def _csfloat_price_to_usd(v: int | float) -> float:
        # CSFloat listing endpoint returns ints in cents.
        return v / 100.0 if isinstance(v, int) else float(v)

    def _source_to_auction_param(src: str) -> str | None:
        src = (src or "").lower()
        if src in {"listed", "withdrawals", "no", "false"}:
            return "no"
        if src in {"auctions", "yes", "true"}:
            return "yes"
        return None

    async def scan_one(auction_param: str) -> list[dict]:
        results: list[dict] = []

        empire_minor_min = int(min_price * 100) if min_price and min_price > 0 else None
        empire_minor_max = int(max_price * 100) if max_price and max_price > 0 else None

        async with httpx.AsyncClient(timeout=20) as client:
            for page in range(1, max(1, pages) + 1):
                wait_if_needed("empire")
                params = {
                    "auction": auction_param,
                    "per_page": per_page,
                    "page": page,
                    "sort": "asc",
                    "order": "market_value",
                }
                if empire_minor_min is not None:
                    params["price_min"] = empire_minor_min
                if empire_minor_max is not None:
                    params["price_max"] = empire_minor_max

                try:
                    resp = await client.get(
                        "https://csgoempire.com/api/v2/trading/items",
                        headers={"Authorization": f"Bearer {empire_api_key}"},
                        params=params,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    items = data.get("data", [])
                except Exception:
                    items = []

                meta["empire_items_fetched"] += len(items)
                if not items:
                    # If this page returns nothing, no point continuing.
                    break

                # Respect CSFloat max-items budget.
                remaining = max(0, max_items - meta["csfloat_items_enqueued"])
                if remaining <= 0:
                    return results
                if len(items) > remaining:
                    items = items[:remaining]

                # Process items in batches of 10
                batch_size = 10
                for batch_start in range(0, len(items), batch_size):
                    batch = items[batch_start : batch_start + batch_size]

                    to_volatile: list[tuple[dict, int | float, str]] = []

                    for item in batch:
                        if meta["csfloat_items_enqueued"] >= max_items:
                            return results

                        name = item.get("market_hash_name") or item.get("market_name", "")
                        # We use purchase_price as the actual USD/USDC listing price.
                        purchase_price = item.get("purchase_price", None)
                        empire_minor = purchase_price if purchase_price is not None else item.get("market_value", 0)
                        if not name or not empire_minor:
                            continue

                        encoded = quote(name)
                        meta["csfloat_items_enqueued"] += 1

                        listing_price, listing_id = await fetch_csfloat_listing_price(client, name)
                        if listing_price is None:
                            continue

                        empire_usd = _empire_price_to_usd(empire_minor)
                        csfloat_usd = _csfloat_price_to_usd(listing_price)

                        if direction == "float_to_empire":
                            buy_price = csfloat_usd
                            csfloat_net = csfloat_usd  # for display consistency
                            sell_price = empire_usd * (1 - FEES["empire_sell"])
                            net_profit = sell_price - buy_price
                            margin_pct = (net_profit / buy_price) * 100 if buy_price else 0
                        else:
                            # Buy on Empire, sell on CSFloat.
                            buy_price = empire_usd
                            sell_price = csfloat_usd * (1 - FEES["float_sell"])
                            net_profit = sell_price - buy_price
                            csfloat_net = sell_price
                            margin_pct = (net_profit / buy_price) * 100 if buy_price else 0

                        if net_profit <= 0:
                            continue

                        meta["profitable_pre_margin"] += 1
                        wear = item.get("wear_name", "")

                        entry = {
                            "name": name,
                            "wear": wear,
                            "empire_usd": round(empire_usd, 2),
                            "csfloat_floor": round(csfloat_usd, 2),
                            "csfloat_net": round(csfloat_net, 2),
                            "net_profit": round(net_profit, 2),
                            "margin_pct": round(margin_pct, 2),
                            "volatile": False,
                            "csfloat_url": (
                                f"https://csfloat.com/item/{listing_id}"
                                if listing_id
                                else f"https://csfloat.com/search?market_hash_name={encoded}"
                            ),
                        }
                        results.append(entry)

                        if check_volatile:
                            # Only fetch history (avg_7d) for items that actually make profit.
                            to_volatile.append((entry, listing_price, encoded))

                    if check_volatile and to_volatile:
                        avg_tasks = [
                            asyncio.create_task(fetch_csfloat_avg7d(client, encoded_name))
                            for _, _, encoded_name in to_volatile
                        ]
                        avg_values = await asyncio.gather(*avg_tasks, return_exceptions=True)

                        for (entry, listing_price, _encoded), avg_7d in zip(to_volatile, avg_values):
                            try:
                                if isinstance(avg_7d, Exception) or avg_7d is None or avg_7d <= 0:
                                    continue
                                diff_pct = abs(listing_price - avg_7d) / avg_7d * 100
                                if diff_pct > 5:
                                    entry["volatile"] = True
                                    meta["volatile_true"] += 1
                            except Exception:
                                pass

                    await asyncio.sleep(0.02)

        return results

    async def fetch_csfloat_listing_price(client: httpx.AsyncClient, name: str) -> tuple[int | float | None, str | None]:
        """Fetch CSFloat buy-now lowest listing price + listing id."""
        # Match the working params used in trend.fetch_float_price()
        from trend import extract_index

        params: dict = {
            "limit": 1,
            "sort_by": "lowest_price",
            "type": "buy_now",
        }

        if "Music Kit" in name:
            params["music_kit_index"] = extract_index(name)
        elif "Sticker" in name:
            params["sticker_index"] = extract_index(name)
        elif "Case" in name or "Capsule" in name:
            params["container_index"] = extract_index(name)
        else:
            params["market_hash_name"] = name

        if float_min is not None:
            params["min_float"] = float_min
        if float_max is not None:
            params["max_float"] = float_max

        # Local throttle: at most `float_limit` CSFloat listing calls per `float_window`.
        while True:
            now = time.time()
            float_call_times[:] = [t for t in float_call_times if now - t < float_window]
            if len(float_call_times) < float_limit:
                float_call_times.append(now)
                break
            sleep_for = float_window - (now - float_call_times[0]) + 0.2
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)

        for attempt in range(2):
            # Throttle locally before each attempt.
            while True:
                now = time.time()
                float_call_times[:] = [t for t in float_call_times if now - t < float_window]
                if len(float_call_times) < float_limit:
                    float_call_times.append(now)
                    break
                sleep_for = float_window - (now - float_call_times[0]) + 0.2
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)

            try:
                r = await client.get(
                    "https://csfloat.com/api/v1/listings",
                    headers={"Authorization": csfloat_api_key},
                    params=params,
                    timeout=15,
                )
                if r.status_code == 200:
                    items = r.json().get("data", [])
                    if items:
                        top = items[0]
                        price = top.get("price", None)
                        listing_id = top.get("id", None)
                        if price is not None:
                            meta["csfloat_listings_found"] += 1
                        return price, listing_id
                    return None, None

                # If we're rate limited, wait and retry once.
                msg = ""
                try:
                    msg = r.text.lower()
                except Exception:
                    msg = ""
                if r.status_code == 429 or "too many requests" in msg:
                    if attempt == 0:
                        await asyncio.sleep(15)
                        continue
                    return None, None
            except Exception:
                if attempt == 0:
                    await asyncio.sleep(1)
                    continue
                return None, None

            # Non-200, non-429: give up.
            return None, None

        return None, None

    async def fetch_csfloat_avg7d(client: httpx.AsyncClient, encoded_name: str) -> float | None:
        """Fetch CSFloat avg price over last 7d. Returns cents as float."""
        wait_if_needed("float")
        avg_7d = None
        try:
            hist_r = await client.get(
                f"https://csfloat.com/api/v1/history/{encoded_name}/sales",
                headers={"Authorization": csfloat_api_key},
                params={"limit": 50},
                timeout=15,
            )
            if hist_r.status_code == 200:
                sales = hist_r.json()
                if isinstance(sales, list) and sales:
                    from datetime import datetime, timedelta

                    cutoff = datetime.utcnow() - timedelta(days=7)
                    recent_prices = []
                    for sale in sales:
                        try:
                            ts = sale.get("created_at", "")
                            if not ts:
                                continue
                            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                            if dt >= cutoff:
                                recent_prices.append(sale.get("price", 0))
                        except Exception:
                            pass
                    if recent_prices:
                        avg_7d = sum(recent_prices) / len(recent_prices)
        except Exception:
            pass
        return avg_7d

    # Decide which sources to scan.
    results: list[dict] = []
    src = (source or "").lower().strip()
    direction = (direction or "").lower().strip()

    # Per-scan throttle for CSFloat listing calls.
    # Prevents global rate limiter state from stalling arbitrage scans.
    float_limit = RATE_LIMITS.get("float", 10)
    float_window = 60.0
    float_call_times: list[float] = []
    if src in {"both"}:
        results.extend(await scan_one("no"))
        results.extend(await scan_one("yes"))
    else:
        auction_param = _source_to_auction_param(src)
        if not auction_param:
            return {"results": [], "meta": meta}
        results.extend(await scan_one(auction_param))

    results.sort(key=lambda x: x["margin_pct"], reverse=True)
    return {"results": results, "meta": meta}


if __name__ == "__main__":
    import uvicorn
    # Bind locally by default so it is only reachable from this machine.
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "3001"))
    uvicorn.run(app, host=host, port=port)
