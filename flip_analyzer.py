import sys
import httpx
from config import FLOAT_API_KEY

CSFLOAT_FEE = 0.02
FLOAT_HEADERS = {"Authorization": FLOAT_API_KEY}


def liquidity_score(w7, w30, w60):
    """
    Liquidity score 0-100 based on sales velocity and consistency.
    Weights: 7d activity (50%), 30d consistency (30%), 60d baseline (20%).
    Trainable — adjust weights and thresholds over time.
    """
    if not w7:
        return 0

    spd_7 = w7["sales"] / w7["days"]   # sales per day last 7d
    spd_30 = w30["sales"] / w30["days"] if w30 else spd_7
    spd_60 = w60["sales"] / w60["days"] if w60 else spd_30

    # 7d raw score: 0-50 (1 sale/day = 10, 5+/day = 50)
    s7 = min(spd_7 / 5 * 50, 50)

    # 30d consistency: penalize if 7d volume dropped vs 30d avg
    if spd_30 > 0:
        consistency = min(spd_7 / spd_30, 1.5)  # cap at 1.5x
    else:
        consistency = 0
    s30 = consistency * 30  # 0-30 (30 if 7d matches or beats 30d)

    # 60d baseline: reward items with long-term proven demand
    s60 = min(spd_60 / 3 * 20, 20)  # 3+/day = full 20 pts

    score = round(min(s7 + s30 + s60, 100), 1)

    # Grade
    if score >= 80:
        grade = "A"
    elif score >= 60:
        grade = "B"
    elif score >= 40:
        grade = "C"
    elif score >= 20:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "spd_7": round(spd_7, 1),
        "spd_30": round(spd_30, 1),
        "spd_60": round(spd_60, 1),
        "weekly_sales": round(spd_7 * 7, 0),
    }


def get_history(item_name):
    from urllib.parse import quote
    from rate_limiter import wait_if_needed
    import re

    wait_if_needed("float")

    # For special items, extract index
    def extract_idx(name):
        match = re.search(r'\((\d+)\)', name)
        return int(match.group(1)) if match else None

    # Try without and with Bearer prefix
    resp = None
    for auth_header in [FLOAT_API_KEY, f"Bearer {FLOAT_API_KEY}"]:
        r = httpx.get(
            f"https://csfloat.com/api/v1/history/{quote(item_name)}/graph",
            headers={"Authorization": auth_header},
            timeout=15,
        )
        if r.status_code == 200:
            resp = r
            break
        if r.status_code in (401, 403):
            continue
        resp = r
        break
    if resp is None:
        return []

    resp.raise_for_status()
    data = resp.json()

    # Filter outliers using IQR method (removes super rare sales, StatTrak variants, etc.)
    if data and len(data) >= 4:
        prices = [d["avg_price"] / 100 for d in data]
        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        q1 = prices_sorted[n // 4]
        q3 = prices_sorted[3 * n // 4]
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        data = [d for d in data if lower <= d["avg_price"] / 100 <= upper]

    return data


def analyze(item_name, buy_price):
    print(f"\n{'='*55}")
    print(f"  FLIP ANALYZER")
    print(f"  Item:      {item_name}")
    print(f"  Buy Price: ${buy_price:.2f}")
    print(f"{'='*55}")

    data = get_history(item_name)
    if not data:
        print("No data returned from CSFloat API.")
        return

    data = sorted(data, key=lambda x: x["day"], reverse=True)

    def window_stats(days):
        subset = data[:days]
        if not subset:
            return None
        prices = [d["avg_price"] / 100 for d in subset]
        counts = [d["count"] for d in subset]
        avg = sum(prices) / len(prices)
        low = min(prices)
        high = max(prices)
        total_sales = sum(counts)
        return {"avg": avg, "low": low, "high": high, "sales": total_sales, "days": len(subset)}

    w7 = window_stats(7)
    w30 = window_stats(30)
    w60 = window_stats(60)

    def show_window(label, w):
        if not w:
            return
        net_sell = w["avg"] * (1 - CSFLOAT_FEE)
        profit = net_sell - buy_price
        pct = (profit / buy_price) * 100
        drop_to_loss = ((w["low"] - buy_price) / buy_price) * 100
        print(f"\n  [{label}]")
        print(f"  Avg Price:     ${w['avg']:.2f}   |  Low: ${w['low']:.2f}  High: ${w['high']:.2f}")
        print(f"  Total Sales:   {w['sales']} ({w['sales']/w['days']:.1f}/day)")
        print(f"  Sell at avg after 2% fee: ${net_sell:.2f}")
        print(f"  Profit:        ${profit:.2f}  ({pct:+.1f}%)")
        if drop_to_loss < 0:
            print(f"  Lowest was ${w['low']:.2f} -- BELOW buy price by {abs(drop_to_loss):.1f}%")
        else:
            print(f"  Lowest was ${w['low']:.2f} -- {drop_to_loss:.1f}% buffer before loss")

    show_window("7 DAYS", w7)
    show_window("30 DAYS", w30)
    show_window("60 DAYS", w60)

    liq = liquidity_score(w7, w30, w60)
    if liq:
        print(f"\n  [LIQUIDITY]")
        print(f"  Score: {liq['score']}/100 (Grade {liq['grade']})")
        print(f"  Sales/day:  7d={liq['spd_7']}  30d={liq['spd_30']}  60d={liq['spd_60']}")
        print(f"  Weekly sales: {int(liq['weekly_sales'])}")

    if w7 and w30:
        pump_pct = ((w7["avg"] / w30["avg"]) - 1) * 100
        print(f"\n  PUMP CHECK: 7d avg vs 30d avg = {pump_pct:+.1f}%")
        if pump_pct > 15:
            print(f"  PUMPED -- 7d avg is {pump_pct:.1f}% above 30d avg. May correct during trade lock.")
        else:
            print(f"  No pump detected. Price is stable.")

    print(f"\n{'='*55}")
    net7 = (w7["avg"] * (1 - CSFLOAT_FEE) - buy_price) / buy_price * 100 if w7 else 0
    net30 = (w30["avg"] * (1 - CSFLOAT_FEE) - buy_price) / buy_price * 100 if w30 else 0
    pump = ((w7["avg"] / w30["avg"]) - 1) * 100 if w7 and w30 else 0
    sales_per_day = w7["sales"] / 7 if w7 else 0
    low7 = w7["low"] if w7 else 0

    if net30 >= 2 and pump <= 15 and low7 > buy_price and sales_per_day >= 2:
        print(f"  VERDICT: BUY -- {net30:.1f}% net profit, stable price, good liquidity")
    elif net30 >= 2 and low7 < buy_price:
        print(f"  VERDICT: RISKY -- profit looks good but 7d low ${low7:.2f} dipped below buy price")
    elif net30 < 2:
        print(f"  VERDICT: SKIP -- only {net30:.1f}% net profit, does not clear 2% threshold")
    elif pump > 15:
        print(f"  VERDICT: SKIP -- pumped {pump:.1f}% above 30d avg, will likely correct")
    else:
        print(f"  VERDICT: BORDERLINE -- check manually")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        analyze(sys.argv[1], float(sys.argv[2]))
    else:
        print('Usage: python flip_analyzer.py "AK-47 | Redline (Field-Tested)" 45.00')
