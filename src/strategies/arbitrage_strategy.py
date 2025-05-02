"""Simple arbitrage strategy implementation for ctrader."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.ml.feature_engineering import FeatureEngineering
from src.ml.model_manager import ModelManager
from src.strategies import BaseStrategy, register_strategy


class SimpleArbitrageStrategy(BaseStrategy):
    """Simple arbitrage strategy implementation.
    
    This strategy looks for price differences between markets and executes trades
    when the price difference exceeds a threshold.
    
    It implements triangular arbitrage detection logic, which looks for opportunities
    to profit from price differences between three related trading pairs.
    """
    
    def initialize(self, exchange_connector: Any, data_cache: Any = None, execution_handler: Any = None) -> None:
        """Initialize the strategy with required components.
        
        Args:
            exchange_connector: Exchange connector instance
            data_cache: Data cache instance (can be None for backtesting)
            execution_handler: Execution handler instance for processing signals
        """
        self.logger.info("Initializing SimpleArbitrageStrategy")
        self.exchange = exchange_connector
        self.execution_handler = execution_handler
        
        # Log if signal_callback is available
        if self.signal_callback:
            self.logger.info("Signal callback is configured - will emit signals on arbitrage opportunities")
        else:
            self.logger.warning("No signal callback configured - will log arbitrage opportunities but not emit signals")
        
        # Handle the case where data_cache is None (e.g., in backtesting)
        if data_cache is None:
            self.logger.warning("No data_cache provided. Some functionality may be limited.")
            self.data_cache = None
        else:
            self.data_cache = data_cache
        
        # Get strategy-specific configuration
        self.min_profit_threshold = self.config.get("min_profit_threshold", 0.001)
        self.max_trade_amount = self.config.get("max_trade_amount", 100)
        self.symbols = self.config.get("symbols", [])
        self.fee_pct = self.config.get("fee_pct", 0.001)  # Default 0.1% fee
        
        # Initialize price cache for storing latest bid/ask prices
        self.price_cache = {}
        
        # Initialize latest prices dictionary for trade data
        self.latest_prices = {symbol: None for symbol in self.symbols}
        self.threshold = self.config.get("threshold", 0.00001)  # Lowered threshold for testing pipeline
        
        # Initialize ML components
        self.feature_engineer = FeatureEngineering()
        self.model_manager = ModelManager(model_dir=self.config.get('model_dir', './models'))
        self.last_prediction = None  # To store the latest prediction
        
        # Load the default model
        default_model_name = self.config.get('ml_model_name', 'arbitrage_predictor_v1')
        loaded = self.model_manager.load_model(default_model_name)
        if loaded:
            self.logger.info(f"Successfully loaded ML model: {default_model_name}")
        else:
            self.logger.warning(f"Failed to load ML model: {default_model_name}. Prediction will be unavailable.")
        
        self.logger.info(f"Strategy configured with: min_profit_threshold={self.min_profit_threshold}, "
                         f"max_trade_amount={self.max_trade_amount}, symbols={self.symbols}, "
                         f"fee_pct={self.fee_pct}, threshold={self.threshold}")
        
    def on_tick(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a market data tick.
        
        Args:
            market_data: Market data dictionary containing symbol, bid, and ask prices
            
        Returns:
            List of signal dictionaries
        """
        # Initialize empty signals list
        signals = []
        self.logger.debug(f"Received tick: {market_data}")
        
        symbol = market_data.get("symbol")
        if symbol not in self.symbols:
            return
            
        self.logger.debug(f"Processing tick for {symbol}")
        
        # Update price cache with latest bid/ask prices
        bid = market_data.get("bid")
        ask = market_data.get("ask")
        
        if bid is None or ask is None:
            self.logger.warning(f"Missing bid or ask price for {symbol}")
            return
            
        self.price_cache[symbol] = {"bid": bid, "ask": ask}
        
        # Generate features and get prediction
        features = self.feature_engineer.generate_tick_features(market_data)
        prediction = self.model_manager.predict(features)
        self.last_prediction = prediction  # Store latest prediction
        self.logger.debug(f"Symbol: {symbol}, Features: {features}, Prediction: {prediction}")
        
        # Check if we have prices for all required symbols for triangular arbitrage
        if self._has_all_required_prices():
            signals.extend(self._check_triangular_arbitrage())
        
        return signals
        
    def _has_all_required_prices(self) -> bool:
        """Check if we have prices for all required symbols for triangular arbitrage.
        
        For triangular arbitrage, we need prices for all three pairs in the triangle.
        For example, BTC/USDT, ETH/USDT, and ETH/BTC.
        
        Returns:
            bool: True if we have all required prices, False otherwise
        """
        # Check if we have at least 3 symbols (required for triangular arbitrage)
        if len(self.symbols) < 3:
            return False
            
        # Check if we have prices for all symbols
        for symbol in self.symbols:
            if symbol not in self.price_cache:
                return False
                
        return True
    
    def _parse_symbol(self, symbol: str) -> tuple[str, str]:
        """Parse a symbol into base and quote currencies.
        
        Args:
            symbol: Symbol in format "BASE/QUOTE"
            
        Returns:
            Tuple of (base_currency, quote_currency)
        """
        parts = symbol.split('/')
        if len(parts) != 2:
            self.logger.warning(f"Invalid symbol format: {symbol}")
            return None, None
        return parts[0], parts[1]
    
    def _find_triangles(self) -> list[tuple[str, str, str]]:
        """Find all valid triangular arbitrage paths from available symbols.
        
        A valid triangle consists of three trading pairs that form a closed loop.
        For example, BTC/USDT, ETH/BTC, ETH/USDT forms a valid triangle.
        
        Returns:
            List of tuples, each containing three symbols forming a valid triangle
        """
        if len(self.symbols) < 3:
            return []
            
        # Create a dictionary of all currencies and their trading pairs
        currencies = {}
        for symbol in self.symbols:
            base, quote = self._parse_symbol(symbol)
            if base is None or quote is None:
                continue
                
            if base not in currencies:
                currencies[base] = set()
            if quote not in currencies:
                currencies[quote] = set()
                
            currencies[base].add(quote)
            currencies[quote].add(base)
            
        # Find all valid triangles
        triangles = []
        for symbol in self.symbols:
            base1, quote1 = self._parse_symbol(symbol)
            if base1 is None or quote1 is None:
                continue
                
            # Find all currencies that can be traded with base1
            if base1 in currencies:
                for currency in currencies[base1]:
                    if currency == quote1:
                        continue
                        
                    # Check if we can form a triangle
                    if quote1 in currencies and currency in currencies[quote1]:
                        # Find the actual symbols for the other two legs
                        symbol2 = None
                        symbol3 = None
                        
                        for s in self.symbols:
                            s_base, s_quote = self._parse_symbol(s)
                            if s_base is None or s_quote is None:
                                continue
                                
                            if (s_base == currency and s_quote == base1) or (s_base == base1 and s_quote == currency):
                                symbol2 = s
                            elif (s_base == currency and s_quote == quote1) or (s_base == quote1 and s_quote == currency):
                                symbol3 = s
                                
                        if symbol2 and symbol3 and (symbol, symbol2, symbol3) not in triangles:
                            triangles.append((symbol, symbol2, symbol3))
                            
        return triangles
    
    def _get_leg_details(self, triangle: tuple[str, str, str], from_currency: str, to_currency: str) -> tuple[str, str]:
        """Determine the symbol and side for a leg of the arbitrage path.
        
        Args:
            triangle: Tuple of three symbols forming a triangle
            from_currency: Currency to trade from
            to_currency: Currency to trade to
            
        Returns:
            Tuple of (symbol, side) where side is "buy" or "sell"
        """
        for symbol in triangle:
            base, quote = self._parse_symbol(symbol)
            if base is None or quote is None:
                continue
                
            if base == from_currency and quote == to_currency:
                # Selling the base currency for the quote currency
                return symbol, "sell"
            elif base == to_currency and quote == from_currency:
                # Buying the base currency with the quote currency
                return symbol, "buy"
                
        return None, None
    
    def _check_path(self, triangle: tuple[str, str, str], start_currency: str, middle_currency: str, end_currency: str) -> List[Dict[str, Any]]:
        """Check if a specific path through a triangle is profitable.
        
        Args:
            triangle: Tuple of three symbols forming a triangle
            start_currency: Currency to start the path with
            middle_currency: Second currency in the path
            end_currency: Third currency in the path
            
        Returns:
            List of signal dictionaries
        """
        # Initialize empty signals list
        signals = []
        # Determine the symbols and sides for each leg of the path
        leg1_symbol, leg1_side = self._get_leg_details(triangle, start_currency, middle_currency)
        leg2_symbol, leg2_side = self._get_leg_details(triangle, middle_currency, end_currency)
        leg3_symbol, leg3_side = self._get_leg_details(triangle, end_currency, start_currency)
        
        if not leg1_symbol or not leg2_symbol or not leg3_symbol:
            return signals
            
        # Get the prices for each leg
        if leg1_side == "buy":
            leg1_price = self.price_cache[leg1_symbol]["ask"]
        else:
            leg1_price = self.price_cache[leg1_symbol]["bid"]
            
        if leg2_side == "buy":
            leg2_price = self.price_cache[leg2_symbol]["ask"]
        else:
            leg2_price = self.price_cache[leg2_symbol]["bid"]
            
        if leg3_side == "buy":
            leg3_price = self.price_cache[leg3_symbol]["ask"]
        else:
            leg3_price = self.price_cache[leg3_symbol]["bid"]
            
        # Calculate the profit for this path
        initial_amount = 100  # Start with 100 units of start_currency
        
        # Leg 1: start_currency -> middle_currency
        if leg1_side == "buy":
            middle_amount = initial_amount / leg1_price
        else:
            middle_amount = initial_amount * leg1_price
        middle_amount *= (1 - self.fee_pct)  # Apply fee
        
        # Leg 2: middle_currency -> end_currency
        if leg2_side == "buy":
            end_amount = middle_amount / leg2_price
        else:
            end_amount = middle_amount * leg2_price
        end_amount *= (1 - self.fee_pct)  # Apply fee
        
        # Leg 3: end_currency -> start_currency
        if leg3_side == "buy":
            final_amount = end_amount / leg3_price
        else:
            final_amount = end_amount * leg3_price
        final_amount *= (1 - self.fee_pct)  # Apply fee
        
        # Calculate profit percentage
        profit_pct = (final_amount - initial_amount) / initial_amount
        
        # If profitable, log and create signals
        # Define prediction threshold (could be from config)
        prediction_threshold = self.config.get('prediction_threshold', 0.6)
        
        if profit_pct > self.min_profit_threshold:
            path_str = f"{start_currency}->{middle_currency}->{end_currency}->{start_currency}"
            self.logger.info(f"Triangular arbitrage opportunity detected ({path_str}): "
                            f"Profit: {profit_pct:.4f} ({final_amount-initial_amount:.2f} {start_currency})")
            self.logger.info(f"Prices: {leg1_symbol}={leg1_price}, {leg2_symbol}={leg2_price}, {leg3_symbol}={leg3_price}")
            self.logger.info(f"Potential arbitrage opportunity found for path {path_str}. Profit: {profit_pct:.4f}. Prediction: {self.last_prediction}")
            
            # Check if prediction meets threshold
            if self.last_prediction is not None and self.last_prediction > prediction_threshold:
                self.logger.info(f"Prediction {self.last_prediction} > threshold {prediction_threshold}. Proceeding with signals.")
                
                # Create and send signals if execution handler is available
                if self.execution_handler:
                    # Calculate trade amount (use initial_amount as base)
                    base_amount = min(initial_amount, self.max_trade_amount)
                    
                    # Signal 1
                    signal1 = {
                        "strategy_id": self.strategy_id,
                        "symbol": leg1_symbol,
                        "side": leg1_side,
                        "quantity": base_amount if leg1_side == "sell" else base_amount / leg1_price,
                        "order_type": "MARKET",
                        "timestamp": None,  # Will be filled by execution handler
                        "params": {
                            "arbitrage_leg": 1,
                            "arbitrage_path": path_str
                        }
                    }
                    self.logger.info(f"Creating signal for leg 1: {leg1_side.capitalize()} {leg1_symbol}")
                    signals.append(signal1)
                    
                    # In backtesting, we assume the order would be filled
                    # Calculate amount for leg 2
                    if leg1_side == "buy":
                        middle_amount = base_amount / leg1_price * (1 - self.fee_pct)
                    else:
                        middle_amount = base_amount * leg1_price * (1 - self.fee_pct)
                    
                    # Signal 2
                    signal2 = {
                        "strategy_id": self.strategy_id,
                        "symbol": leg2_symbol,
                        "side": leg2_side,
                        "quantity": middle_amount if leg2_side == "sell" else middle_amount / leg2_price,
                        "order_type": "MARKET",
                        "timestamp": None,
                        "params": {
                            "arbitrage_leg": 2,
                            "arbitrage_path": path_str
                        }
                    }
                    self.logger.info(f"Creating signal for leg 2: {leg2_side.capitalize()} {leg2_symbol}")
                    signals.append(signal2)
                    
                    # In backtesting, we assume the order would be filled
                    # Calculate amount for leg 3
                    if leg2_side == "buy":
                        end_amount = middle_amount / leg2_price * (1 - self.fee_pct)
                    else:
                        end_amount = middle_amount * leg2_price * (1 - self.fee_pct)
                    
                    # Signal 3
                    signal3 = {
                        "strategy_id": self.strategy_id,
                        "symbol": leg3_symbol,
                        "side": leg3_side,
                        "quantity": end_amount if leg3_side == "sell" else end_amount / leg3_price,
                        "order_type": "MARKET",
                        "timestamp": None,
                        "params": {
                            "arbitrage_leg": 3,
                            "arbitrage_path": path_str
                        }
                    }
                    self.logger.info(f"Creating signal for leg 3: {leg3_side.capitalize()} {leg3_symbol}")
                    signals.append(signal3)
            else:
                self.logger.info(f"Skipping signals for path {path_str} due to prediction {self.last_prediction} <= threshold {prediction_threshold}.")
        
        return signals
    
    def _check_triangular_arbitrage(self) -> List[Dict[str, Any]]:
        """Check for triangular arbitrage opportunities.
        
        This method dynamically identifies all valid triangular arbitrage paths
        from the available symbols and checks if there's a profitable opportunity
        using the current prices in the price cache.
        
        For each triangle, it checks both possible paths:
        1. A -> B -> C -> A
        2. A -> C -> B -> A
        
        If the final amount is greater than the initial amount (after fees),
        then there's a profitable arbitrage opportunity.
        
        Returns:
            List of signal dictionaries
        """
        # Initialize empty signals list
        signals = []
        # Find all valid triangles
        triangles = self._find_triangles()
        
        for triangle in triangles:
            # Check if we have prices for all symbols in the triangle
            if not all(symbol in self.price_cache for symbol in triangle):
                continue
                
            symbol1, symbol2, symbol3 = triangle
            
            # Parse the symbols to get the currencies
            base1, quote1 = self._parse_symbol(symbol1)
            base2, quote2 = self._parse_symbol(symbol2)
            base3, quote3 = self._parse_symbol(symbol3)
            
            if base1 is None or quote1 is None or base2 is None or quote2 is None or base3 is None or quote3 is None:
                continue
                
            # Determine the unique currencies in this triangle
            currencies = set([base1, quote1, base2, quote2, base3, quote3])
            
            # We should have exactly 3 unique currencies for a valid triangle
            if len(currencies) != 3:
                continue
                
            # Try all possible paths through the triangle
            # Each currency can be a starting point
            for start_currency in currencies:
                # Find the other two currencies
                other_currencies = [c for c in currencies if c != start_currency]
                
                # Try both possible paths
                signals.extend(self._check_path(triangle, start_currency, other_currencies[0], other_currencies[1]))
                signals.extend(self._check_path(triangle, start_currency, other_currencies[1], other_currencies[0]))
            
        return signals
    
    def on_order_update(self, order_update: Dict[str, Any]) -> None:
        """Process an order update.
        
        Args:
            order_update: Order update dictionary
        """
        self.logger.debug(f"Received order update: {order_update}")
        
        # In a real implementation, this would update the strategy's state
        # based on the order status
        order_id = order_update.get("order_id")
        status = order_update.get("status")
        
        self.logger.info(f"Order {order_id} status updated to {status}")
        
    def on_trade(self, trade: Dict[str, Any]) -> None:
        """Process a trade update.
        
        This method is called whenever a new trade is received. It updates the latest price
        for the traded symbol and checks for triangular arbitrage opportunities.
        If an opportunity is found, it generates a signal and emits it via the callback.
        
        Args:
            trade: Trade data dictionary containing at least 'symbol' and 'price'
        """
        # Enhanced logging at the beginning
        self.logger.info(f"on_trade received: {trade.get('symbol')} at price {trade.get('price')}")
        
        symbol = trade.get('symbol')
        price = trade.get('price')
        
        if not symbol or price is None:
            self.logger.warning(f"Received trade data missing symbol or price: {trade}")
            return
            
        if symbol not in self.symbols:
            self.logger.info(f"Symbol {symbol} not in configured symbols {self.symbols}, ignoring")
            return
            
        # Update latest price for this symbol
        self.latest_prices[symbol] = price
        # Enhanced logging after updating price
        self.logger.info(f"Updated latest_prices: {self.latest_prices}")
        
        # Check if we have prices for all required symbols
        if all(price is not None for price in self.latest_prices.values()):
            self.logger.info(f"Have prices for all symbols, checking for arbitrage opportunities")
            # This will generate and emit signals if opportunities are found
            self._check_triangular_arbitrage_from_trades()
        else:
            missing_prices = [s for s, p in self.latest_prices.items() if p is None]
            self.logger.info(f"Still missing prices for: {missing_prices}")
    
    def _check_triangular_arbitrage_from_trades(self) -> None:
        """Check for triangular arbitrage opportunities using latest trade prices.
        
        This method checks for triangular arbitrage opportunities using the latest trade prices.
        It implements two paths:
        1. USDT -> ETH -> BTC -> USDT
        2. USDT -> BTC -> ETH -> USDT
        
        Added detailed logging to diagnose why no trades are being made.
        
        If a profitable opportunity is found, it generates a signal and emits it via the callback.
        """
        # Add debug logging at the beginning
        self.logger.debug("Performing arbitrage check...")
        
        # Check if we have the required symbols for triangular arbitrage
        required_symbols = ['BTC/USDT', 'ETH/USDT', 'ETH/BTC']
        self.logger.info(f"Checking for required symbols: {required_symbols}")
        self.logger.info(f"Configured symbols: {self.symbols}")
        self.logger.info(f"Latest prices: {self.latest_prices}")
        
        # Verify all required symbols are in our configuration
        missing_from_config = [s for s in required_symbols if s not in self.symbols]
        if missing_from_config:
            self.logger.error(f"Missing required symbols in configuration: {missing_from_config}")
            return
            
        # Verify we have prices for all required symbols
        missing_prices = [s for s in required_symbols if s not in self.latest_prices]
        if missing_prices:
            self.logger.warning(f"Missing prices for required symbols: {missing_prices}")
            return
            
        self.logger.info(f"All required symbols have prices, proceeding with arbitrage check")
            
        try:
            # Path 1: USDT -> ETH -> BTC -> USDT
            # Step 1: Buy ETH with USDT
            eth_amount = 1.0 / self.latest_prices['ETH/USDT']
            # Step 2: Sell ETH for BTC
            btc_amount = eth_amount * self.latest_prices['ETH/BTC']
            # Step 3: Sell BTC for USDT
            final_usdt = btc_amount * self.latest_prices['BTC/USDT']
            # Calculate profit percentage
            profit_pct = (final_usdt - 1.0) / 1.0
            
            # Enhanced logging for profit percentage and threshold comparison
            self.logger.info(f"Path 1 Profit: {profit_pct:.6%}, Threshold: {self.threshold:.6%}, Profitable: {profit_pct > self.threshold}")
            self.logger.info(f"  Steps: 1 USDT -> {eth_amount:.8f} ETH -> {btc_amount:.8f} BTC -> {final_usdt:.8f} USDT")
            
            if profit_pct > self.threshold:
                self.logger.info(f"Arbitrage Opportunity (Path 1): USDT->ETH->BTC->USDT, Profit: {profit_pct:.4%}, EXCEEDS threshold {self.threshold:.6%}")
                
                # Calculate quantities for each leg
                base_usdt_qty = 10.0  # Example fixed amount
                eth_qty = base_usdt_qty / self.latest_prices['ETH/USDT']
                btc_qty = eth_qty * self.latest_prices['ETH/BTC']
                
                # Generate signal
                signal = {
                    'type': 'signal',
                    'strategy_id': self.strategy_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'actions': [
                        {'symbol': 'ETH/USDT', 'side': 'buy', 'type': 'market', 'quantity': eth_qty},
                        {'symbol': 'ETH/BTC', 'side': 'sell', 'type': 'market', 'quantity': eth_qty},
                        {'symbol': 'BTC/USDT', 'side': 'sell', 'type': 'market', 'quantity': btc_qty},
                    ]
                }
                
                self.logger.info(f"Generated Signal: {signal}")
                
                # Emit signal via callback if available
                if self.signal_callback:
                    self.logger.info(f"Signal callback is available, attempting to send signal")
                    if asyncio.iscoroutinefunction(self.signal_callback):
                        # We're in an async context, so we need to await the callback
                        # Since on_trade is not async, we need to create a task
                        try:
                            self.logger.info(f"Signal callback is a coroutine function, creating task")
                            loop = asyncio.get_event_loop()
                            loop.create_task(self.signal_callback(signal))
                            self.logger.info(f"Created task for async signal callback")
                        except RuntimeError as e:
                            self.logger.error(f"No event loop running - cannot emit signal asynchronously: {e}")
                    else:
                        # Synchronous callback
                        self.logger.info(f"Signal callback is synchronous, calling directly")
                        try:
                            self.signal_callback(signal)
                            self.logger.info(f"Successfully called signal callback")
                        except Exception as e:
                            self.logger.error(f"Error calling signal callback: {e}")
                else:
                    self.logger.warning(f"No signal callback available, cannot send signal")
            
            # Path 2: USDT -> BTC -> ETH -> USDT
            # Step 1: Buy BTC with USDT
            btc_amount = 1.0 / self.latest_prices['BTC/USDT']
            # Step 2: Buy ETH with BTC
            eth_amount = btc_amount / self.latest_prices['ETH/BTC']
            # Step 3: Sell ETH for USDT
            final_usdt = eth_amount * self.latest_prices['ETH/USDT']
            # Calculate profit percentage
            profit_pct = (final_usdt - 1.0) / 1.0
            
            # Enhanced logging for profit percentage and threshold comparison
            self.logger.info(f"Path 2 Profit: {profit_pct:.6%}, Threshold: {self.threshold:.6%}, Profitable: {profit_pct > self.threshold}")
            self.logger.info(f"  Steps: 1 USDT -> {btc_amount:.8f} BTC -> {eth_amount:.8f} ETH -> {final_usdt:.8f} USDT")
            
            if profit_pct > self.threshold:
                self.logger.info(f"Arbitrage Opportunity (Path 2): USDT->BTC->ETH->USDT, Profit: {profit_pct:.4%}, EXCEEDS threshold {self.threshold:.6%}")
                
                # Calculate quantities for each leg
                base_usdt_qty = 10.0  # Example fixed amount
                btc_qty = base_usdt_qty / self.latest_prices['BTC/USDT']
                eth_qty = btc_qty / self.latest_prices['ETH/BTC']
                
                # Generate signal
                signal = {
                    'type': 'signal',
                    'strategy_id': self.strategy_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'actions': [
                        {'symbol': 'BTC/USDT', 'side': 'buy', 'type': 'market', 'quantity': btc_qty},
                        {'symbol': 'ETH/BTC', 'side': 'buy', 'type': 'market', 'quantity': eth_qty},
                        {'symbol': 'ETH/USDT', 'side': 'sell', 'type': 'market', 'quantity': eth_qty},
                    ]
                }
                
                self.logger.info(f"Generated Signal: {signal}")
                
                # Emit signal via callback if available
                if self.signal_callback:
                    import asyncio
                    if asyncio.iscoroutinefunction(self.signal_callback):
                        asyncio.create_task(self.signal_callback(signal))
                    else:
                        self.signal_callback(signal)
                
        except ZeroDivisionError:
            self.logger.warning("Zero price detected in arbitrage calculation")
        except Exception as e:
            self.logger.error(f"Error in triangular arbitrage calculation: {e}")
    
    def on_error(self, error_data: Dict[str, Any]) -> None:
        """Process an error.
        
        Args:
            error_data: Error data dictionary
        """
        self.logger.error(f"Error occurred: {error_data}")
        
        # In a real implementation, this would handle the error appropriately
        # For example, by cancelling open orders or adjusting the strategy's state
        error_type = error_data.get("type")
        error_message = error_data.get("message")
        
        self.logger.error(f"Error type: {error_type}, message: {error_message}")


# Register the strategy with the registry
register_strategy("simple_arbitrage", SimpleArbitrageStrategy)