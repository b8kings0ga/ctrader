"""Base strategy class for ctrader."""

import abc
from typing import Any, Dict, List, Optional

from src.utils.config import config_manager
from src.utils.logger import get_logger


class BaseStrategy(abc.ABC):
    """Abstract base class for all trading strategies.
    
    This class defines the interface that all trading strategies must implement.
    It provides common functionality such as logging and configuration management.
    
    Attributes:
        strategy_id: Unique identifier for the strategy instance
        config: Strategy-specific configuration
        logger: Logger instance for the strategy
    """
    
    def __init__(self, strategy_id: str, strategy_config: Optional[Dict[str, Any]] = None, signal_callback=None):
        """Initialize the strategy.
        
        Args:
            strategy_id: Unique identifier for the strategy instance
            strategy_config: Strategy-specific configuration (overrides config from config_manager)
            signal_callback: Callback function to emit signals
        """
        self.strategy_id = strategy_id
        self.logger = get_logger(f"strategy.{self.__class__.__name__}.{strategy_id}")
        self.signal_callback = signal_callback
        
        # Get strategy config from config manager or use provided config
        strategy_type = self.__class__.__name__.lower()
        if strategy_type.endswith("strategy"):
            strategy_type = strategy_type[:-8]  # Remove "strategy" suffix
            
        self.config = config_manager.get("strategies", strategy_type, {})
        
        # Override with provided config if any
        if strategy_config:
            self.config.update(strategy_config)
            
        self.logger.info(f"Strategy {self.__class__.__name__} ({strategy_id}) initialized")
        
    @abc.abstractmethod
    def initialize(self, exchange_connector: Any, data_cache: Any, execution_handler: Any = None) -> None:
        """Initialize the strategy with required components.
        
        This method is called after the strategy is instantiated to provide
        access to the exchange connector and data cache.
        
        Args:
            exchange_connector: Exchange connector instance
            data_cache: Data cache instance
            execution_handler: Execution handler instance for processing signals
        """
        pass
        
    @abc.abstractmethod
    def on_tick(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a market data tick.
        
        This method is called whenever new market data is available.
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            List of signal dictionaries
        """
        pass
        
    @abc.abstractmethod
    def on_trade(self, trade: Dict[str, Any]) -> None:
        """Process a trade update.
        
        This method is called whenever a new trade is received.
        
        Args:
            trade: Trade data dictionary containing at least 'symbol' and 'price'
        """
        pass
        
    @abc.abstractmethod
    def on_order_update(self, order_update: Dict[str, Any]) -> None:
        """Process an order update.
        
        This method is called whenever an order status is updated.
        
        Args:
            order_update: Order update dictionary
        """
        pass
        
    @abc.abstractmethod
    def on_error(self, error_data: Dict[str, Any]) -> None:
        """Process an error.
        
        This method is called whenever an error occurs that is relevant to the strategy.
        
        Args:
            error_data: Error data dictionary
        """
        pass