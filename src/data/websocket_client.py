"""WebSocket client for real-time market data collection."""

import asyncio
import json
import time
from typing import Any, Callable, Dict, List, Optional, Set, Union

import websockets
from pydantic import BaseModel

from src.utils.config import config_manager
from src.utils.logger import get_logger

# Create logger
logger = get_logger("data.websocket")


class WebSocketMessage(BaseModel):
    """WebSocket message model."""
    
    stream: str
    data: Dict[str, Any]


class BinanceWebSocketClient:
    """Binance WebSocket client for real-time market data collection."""
    
    def __init__(self):
        """Initialize the WebSocket client."""
        self.base_url = "wss://stream.binance.com:9443/ws"
        self.testnet_url = "wss://testnet.binance.vision/ws"
        self.subscriptions: Set[str] = set()
        self.callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.websocket = None
        self.running = False
        self.reconnect_interval = config_manager.get(
            "data", "websocket", "reconnect_interval", 5
        )
        self.max_reconnect_attempts = config_manager.get(
            "data", "websocket", "max_reconnect_attempts", 10
        )
        self.testnet = config_manager.get("exchange", "testnet", True)
        
    @property
    def ws_url(self) -> str:
        """Get the WebSocket URL based on testnet setting."""
        return self.testnet_url if self.testnet else self.base_url
        
    async def connect(self):
        """Connect to the WebSocket server."""
        if self.websocket is not None:
            await self.websocket.close()
            
        logger.info(f"Connecting to {self.ws_url}")
        self.websocket = await websockets.connect(self.ws_url)
        logger.info("Connected to WebSocket server")
        
        # Resubscribe to streams
        if self.subscriptions:
            await self._subscribe(list(self.subscriptions))
            
    async def _subscribe(self, streams: List[str]):
        """Subscribe to streams.
        
        Args:
            streams: List of streams to subscribe to
        """
        if not streams:
            return
            
        if self.websocket is None:
            await self.connect()
            
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000),
        }
        
        logger.info(f"Subscribing to streams: {streams}")
        await self.websocket.send(json.dumps(subscribe_msg))
        
    async def _unsubscribe(self, streams: List[str]):
        """Unsubscribe from streams.
        
        Args:
            streams: List of streams to unsubscribe from
        """
        if not streams or self.websocket is None:
            return
            
        unsubscribe_msg = {
            "method": "UNSUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000),
        }
        
        logger.info(f"Unsubscribing from streams: {streams}")
        await self.websocket.send(json.dumps(unsubscribe_msg))
        
    async def subscribe(self, stream: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to a stream.
        
        Args:
            stream: Stream to subscribe to
            callback: Callback function to call when a message is received
        """
        if stream not in self.subscriptions:
            self.subscriptions.add(stream)
            await self._subscribe([stream])
            
        if stream not in self.callbacks:
            self.callbacks[stream] = []
            
        self.callbacks[stream].append(callback)
        
    async def unsubscribe(self, stream: str, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """Unsubscribe from a stream.
        
        Args:
            stream: Stream to unsubscribe from
            callback: Callback function to remove (if None, remove all callbacks)
        """
        if stream not in self.subscriptions:
            return
            
        if callback is None:
            # Remove all callbacks
            self.callbacks.pop(stream, None)
        else:
            # Remove specific callback
            if stream in self.callbacks:
                self.callbacks[stream] = [cb for cb in self.callbacks[stream] if cb != callback]
                
        # If no more callbacks, unsubscribe from stream
        if stream not in self.callbacks or not self.callbacks[stream]:
            self.subscriptions.remove(stream)
            await self._unsubscribe([stream])
            
    async def start(self):
        """Start the WebSocket client."""
        if self.running:
            return
            
        self.running = True
        
        reconnect_attempts = 0
        while self.running:
            try:
                if self.websocket is None:
                    await self.connect()
                    
                async for message in self.websocket:
                    if not self.running:
                        break
                        
                    try:
                        data = json.loads(message)
                        
                        # Handle subscription response
                        if "result" in data:
                            logger.debug(f"Subscription response: {data}")
                            continue
                            
                        # Handle stream data
                        if "stream" in data:
                            stream = data["stream"]
                            stream_data = data["data"]
                            
                            # Call callbacks
                            if stream in self.callbacks:
                                for callback in self.callbacks[stream]:
                                    try:
                                        callback(stream_data)
                                    except Exception as e:
                                        logger.error(f"Error in callback for stream {stream}: {e}")
                        else:
                            logger.warning(f"Unknown message format: {data}")
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON: {message}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        
                # Reset reconnect attempts on successful connection
                reconnect_attempts = 0
                
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                
                # Reconnect
                reconnect_attempts += 1
                if reconnect_attempts > self.max_reconnect_attempts:
                    logger.error(f"Max reconnect attempts reached ({self.max_reconnect_attempts})")
                    self.running = False
                    break
                    
                logger.info(f"Reconnecting in {self.reconnect_interval} seconds (attempt {reconnect_attempts}/{self.max_reconnect_attempts})")
                await asyncio.sleep(self.reconnect_interval)
                self.websocket = None
                
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                
                # Reconnect
                reconnect_attempts += 1
                if reconnect_attempts > self.max_reconnect_attempts:
                    logger.error(f"Max reconnect attempts reached ({self.max_reconnect_attempts})")
                    self.running = False
                    break
                    
                logger.info(f"Reconnecting in {self.reconnect_interval} seconds (attempt {reconnect_attempts}/{self.max_reconnect_attempts})")
                await asyncio.sleep(self.reconnect_interval)
                self.websocket = None
                
    async def stop(self):
        """Stop the WebSocket client."""
        self.running = False
        
        if self.websocket is not None:
            await self.websocket.close()
            self.websocket = None
            
        logger.info("WebSocket client stopped")


class BinanceMarketDataClient:
    """Binance market data client using WebSocket."""
    
    def __init__(self):
        """Initialize the market data client."""
        self.ws_client = BinanceWebSocketClient()
        self.callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        
    async def start(self):
        """Start the market data client."""
        await self.ws_client.start()
        
    async def stop(self):
        """Stop the market data client."""
        await self.ws_client.stop()
        
    async def subscribe_ticker(self, symbol: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to ticker updates.
        
        Args:
            symbol: Symbol to subscribe to
            callback: Callback function to call when a ticker update is received
        """
        # Convert symbol format from BTC/USDT to btcusdt
        formatted_symbol = symbol.replace("/", "").lower()
        stream = f"{formatted_symbol}@ticker"
        
        await self.ws_client.subscribe(stream, callback)
        
    async def subscribe_trades(self, symbol: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to trade updates.
        
        Args:
            symbol: Symbol to subscribe to
            callback: Callback function to call when a trade update is received
        """
        # Convert symbol format from BTC/USDT to btcusdt
        formatted_symbol = symbol.replace("/", "").lower()
        stream = f"{formatted_symbol}@trade"
        
        await self.ws_client.subscribe(stream, callback)
        
    async def subscribe_klines(
        self, symbol: str, interval: str, callback: Callable[[Dict[str, Any]], None]
    ):
        """Subscribe to kline updates.
        
        Args:
            symbol: Symbol to subscribe to
            interval: Kline interval (1m, 5m, 15m, etc.)
            callback: Callback function to call when a kline update is received
        """
        # Convert symbol format from BTC/USDT to btcusdt
        formatted_symbol = symbol.replace("/", "").lower()
        stream = f"{formatted_symbol}@kline_{interval}"
        
        await self.ws_client.subscribe(stream, callback)
        
    async def subscribe_depth(
        self, symbol: str, callback: Callable[[Dict[str, Any]], None], update_speed: str = "100ms"
    ):
        """Subscribe to order book updates.
        
        Args:
            symbol: Symbol to subscribe to
            update_speed: Update speed (100ms, 1000ms)
            callback: Callback function to call when an order book update is received
        """
        # Convert symbol format from BTC/USDT to btcusdt
        formatted_symbol = symbol.replace("/", "").lower()
        stream = f"{formatted_symbol}@depth@{update_speed}"
        
        await self.ws_client.subscribe(stream, callback)
        
    async def subscribe_book_ticker(self, symbol: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to book ticker updates.
        
        Args:
            symbol: Symbol to subscribe to
            callback: Callback function to call when a book ticker update is received
        """
        # Convert symbol format from BTC/USDT to btcusdt
        formatted_symbol = symbol.replace("/", "").lower()
        stream = f"{formatted_symbol}@bookTicker"
        
        await self.ws_client.subscribe(stream, callback)


# Create a singleton instance
binance_market_data_client = BinanceMarketDataClient()