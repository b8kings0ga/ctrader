"""Binance exchange connector for ctrader."""

import asyncio
from typing import Any, Dict, List, Optional, Union

import ccxt
import ccxt.async_support as ccxt_async
from pydantic import BaseModel

from src.utils.config import config_manager
from src.utils.logger import get_logger

# Create logger
logger = get_logger("exchange.binance")


class OrderRequest(BaseModel):
    """Order request model."""
    
    symbol: str
    side: str  # "buy" or "sell"
    type: str  # "limit", "market", etc.
    amount: float
    price: Optional[float] = None  # Required for limit orders
    params: Dict[str, Any] = {}


class OrderResponse(BaseModel):
    """Order response model."""
    
    id: str
    symbol: str
    side: str
    type: str
    amount: float
    price: Optional[float] = None
    status: str
    timestamp: int
    datetime: str
    raw: Dict[str, Any] = {}


class BinanceConnector:
    """Binance exchange connector using ccxt."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: Optional[bool] = None,
    ):
        """Initialize the Binance connector.
        
        Args:
            api_key: API key
            api_secret: API secret
            testnet: Whether to use testnet
        """
        # Get configuration from config manager
        if api_key is None:
            api_key = config_manager.get("exchange", "api_key", "")
            
        if api_secret is None:
            api_secret = config_manager.get("exchange", "api_secret", "")
            
        if testnet is None:
            testnet = config_manager.get("exchange", "testnet", True)
            
        # Initialize ccxt exchange
        self.exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
                "adjustForTimeDifference": True,
                "testnet": testnet,
            },
        })
        
        # Initialize async ccxt exchange
        self.async_exchange = ccxt_async.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
                "adjustForTimeDifference": True,
                "testnet": testnet,
            },
        })
        
        logger.info(f"Initialized Binance connector (testnet: {testnet})")
        
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, "async_exchange"):
            asyncio.create_task(self.async_exchange.close())
            
    async def close(self):
        """Close the async exchange."""
        if hasattr(self, "async_exchange"):
            await self.async_exchange.close()
            
    def get_markets(self) -> Dict[str, Any]:
        """Get all markets.
        
        Returns:
            Dictionary of markets
        """
        return self.exchange.load_markets()
        
    async def get_markets_async(self) -> Dict[str, Any]:
        """Get all markets asynchronously.
        
        Returns:
            Dictionary of markets
        """
        return await self.async_exchange.load_markets()
        
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker for a symbol.
        
        Args:
            symbol: Symbol to get ticker for
            
        Returns:
            Ticker data
        """
        return self.exchange.fetch_ticker(symbol)
        
    async def get_ticker_async(self, symbol: str) -> Dict[str, Any]:
        """Get ticker for a symbol asynchronously.
        
        Args:
            symbol: Symbol to get ticker for
            
        Returns:
            Ticker data
        """
        return await self.async_exchange.fetch_ticker(symbol)
        
    def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get order book for a symbol.
        
        Args:
            symbol: Symbol to get order book for
            limit: Number of orders to get
            
        Returns:
            Order book data
        """
        return self.exchange.fetch_order_book(symbol, limit)
        
    async def get_order_book_async(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get order book for a symbol asynchronously.
        
        Args:
            symbol: Symbol to get order book for
            limit: Number of orders to get
            
        Returns:
            Order book data
        """
        return await self.async_exchange.fetch_order_book(symbol, limit)
        
    def get_balance(self) -> Dict[str, Any]:
        """Get account balance.
        
        Returns:
            Account balance
        """
        return self.exchange.fetch_balance()
        
    async def get_balance_async(self) -> Dict[str, Any]:
        """Get account balance asynchronously.
        
        Returns:
            Account balance
        """
        return await self.async_exchange.fetch_balance()
        
    def create_order(self, order_request: OrderRequest) -> OrderResponse:
        """Create an order.
        
        Args:
            order_request: Order request
            
        Returns:
            Order response
        """
        try:
            response = self.exchange.create_order(
                symbol=order_request.symbol,
                type=order_request.type,
                side=order_request.side,
                amount=order_request.amount,
                price=order_request.price,
                params=order_request.params,
            )
            
            return OrderResponse(
                id=response["id"],
                symbol=response["symbol"],
                side=response["side"],
                type=response["type"],
                amount=float(response["amount"]),
                price=float(response["price"]) if "price" in response else None,
                status=response["status"],
                timestamp=response["timestamp"],
                datetime=response["datetime"],
                raw=response,
            )
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise
            
    async def create_order_async(self, order_request: OrderRequest) -> OrderResponse:
        """Create an order asynchronously.
        
        Args:
            order_request: Order request
            
        Returns:
            Order response
        """
        try:
            response = await self.async_exchange.create_order(
                symbol=order_request.symbol,
                type=order_request.type,
                side=order_request.side,
                amount=order_request.amount,
                price=order_request.price,
                params=order_request.params,
            )
            
            return OrderResponse(
                id=response["id"],
                symbol=response["symbol"],
                side=response["side"],
                type=response["type"],
                amount=float(response["amount"]),
                price=float(response["price"]) if "price" in response else None,
                status=response["status"],
                timestamp=response["timestamp"],
                datetime=response["datetime"],
                raw=response,
            )
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise
            
    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an order.
        
        Args:
            order_id: Order ID
            symbol: Symbol
            
        Returns:
            Cancellation response
        """
        return self.exchange.cancel_order(order_id, symbol)
        
    async def cancel_order_async(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an order asynchronously.
        
        Args:
            order_id: Order ID
            symbol: Symbol
            
        Returns:
            Cancellation response
        """
        return await self.async_exchange.cancel_order(order_id, symbol)
        
    def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get an order.
        
        Args:
            order_id: Order ID
            symbol: Symbol
            
        Returns:
            Order data
        """
        return self.exchange.fetch_order(order_id, symbol)
        
    async def get_order_async(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get an order asynchronously.
        
        Args:
            order_id: Order ID
            symbol: Symbol
            
        Returns:
            Order data
        """
        return await self.async_exchange.fetch_order(order_id, symbol)
        
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open orders.
        
        Args:
            symbol: Symbol to get open orders for
            
        Returns:
            List of open orders
        """
        return self.exchange.fetch_open_orders(symbol)
        
    async def get_open_orders_async(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open orders asynchronously.
        
        Args:
            symbol: Symbol to get open orders for
            
        Returns:
            List of open orders
        """
        return await self.async_exchange.fetch_open_orders(symbol)
        
    def get_closed_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get closed orders.
        
        Args:
            symbol: Symbol to get closed orders for
            
        Returns:
            List of closed orders
        """
        return self.exchange.fetch_closed_orders(symbol)
        
    async def get_closed_orders_async(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get closed orders asynchronously.
        
        Args:
            symbol: Symbol to get closed orders for
            
        Returns:
            List of closed orders
        """
        return await self.async_exchange.fetch_closed_orders(symbol)
        
    def get_ohlcv(
        self, symbol: str, timeframe: str = "1m", limit: int = 100
    ) -> List[List[Union[int, float]]]:
        """Get OHLCV data.
        
        Args:
            symbol: Symbol to get OHLCV data for
            timeframe: Timeframe
            limit: Number of candles to get
            
        Returns:
            OHLCV data
        """
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
    async def get_ohlcv_async(
        self, symbol: str, timeframe: str = "1m", limit: int = 100
    ) -> List[List[Union[int, float]]]:
        """Get OHLCV data asynchronously.
        
        Args:
            symbol: Symbol to get OHLCV data for
            timeframe: Timeframe
            limit: Number of candles to get
            
        Returns:
            OHLCV data
        """
        return await self.async_exchange.fetch_ohlcv(symbol, timeframe, limit=limit)


# Create a singleton instance
binance_connector = BinanceConnector()