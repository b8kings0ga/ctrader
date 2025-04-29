"""Redis cache for market data."""

import json
import time
from typing import Any, Dict, List, Optional, Union

import redis
from pydantic import BaseModel

from src.utils.config import config_manager
from src.utils.logger import get_logger

# Create logger
logger = get_logger("data.cache")


class RedisCache:
    """Redis cache for market data."""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        default_ttl: Optional[int] = None,
    ):
        """Initialize the Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database
            default_ttl: Default TTL in seconds
        """
        # Get configuration from config manager
        if host is None:
            host = config_manager.get("data", "cache", "redis", "host", "localhost")
            
        if port is None:
            port = config_manager.get("data", "cache", "redis", "port", 6379)
            
        if db is None:
            db = config_manager.get("data", "cache", "redis", "db", 0)
            
        if default_ttl is None:
            default_ttl = config_manager.get("data", "cache", "redis", "ttl", 3600)
            
        self.default_ttl = default_ttl
        
        # Initialize Redis client
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,  # Automatically decode responses to strings
        )
        
        logger.info(f"Initialized Redis cache ({host}:{port}, db={db})")
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache.
        
        Args:
            key: Key
            value: Value
            ttl: TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert value to JSON string
            if not isinstance(value, str):
                value = json.dumps(value)
                
            # Set value in Redis
            if ttl is None:
                ttl = self.default_ttl
                
            return self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Error setting value in cache: {e}")
            return False
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache.
        
        Args:
            key: Key
            default: Default value to return if key is not found
            
        Returns:
            Value or default
        """
        try:
            value = self.redis.get(key)
            
            if value is None:
                return default
                
            # Try to parse as JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Error getting value from cache: {e}")
            return default
            
    def delete(self, key: str) -> bool:
        """Delete a value from the cache.
        
        Args:
            key: Key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Error deleting value from cache: {e}")
            return False
            
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.
        
        Args:
            key: Key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return bool(self.redis.exists(key))
        except Exception as e:
            logger.error(f"Error checking if key exists in cache: {e}")
            return False
            
    def ttl(self, key: str) -> int:
        """Get the TTL of a key in the cache.
        
        Args:
            key: Key
            
        Returns:
            TTL in seconds, -1 if key exists but has no TTL, -2 if key does not exist
        """
        try:
            return self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL of key in cache: {e}")
            return -2
            
    def expire(self, key: str, ttl: int) -> bool:
        """Set the TTL of a key in the cache.
        
        Args:
            key: Key
            ttl: TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return bool(self.redis.expire(key, ttl))
        except Exception as e:
            logger.error(f"Error setting TTL of key in cache: {e}")
            return False
            
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern.
        
        Args:
            pattern: Pattern to match
            
        Returns:
            List of keys
        """
        try:
            return self.redis.keys(pattern)
        except Exception as e:
            logger.error(f"Error getting keys from cache: {e}")
            return []
            
    def flush(self) -> bool:
        """Flush the cache.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            return bool(self.redis.flushdb())
        except Exception as e:
            logger.error(f"Error flushing cache: {e}")
            return False


class MarketDataCache:
    """Market data cache using Redis."""
    
    def __init__(self):
        """Initialize the market data cache."""
        self.redis_cache = RedisCache()
        
    def set_ticker(self, symbol: str, ticker: Dict[str, Any]) -> bool:
        """Set ticker data in the cache.
        
        Args:
            symbol: Symbol
            ticker: Ticker data
            
        Returns:
            True if successful, False otherwise
        """
        key = f"ticker:{symbol}"
        return self.redis_cache.set(key, ticker)
        
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data from the cache.
        
        Args:
            symbol: Symbol
            
        Returns:
            Ticker data or None
        """
        key = f"ticker:{symbol}"
        return self.redis_cache.get(key)
        
    def set_order_book(self, symbol: str, order_book: Dict[str, Any]) -> bool:
        """Set order book data in the cache.
        
        Args:
            symbol: Symbol
            order_book: Order book data
            
        Returns:
            True if successful, False otherwise
        """
        key = f"orderbook:{symbol}"
        return self.redis_cache.set(key, order_book)
        
    def get_order_book(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get order book data from the cache.
        
        Args:
            symbol: Symbol
            
        Returns:
            Order book data or None
        """
        key = f"orderbook:{symbol}"
        return self.redis_cache.get(key)
        
    def set_kline(self, symbol: str, interval: str, kline: Dict[str, Any]) -> bool:
        """Set kline data in the cache.
        
        Args:
            symbol: Symbol
            interval: Kline interval
            kline: Kline data
            
        Returns:
            True if successful, False otherwise
        """
        key = f"kline:{symbol}:{interval}"
        return self.redis_cache.set(key, kline)
        
    def get_kline(self, symbol: str, interval: str) -> Optional[Dict[str, Any]]:
        """Get kline data from the cache.
        
        Args:
            symbol: Symbol
            interval: Kline interval
            
        Returns:
            Kline data or None
        """
        key = f"kline:{symbol}:{interval}"
        return self.redis_cache.get(key)
        
    def set_trade(self, symbol: str, trade: Dict[str, Any]) -> bool:
        """Set trade data in the cache.
        
        Args:
            symbol: Symbol
            trade: Trade data
            
        Returns:
            True if successful, False otherwise
        """
        key = f"trade:{symbol}:{trade['id']}"
        return self.redis_cache.set(key, trade)
        
    def get_trade(self, symbol: str, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get trade data from the cache.
        
        Args:
            symbol: Symbol
            trade_id: Trade ID
            
        Returns:
            Trade data or None
        """
        key = f"trade:{symbol}:{trade_id}"
        return self.redis_cache.get(key)
        
    def set_book_ticker(self, symbol: str, book_ticker: Dict[str, Any]) -> bool:
        """Set book ticker data in the cache.
        
        Args:
            symbol: Symbol
            book_ticker: Book ticker data
            
        Returns:
            True if successful, False otherwise
        """
        key = f"bookticker:{symbol}"
        return self.redis_cache.set(key, book_ticker)
        
    def get_book_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get book ticker data from the cache.
        
        Args:
            symbol: Symbol
            
        Returns:
            Book ticker data or None
        """
        key = f"bookticker:{symbol}"
        return self.redis_cache.get(key)


# Create a singleton instance
market_data_cache = MarketDataCache()