"""Market simulator for backtesting."""

from typing import Dict, Any

from src.utils.config import config_manager
from src.utils.logger import get_logger


class MarketSimulator:
    """Market simulator for backtesting.
    
    This class simulates market behavior for backtesting purposes,
    including order execution and price information.
    
    Attributes:
        config: Configuration manager
        logger: Logger instance
    """
    
    def __init__(self, config=None, logger=None):
        """Initialize the market simulator.
        
        Args:
            config: Configuration manager (default: global config_manager)
            logger: Logger instance (default: create new logger)
        """
        self.config = config or config_manager
        self.logger = logger or get_logger("backtesting.market_simulator")
        
        # Load backtesting configuration
        self.backtesting_config = self.config.get("backtesting", {})
        
        # Initialize internal state
        self.current_tick = None
        self.order_id_counter = 0
        
        self.logger.info("Market simulator initialized")
        
    def process_tick(self, tick_data: Dict[str, Any]) -> None:
        """Process a market data tick.
        
        This method updates the internal state of the simulator
        with the latest market data.
        
        Args:
            tick_data: Dictionary containing tick data
        """
        self.logger.debug(f"Processing tick: {tick_data}")
        self.current_tick = tick_data
        
    def simulate_order_fill(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate order execution.
        
        This method simulates the execution of an order based on
        the current market state and order parameters.
        
        Args:
            order_params: Dictionary containing order parameters
            
        Returns:
            Dictionary containing filled order information
        """
        self.logger.info(f"Simulating order fill: {order_params}")
        
        # Generate a unique order ID
        self.order_id_counter += 1
        order_id = f"sim_{self.order_id_counter}"
        
        # Create a dummy filled order response
        filled_order = {
            "id": order_id,
            "status": "filled",
            "symbol": order_params.get("symbol", ""),
            "side": order_params.get("side", ""),
            "type": order_params.get("type", ""),
            "quantity": order_params.get("quantity", 0.0),
            "price": order_params.get("price", 0.0),
            "filled_quantity": order_params.get("quantity", 0.0),
            "filled_price": order_params.get("price", 0.0),
            "timestamp": 0,  # Would be set to a real timestamp in actual implementation
        }
        
        self.logger.info(f"Order {order_id} filled")
        return filled_order
        
    def get_current_market_price(self, symbol: str) -> float:
        """Get the current market price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            Current market price
        """
        self.logger.debug(f"Getting current market price for {symbol}")
        
        # In a real implementation, this would return the price from the current tick
        # For now, just return a dummy value
        return 0.0