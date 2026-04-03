"""
Official Skinport catalog — GET https://api.skinport.com/v1/items
No API key. Rate limit is strict (~8 calls / 5 min); cache one snapshot for all users.
Docs: https://docs.skinport.com/
"""

from __future__ import annotations

import re
import threading
import time

import httpx

SKINPORT_ITEMS_URL = "https://api.skinport.com/v1/items"
# Stay under Skinport's 5-minute window; one fetch serves search + scans.
CACHE_TTL_SEC = 280.0

_cache_rows: list | None = None
_cache_ts: float = 0.0
_lock = threading.Lock()

# Match PricEmpire-style exclusions (lowercase substrings).
DEFAULT_NAME_BLACKLIST = (
    "battle-scarred",
    "sticker |",
    "sticker capsule",
    "capsule",
    " charm",
    "| charm",
    "patch",
    "graffiti",
    " music kit",
    "souvenir package",
)


def wear_from_market_hash(name: str) -> str:
    m = re.search(r"\(([^)]+)\)\s*$", name or "")
    return m.group(1).strip() if m else ""


def _fetch_catalog_unlocked() -> list:
    global _cache_rows, _cache_ts
    r = httpx.get(
        SKINPORT_ITEMS_URL,
        params={"app_id": 730, "currency": "USD", "tradable": "1"},
        headers={"Accept-Encoding": "gzip, deflate, br"},
        timeout=120.0,
    )
    r.raise_for_status()
    data = r.json()
    rows = data if isinstance(data, list) else []
    _cache_rows = rows
    _cache_ts = time.time()
    return rows


def get_catalog_sync(force_refresh: bool = False) -> list:
    """Return full Skinport CS2 USD tradable catalog (large JSON)."""
    now = time.time()
    with _lock:
        if (
            not force_refresh
            and _cache_rows is not None
            and now - _cache_ts < CACHE_TTL_SEC
        ):
            return _cache_rows
    with _lock:
        if (
            not force_refresh
            and _cache_rows is not None
            and time.time() - _cache_ts < CACHE_TTL_SEC
        ):
            return _cache_rows
        return _fetch_catalog_unlocked()


def search_items(query: str, limit: int = 15) -> list[dict]:
    """Substring match on market_hash_name; results for /api/search."""
    q = (query or "").strip().lower()
    if len(q) < 2:
        return []
    cat = get_catalog_sync()
    out: list[dict] = []
    for row in cat:
        name = row.get("market_hash_name") or ""
        if q not in name.lower():
            continue
        mp = row.get("min_price")
        out.append(
            {
                "name": name,
                "price": round(float(mp), 2) if mp is not None else 0.0,
            }
        )
        if len(out) >= limit:
            break
    return out


def excluded_by_name(name: str, blacklist: tuple[str, ...] | None = None) -> bool:
    bl = blacklist if blacklist is not None else DEFAULT_NAME_BLACKLIST
    ln = (name or "").lower()
    return any(b in ln for b in bl)


def candidates_for_arbitrage(
    *,
    min_price: float,
    max_price: float,
    min_listings: int = 1,
    blacklist: tuple[str, ...] | None = None,
    max_candidates: int = 500,
) -> list[dict]:
    """
    Rows from catalog filtered for Skinport -> CSFloat scan.
    Sorted by Skinport quantity (desc) then min_price for stable ordering.
    """
    cat = get_catalog_sync()
    bl = blacklist if blacklist is not None else DEFAULT_NAME_BLACKLIST
    picked: list[dict] = []
    for row in cat:
        name = row.get("market_hash_name")
        mp = row.get("min_price")
        qty = int(row.get("quantity") or 0)
        if not name or mp is None:
            continue
        try:
            usd = float(mp)
        except (TypeError, ValueError):
            continue
        if usd < min_price or usd > max_price:
            continue
        if qty < min_listings:
            continue
        if excluded_by_name(name, bl):
            continue
        picked.append(row)
    picked.sort(key=lambda r: (-int(r.get("quantity") or 0), float(r.get("min_price") or 0)))
    return picked[:max_candidates]
