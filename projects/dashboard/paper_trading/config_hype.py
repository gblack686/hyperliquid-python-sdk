"""
Configuration for HYPE paper trading
"""

# Trading configuration
TRADING_CONFIG = {
    "account_name": "hype_paper_trader",
    "initial_balance": 100000.0,
    "symbol": "HYPE",
    "base_position_size": 100.0,  # Base size in HYPE tokens
    "max_position_size": 1000.0,  # Maximum HYPE tokens per position
    "commission_rate": 0.0004,  # 0.04%
    "slippage_pct": 0.001,  # 0.1%
}

# Risk management
RISK_CONFIG = {
    "max_positions": 3,  # Maximum simultaneous positions
    "stop_loss_pct": 0.05,  # 5% stop loss
    "take_profit_pct": 0.10,  # 10% take profit
    "max_daily_loss": 0.02,  # 2% daily max loss
    "position_sizing": "fixed",  # fixed, kelly, or volatility_based
}

# Trigger thresholds for HYPE
TRIGGER_THRESHOLDS = {
    "confidence_min": 0.60,  # Minimum confidence to take trade
    "funding_rate_threshold": 0.005,  # 0.5% funding rate
    "volume_spike_threshold": 2.0,  # 2x average volume
    "price_momentum_threshold": 0.02,  # 2% price change
}

# HYPE-specific parameters
HYPE_PARAMS = {
    "typical_price": 35.0,  # Typical HYPE price for initialization
    "volatility_lookback": 24,  # Hours for volatility calculation
    "trend_lookback": 48,  # Hours for trend determination
    "support_resistance_lookback": 168,  # 1 week for S/R levels
}

# Paper trading behavior
PAPER_TRADING = {
    "auto_trade": True,  # Automatically execute on triggers
    "simulate_latency": 0.5,  # Simulated execution latency in seconds
    "use_limit_orders": False,  # Use market orders for simplicity
    "record_all_signals": True,  # Record even non-traded signals
}

# Monitoring and reporting
MONITORING = {
    "update_interval": 10,  # Seconds between account updates
    "performance_save_interval": 300,  # Save performance every 5 minutes
    "print_summary": True,  # Print account summary to console
    "save_trades_to_db": True,  # Save all trades to database
}

# API endpoints (if needed)
API_CONFIG = {
    "trigger_analyzer": "http://hl-trigger-analyzer:8000",  # Docker internal
    "fallback_analyzer": "http://localhost:8000",  # Fallback to localhost
}

def get_position_size(confidence: float, base_size: float = None) -> float:
    """
    Calculate position size based on confidence
    
    Args:
        confidence: Trigger confidence score (0-1)
        base_size: Base position size in tokens
        
    Returns:
        Position size in tokens
    """
    if base_size is None:
        base_size = TRADING_CONFIG["base_position_size"]
    
    # Scale position size with confidence
    if confidence >= 0.80:
        multiplier = 1.5
    elif confidence >= 0.70:
        multiplier = 1.0
    elif confidence >= 0.60:
        multiplier = 0.5
    else:
        multiplier = 0.0  # Don't trade below threshold
    
    position_size = base_size * multiplier
    
    # Cap at maximum position size
    return min(position_size, TRADING_CONFIG["max_position_size"])

def should_trade(trigger_name: str, confidence: float, features: dict) -> bool:
    """
    Determine if a trade should be executed
    
    Args:
        trigger_name: Name of the triggered signal
        confidence: Confidence score
        features: Current market features
        
    Returns:
        True if trade should be executed
    """
    # Check minimum confidence
    if confidence < TRIGGER_THRESHOLDS["confidence_min"]:
        return False
    
    # Check specific conditions for HYPE
    if "extreme" in trigger_name.lower() and confidence < 0.75:
        return False  # Higher threshold for extreme signals
    
    # Check funding rate if available
    if "funding_bp" in features:
        funding_rate = features["funding_bp"] / 10000  # Convert basis points
        if abs(funding_rate) > TRIGGER_THRESHOLDS["funding_rate_threshold"]:
            return True  # Strong funding signal
    
    # Check volume if available
    if "volume_spike" in features:
        if features["volume_spike"] > TRIGGER_THRESHOLDS["volume_spike_threshold"]:
            return True  # High volume confirmation
    
    return confidence >= TRIGGER_THRESHOLDS["confidence_min"]

# Export configuration
CONFIG = {
    "trading": TRADING_CONFIG,
    "risk": RISK_CONFIG,
    "triggers": TRIGGER_THRESHOLDS,
    "hype": HYPE_PARAMS,
    "paper": PAPER_TRADING,
    "monitoring": MONITORING,
    "api": API_CONFIG
}