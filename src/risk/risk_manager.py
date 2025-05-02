"""Risk manager for ctrader."""

from typing import Any, Dict, Optional

from src.utils.config import config_manager
from src.utils.logger import get_logger


class RiskManager:
    """Risk manager for checking order risk.
    
    This class is responsible for checking if orders meet risk criteria.
    Currently, it's a placeholder that always returns True.
    
    Attributes:
        config: Configuration manager
        logger: Logger instance
    """
    
    def __init__(
        self,
        config=None,
        logger=None,
    ):
        """Initialize the risk manager.
        
        Args:
            config: Configuration manager (default: global config_manager)
            logger: Logger instance (default: create new logger)
        """
        self.config = config or config_manager
        self.logger = logger or get_logger("risk.risk_manager")
        
        # Add debug logging for config type
        self.logger.info(f"RiskManager initialized with config type: {type(self.config)}")
        
        try:
            if hasattr(self.config, 'config'):
                self.logger.info("Config is a ConfigManager instance")
                # Load risk configuration
                try:
                    self.logger.info("Attempting to get risk configuration from ConfigManager")
                    self.logger.info(f"Type of 'risk' parameter: {type('risk')}")
                    self.logger.info(f"Value of 'risk' parameter: {'risk'}")
                    
                    # Get risk configuration with empty dict as default
                    self.risk_config = self.config.get("risk", None, {})
                    self.logger.info(f"Retrieved risk_config: {self.risk_config}")
                except Exception as e:
                    self.logger.error(f"Error getting risk configuration: {e}")
                    self.risk_config = {}
            else:
                self.logger.info("Config is a dictionary, not a ConfigManager instance")
                # If config is a dictionary, use it directly
                try:
                    self.logger.info("Attempting to get risk configuration from dictionary")
                    self.risk_config = self.config.get("risk", None, {}) if isinstance(self.config, dict) else {}
                    self.logger.info(f"Retrieved risk_config: {self.risk_config}")
                except Exception as e:
                    self.logger.error(f"Error getting risk configuration from dictionary: {e}")
                    self.risk_config = {}
            
            # Log the risk_config type
            self.logger.info(f"risk_config type: {type(self.risk_config)}")
        except Exception as e:
            self.logger.error(f"Error in RiskManager initialization: {e}")
            self.risk_config = {}
        try:
            self.logger.info("Loading risk parameters from risk_config")
            self.max_position_size = self.risk_config.get("max_position_size", 100)
            self.logger.info(f"max_position_size: {self.max_position_size}")
            
            self.max_open_positions = self.risk_config.get("max_open_positions", 3)
            self.logger.info(f"max_open_positions: {self.max_open_positions}")
            
            self.max_order_quantity = self.risk_config.get("max_order_quantity", 1.0)
            self.logger.info(f"max_order_quantity: {self.max_order_quantity}")
            
            self.stop_loss_percentage = self.risk_config.get("stop_loss_percentage", 0.01)
            self.logger.info(f"stop_loss_percentage: {self.stop_loss_percentage}")
            
            self.daily_loss_limit = self.risk_config.get("daily_loss_limit", 50)
            self.logger.info(f"daily_loss_limit: {self.daily_loss_limit}")
            
            self.max_order_value_usd = self.risk_config.get("max_order_value_usd", 100.0)
            self.logger.info(f"max_order_value_usd: {self.max_order_value_usd}")
            
            # Initialize position tracking dictionary
            self.logger.info("Initializing positions dictionary")
            self.positions = {}  # {symbol: current_position_size}
            self.logger.info(f"positions initialized: {self.positions}")
            
            self.logger.info("Risk manager initialized successfully")
            self.logger.debug(f"Risk parameters: max_position_size={self.max_position_size}, "
                             f"max_open_positions={self.max_open_positions}, "
                             f"max_order_quantity={self.max_order_quantity}, "
                             f"stop_loss_percentage={self.stop_loss_percentage}, "
                             f"daily_loss_limit={self.daily_loss_limit}, "
                             f"max_order_value_usd={self.max_order_value_usd}")
        except Exception as e:
            self.logger.error(f"Error initializing risk parameters: {e}")
            # Set default values
            self.max_position_size = 100
            self.max_open_positions = 3
            self.max_order_quantity = 1.0
            self.stop_loss_percentage = 0.01
            self.daily_loss_limit = 50
            self.max_order_value_usd = 100.0
            self.positions = {}
        
    def check_order_risk(self, order_params: Dict[str, Any]) -> bool:
        """Check if an order meets risk criteria.
        
        Implements basic risk checks:
        1. Check if the order quantity exceeds max_order_quantity
        2. Check if adding this position would exceed max_position_size
        
        Args:
            order_params: Order parameters dictionary containing at least:
                - symbol: Trading pair symbol
                - side: Order side ("buy" or "sell")
                - type: Order type ("limit", "market", etc.)
                - quantity: Order quantity
                - price: Order price (optional)
                
        Returns:
            True if the order meets risk criteria, False otherwise
        """
        self.logger.debug(f"Performing risk check for order: {order_params}")
        
        # Extract order parameters
        symbol = order_params.get("symbol")
        side = order_params.get("side", "").lower()
        quantity = order_params.get("quantity", 0.0)
        
        # Validate required parameters
        if not symbol or not side or quantity <= 0:
            self.logger.warning(f"Invalid order parameters: {order_params}")
            return False
        
        # Check 1: Max Order Quantity Check
        if quantity > self.max_order_quantity:
            self.logger.warning(
                f"Order quantity {quantity} exceeds max order quantity {self.max_order_quantity} for {symbol}"
            )
            return False
        
        # Check 2: Max Position Size Check
        current_position = self.positions.get(symbol, 0.0)
        
        # Calculate new position size based on order side
        new_position = current_position
        if side == "buy":
            new_position += quantity
        elif side == "sell":
            new_position -= quantity
        
        # Check if new position would exceed max position size
        if abs(new_position) > self.max_position_size:
            self.logger.warning(
                f"New position size {new_position} would exceed max position size {self.max_position_size} for {symbol}"
            )
            return False
        
        # All checks passed
        self.logger.info(f"Order passed risk checks: {order_params}")
        return True
        
    def update_position(self, symbol: str, quantity: float, side: str) -> None:
        """Update the position tracking for a symbol.
        
        Args:
            symbol: Trading pair symbol
            quantity: Order quantity
            side: Order side ("buy" or "sell")
        """
        current_position = self.positions.get(symbol, 0.0)
        
        if side.lower() == "buy":
            self.positions[symbol] = current_position + quantity
        elif side.lower() == "sell":
            self.positions[symbol] = current_position - quantity
            
        self.logger.debug(f"Updated position for {symbol}: {self.positions[symbol]}")
        
    def check_order(self, action: dict, latest_prices: dict) -> bool:
        """Check if a proposed order action is acceptable based on risk parameters.
        
        Args:
            action: Dictionary containing order action details with at least:
                - symbol: Trading pair symbol
                - quantity: Order quantity
                - side: Order side ("buy" or "sell")
            latest_prices: Dictionary mapping symbols to their latest prices
            
        Returns:
            True if the order is allowed, False otherwise
        """
        self.logger.info(f"RiskManager.check_order called with action: {action}")
        self.logger.info(f"latest_prices type: {type(latest_prices)}")
        self.logger.info(f"latest_prices content: {latest_prices}")
        
        # Extract order parameters
        symbol = action.get("symbol")
        self.logger.info(f"Symbol from action: {symbol}, type: {type(symbol)}")
        quantity = action.get("quantity", 0.0)
        side = action.get("side", "").lower()
        
        # Validate required parameters
        if not symbol or not side or quantity <= 0:
            self.logger.warning(f"Invalid order parameters: {action}")
            return False
        
        # Check if symbol is a dictionary (which would cause the unhashable type error)
        if isinstance(symbol, dict):
            self.logger.error(f"Symbol is a dictionary, which is unhashable: {symbol}")
            return False
            
        # Get the latest price for the symbol
        if symbol not in latest_prices:
            self.logger.warning(f"Cannot assess risk for {symbol}: price not available")
            return False
            
        price = latest_prices[symbol]
        self.logger.info(f"Price for {symbol}: {price}, type: {type(price)}")
        
        # If price is None, we can't proceed with risk calculation
        if price is None:
            self.logger.warning(f"Price for {symbol} is None, cannot calculate risk")
            return False
        
        # Extract base and quote currencies from symbol (e.g., "BTC-USDT" -> "BTC", "USDT")
        symbol_parts = symbol.split("-") if "-" in symbol else symbol.split("/")
        if len(symbol_parts) != 2:
            self.logger.warning(f"Invalid symbol format: {symbol}")
            return False
            
        quote_currency = symbol_parts[1]
        
        # Calculate estimated order value in USD
        estimated_usd_value = quantity * price
        
        # If quote currency is not USD/USDT/BUSD, we need conversion
        if not any(quote_currency.upper().startswith(usd) for usd in ["USD", "USDT", "BUSD"]):
            self.logger.warning(f"Cannot calculate USD value for {symbol}, allowing order for now.")
            return True
        
        # Check if the estimated USD value exceeds max_order_value_usd
        if estimated_usd_value > self.max_order_value_usd:
            # Add warning log with more details about the risk check failure
            self.logger.warning(f"Risk Check FAIL: Value {estimated_usd_value:.2f} > Max {self.max_order_value_usd:.2f}. Action: {action}")
            return False
        
        # All checks passed
        # Add debug log for successful risk check
        self.logger.debug(f"Risk Check PASS. Action: {action}")
        self.logger.info(f"Order passed risk checks: {action}")
        return True