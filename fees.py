"""
Fee calculator for Empire buy -> CSFloat sell flow.

Empire buy price = what you pay on Empire
CSFloat price = true market value (100% reference)
CSFloat sell fee = 2%

Net profit = (csfloat_price * 0.98) - empire_price
"""

from config import FEES


def net_after_float_sell(csfloat_price: float) -> float:
    """What you receive after CSFloat's 2% fee."""
    return csfloat_price * (1 - FEES["float_sell"])


def net_profit(empire_buy_price: float, csfloat_sell_price: float) -> float:
    """Net profit in dollars: sell on CSFloat minus what you paid on Empire."""
    return net_after_float_sell(csfloat_sell_price) - empire_buy_price


def net_profit_pct(empire_buy_price: float, csfloat_sell_price: float) -> float:
    """Net profit as percentage of buy price."""
    if empire_buy_price <= 0:
        return 0
    return net_profit(empire_buy_price, csfloat_sell_price) / empire_buy_price
