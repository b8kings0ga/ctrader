"""Order manager for ctrader execution engine."""

from typing import Any, Dict, List, Optional, Union

from src.exchange.binance_connector import OrderRequest, OrderResponse, binance_connector
from src.utils.config import config_manager
from src.utils.logger import get_logger


class OrderManager:
    """Order manager for handling order lifecycle.
    
    This class is responsible for creating, canceling, and tracking orders.
    It maintains a local state of active orders and interacts with the exchange connector.
    
    Attributes:
        config: Configuration manager
        logger: Logger instance
        exchange_connector: Exchange connector instance
        active_orders: Dictionary of active orders keyed by order_id
    """
    
    def __init__(
        self,
        config=None,
        logger=None,
        exchange_connector=None,
    ):
        """Initialize the order manager.
        
        Args:
            config: Configuration manager (default: global config_manager)
            logger: Logger instance (default: create new logger)
            exchange_connector: Exchange connector instance (default: global binance_connector)
        """
        self.config = config or config_manager
        self.logger = logger or get_logger("execution.order_manager")
        self.exchange_connector = exchange_connector or binance_connector
        
        # Dictionary to track active orders: {order_id: order_data}
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("Order manager initialized")
        
    def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        quantity: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Create an order on the exchange.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            side: Order side ("buy" or "sell")
            type: Order type ("limit", "market", etc.)
            quantity: Order quantity
            price: Order price (required for limit orders)
            params: Additional parameters for the order
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            # Create order request
            order_request = OrderRequest(
                symbol=symbol,
                side=side,
                type=type,
                amount=quantity,
                price=price,
                params=params or {},
            )
            
            # Submit order to exchange
            self.logger.info(f"Creating {side} {type} order for {quantity} {symbol} at price {price}")
            order_response = self.exchange_connector.create_order(order_request)
            
            # Store order in local state
            self.active_orders[order_response.id] = order_response.dict()
            
            self.logger.info(f"Order created successfully: {order_response.id}")
            return order_response.id
            
        except Exception as e:
            self.logger.error(f"Error creating order: {e}")
            return None
            
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order on the exchange.
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading pair symbol
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        try:
            self.logger.info(f"Cancelling order {order_id} for {symbol}")
            result = self.exchange_connector.cancel_order(order_id, symbol)
            
            # Remove from active orders if cancellation was successful
            if order_id in self.active_orders:
                del self.active_orders[order_id]
                
            self.logger.info(f"Order {order_id} cancelled successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False
            
    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get the status of an order.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            Order status data
        """
        try:
            # Check local cache first
            if order_id in self.active_orders:
                self.logger.debug(f"Returning cached order status for {order_id}")
                return self.active_orders[order_id]
                
            # Fetch from exchange if not in cache
            self.logger.debug(f"Fetching order status for {order_id} from exchange")
            order_data = self.exchange_connector.get_order(order_id, symbol)
            
            # Update local cache if order is still active
            if order_data.get("status") not in ["closed", "canceled", "expired", "rejected"]:
                self.active_orders[order_id] = order_data
            elif order_id in self.active_orders:
                del self.active_orders[order_id]
                
            return order_data
            
        except Exception as e:
            self.logger.error(f"Error getting order status for {order_id}: {e}")
            return {"error": str(e)}
            
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open orders.
        
        Args:
            symbol: Trading pair symbol (optional)
            
        Returns:
            List of open orders
        """
        try:
            self.logger.debug(f"Fetching open orders for {symbol if symbol else 'all symbols'}")
            open_orders = self.exchange_connector.get_open_orders(symbol)
            
            # Update local cache
            for order in open_orders:
                self.active_orders[order["id"]] = order
                
            return open_orders
            
        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return []
            
    def update_local_order_state(self, order_update: Dict[str, Any]) -> None:
        """Update the local order state based on an order update.
        
        Args:
            order_update: Order update data
        """
        order_id = order_update.get("id")
        if not order_id:
            self.logger.warning(f"Received order update without order ID: {order_update}")
            return
            
        status = order_update.get("status")
        
        if status in ["closed", "canceled", "expired", "rejected"]:
            # Remove from active orders if it's no longer active
            if order_id in self.active_orders:
                self.logger.debug(f"Removing order {order_id} from active orders (status: {status})")
                del self.active_orders[order_id]
        else:
            # Update or add to active orders
            self.logger.debug(f"Updating local state for order {order_id} (status: {status})")
            self.active_orders[order_id] = order_update