"""Order manager for ctrader execution engine."""

from typing import Any, Dict, List, Optional, Union
import json

from src.exchange.binance_connector import OrderRequest, OrderResponse, binance_connector
from src.utils.config import config_manager
from src.utils.logger import get_logger
from src.database.utils import save_execution


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
            
            # Prepare execution data for database
            execution_data = {
                'order_id': order_response.id,
                'client_order_id': order_response.client_order_id if hasattr(order_response, 'client_order_id') else None,
                'symbol': symbol,
                'side': side,
                'type': type,
                'quantity_requested': quantity,
                'quantity_executed': 0.0,  # Initial execution quantity is 0
                'price': price,
                'status': 'new',
                'exchange_response': order_response.dict()
            }
            
            # Save execution to database
            try:
                save_execution(execution_data)
                self.logger.debug(f"Order execution saved to database: {order_response.id}")
            except Exception as db_e:
                self.logger.error(f"Failed to save execution to database: {db_e}", exc_info=True)
            
            self.logger.info(f"Order created successfully: {order_response.id}")
            return order_response.id
            
        except Exception as e:
            self.logger.error(f"Error creating order: {e}")
            
            # Save failed execution to database
            try:
                execution_data = {
                    'order_id': None,
                    'client_order_id': None,
                    'symbol': symbol,
                    'side': side,
                    'type': type,
                    'quantity_requested': quantity,
                    'price': price,
                    'status': 'error',
                    'exchange_response': str(e)
                }
                save_execution(execution_data)
                self.logger.debug("Failed order execution saved to database")
            except Exception as db_e:
                self.logger.error(f"Failed to save failed execution to database: {db_e}", exc_info=True)
                
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
                order_data = self.active_orders[order_id]
                del self.active_orders[order_id]
                
                # Save cancellation to database
                try:
                    execution_data = {
                        'order_id': order_id,
                        'symbol': symbol,
                        'side': order_data.get('side'),
                        'type': order_data.get('type'),
                        'quantity_requested': order_data.get('amount'),
                        'price': order_data.get('price'),
                        'status': 'canceled',
                        'exchange_response': json.dumps(result) if isinstance(result, dict) else str(result)
                    }
                    save_execution(execution_data)
                    self.logger.debug(f"Order cancellation saved to database: {order_id}")
                except Exception as db_e:
                    self.logger.error(f"Failed to save cancellation to database: {db_e}", exc_info=True)
                
            self.logger.info(f"Order {order_id} cancelled successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            
            # Save failed cancellation to database
            try:
                execution_data = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'status': 'cancel_error',
                    'exchange_response': str(e)
                }
                save_execution(execution_data)
                self.logger.debug(f"Failed cancellation saved to database: {order_id}")
            except Exception as db_e:
                self.logger.error(f"Failed to save failed cancellation to database: {db_e}", exc_info=True)
                
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
        
        # Prepare execution data for database
        try:
            execution_data = {
                'order_id': order_id,
                'symbol': order_update.get('symbol'),
                'side': order_update.get('side'),
                'type': order_update.get('type'),
                'quantity_requested': order_update.get('amount'),
                'quantity_executed': order_update.get('filled', 0.0),
                'price': order_update.get('price'),
                'average_fill_price': order_update.get('average', order_update.get('price')),
                'status': status.lower() if status else 'unknown',
                'exchange_response': json.dumps(order_update) if isinstance(order_update, dict) else str(order_update)
            }
            save_execution(execution_data)
            self.logger.debug(f"Order update saved to database: {order_id}, status: {status}")
        except Exception as db_e:
            self.logger.error(f"Failed to save order update to database: {db_e}", exc_info=True)
        
        if status in ["closed", "canceled", "expired", "rejected"]:
            # Remove from active orders if it's no longer active
            if order_id in self.active_orders:
                self.logger.debug(f"Removing order {order_id} from active orders (status: {status})")
                del self.active_orders[order_id]
        else:
            # Update or add to active orders
            self.logger.debug(f"Updating local state for order {order_id} (status: {status})")
            self.active_orders[order_id] = order_update
            
    async def place_order(self, action: dict) -> Optional[str]:
        """Place an order based on a validated action dictionary.
        
        Args:
            action: A dictionary containing order details (symbol, side, type, quantity)
            
        Returns:
            Order ID if successful, None otherwise
        """
        self.logger.info(f"OrderManager.place_order called with action: {action}")
        
        try:
            # Validate action has required fields
            required_fields = ['symbol', 'side', 'type', 'quantity']
            for field in required_fields:
                if field not in action:
                    self.logger.error(f"Action missing required field '{field}': {action}")
                    return None
            
            # Log detailed information about the order
            self.logger.info(f"Creating order: {action['side']} {action['quantity']} {action['symbol']} @ {action['type']}")
            
            # Create order request
            order_request = OrderRequest(
                symbol=action['symbol'],
                side=action['side'],
                type=action['type'],  # Assuming 'market' for now
                amount=action['quantity'],
                price=None  # Market orders don't need a price
            )
            
            # Log the exchange connector being used
            self.logger.info(f"Using exchange connector: {self.exchange_connector.__class__.__name__}")
            
            # Execute via connector
            self.logger.info(f"Calling exchange_connector.create_order_async with request: {order_request}")
            try:
                order_response = await self.exchange_connector.create_order_async(order_request)
                self.logger.info(f"Order placed successfully: {order_response}")
                
                # Store order details in database
                try:
                    execution_data = {
                        'order_id': order_response.id,
                        'symbol': action['symbol'],
                        'side': action['side'],
                        'type': action['type'],
                        'quantity_requested': action['quantity'],
                        'status': 'new',
                        'exchange_response': order_response.dict() if hasattr(order_response, 'dict') else str(order_response)
                    }
                    save_execution(execution_data)
                    self.logger.info(f"Order execution saved to database: {order_response.id}")
                except Exception as db_e:
                    self.logger.error(f"Failed to save execution to database: {db_e}")
                
                return order_response.id
            except Exception as order_e:
                self.logger.error(f"Error from exchange when creating order: {order_e}")
                raise
            
        except Exception as e:
            self.logger.error(f"Failed to place order for action {action}: {e}", exc_info=True)
            return None