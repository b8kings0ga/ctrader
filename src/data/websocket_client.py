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
        websocket_config = config_manager.get("data", "websocket", {})
        self.reconnect_interval = websocket_config.get("reconnect_interval", 5)
        self.max_reconnect_attempts = websocket_config.get("max_reconnect_attempts", 10)
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


# Keep the existing BinanceWebSocketClient and BinanceMarketDataClient classes

# Import ccxt.pro for the new WebSocketClient implementation
import ccxt.pro

class WebSocketClient:
    """WebSocket client for real-time trade data using ccxt.pro.
    
    This class connects to Binance using ccxt.pro and subscribes to the public trades stream
    for the configured symbols. It receives and logs trade data in real-time.
    
    Attributes:
        config: Configuration dictionary or manager
        symbols: List of symbols to subscribe to
        logger: Logger instance
        exchange: ccxt.pro exchange instance
        running: Flag indicating if the client is running
    """
    
    def __init__(self, config, strategy, logger):
        """Initialize the WebSocket client.
        
        Args:
            config: Configuration dictionary or manager
            strategy: Strategy instance (subclass of BaseStrategy)
            logger: Logger instance
        """
        self.config = config
        self.strategy = strategy
        self.logger = logger
        self.running = False
        
        # Add diagnostic logging for symbols
        self.logger.info(f"Strategy config type: {type(self.strategy.config)}")
        self.logger.info(f"Strategy config keys: {list(self.strategy.config.keys()) if hasattr(self.strategy.config, 'keys') else 'Not a dict'}")
        
        # Get symbols from strategy config
        self.symbols = self.strategy.config.get('symbols', [])
        self.logger.info(f"Symbols from strategy config: {self.symbols}")
        self.logger.info(f"Symbols type: {type(self.symbols)}")
        
        # Check each symbol to ensure it's a string
        if isinstance(self.symbols, list):
            for i, symbol in enumerate(self.symbols):
                self.logger.info(f"Symbol {i}: {symbol}, type: {type(symbol)}")
                if not isinstance(symbol, str):
                    self.logger.error(f"Non-string symbol detected: {symbol}, type: {type(symbol)}")
        
        # Initialize ccxt.pro.binance with keys/testnet from config
        api_key = None
        api_secret = None
        
        if isinstance(config, dict):
            api_key = config.get('exchange', {}).get('api_key')
            api_secret = config.get('exchange', {}).get('api_secret')
            testnet = config.get('exchange', {}).get('testnet', True)
        else:
            # Assume it's a ConfigManager instance
            api_key = config.get('exchange', 'api_key', None)
            api_secret = config.get('exchange', 'api_secret', None)
            testnet = config.get('exchange', 'testnet', True)
        
        exchange_options = {
            'enableRateLimit': True,
        }
        
        if api_key and api_secret:
            exchange_options['apiKey'] = api_key
            exchange_options['secret'] = api_secret
            
        self.exchange = ccxt.pro.binance(exchange_options)
        
        # Set testnet mode if configured
        if testnet:
            self.exchange.set_sandbox_mode(True)
            self.logger.info("Using Binance testnet")
        
    async def connect(self):
        """Connect to the WebSocket and subscribe to trade streams.
        
        This method establishes the WebSocket connection and subscribes to the
        public trades stream for the configured symbols.
        """
        print(f"STARTUP: WebSocketClient.connect called for symbols: {self.symbols}")
        self.logger.info(f"STARTUP: WebSocketClient.connect called for symbols: {self.symbols}")
        self.logger.info(f"Connecting to WebSocket for symbols: {self.symbols}")
        
        # Add diagnostic logging for symbols right before they're used
        self.logger.info(f"Symbols type before connection: {type(self.symbols)}")
        if isinstance(self.symbols, list):
            for i, symbol in enumerate(self.symbols):
                self.logger.info(f"Symbol {i} before connection: {symbol}, type: {type(symbol)}")
                if isinstance(symbol, dict):
                    self.logger.error(f"Dictionary symbol detected: {symbol}")
                    # Convert dict symbol to string if possible
                    if 'symbol' in symbol:
                        self.logger.warning(f"Attempting to convert dict symbol to string using 'symbol' key: {symbol['symbol']}")
        
        # No explicit connect needed before watch loop in ccxt.pro
        # The connection is established when watch_trades is called
        
    async def _handle_messages(self):
        """Handle WebSocket messages in a loop.
        
        This method runs indefinitely after connection, receiving trade messages
        from the watch_trades stream and logging the essential trade details.
        """
        self.running = True
        
        # Ensure symbols is a list of strings
        if not isinstance(self.symbols, list):
            self.logger.error(f"Expected symbols to be a list, got {type(self.symbols)}: {self.symbols}")
            self.symbols = [str(self.symbols)]
        
        # Convert any non-string symbols to strings
        for i, symbol in enumerate(self.symbols):
            if not isinstance(symbol, str):
                self.logger.warning(f"Converting non-string symbol at index {i} from {type(symbol)} to string: {symbol}")
                self.symbols[i] = str(symbol)
        
        self.logger.info(f"Watching trades for symbols: {self.symbols}")
        
        while self.running:
            try:
                # Process each symbol individually
                for symbol in self.symbols:
                    try:
                        self.logger.info(f"Watching trades for symbol: {symbol}")
                        trades = await self.exchange.watch_trades(symbol)
                        self.logger.info(f"Successfully received trades for {symbol}")
                        
                        for trade in trades:
                            # Enhanced logging for trade data
                            self.logger.info(f"WS Received Trade: {trade.get('symbol')} Price: {trade.get('price')} Time: {trade.get('datetime')}")
                            # Pass trade data to strategy
                            self.logger.info(f"Passing trade to strategy.on_trade: {trade.get('symbol')}")
                            # Check if on_trade is a coroutine function
                            import asyncio
                            if asyncio.iscoroutinefunction(self.strategy.on_trade):
                                await self.strategy.on_trade(trade)
                            else:
                                # Call non-async method directly
                                self.logger.info(f"Strategy.on_trade is not async, calling directly")
                                self.strategy.on_trade(trade)
                    except TypeError as te:
                        self.logger.error(f"TypeError in watch_trades for symbol {symbol}: {te}")
                        # If there's a type error with a specific symbol, log it but continue with other symbols
                        continue
                    except Exception as e:
                        self.logger.error(f"Error watching trades for symbol {symbol}: {e}")
                        # If there's an error with a specific symbol, log it but continue with other symbols
                        continue
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}. Attempting reconnect...")
                await asyncio.sleep(5)  # Delay before implicit reconnect
                
    async def start(self):
        """Start the WebSocket client.
        
        This method connects to the WebSocket and starts the message handling loop.
        """
        if self.running:
            return
            
        self.logger.info(f"Starting WebSocket client for symbols: {self.symbols}")
        try:
            await self.connect()
            await self._handle_messages()
        except Exception as e:
            self.logger.error(f"Error starting WebSocket client: {e}")
            
    async def stop(self):
        """Stop the WebSocket client.
        
        This method gracefully closes the WebSocket connection.
        """
        if not self.running:
            return
            
        self.running = False
        self.logger.info("Stopping WebSocket client")
        
        if hasattr(self, 'exchange') and self.exchange:
            try:
                self.logger.info("Closing WebSocket connection...")
                await self.exchange.close()
                self.logger.info("WebSocket connection closed.")
            except Exception as e:
                self.logger.error(f"Error closing WebSocket connection: {e}")