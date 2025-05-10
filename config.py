import os

# Bot configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///trading_signals.db")

# Affiliate link
AFFILIATE_LINK = "https://bit.ly/trading3litepro"

# Signal generation settings
MIN_PROBABILITY = 75
MAX_PROBABILITY = 95
TIMEFRAME_MINUTES = 1

# OTC currency pairs
DEFAULT_OTC_PAIRS = [
    "EURUSD-OTC", "EURGBP-OTC", "EURJPY-OTC", "USDCHF-OTC", 
    "USDJPY-OTC", "GBPUSD-OTC", "AUDCAD-OTC", "NZDUSD-OTC", 
    "AUDUSD-OTC", "USDCAD-OTC", "AUDJPY-OTC", "GBPJPY-OTC", 
    "XAUUSD-OTC", "XAGUSD-OTC", "GBPCAD-OTC", "EURCHF-OTC", 
    "NZDJPY-OTC", "CADCHF-OTC", "EURCAD-OTC", "CHFJPY-OTC"
]

# Official channel ID
OFFICIAL_CHANNEL = "@Trading3litepro"
