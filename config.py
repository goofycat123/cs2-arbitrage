import os
from dotenv import load_dotenv

load_dotenv()

FLOAT_API_KEY = os.getenv("FLOAT_API_KEY")
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
CSGOEMPIRE_API_KEY = os.getenv("CSGOEMPIRE_API_KEY")
PRICEMPIRE_API_KEY = os.getenv("PRICEMPIRE_API_KEY")

# Fees — Empire buy side ~6% avg, CSFloat sell side 2%
FEES = {
    "empire_buy": 0.06,  # ~5-7% markup on Empire withdrawals
    "float_sell": 0.02,  # 2% CSFloat seller fee
}

MIN_PRICE = 10.0
MAX_PRICE = 200.0
MIN_NET_PROFIT_PCT = 0.02
MIN_SALES_7D = 5
PUMP_THRESHOLD = 0.15  # 7d avg > 30d avg by 15% = pumped

TARGET_WEAPONS = ["AK-47", "M4A4", "M4A1-S", "AWP", "Knife", "Bayonet", "Karambit", "Butterfly", "Flip Knife", "Gut Knife", "Falchion", "Shadow Daggers", "Bowie", "Huntsman", "Navaja", "Stiletto", "Talon", "Ursus", "Classic Knife", "Nomad", "Skeleton", "Survival", "Paracord", "Kukri"]

SCAN_INTERVAL = 300

RATE_LIMITS = {
    "float": 10,
    "steam": 20,
    "empire": 5,       # Empire is strict, keep it slow
    "pricempire_free": 10,  # Pricempire free tier: 10/min, 1000/day
}
