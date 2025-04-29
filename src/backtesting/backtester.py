"""Backtester for ctrader."""

from typing import Dict, Any, Optional

from src.backtesting.data_replay import DataReplayEngine
from src.backtesting.market_simulator import MarketSimulator
from src.backtesting.performance import PerformanceAnalyzer
from src.strategies.base_strategy import BaseStrategy
from src.utils.config import config_manager
from src.utils.logger import get_logger


class Backtester:
    """Backtester for running trading strategies against historical data.
    
    This class orchestrates the backtesting process, coordinating between
    the data replay engine, market simulator, strategy, and performance analyzer.
    
    Attributes:
        config: Configuration manager
        logger: Logger instance
        strategy: Trading strategy to backtest
        data_replay_engine: Data replay engine
        market_simulator: Market simulator
        performance_analyzer: Performance analyzer
    """
    
    def __init__(
        self,
        config=None,
        logger=None,
        strategy=None,
        data_replay_engine=None,
        market_simulator=None,
        performance_analyzer=None,
    ):
        """Initialize the backtester.
        
        Args:
            config: Configuration manager (default: global config_manager)
            logger: Logger instance (default: create new logger)
            strategy: Trading strategy to backtest
            data_replay_engine: Data replay engine (default: create new instance)
            market_simulator: Market simulator (default: create new instance)
            performance_analyzer: Performance analyzer (default: create new instance)
        """
        self.config = config or config_manager
        self.logger = logger or get_logger("backtesting.backtester")
        
        # Ensure a strategy is provided
        if strategy is None:
            raise ValueError("A strategy must be provided for backtesting")
        self.strategy = strategy
        
        # Initialize components if not provided
        self.data_replay_engine = data_replay_engine or DataReplayEngine(config=self.config)
        self.market_simulator = market_simulator or MarketSimulator(config=self.config)
        self.performance_analyzer = performance_analyzer or PerformanceAnalyzer(config=self.config)
        
        # Load backtesting configuration
        self.backtesting_config = self.config.get("backtesting", {})
        
        self.logger.info("Backtester initialized")
        
    def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str,
    ) -> Dict[str, Any]:
        """Run the backtesting process.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            timeframe: Timeframe for the data (e.g., "1m", "1h", "1d")
            
        Returns:
            Dictionary containing backtest results
        """
        self.logger.info(
            f"Starting backtest for {symbol} from {start_date} to {end_date} "
            f"with timeframe {timeframe}"
        )
        
        # Step 1: Load historical data
        self.logger.info("Loading historical data...")
        historical_data = self.data_replay_engine.load_historical_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
        )
        
        # Step 2: Initialize strategy
        self.logger.info("Initializing strategy...")
        self.strategy.initialize()
        
        # Step 3: Replay data and process each tick
        self.logger.info("Starting data replay and strategy execution...")
        for tick_data in self.data_replay_engine.replay_data(historical_data):
            # Process the tick in the market simulator
            self.logger.debug(f"Processing tick: {tick_data}")
            self.market_simulator.process_tick(tick_data)
            
            # Generate signals from the strategy
            self.logger.debug("Generating signals from strategy...")
            signals = self.strategy.on_tick(tick_data)
            
            # Process signals and simulate order execution
            for signal in signals:
                self.logger.debug(f"Processing signal: {signal}")
                
                # Convert signal to order parameters
                order_params = self._convert_signal_to_order_params(signal)
                
                # Simulate order execution
                filled_order = self.market_simulator.simulate_order_fill(order_params)
                
                # Record the trade
                trade_data = self._convert_order_to_trade(filled_order)
                self.performance_analyzer.record_trade(trade_data)
        
        # Step 4: Calculate performance metrics
        self.logger.info("Calculating performance metrics...")
        metrics = self.performance_analyzer.calculate_metrics()
        
        # Step 5: Return results
        results = {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "timeframe": timeframe,
            "strategy": self.strategy.__class__.__name__,
            "metrics": metrics,
        }
        
        self.logger.info(f"Backtest completed: {results}")
        return results
        
    def _convert_signal_to_order_params(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a strategy signal to order parameters.
        
        Args:
            signal: Signal data from the strategy
            
        Returns:
            Order parameters for the market simulator
        """
        # Basic conversion from signal to order parameters
        # In a real implementation, this would be more sophisticated
        order_params = {
            "symbol": signal.get("symbol", ""),
            "side": signal.get("side", ""),
            "type": signal.get("order_type", "MARKET"),
            "quantity": signal.get("quantity", 0.0),
        }
        
        if "price" in signal:
            order_params["price"] = signal["price"]
            
        return order_params
        
    def _convert_order_to_trade(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a filled order to a trade record.
        
        Args:
            order: Filled order data from the market simulator
            
        Returns:
            Trade data for the performance analyzer
        """
        # Basic conversion from order to trade record
        # In a real implementation, this would be more sophisticated
        trade = {
            "order_id": order.get("id", ""),
            "symbol": order.get("symbol", ""),
            "side": order.get("side", ""),
            "quantity": order.get("filled_quantity", 0.0),
            "price": order.get("filled_price", 0.0),
            "timestamp": order.get("timestamp", 0),
        }
        
        return trade