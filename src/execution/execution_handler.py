"""Execution handler for ctrader execution engine."""

from typing import Any, Dict, Optional

from src.execution.order_manager import OrderManager
from src.execution.signal_aggregator import SignalAggregator
from src.risk.risk_manager import RiskManager
from src.utils.config import config_manager
from src.utils.logger import get_logger


class ExecutionHandler:
    """Execution handler for processing signals and creating orders.
    
    This class is responsible for translating trading signals into orders.
    It coordinates between the signal aggregator, risk manager, and order manager.
    
    Attributes:
        config: Configuration manager
        logger: Logger instance
        order_manager: Order manager instance
        signal_aggregator: Signal aggregator instance
        risk_manager: Risk manager instance
    """
    
    def __init__(
        self,
        config=None,
        logger=None,
        order_manager=None,
        signal_aggregator=None,
        risk_manager=None,
    ):
        """Initialize the execution handler.
        
        Args:
            config: Configuration manager (default: global config_manager)
            logger: Logger instance (default: create new logger)
            order_manager: Order manager instance (default: create new instance)
            signal_aggregator: Signal aggregator instance (default: create new instance)
            risk_manager: Risk manager instance (default: create new instance)
        """
        self.config = config or config_manager
        self.logger = logger or get_logger("execution.execution_handler")
        
        # Initialize components if not provided
        self.order_manager = order_manager or OrderManager(config=self.config)
        self.signal_aggregator = signal_aggregator or SignalAggregator(config=self.config)
        self.risk_manager = risk_manager or RiskManager(config=self.config)
        
        # Load execution configuration
        self.execution_config = self.config.get("execution", {})
        self.default_order_type = self.execution_config.get("default_order_type", "LIMIT")
        
        self.logger.info("Execution handler initialized")
        
    def handle_signal(self, signal_data: Dict[str, Any]) -> Optional[str]:
        """Handle a trading signal.
        
        This method processes a signal through the signal aggregator,
        checks risk criteria, and creates an order if appropriate.
        
        Args:
            signal_data: Signal data dictionary
            
        Returns:
            Order ID if an order was created, None otherwise
        """
        self.logger.info(f"Handling signal: {signal_data}")
        
        # Process signal through aggregator
        processed_signal = self.signal_aggregator.process_signal(signal_data)
        
        # Check for errors in signal processing
        if "error" in processed_signal:
            self.logger.error(f"Error processing signal: {processed_signal['error']}")
            return None
            
        # Translate signal to order parameters
        order_params = self._translate_signal_to_order(processed_signal)
        
        # Check risk criteria
        if not self.risk_manager.check_order_risk(order_params):
            self.logger.warning(f"Signal rejected due to risk criteria: {signal_data}")
            return None
            
        # Create order
        order_id = self.order_manager.create_order(
            symbol=order_params["symbol"],
            side=order_params["side"],
            type=order_params["type"],
            quantity=order_params["quantity"],
            price=order_params.get("price"),
            params=order_params.get("params", {}),
        )
        
        if order_id:
            self.logger.info(f"Created order {order_id} from signal")
        else:
            self.logger.error("Failed to create order from signal")
            
        return order_id
        
    def _translate_signal_to_order(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a signal into order parameters.
        
        Args:
            signal_data: Signal data dictionary
            
        Returns:
            Order parameters dictionary
        """
        # Extract basic parameters from signal
        symbol = signal_data["symbol"]
        side = signal_data["side"]
        
        # Determine order type (default to LIMIT)
        order_type = signal_data.get("order_type", self.default_order_type)
        
        # Determine quantity based on signal strength or fixed amount
        quantity = signal_data.get("quantity", 0.0)
        if quantity <= 0.0 and "strength" in signal_data:
            # Scale quantity based on signal strength and max position size
            max_position = self.risk_manager.max_position_size
            quantity = max_position * signal_data["strength"]
            
        # Determine price for limit orders
        price = signal_data.get("price", None)
        
        # Prepare order parameters
        order_params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        
        if price is not None:
            order_params["price"] = price
            
        # Add any additional parameters from the signal
        if "params" in signal_data:
            order_params["params"] = signal_data["params"]
            
        self.logger.debug(f"Translated signal to order parameters: {order_params}")
        return order_params