"""Shared configuration and constants."""

# Risk limits
MAX_POSITION_SIZE_USDC = 500.0       # Max single position
MAX_PORTFOLIO_EXPOSURE_USDC = 5000.0 # Max total exposure
MAX_DELTA_DRIFT = 0.15               # Max allowed delta deviation from neutral
MIN_EDGE = 0.03                      # Minimum required edge (model_prob - market_price)
MAX_MARKET_PRICE = 0.95              # Skip near-certain outcomes
MIN_MARKET_PRICE = 0.05              # Skip near-impossible outcomes

# Polymarket API
POLYMARKET_API_BASE = "https://clob.polymarket.com"
POLYMARKET_GAMMA_API = "https://gamma-api.polymarket.com"

# Portfolio
PORTFOLIO_LOG_PATH = "portfolio_log.jsonl"
STARTING_BALANCE_USDC = 10_000.0
