"""
Configuration Management for Trading System
Handles environment variables, validation, and settings
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()


class TradingMode(Enum):
    """Trading modes"""
    DRY_RUN = "dry_run"
    PAPER = "paper"
    LIVE = "live"


class Network(Enum):
    """Network types"""
    MAINNET = "MAINNET_API_URL"
    TESTNET = "TESTNET_API_URL"


@dataclass
class HyperliquidConfig:
    """Hyperliquid configuration"""
    api_key: str
    account_address: str
    network: str = "MAINNET_API_URL"
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.api_key or not self.account_address:
            raise ValueError("Missing Hyperliquid credentials")
        if len(self.account_address) != 42 or not self.account_address.startswith("0x"):
            raise ValueError("Invalid account address format")
        return True


@dataclass
class StrategyConfig:
    """Strategy configuration"""
    name: str = "mean_reversion"
    lookback_period: int = 12
    entry_z_score: float = 0.75
    exit_z_score: float = 0.5
    stop_loss_pct: float = 0.05
    max_position_size: float = 1000.0
    max_leverage: float = 3.0
    min_order_size: float = 10.0
    signal_cooldown: int = 60
    
    def validate(self) -> bool:
        """Validate strategy parameters"""
        if self.lookback_period < 2:
            raise ValueError("Lookback period must be at least 2")
        if self.entry_z_score <= 0 or self.exit_z_score <= 0:
            raise ValueError("Z-scores must be positive")
        if self.entry_z_score <= self.exit_z_score:
            raise ValueError("Entry Z-score must be greater than exit Z-score")
        if self.stop_loss_pct <= 0 or self.stop_loss_pct >= 1:
            raise ValueError("Stop loss must be between 0 and 1")
        if self.max_position_size <= 0:
            raise ValueError("Max position size must be positive")
        if self.max_leverage < 1:
            raise ValueError("Max leverage must be at least 1")
        return True


@dataclass
class DatabaseConfig:
    """Database configuration"""
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    @property
    def has_supabase(self) -> bool:
        """Check if Supabase is configured"""
        return bool(self.supabase_url and self.supabase_key)
    
    @property
    def has_redis(self) -> bool:
        """Check if Redis is configured"""
        return bool(self.redis_host)


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_port: int = 8080
    health_check_interval: int = 60
    enable_alerts: bool = False
    discord_webhook: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    @property
    def has_discord(self) -> bool:
        """Check if Discord is configured"""
        return bool(self.discord_webhook)
    
    @property
    def has_telegram(self) -> bool:
        """Check if Telegram is configured"""
        return bool(self.telegram_bot_token and self.telegram_chat_id)


@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_daily_loss: float = 0.10  # 10% of max position
    max_consecutive_losses: int = 5
    max_error_count: int = 10
    volatility_threshold: float = 0.15  # 15% daily volatility
    position_timeout_hours: int = 48
    order_timeout_seconds: int = 30
    slippage_tolerance: float = 0.002  # 0.2%
    
    def validate(self) -> bool:
        """Validate risk parameters"""
        if self.max_daily_loss <= 0 or self.max_daily_loss >= 1:
            raise ValueError("Max daily loss must be between 0 and 1")
        if self.volatility_threshold <= 0:
            raise ValueError("Volatility threshold must be positive")
        return True


class Config:
    """Main configuration manager"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_file: Optional JSON config file to load
        """
        
        # Load from environment first
        self.hyperliquid = HyperliquidConfig(
            api_key=os.getenv("HYPERLIQUID_API_KEY", ""),
            account_address=os.getenv("ACCOUNT_ADDRESS", ""),
            network=os.getenv("NETWORK", "MAINNET_API_URL")
        )
        
        self.strategy = StrategyConfig(
            name=os.getenv("STRATEGY_NAME", "mean_reversion"),
            lookback_period=int(os.getenv("LOOKBACK_PERIOD", 12)),
            entry_z_score=float(os.getenv("ENTRY_Z_SCORE", 0.75)),
            exit_z_score=float(os.getenv("EXIT_Z_SCORE", 0.5)),
            stop_loss_pct=float(os.getenv("STOP_LOSS_PCT", 0.05)),
            max_position_size=float(os.getenv("MAX_POSITION_SIZE", 1000)),
            max_leverage=float(os.getenv("MAX_LEVERAGE", 3.0)),
            min_order_size=float(os.getenv("MIN_ORDER_SIZE", 10)),
            signal_cooldown=int(os.getenv("SIGNAL_COOLDOWN", 60))
        )
        
        self.database = DatabaseConfig(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_ANON_KEY"),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
            redis_db=int(os.getenv("REDIS_DB", 0))
        )
        
        self.monitoring = MonitoringConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
            metrics_port=int(os.getenv("METRICS_PORT", 8080)),
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", 60)),
            enable_alerts=os.getenv("ENABLE_ALERTS", "false").lower() == "true",
            discord_webhook=os.getenv("DISCORD_WEBHOOK_URL"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID")
        )
        
        self.risk = RiskConfig(
            max_daily_loss=float(os.getenv("MAX_DAILY_LOSS", 0.10)),
            max_consecutive_losses=int(os.getenv("MAX_CONSECUTIVE_LOSSES", 5)),
            max_error_count=int(os.getenv("MAX_ERROR_COUNT", 10)),
            volatility_threshold=float(os.getenv("VOLATILITY_THRESHOLD", 0.15)),
            position_timeout_hours=int(os.getenv("POSITION_TIMEOUT_HOURS", 48)),
            order_timeout_seconds=int(os.getenv("ORDER_TIMEOUT", 30)),
            slippage_tolerance=float(os.getenv("SLIPPAGE_TOLERANCE", 0.002))
        )
        
        # Load from config file if provided
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
        
        # Set trading mode
        self.mode = TradingMode.DRY_RUN  # Default to dry run for safety
    
    def load_from_file(self, filepath: str):
        """Load configuration from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Override with file values
            if "strategy" in data:
                for key, value in data["strategy"].items():
                    if hasattr(self.strategy, key):
                        setattr(self.strategy, key, value)
            
            if "risk" in data:
                for key, value in data["risk"].items():
                    if hasattr(self.risk, key):
                        setattr(self.risk, key, value)
            
            logger.info(f"Loaded configuration from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
    
    def save_to_file(self, filepath: str):
        """Save current configuration to JSON file"""
        try:
            config_dict = {
                "strategy": asdict(self.strategy),
                "risk": asdict(self.risk),
                "monitoring": asdict(self.monitoring)
            }
            
            with open(filepath, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            logger.info(f"Saved configuration to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save config file: {e}")
    
    def validate(self) -> bool:
        """Validate all configuration sections"""
        try:
            self.hyperliquid.validate()
            self.strategy.validate()
            self.risk.validate()
            
            logger.info("Configuration validation successful")
            return True
            
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        return {
            "mode": self.mode.value,
            "network": self.hyperliquid.network,
            "strategy": {
                "name": self.strategy.name,
                "lookback": self.strategy.lookback_period,
                "entry_z": self.strategy.entry_z_score,
                "exit_z": self.strategy.exit_z_score,
                "max_position": self.strategy.max_position_size,
                "max_leverage": self.strategy.max_leverage
            },
            "risk": {
                "max_daily_loss": f"{self.risk.max_daily_loss:.1%}",
                "volatility_threshold": f"{self.risk.volatility_threshold:.1%}",
                "slippage_tolerance": f"{self.risk.slippage_tolerance:.1%}"
            },
            "database": {
                "supabase": self.database.has_supabase,
                "redis": self.database.has_redis
            },
            "monitoring": {
                "log_level": self.monitoring.log_level,
                "metrics": self.monitoring.enable_metrics,
                "alerts": self.monitoring.enable_alerts,
                "discord": self.monitoring.has_discord,
                "telegram": self.monitoring.has_telegram
            }
        }
    
    def print_summary(self):
        """Print configuration summary"""
        summary = self.get_summary()
        
        print("\n" + "="*50)
        print("TRADING SYSTEM CONFIGURATION")
        print("="*50)
        
        print(f"\nMode: {summary['mode'].upper()}")
        print(f"Network: {summary['network']}")
        
        print("\nStrategy:")
        for key, value in summary["strategy"].items():
            print(f"  {key}: {value}")
        
        print("\nRisk Management:")
        for key, value in summary["risk"].items():
            print(f"  {key}: {value}")
        
        print("\nDatabase:")
        for key, value in summary["database"].items():
            print(f"  {key}: {'Enabled' if value else 'Disabled'}")
        
        print("\nMonitoring:")
        for key, value in summary["monitoring"].items():
            if isinstance(value, bool):
                print(f"  {key}: {'Enabled' if value else 'Disabled'}")
            else:
                print(f"  {key}: {value}")
        
        print("="*50 + "\n")


# Singleton instance
_config_instance: Optional[Config] = None


def get_config(config_file: Optional[str] = None) -> Config:
    """Get configuration singleton"""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config(config_file)
    
    return _config_instance


def reset_config():
    """Reset configuration singleton"""
    global _config_instance
    _config_instance = None


if __name__ == "__main__":
    # Test configuration
    config = get_config()
    
    # Validate
    if config.validate():
        config.print_summary()
        
        # Save example config
        config.save_to_file("config_example.json")
    else:
        print("Configuration validation failed!")